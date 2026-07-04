"""Package metadata checks."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


def test_source_distribution_includes_examples() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    source_include = pyproject["tool"]["uv"]["build-backend"]["source-include"]

    assert "examples/**" in source_include


def test_docs_dependency_group_uses_mkdocs_without_runtime_dependency() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    docs_dependencies = pyproject["dependency-groups"]["docs"]
    runtime_dependencies = pyproject["project"]["dependencies"]

    assert "mkdocs>=1.6" in docs_dependencies
    assert not any(dependency.startswith("mkdocs") for dependency in runtime_dependencies)
