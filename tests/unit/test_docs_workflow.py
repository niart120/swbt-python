"""GitHub Actions documentation workflow checks."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS_WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"


def _load_workflow(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_docs_workflow_builds_on_pull_request_and_main_push() -> None:
    workflow = _load_workflow(DOCS_WORKFLOW)

    triggers = workflow["on"]
    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers

    build = workflow["jobs"]["build"]
    commands = "\n".join(
        step["run"] for step in build["steps"] if isinstance(step, dict) and "run" in step
    )

    assert "uv sync --locked --group docs" in commands
    assert "uv run mkdocs build --strict" in commands
    assert "uv run ruff" not in commands
    assert "pytest -m hardware" not in commands
    assert "pytest -m bumble" not in commands


def test_docs_workflow_deploys_pages_only_from_main_push() -> None:
    workflow = _load_workflow(DOCS_WORKFLOW)

    deploy = workflow["jobs"]["deploy"]
    assert deploy["needs"] == "build"
    assert deploy["if"] == "github.event_name == 'push' && github.ref == 'refs/heads/main'"
    assert deploy["permissions"] == {
        "contents": "read",
        "pages": "write",
        "id-token": "write",
    }
    assert deploy["environment"]["name"] == "github-pages"
    assert deploy["environment"]["url"] == "${{ steps.deployment.outputs.page_url }}"

    deploy_uses = [
        step["uses"] for step in deploy["steps"] if isinstance(step, dict) and "uses" in step
    ]
    build_uses = [
        step["uses"]
        for step in workflow["jobs"]["build"]["steps"]
        if isinstance(step, dict) and "uses" in step
    ]

    assert "actions/configure-pages@v5" in build_uses
    assert "actions/upload-pages-artifact@v4" in build_uses
    assert "actions/deploy-pages@v4" in deploy_uses


def test_python_ci_keeps_read_only_permissions() -> None:
    workflow = _load_workflow(CI_WORKFLOW)

    assert workflow["permissions"] == {"contents": "read"}
