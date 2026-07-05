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
from typing import get_args

import pytest

import swbt
from swbt import (
    ControllerColors,
    DiagnosticsConfig,
    InvalidInputError,
    SwitchGamepad,
    SwitchGamepadConfig,
)
from swbt.gamepad import ConnectionStatus
from swbt.transport.base import BondedPeer, DisconnectRequestResult, HidDeviceTransport


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
                key_store_path: str | None,
                diagnostics: object,
            ) -> None:
                captured_config.update(
                    {
                        "adapter": adapter,
                        "device_name": device_name,
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
        assert captured_config["key_store_path"] == str(key_store_path)
        assert captured_config["diagnostics"] is not None
        assert result.status == "no_bond"

    asyncio.run(run())


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
                key_store_path: str | None,
                diagnostics: object,
            ) -> None:
                _ = (adapter, device_name, key_store_path, diagnostics)

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
