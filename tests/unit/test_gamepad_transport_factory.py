import importlib
import subprocess
import sys
from pathlib import Path

import pytest

from swbt.diagnostics import DiagnosticsRecorder
from swbt.gamepad.transport_factory import (
    _BumbleTransportFactory,
    _StaticTransportFactory,
    create_default_transport,
)
from swbt.protocol.profiles.pro_controller import ProControllerProfile
from swbt.transport.fake import FakeHidTransport


def test_importing_transport_factory_does_not_import_bumble() -> None:
    code = """
import sys

import swbt.gamepad.transport_factory

imported_bumble_modules = [
    module_name
    for module_name in sys.modules
    if module_name == "bumble" or module_name.startswith("bumble.")
]
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


def test_default_transport_factory_passes_resource_config_to_bumble_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bumble_module = importlib.import_module("swbt.transport.bumble")
    captured_config: dict[str, object] = {}

    class FakeBumbleTransport:
        def __init__(
            self,
            *,
            adapter: str,
            device_name: str,
            profile: ProControllerProfile,
            profile_path: str | None,
            diagnostics: object,
            expected_local_bluetooth_address: bytes | None = None,
        ) -> None:
            _ = expected_local_bluetooth_address
            captured_config.update(
                {
                    "adapter": adapter,
                    "device_name": device_name,
                    "profile": profile,
                    "profile_path": profile_path,
                    "diagnostics": diagnostics,
                    "transport": self,
                }
            )

    monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

    diagnostics = DiagnosticsRecorder()
    profile = ProControllerProfile(battery_connection=0x92)
    profile_path = tmp_path / "profile.json"
    transport = create_default_transport(
        adapter="usb:1",
        device_name="Reference Pad",
        profile=profile,
        diagnostics=diagnostics,
        profile_path=str(profile_path),
    )

    assert captured_config == {
        "adapter": "usb:1",
        "device_name": "Reference Pad",
        "profile": profile,
        "diagnostics": diagnostics,
        "profile_path": str(profile_path),
        "transport": transport,
    }


def test_static_transport_factory_returns_injected_transport() -> None:
    transport = FakeHidTransport()
    diagnostics = DiagnosticsRecorder()
    profile = ProControllerProfile()
    factory = _StaticTransportFactory(transport)

    created_transport = factory.create(
        adapter="test-adapter",
        device_name="Reference Pad",
        profile=profile,
        diagnostics=diagnostics,
        profile_path=None,
    )

    assert created_transport is transport


def test_bumble_transport_factory_passes_resource_config_to_default_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bumble_module = importlib.import_module("swbt.transport.bumble")
    captured_config: dict[str, object] = {}

    class FakeBumbleTransport:
        def __init__(
            self,
            *,
            adapter: str,
            device_name: str,
            profile: ProControllerProfile,
            profile_path: str | None,
            diagnostics: object,
            expected_local_bluetooth_address: bytes | None = None,
        ) -> None:
            _ = expected_local_bluetooth_address
            captured_config.update(
                {
                    "adapter": adapter,
                    "device_name": device_name,
                    "profile": profile,
                    "profile_path": profile_path,
                    "diagnostics": diagnostics,
                    "transport": self,
                }
            )

    monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

    diagnostics = DiagnosticsRecorder()
    profile = ProControllerProfile(battery_connection=0x92)
    profile_path = tmp_path / "profile.json"
    factory = _BumbleTransportFactory()
    transport = factory.create(
        adapter="usb:1",
        device_name="Reference Pad",
        profile=profile,
        diagnostics=diagnostics,
        profile_path=str(profile_path),
    )

    assert captured_config == {
        "adapter": "usb:1",
        "device_name": "Reference Pad",
        "profile": profile,
        "diagnostics": diagnostics,
        "profile_path": str(profile_path),
        "transport": transport,
    }
