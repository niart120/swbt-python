"""swbt-probe command line surface tests."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path
from types import TracebackType
from typing import Protocol, TextIO

import pytest

from swbt import probe as probe_module


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


def test_swbt_probe_adapters_json_reports_no_open_environment() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "swbt.probe", "adapters", "--json"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)

    assert payload["opens_adapter"] is False
    assert payload["candidate_adapters"] == ["usb:0"]
    assert payload["platform"]
    assert payload["python_version"]
    assert payload["bumble_version"]


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
            diagnostics: DiagnosticsLike,
        ) -> None:
            captured["adapter"] = adapter
            self._trace_writer = diagnostics.trace_writer

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
            *,
            key_store_path: str | None,
        ) -> None:
            captured["timeout"] = timeout
            captured["key_store_path"] = key_store_path
            self._write_event("fake_pair")

        def _write_event(self, event: str) -> None:
            self._trace_writer.write(json.dumps({"event": event}, sort_keys=True))
            self._trace_writer.write("\n")

    monkeypatch.setattr(probe_module, "SwitchGamepad", FakeGamepad)

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
