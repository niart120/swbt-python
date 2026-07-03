import importlib
from pathlib import Path

import pytest

from swbt._gamepad_transport import create_default_transport
from swbt.diagnostics import DiagnosticsRecorder


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
            key_store_path: str | None,
            diagnostics: object,
        ) -> None:
            captured_config.update(
                {
                    "adapter": adapter,
                    "device_name": device_name,
                    "key_store_path": key_store_path,
                    "diagnostics": diagnostics,
                    "transport": self,
                }
            )

    monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

    diagnostics = DiagnosticsRecorder()
    key_store_path = tmp_path / "keys.json"
    transport = create_default_transport(
        adapter="usb:1",
        device_name="Reference Pad",
        diagnostics=diagnostics,
        key_store_path=str(key_store_path),
    )

    assert captured_config == {
        "adapter": "usb:1",
        "device_name": "Reference Pad",
        "diagnostics": diagnostics,
        "key_store_path": str(key_store_path),
        "transport": transport,
    }
