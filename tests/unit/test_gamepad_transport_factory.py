import importlib
from pathlib import Path

import pytest

from swbt.diagnostics import DiagnosticsRecorder
from swbt.gamepad.transport_factory import (
    _BumbleTransportFactory,
    _StaticTransportFactory,
    create_default_transport,
)
from swbt.protocol.profile import ProControllerProfile
from swbt.transport.fake import FakeHidTransport


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
                    "transport": self,
                }
            )

    monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

    diagnostics = DiagnosticsRecorder()
    profile = ProControllerProfile(battery_connection=0x92)
    key_store_path = tmp_path / "keys.json"
    transport = create_default_transport(
        adapter="usb:1",
        device_name="Reference Pad",
        profile=profile,
        diagnostics=diagnostics,
        key_store_path=str(key_store_path),
    )

    assert captured_config == {
        "adapter": "usb:1",
        "device_name": "Reference Pad",
        "profile": profile,
        "diagnostics": diagnostics,
        "key_store_path": str(key_store_path),
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
        key_store_path=None,
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
                    "transport": self,
                }
            )

    monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

    diagnostics = DiagnosticsRecorder()
    profile = ProControllerProfile(battery_connection=0x92)
    key_store_path = tmp_path / "keys.json"
    factory = _BumbleTransportFactory()
    transport = factory.create(
        adapter="usb:1",
        device_name="Reference Pad",
        profile=profile,
        diagnostics=diagnostics,
        key_store_path=str(key_store_path),
    )

    assert captured_config == {
        "adapter": "usb:1",
        "device_name": "Reference Pad",
        "profile": profile,
        "diagnostics": diagnostics,
        "key_store_path": str(key_store_path),
        "transport": transport,
    }
