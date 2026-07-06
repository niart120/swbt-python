import asyncio
import builtins
import importlib
import inspect
import json
import pkgutil
import subprocess
import sys
from dataclasses import fields
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, cast, get_args

import pytest

import swbt
from swbt import (
    ControllerColors,
    DiagnosticsConfig,
    InvalidInputError,
    JoyCon,
    SwitchGamepad,
    SwitchGamepadConfig,
)
from swbt.gamepad import ConnectionStatus
from swbt.gamepad import core as gamepad_core
from swbt.protocol.profile import JoyConLeftProfile, ProControllerProfile
from swbt.transport.base import BondedPeer, DisconnectRequestResult, HidDeviceTransport
from swbt.transport.fake import FakeHidTransport

if TYPE_CHECKING:
    from swbt.protocol.profile import ControllerProfile


REARCHITECTURE_TARGET_XFAIL_REASON = (
    "target boundary fixed before implementation; unit_040 makes this green"
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


def test_only_bumble_transport_module_may_resolve_bumble(
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
        if module.name == "swbt.transport.bumble":
            continue
        importlib.import_module(module.name)


def test_switch_gamepad_signature_does_not_expose_bumble_types() -> None:
    signature = inspect.signature(SwitchGamepad)
    annotation_text = " ".join(
        repr(parameter.annotation) for parameter in signature.parameters.values()
    )

    assert "bumble" not in annotation_text.lower()


@pytest.mark.xfail(reason=REARCHITECTURE_TARGET_XFAIL_REASON, strict=True)
def test_rearchitecture_target_switch_gamepad_is_abstract_interface() -> None:
    assert inspect.isabstract(SwitchGamepad)

    with pytest.raises(TypeError):
        SwitchGamepad()


def test_switch_gamepad_constructor_accepts_key_store_path() -> None:
    signature = inspect.signature(SwitchGamepad)

    assert "key_store_path" in signature.parameters


def test_switch_gamepad_constructor_accepts_controller_colors_config() -> None:
    constructor_signature = inspect.signature(SwitchGamepad)
    config_fields = {field.name for field in fields(SwitchGamepadConfig)}
    colors = ControllerColors(body=0x112233, buttons=0x445566)
    config = SwitchGamepadConfig(controller_colors=colors)

    assert "controller_colors" in constructor_signature.parameters
    assert "controller_colors" in config_fields
    assert config.controller_colors == colors


def test_switch_gamepad_config_defaults_to_distinct_pro_controller_profiles() -> None:
    config_a = SwitchGamepadConfig()
    config_b = SwitchGamepadConfig()

    assert isinstance(config_a.profile, ProControllerProfile)
    assert isinstance(config_b.profile, ProControllerProfile)
    assert config_a.profile == config_b.profile
    assert config_a.profile is not config_b.profile


def test_switch_gamepad_config_rejects_invalid_profile() -> None:
    with pytest.raises(InvalidInputError):
        SwitchGamepadConfig(profile=cast("ControllerProfile", object()))


def test_joycon_public_constructor_is_thin_switch_gamepad_wrapper() -> None:
    signature = inspect.signature(JoyCon)

    assert issubclass(JoyCon, SwitchGamepad)
    assert "side" in signature.parameters
    assert "adapter" in signature.parameters
    assert "key_store_path" in signature.parameters
    assert "JoyConLeftProfile" not in swbt.__all__
    assert "JoyConRightProfile" not in swbt.__all__


def test_joycon_from_config_requires_joycon_profile() -> None:
    with pytest.raises(InvalidInputError):
        JoyCon.from_config(SwitchGamepadConfig(), transport=FakeHidTransport())


def test_joycon_from_config_accepts_joycon_profile() -> None:
    pad = JoyCon.from_config(
        SwitchGamepadConfig(profile=JoyConLeftProfile()),
        transport=FakeHidTransport(),
    )

    assert isinstance(pad, JoyCon)
    assert pad.snapshot() == swbt.InputState.neutral()


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


def test_default_transport_requires_explicit_adapter() -> None:
    with pytest.raises(InvalidInputError):
        SwitchGamepad()


@pytest.mark.parametrize("report_period_us", [0, -1])
def test_switch_gamepad_rejects_non_positive_report_period(report_period_us: int) -> None:
    with pytest.raises(InvalidInputError):
        SwitchGamepad(adapter="usb:0", report_period_us=report_period_us)


def test_switch_gamepad_from_config_passes_resource_config_to_bumble_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        bumble_module = importlib.import_module("swbt.transport.bumble")

        captured_config: dict[str, object] = {}

        class FakeBumbleTransport:
            def __init__(
                self,
                *,
                adapter: str,
                device_name: str,
                profile: ProControllerProfile,
                key_store_path: str | None,
                diagnostics: object,
            ) -> None:
                captured_config.update(
                    {
                        "adapter": adapter,
                        "device_name": device_name,
                        "profile": profile,
                        "key_store_path": key_store_path,
                        "diagnostics": diagnostics,
                    }
                )

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

        key_store_path = tmp_path / "keys.json"
        pad = SwitchGamepad.from_config(
            SwitchGamepadConfig(
                adapter="usb:1",
                device_name="Reference Pad",
                key_store_path=str(key_store_path),
            )
        )

        await pad.open()
        result = await pad.try_reconnect()
        await pad.close(neutral=True)

        assert captured_config["adapter"] == "usb:1"
        assert captured_config["device_name"] == "Reference Pad"
        assert isinstance(captured_config["profile"], ProControllerProfile)
        assert captured_config["key_store_path"] == str(key_store_path)
        assert captured_config["diagnostics"] is not None
        assert result.status == "no_bond"

    asyncio.run(run())


def test_from_config_uses_profile_device_name_unless_user_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run(config: SwitchGamepadConfig) -> str:
        bumble_module = importlib.import_module("swbt.transport.bumble")
        captured_config: dict[str, object] = {}

        class FakeBumbleTransport:
            def __init__(
                self,
                *,
                adapter: str,
                device_name: str,
                profile: ProControllerProfile,
                key_store_path: str | None,
                diagnostics: object,
            ) -> None:
                _ = (adapter, profile, key_store_path, diagnostics)
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

        pad = SwitchGamepad.from_config(config)
        await pad.open()
        await pad.close(neutral=True)

        return str(captured_config["device_name"])

    profile_default_name = asyncio.run(
        run(
            SwitchGamepadConfig(
                adapter="usb:1",
                profile=ProControllerProfile(device_name="Profile Pad"),
            )
        )
    )
    explicit_name = asyncio.run(
        run(
            SwitchGamepadConfig(
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
            diagnostics: object | None = None,
        ) -> None:
            _ = (transport, state_store, input_report_builder, diagnostics)
            captured_periods.append(report_period_us)

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(gamepad_core, "ReportLoop", SpyReportLoop)

    async def run(config: SwitchGamepadConfig) -> int:
        pad = SwitchGamepad.from_config(config, transport=FakeHidTransport())
        await pad.open()
        await pad.close(neutral=False)
        return captured_periods[-1]

    profile_default_period = asyncio.run(
        run(
            SwitchGamepadConfig(
                profile=ProControllerProfile(default_report_period_us=12_345),
            )
        )
    )
    explicit_period = asyncio.run(
        run(
            SwitchGamepadConfig(
                profile=ProControllerProfile(default_report_period_us=12_345),
                report_period_us=8000,
            )
        )
    )

    assert profile_default_period == 12_345
    assert explicit_period == 8000


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
                key_store_path: str | None,
                diagnostics: object,
            ) -> None:
                _ = (adapter, device_name, profile, key_store_path, diagnostics)

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

        pad = SwitchGamepad(
            adapter="usb:0",
            diagnostics=DiagnosticsConfig(trace_writer=trace),
        )

        result = await pad.try_reconnect()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert result.status == "no_bond"
        assert {
            "event": "reconnect_key_store_unavailable",
            "reason": "key_store_path_none",
            "route": "active_reconnect",
        } in events

    asyncio.run(run())
