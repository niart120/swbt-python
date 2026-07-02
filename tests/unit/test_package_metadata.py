"""Package metadata checks."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


def test_source_distribution_includes_examples() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    source_include = pyproject["tool"]["uv"]["build-backend"]["source-include"]

    assert "examples/**" in source_include
