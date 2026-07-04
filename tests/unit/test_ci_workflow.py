"""GitHub Actions CI workflow checks."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _load_workflow(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _run_commands(job: dict[str, Any]) -> str:
    return "\n".join(
        step["run"] for step in job["steps"] if isinstance(step, dict) and "run" in step
    )


def test_ci_runs_no_hardware_gate_on_ubuntu_and_macos() -> None:
    workflow = _load_workflow(CI_WORKFLOW)

    python_job = workflow["jobs"]["python"]
    matrix = python_job["strategy"]["matrix"]
    commands = _run_commands(python_job)

    assert matrix["os"] == ["ubuntu-latest", "macos-latest"]
    assert matrix["python-version"] == ["3.12", "3.13"]
    assert python_job["runs-on"] == "${{ matrix.os }}"
    assert "uv sync --locked --dev" in commands
    assert "uv run pytest tests/unit" in commands
    assert "uv run pytest tests/integration" in commands
    assert "uv build" in commands
    assert "pytest -m bumble" not in commands
    assert "pytest -m hardware" not in commands
    assert "swbt-probe pair" not in commands
    assert "swbt-probe adapters" not in commands
