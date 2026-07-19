import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "csr_bd_addr_switch_pair_probe.py"


def _load_tool(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    monkeypatch.syspath_prepend(str(TOOL.parent))
    spec = importlib.util.spec_from_file_location("csr_bd_addr_switch_pair_probe", TOOL)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_switch_pair_probe_defaults_to_non_hardware_dry_run(tmp_path: Path) -> None:
    output_path = tmp_path / "result.json"
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(TOOL),
            "--expected-address",
            "02:1B:DC:F9:9F:7D",
            "--key-store",
            str(tmp_path / "keys.json"),
            "--trace",
            str(tmp_path / "trace.jsonl"),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["adapter_opened"] is False
    assert payload["advertising"] is False
    assert payload["switch_facing"] is False
    assert payload["key_store_must_be_fresh"] is True
    assert payload["expected_address"] == "02:1B:DC:F9:9F:7D"
    assert payload["observation_seconds"] == 5.0
    assert "hold_connected_for_observation" in payload["sequence"]
    assert output_path.read_text(encoding="utf-8") == result.stdout


def test_switch_pair_probe_rejects_existing_key_store_before_adapter_open(
    tmp_path: Path,
) -> None:
    key_store_path = tmp_path / "keys.json"
    key_store_path.write_text("{}\n", encoding="utf-8")
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(TOOL),
            "--adapter",
            "invalid:test-adapter",
            "--expected-address",
            "00:11:22:33:44:55",
            "--key-store",
            str(key_store_path),
            "--trace",
            str(tmp_path / "trace.jsonl"),
            "--output",
            str(tmp_path / "result.json"),
            "--execute",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "failed"
    assert payload["stage"] == "reject_existing_key_store"
    assert payload["cleanup"] == "adapter_not_opened"
    assert payload["advertising"] is False
    assert payload["switch_facing"] is False


def test_switch_pair_probe_dry_run_can_plan_explicit_key_store_reuse(
    tmp_path: Path,
) -> None:
    key_store_path = tmp_path / "keys.json"
    key_store_path.write_text("{}\n", encoding="utf-8")
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(TOOL),
            "--expected-address",
            "02:1B:DC:F9:9F:7D",
            "--key-store",
            str(key_store_path),
            "--reuse-key-store",
            "--trace",
            str(tmp_path / "trace.jsonl"),
            "--output",
            str(tmp_path / "result.json"),
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["adapter_opened"] is False
    assert payload["key_store_mode"] == "reuse"
    assert payload["key_store_must_be_fresh"] is False
    assert payload["sequence"][0] == "require_existing_key_store"


def test_switch_pair_probe_can_plan_address_read_immediately_after_close(
    tmp_path: Path,
) -> None:
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(TOOL),
            "--expected-address",
            "00:11:22:33:44:55",
            "--key-store",
            str(tmp_path / "keys.json"),
            "--reuse-key-store",
            "--trace",
            str(tmp_path / "trace.jsonl"),
            "--output",
            str(tmp_path / "result.json"),
            "--post-close-address-read",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["adapter_opened"] is False
    assert payload["post_close_address_read"] is True
    assert payload["sequence"].index("close_controller_and_adapter") < payload["sequence"].index(
        "read_standard_and_csr_address_after_close_without_hci_reset"
    )


def test_switch_pair_probe_reads_address_after_controller_context_closes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_tool(monkeypatch)
    pad_closed = False
    probe_calls: list[tuple[bool, bool]] = []

    class FakePad:
        async def __aenter__(self) -> "FakePad":
            return self

        async def __aexit__(
            self,
            exc_type: object,
            exc_value: object,
            traceback: object,
        ) -> None:
            nonlocal pad_closed
            pad_closed = True

        async def pair(self, **options: float) -> None:
            assert options["timeout"] == 1.0

    class FakeProController:
        @classmethod
        def _from_config(cls, *_args: object, **_kwargs: object) -> FakePad:
            return FakePad()

    async def fake_probe(
        adapter: str,
        *,
        response_timeout: float,
        hci_reset: bool,
    ) -> dict[str, object]:
        assert adapter == "usb:0"
        assert response_timeout == 2.0
        probe_calls.append((pad_closed, hci_reset))
        return {
            "status": "passed",
            "standard_hci": {"address": "00:11:22:33:44:55"},
            "csr": {
                "address": "00:11:22:33:44:55",
                "matches_standard_hci": True,
            },
            "cleanup": "adapter_closed",
        }

    monkeypatch.setattr(module, "_probe", fake_probe)
    monkeypatch.setattr(module, "BumbleHidTransport", lambda **_kwargs: object())
    monkeypatch.setattr(module, "ProController", FakeProController)

    execute = module.__dict__["_execute"]
    result = asyncio.run(
        execute(
            adapter="usb:0",
            expected_address=bytes.fromhex("001122334455"),
            key_store_path=tmp_path / "keys.json",
            trace_path=tmp_path / "trace.jsonl",
            preflight_timeout=2.0,
            pair_timeout=1.0,
            observation_seconds=0.0,
            reuse_key_store=True,
            post_close_address_read=True,
        )
    )

    assert probe_calls == [(False, False), (True, False)]
    assert result["status"] == "paired"
    assert result["post_close_matches_expected"] is True
    assert result["post_close_status"] == "expected_address_retained"
