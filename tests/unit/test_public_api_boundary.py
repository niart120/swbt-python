import asyncio
import builtins
import importlib
import importlib.util
import inspect
import json
import pkgutil
import subprocess
import sys
from dataclasses import fields
from io import StringIO
from typing import TYPE_CHECKING, Any, cast, get_args

import pytest

import swbt
from swbt import (
    ControllerColors,
    DiagnosticsConfig,
    InvalidInputError,
    JoyConL,
    JoyConR,
    ProController,
    SwitchGamepad,
)
from swbt.gamepad import ConnectionResult, ConnectionStatus
from swbt.gamepad import _config as gamepad_config
from swbt.gamepad import core as gamepad_core
from swbt.gamepad import runtime as gamepad_runtime
from swbt.gamepad import transport_factory as gamepad_transport_factory
from swbt.gamepad._config import _SwitchGamepadConfig
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import ProControllerProfile
from swbt.transport.base import BondedPeer, DisconnectRequestResult, HidDeviceTransport
from swbt.transport.fake import FakeHidTransport

if TYPE_CHECKING:
    from swbt.protocol.profiles.base import ControllerProfile


REARCHITECTURE_TARGET_XFAIL_REASON = (
    "target boundary fixed before implementation; unit_042 makes this green"
)


def test_public_api_import_does_not_import_bumble() -> None:
    code = """
import sys

import swbt
from swbt import SwitchGamepad

imported_bumble_modules = [
    module_name
    for module_name in sys.modules
    if module_name == "bumble" or module_name.startswith("bumble.")
]
assert swbt.SwitchGamepad is SwitchGamepad
if imported_bumble_modules:
    raise AssertionError(imported_bumble_modules)
"""

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


def test_public_api_import_does_not_resolve_bumble(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        global_vars: dict[str, object] | None = None,
        local_vars: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "bumble" or name.startswith("bumble."):
            msg = f"public API import resolved Bumble unexpectedly: {name}"
            raise AssertionError(msg)
        return original_import(name, global_vars, local_vars, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    __import__("swbt")


def test_only_bumble_transport_and_csr_harness_may_resolve_bumble(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        global_vars: dict[str, object] | None = None,
        local_vars: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "bumble" or name.startswith("bumble."):
            msg = f"unexpected Bumble import outside swbt.transport.bumble: {name}"
            raise AssertionError(msg)
        return original_import(name, global_vars, local_vars, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    for module in pkgutil.walk_packages(swbt.__path__, f"{swbt.__name__}."):
        if module.name in {
            "swbt.transport.bumble",
            "swbt.transport._csr_bd_addr_harness",
        }:
            continue
        importlib.import_module(module.name)


def test_switch_gamepad_signature_does_not_expose_bumble_types() -> None:
    signature = inspect.signature(SwitchGamepad)
    annotation_text = " ".join(
        repr(parameter.annotation) for parameter in signature.parameters.values()
    )

    assert "bumble" not in annotation_text.lower()


def test_rearchitecture_target_switch_gamepad_is_abstract_interface() -> None:
    assert inspect.isabstract(SwitchGamepad)

    with pytest.raises(TypeError):
        SwitchGamepad()


def test_rearchitecture_target_public_concrete_controllers_share_interface() -> None:
    for controller_name in ("ProController", "JoyConL", "JoyConR"):
        controller_cls = getattr(swbt, controller_name)

        assert issubclass(controller_cls, SwitchGamepad)


def test_reporting_types_and_direct_controllers_are_public_and_classified() -> None:
    periodic_type = swbt.PeriodicSwitchGamepad
    direct_type = swbt.DirectSwitchGamepad

    assert inspect.isabstract(periodic_type)
    assert inspect.isabstract(direct_type)
    assert issubclass(periodic_type, SwitchGamepad)
    assert issubclass(direct_type, SwitchGamepad)

    for controller_name in ("ProController", "JoyConL", "JoyConR"):
        controller_cls = getattr(swbt, controller_name)
        assert issubclass(controller_cls, periodic_type)
        assert not issubclass(controller_cls, direct_type)

    for controller_name in (
        "DirectProController",
        "DirectJoyConL",
        "DirectJoyConR",
    ):
        controller_cls = getattr(swbt, controller_name)
        assert controller_name in swbt.__all__
        assert issubclass(controller_cls, direct_type)
        assert not issubclass(controller_cls, periodic_type)
        assert not inspect.isabstract(controller_cls)


def test_reporting_types_expose_only_their_owned_full_state_operation() -> None:
    periodic_type = swbt.PeriodicSwitchGamepad
    direct_type = swbt.DirectSwitchGamepad

    assert hasattr(periodic_type, "apply")
    assert not hasattr(periodic_type, "send")
    assert hasattr(direct_type, "send")
    assert not hasattr(direct_type, "apply")

    for controller_name in ("ProController", "JoyConL", "JoyConR"):
        controller_cls = getattr(swbt, controller_name)
        assert hasattr(controller_cls, "apply")
        assert not hasattr(controller_cls, "send")
        assert "report_period_us" in inspect.signature(controller_cls).parameters

    for controller_name in (
        "DirectProController",
        "DirectJoyConL",
        "DirectJoyConR",
    ):
        controller_cls = getattr(swbt, controller_name)
        assert hasattr(controller_cls, "send")
        assert not hasattr(controller_cls, "apply")
        assert "report_period_us" not in inspect.signature(controller_cls).parameters
        assert "profile_path" in inspect.signature(controller_cls).parameters
        assert hasattr(controller_cls, "create_profile")
        assert "key_store_path" not in inspect.signature(controller_cls).parameters


def test_rearchitecture_target_public_controller_constructors_hide_config_identity_seams() -> None:
    common_parameters = {
        "adapter",
        "controller_colors",
        "diagnostics",
        "report_period_us",
    }
    forbidden_parameters = {"device_name", "profile", "transport"}

    pro_parameters = set(inspect.signature(ProController).parameters)
    assert common_parameters | {"profile_path"} <= pro_parameters
    assert (forbidden_parameters | {"key_store_path"}).isdisjoint(pro_parameters)

    for controller_name in ("JoyConL", "JoyConR"):
        controller_cls = getattr(swbt, controller_name)
        parameters = set(inspect.signature(controller_cls).parameters)

        assert common_parameters | {"profile_path"} <= parameters
        assert (forbidden_parameters | {"key_store_path"}).isdisjoint(parameters)


def test_rearchitecture_target_public_controller_constructors_hide_transport_seam() -> None:
    for controller_name in ("ProController", "JoyConL", "JoyConR"):
        controller_cls = getattr(swbt, controller_name)

        assert "transport" not in inspect.signature(controller_cls).parameters


def test_pro_controller_constructor_accepts_profile_path_instead_of_key_store_path() -> None:
    signature = inspect.signature(ProController)

    assert "profile_path" in signature.parameters
    assert "key_store_path" not in signature.parameters


def test_profileless_pro_controller_uses_native_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_config: dict[str, object] = {}
    expected_transport = FakeHidTransport()

    def fake_create_default_transport(
        *,
        adapter: str,
        device_name: str,
        profile: ProControllerProfile,
        diagnostics: object,
    ) -> HidDeviceTransport:
        captured_config.update(
            {
                "adapter": adapter,
                "device_name": device_name,
                "profile": profile,
                "diagnostics": diagnostics,
            }
        )
        return expected_transport

    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        fake_create_default_transport,
    )

    pad = ProController(adapter="usb:0", profile_path=None)

    assert pad._runtime._ensure_transport() is expected_transport
    assert captured_config["adapter"] == "usb:0"
    assert pad._runtime._config.profile_path is None


def test_pro_controller_uses_controller_runtime_owner() -> None:
    transport = FakeHidTransport()
    pad = ProController._from_config(_SwitchGamepadConfig(), transport=transport)

    assert isinstance(pad._runtime, gamepad_core.ControllerRuntime)
    assert pad._runtime._transport is transport
    assert pad.snapshot() == swbt.InputState.neutral()


def test_pro_controller_constructor_accepts_controller_colors_config() -> None:
    constructor_signature = inspect.signature(ProController)
    config_fields = {field.name for field in fields(_SwitchGamepadConfig)}
    colors = ControllerColors(body=0x112233, buttons=0x445566)
    config = _SwitchGamepadConfig(controller_colors=colors)

    assert "controller_colors" in constructor_signature.parameters
    assert "controller_colors" in config_fields
    assert config.controller_colors == colors


def test_switch_gamepad_config_defaults_to_distinct_pro_controller_profiles() -> None:
    config_a = _SwitchGamepadConfig()
    config_b = _SwitchGamepadConfig()

    assert isinstance(config_a.profile, ProControllerProfile)
    assert isinstance(config_b.profile, ProControllerProfile)
    assert config_a.profile == config_b.profile
    assert config_a.profile is not config_b.profile


def test_switch_gamepad_config_rejects_invalid_profile() -> None:
    with pytest.raises(InvalidInputError):
        _SwitchGamepadConfig(profile=cast("ControllerProfile", object()))


def test_internal_gamepad_config_uses_private_class_name() -> None:
    assert hasattr(gamepad_config, "_SwitchGamepadConfig")
    assert not hasattr(gamepad_config, "SwitchGamepadConfig")


def test_joycon_public_constructors_are_thin_switch_gamepad_wrappers() -> None:
    for controller_cls in (JoyConL, JoyConR):
        signature = inspect.signature(controller_cls)

        assert issubclass(controller_cls, SwitchGamepad)
        assert "side" not in signature.parameters
        assert "adapter" in signature.parameters
        assert "key_store_path" not in signature.parameters
        assert "profile_path" in signature.parameters
        assert hasattr(controller_cls, "create_profile")
    assert "JoyConLeftProfile" not in swbt.__all__
    assert "JoyConRightProfile" not in swbt.__all__


@pytest.mark.parametrize("controller_cls", [JoyConL, JoyConR])
def test_joycon_constructor_rejects_key_store_and_profile_paths_together(
    controller_cls: type[JoyConL | JoyConR],
) -> None:
    with pytest.raises(TypeError, match="key_store_path"):
        cast("Any", controller_cls)(
            adapter="usb:0",
            key_store_path="keys.json",
        )


def test_concrete_controller_classes_own_internal_controller_specs() -> None:
    assert isinstance(ProController._controller_spec.profile, ProControllerProfile)
    assert isinstance(JoyConL._controller_spec.profile, JoyConLeftProfile)
    assert isinstance(JoyConR._controller_spec.profile, JoyConRightProfile)


def test_legacy_protocol_profile_module_is_removed() -> None:
    assert importlib.util.find_spec("swbt.protocol.profile") is None


@pytest.mark.parametrize(
    ("controller_cls", "profile"),
    [
        (ProController, JoyConLeftProfile()),
        (ProController, JoyConRightProfile()),
        (JoyConL, ProControllerProfile()),
        (JoyConR, JoyConLeftProfile()),
    ],
)
def test_from_config_rejects_mismatched_controller_profile(
    controller_cls: type[ProController | JoyConL | JoyConR],
    profile: ProControllerProfile | JoyConLeftProfile | JoyConRightProfile,
) -> None:
    with pytest.raises(InvalidInputError):
        controller_cls._from_config(
            _SwitchGamepadConfig(profile=profile),
            transport=FakeHidTransport(),
        )


def test_joycon_from_config_accepts_matching_joycon_profile() -> None:
    pad = JoyConL._from_config(
        _SwitchGamepadConfig(profile=JoyConLeftProfile()),
        transport=FakeHidTransport(),
    )

    assert isinstance(pad, JoyConL)
    assert pad.snapshot() == swbt.InputState.neutral()


def test_rearchitecture_target_public_controllers_do_not_expose_from_config() -> None:
    for controller_cls in (ProController, JoyConL, JoyConR):
        assert not hasattr(controller_cls, "from_config")


def test_connection_methods_do_not_accept_key_store_path() -> None:
    for method in (
        SwitchGamepad.pair,
        SwitchGamepad.reconnect,
        SwitchGamepad.try_reconnect,
        SwitchGamepad.connect,
        SwitchGamepad.try_connect,
    ):
        assert "key_store_path" not in inspect.signature(method).parameters


def test_connection_status_does_not_include_ambiguous_bond() -> None:
    assert "ambiguous_bond" not in get_args(ConnectionStatus)


def test_connection_result_exposes_plain_reconnect_values_without_bonded_peer() -> None:
    field_names = {field.name for field in fields(ConnectionResult)}
    result = ConnectionResult(
        route="active_reconnect",
        status="connected",
        peer_address="aa:bb:cc:dd:ee:ff",
        peer_count=1,
    )

    assert field_names == {"route", "status", "peer_address", "peer_count"}
    assert result.peer_address == "aa:bb:cc:dd:ee:ff"
    assert result.peer_count == 1


def test_default_transport_requires_explicit_adapter() -> None:
    with pytest.raises(InvalidInputError):
        ProController()


@pytest.mark.parametrize("report_period_us", [0, -1])
def test_switch_gamepad_rejects_non_positive_report_period(report_period_us: int) -> None:
    with pytest.raises(InvalidInputError):
        ProController(adapter="usb:0", report_period_us=report_period_us)


def test_from_config_uses_profile_device_name_unless_user_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run(config: _SwitchGamepadConfig) -> str:
        bumble_module = importlib.import_module("swbt.transport.bumble")
        captured_config: dict[str, object] = {}

        class FakeBumbleTransport:
            def __init__(
                self,
                *,
                adapter: str,
                device_name: str,
                profile: ProControllerProfile,
                diagnostics: object,
            ) -> None:
                _ = (adapter, profile, diagnostics)
                captured_config["device_name"] = device_name

            async def open(self) -> None:
                return None

            async def start_advertising(self) -> None:
                return None

            async def close(self) -> None:
                return None

            async def request_disconnect(self) -> DisconnectRequestResult:
                return DisconnectRequestResult(status="unavailable")

            async def list_bonded_peers(self) -> tuple[BondedPeer, ...]:
                return ()

            async def connect_bonded_peer(
                self,
                peer_address: str,
                *,
                connect_timeout: float | None,
            ) -> None:
                _ = (peer_address, connect_timeout)

            async def send_interrupt(self, payload: bytes) -> None:
                _ = payload

            async def send_control(self, payload: bytes) -> None:
                _ = payload

            def on_interrupt_data(self, callback: object) -> None:
                _ = callback

            def on_control_data(self, callback: object) -> None:
                _ = callback

            def on_connected(self, callback: object) -> None:
                _ = callback

            def on_disconnected(self, callback: object) -> None:
                _ = callback

        monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

        pad = ProController._from_config(config)
        await pad.open()
        await pad.close(neutral=True)

        return str(captured_config["device_name"])

    profile_default_name = asyncio.run(
        run(
            _SwitchGamepadConfig(
                adapter="usb:1",
                profile=ProControllerProfile(device_name="Profile Pad"),
            )
        )
    )
    explicit_name = asyncio.run(
        run(
            _SwitchGamepadConfig(
                adapter="usb:1",
                device_name="Override Pad",
                profile=ProControllerProfile(device_name="Profile Pad"),
            )
        )
    )

    assert profile_default_name == "Profile Pad"
    assert explicit_name == "Override Pad"


def test_from_config_uses_profile_report_period_unless_user_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_periods: list[int] = []

    class SpyReportLoop:
        def __init__(
            self,
            *,
            transport: object,
            state_store: object,
            report_period_us: int,
            input_report_builder: object | None = None,
            session: object | None = None,
            diagnostics: object | None = None,
            sender: object | None = None,
        ) -> None:
            _ = (transport, state_store, input_report_builder, session, diagnostics, sender)
            captured_periods.append(report_period_us)

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(gamepad_runtime, "ReportLoop", SpyReportLoop)

    async def run(config: _SwitchGamepadConfig) -> int:
        pad = ProController._from_config(config, transport=FakeHidTransport())
        await pad.open()
        await pad.close(neutral=False)
        return captured_periods[-1]

    profile_default_period = asyncio.run(
        run(
            _SwitchGamepadConfig(
                profile=ProControllerProfile(default_report_period_us=12_345),
            )
        )
    )
    explicit_period = asyncio.run(
        run(
            _SwitchGamepadConfig(
                profile=ProControllerProfile(default_report_period_us=12_345),
                report_period_us=8000,
            )
        )
    )

    assert profile_default_period == 12_345
    assert explicit_period == 8000


def test_public_constructor_uses_profile_default_report_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_periods: list[int] = []

    class SpyReportLoop:
        def __init__(
            self,
            *,
            transport: object,
            state_store: object,
            report_period_us: int,
            input_report_builder: object | None = None,
            session: object | None = None,
            diagnostics: object | None = None,
            sender: object | None = None,
        ) -> None:
            _ = (transport, state_store, input_report_builder, session, diagnostics, sender)
            captured_periods.append(report_period_us)

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(gamepad_runtime, "ReportLoop", SpyReportLoop)

    async def run() -> int:
        pad = ProController._from_config(_SwitchGamepadConfig(), transport=FakeHidTransport())
        await pad.open()
        await pad.close(neutral=False)
        return captured_periods[-1]

    report_period_us = asyncio.run(run())

    assert report_period_us == ProControllerProfile().default_report_period_us


def test_hid_transport_disconnect_request_boundary_uses_plain_types() -> None:
    signature = inspect.signature(HidDeviceTransport.request_disconnect)
    annotation_text = repr(signature.return_annotation).lower()

    result = DisconnectRequestResult(status="requested", channels=("interrupt", "control"))

    assert list(signature.parameters) == ["self"]
    assert "bumble" not in annotation_text
    assert result.status == "requested"
    assert result.channels == ("interrupt", "control")


def test_hid_transport_has_no_key_store_mutation_hook() -> None:
    assert not hasattr(HidDeviceTransport, "configure_key_store_path")


def test_hid_transport_bonded_peer_listing_documents_current_candidate_contract() -> None:
    doc = inspect.getdoc(HidDeviceTransport.list_bonded_peers)

    assert doc is not None
    assert "current reconnect candidates" in doc
    assert "zero or one peer" in doc
    assert "InvalidKeyStoreError" in doc


def test_hid_transport_local_bluetooth_address_boundary_uses_plain_types() -> None:
    signature = inspect.signature(HidDeviceTransport.local_bluetooth_address)
    annotation_text = repr(signature.return_annotation).lower()
    doc = inspect.getdoc(HidDeviceTransport.local_bluetooth_address)

    assert list(signature.parameters) == ["self"]
    assert "bumble" not in annotation_text
    assert doc is not None
    assert "Device Info" in doc


def test_default_transport_without_key_store_records_reconnect_limitation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        bumble_module = importlib.import_module("swbt.transport.bumble")
        trace = StringIO()

        class FakeBumbleTransport:
            def __init__(
                self,
                *,
                adapter: str,
                device_name: str,
                profile: ProControllerProfile,
                diagnostics: object,
            ) -> None:
                _ = (adapter, device_name, profile, diagnostics)

            async def open(self) -> None:
                return None

            async def start_advertising(self) -> None:
                return None

            async def close(self) -> None:
                return None

            async def request_disconnect(self) -> DisconnectRequestResult:
                return DisconnectRequestResult(status="unavailable")

            async def list_bonded_peers(self) -> tuple[BondedPeer, ...]:
                return ()

            async def connect_bonded_peer(
                self,
                peer_address: str,
                *,
                connect_timeout: float | None,
            ) -> None:
                _ = (peer_address, connect_timeout)

            async def send_interrupt(self, payload: bytes) -> None:
                _ = payload

            async def send_control(self, payload: bytes) -> None:
                _ = payload

            def on_interrupt_data(self, callback: object) -> None:
                _ = callback

            def on_control_data(self, callback: object) -> None:
                _ = callback

            def on_connected(self, callback: object) -> None:
                _ = callback

            def on_disconnected(self, callback: object) -> None:
                _ = callback

        monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

        pad = ProController(
            adapter="usb:0",
            diagnostics=DiagnosticsConfig(trace_writer=trace),
        )

        result = await pad.try_reconnect()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert result.status == "no_bond"
        assert {
            "event": "reconnect_profile_unavailable",
            "reason": "profile_path_none",
            "route": "active_reconnect",
        } in events

    asyncio.run(run())
