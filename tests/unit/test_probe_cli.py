"""swbt-probe command line surface tests."""

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
