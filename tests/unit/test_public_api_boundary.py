import asyncio
import builtins
import importlib
import inspect
import pkgutil
import subprocess
import sys
from pathlib import Path

import pytest

import swbt
from swbt import SwitchGamepad
from swbt.transport.base import DisconnectRequestResult, HidDeviceTransport


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


def test_switch_gamepad_key_store_path_is_passed_to_bumble_transport(
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
        pad = SwitchGamepad(
            adapter="usb:1",
            device_name="Reference Pad",
            key_store_path=str(key_store_path),
        )

        await pad.open()
        await pad.close(neutral=True)

        assert captured_config["adapter"] == "usb:1"
        assert captured_config["device_name"] == "Reference Pad"
        assert captured_config["key_store_path"] == str(key_store_path)
        assert captured_config["diagnostics"] is not None

    asyncio.run(run())


def test_hid_transport_disconnect_request_boundary_uses_plain_types() -> None:
    signature = inspect.signature(HidDeviceTransport.request_disconnect)
    annotation_text = repr(signature.return_annotation).lower()

    result = DisconnectRequestResult(status="requested", channels=("interrupt", "control"))

    assert list(signature.parameters) == ["self"]
    assert "bumble" not in annotation_text
    assert result.status == "requested"
    assert result.channels == ("interrupt", "control")
