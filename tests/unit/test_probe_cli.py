"""swbt-probe command line surface tests."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from types import TracebackType
from typing import Protocol, TextIO

import pytest

from swbt import AdapterDiscoveryError, AdapterInfo
from swbt import probe as probe_module
from swbt.gamepad._config import _SwitchGamepadConfig


class DiagnosticsLike(Protocol):
    """Diagnostics object shape consumed by the fake gamepad."""

    trace_writer: TextIO


def test_swbt_probe_entry_point_is_declared() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["scripts"]["swbt-probe"] == "swbt.probe:main"


def test_swbt_probe_adapters_help_runs_without_opening_adapter() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "swbt.probe", "adapters", "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    help_text = " ".join(result.stdout.split())

    assert "usage:" in result.stdout
    assert "swbt-probe adapters" in result.stdout
    assert "--json" in result.stdout
    assert "does not open a Bluetooth adapter" in help_text


def test_swbt_probe_adapters_json_reports_no_open_environment(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        probe_module,
        "list_adapters",
        lambda: (
            AdapterInfo(
                name="usb:0",
                aliases=("usb:0A12:0001", "usb:0A12:0001/ABC123"),
                vendor_id=0x0A12,
                product_id=0x0001,
                manufacturer="Cambridge Silicon Radio",
                product="Bluetooth Dongle",
                serial_number="ABC123",
                bus_number=1,
                device_address=7,
                port_numbers=(2, 4),
                is_bluetooth_hci=True,
            ),
        ),
    )

    exit_code = probe_module.main(["adapters", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["opens_adapter"] is False
    assert "candidate_adapters" not in payload
    assert payload["adapters"] == [
        {
            "aliases": ["usb:0A12:0001", "usb:0A12:0001/ABC123"],
            "bus_number": 1,
            "device_address": 7,
            "is_bluetooth_hci": True,
            "manufacturer": "Cambridge Silicon Radio",
            "name": "usb:0",
            "port_numbers": [2, 4],
            "product": "Bluetooth Dongle",
            "product_id": 1,
            "product_id_hex": "0001",
            "serial_number": "ABC123",
            "vendor_id": 2578,
            "vendor_id_hex": "0A12",
        }
    ]
    assert payload["platform"]
    assert payload["python_version"]
    assert payload["bumble_version"]


def test_swbt_probe_adapters_json_reports_discovery_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    message = "libusb unavailable"

    def fail_discovery() -> tuple[AdapterInfo, ...]:
        raise AdapterDiscoveryError(
            message,
            platform="test-platform",
            backend="bumble-usb",
            libusb_available=False,
            bumble_version="0.0.230",
        )

    monkeypatch.setattr(probe_module, "list_adapters", fail_discovery)

    exit_code = probe_module.main(["adapters", "--json"])
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["status"] == "discovery_error"
    assert payload["opens_adapter"] is False
    assert payload["error"] == {
        "backend": "bumble-usb",
        "bumble_version": "0.0.230",
        "libusb_available": False,
        "message": "libusb unavailable",
        "platform": "test-platform",
        "type": "AdapterDiscoveryError",
    }


def test_swbt_probe_adapters_human_output_reports_no_open_and_candidate_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        probe_module,
        "list_adapters",
        lambda: (
            AdapterInfo(
                name="usb:0",
                aliases=("usb:0A12:0001",),
                vendor_id=0x0A12,
                product_id=0x0001,
                manufacturer="Cambridge Silicon Radio",
                product="Bluetooth Dongle",
                serial_number="ABC123",
                bus_number=1,
                device_address=7,
                port_numbers=(2, 4),
                is_bluetooth_hci=True,
            ),
        ),
    )

    exit_code = probe_module.main(["adapters"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "This command does not open a Bluetooth adapter." in output
    assert "Candidate adapters:" in output
    assert "usb:0" in output
    assert "VID/PID: 0A12:0001" in output
    assert "Cambridge Silicon Radio" in output
    assert "Bluetooth Dongle" in output
    assert "ABC123" in output


def test_swbt_probe_pair_help_describes_approval_boundary() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "swbt.probe", "pair", "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    help_text = " ".join(result.stdout.split())

    assert "usage:" in result.stdout
    assert "swbt-probe pair" in result.stdout
    assert "--adapter" in result.stdout
    assert "--trace" in result.stdout
    assert "--timeout" in result.stdout
    assert "requires explicit approval" in help_text
    assert "Switch-facing" in help_text


def test_swbt_probe_pair_writes_trace_with_injected_gamepad(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class FakeGamepad:
        def __init__(
            self,
            *,
            adapter: str,
            key_store_path: str | None,
            diagnostics: DiagnosticsLike,
        ) -> None:
            captured["adapter"] = adapter
            captured["key_store_path"] = key_store_path
            self._trace_writer = diagnostics.trace_writer

        @classmethod
        def _from_config(
            cls,
            config: _SwitchGamepadConfig,
            *,
            diagnostics: DiagnosticsLike,
        ) -> "FakeGamepad":
            return cls(
                adapter=config.adapter or "",
                key_store_path=config.key_store_path,
                diagnostics=diagnostics,
            )

        async def __aenter__(self) -> "FakeGamepad":
            self._write_event("fake_open")
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            _ = (exc_type, exc, traceback)
            self._write_event("fake_close")

        async def pair(
            self,
            timeout: float | None,  # noqa: ASYNC109
        ) -> None:
            captured["timeout"] = timeout
            self._write_event("fake_pair")

        def _write_event(self, event: str) -> None:
            self._trace_writer.write(json.dumps({"event": event}, sort_keys=True))
            self._trace_writer.write("\n")

    monkeypatch.setattr(probe_module, "ProController", FakeGamepad)

    trace_path = tmp_path / "pair-trace.jsonl"
    exit_code = probe_module.main(
        [
            "pair",
            "--adapter",
            "usb:7",
            "--key-store",
            str(tmp_path / "keys.json"),
            "--trace",
            str(trace_path),
            "--timeout",
            "1.5",
        ]
    )

    events = [json.loads(line)["event"] for line in trace_path.read_text().splitlines()]

    assert exit_code == 0
    assert captured["adapter"] == "usb:7"
    assert captured["key_store_path"] == str(tmp_path / "keys.json")
    assert captured["timeout"] == 1.5
    assert events == ["fake_open", "fake_pair", "fake_close"]
