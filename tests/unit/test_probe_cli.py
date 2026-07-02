"""swbt-probe command line surface tests."""

import json
import subprocess
import sys
import tomllib
from pathlib import Path


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
