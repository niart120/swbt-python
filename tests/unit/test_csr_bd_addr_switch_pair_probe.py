import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[2] / "tools" / "csr_bd_addr_switch_pair_probe.py"


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
