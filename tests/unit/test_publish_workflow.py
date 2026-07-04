"""GitHub Actions publish workflow checks."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
PUBLISH_WORKFLOW = ROOT / ".github" / "workflows" / "publish.yml"
PUBLISHING_DOC = ROOT / "spec" / "publishing.md"
PYPI_RELEASE_SKILL = ROOT / ".agents" / "skills" / "pypi-release" / "SKILL.md"


def _load_workflow(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _run_commands(job: dict[str, Any]) -> str:
    return "\n".join(
        step["run"] for step in job["steps"] if isinstance(step, dict) and "run" in step
    )


def _uses(job: dict[str, Any]) -> list[str]:
    return [step["uses"] for step in job["steps"] if isinstance(step, dict) and "uses" in step]


def test_publish_workflow_is_manual_and_requires_target_choice() -> None:
    workflow = _load_workflow(PUBLISH_WORKFLOW)

    triggers = workflow["on"]

    assert set(triggers) == {"workflow_dispatch"}
    target = triggers["workflow_dispatch"]["inputs"]["target"]
    assert target["type"] == "choice"
    assert target["required"] is True
    assert target["default"] == "testpypi"
    assert target["options"] == ["testpypi", "pypi"]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] is False


def test_publish_workflow_rejects_production_without_v_tag_ref() -> None:
    workflow = _load_workflow(PUBLISH_WORKFLOW)

    validate = workflow["jobs"]["validate"]
    commands = _run_commands(validate)
    guarded_steps = [
        step
        for step in validate["steps"]
        if step.get("name") == "Reject production publish without a v tag ref"
    ]

    assert guarded_steps == [
        {
            "name": "Reject production publish without a v tag ref",
            "if": (
                "${{ inputs.target == 'pypi' && (github.ref_type != 'tag' || "
                "!startsWith(github.ref_name, 'v')) }}"
            ),
            "run": 'echo "target=pypi must be run from a v* tag ref." >&2\nexit 1\n',
        }
    ]
    assert "target=${{ inputs.target }}" in commands
    assert "ref_type=${{ github.ref_type }}" in commands


def test_publish_workflow_builds_and_checks_exact_candidate_artifacts() -> None:
    workflow = _load_workflow(PUBLISH_WORKFLOW)

    build = workflow["jobs"]["build"]
    commands = _run_commands(build)

    assert build["needs"] == "validate"
    assert "uv lock --check" in commands
    assert "uv sync --locked --dev" in commands
    assert "rm -rf dist" in commands
    assert "uv build" in commands
    assert 'WHEEL="dist/swbt_python-${VERSION}-py3-none-any.whl"' in commands
    assert 'SDIST="dist/swbt_python-${VERSION}.tar.gz"' in commands
    assert 'uvx --from twine twine check --strict "${WHEEL}" "${SDIST}"' in commands
    assert "actions/upload-artifact@v5" in _uses(build)


def test_publish_workflow_uses_trusted_publishing_environments() -> None:
    workflow = _load_workflow(PUBLISH_WORKFLOW)

    testpypi = workflow["jobs"]["publish-to-testpypi"]
    pypi = workflow["jobs"]["publish-to-pypi"]

    assert testpypi["if"] == "${{ inputs.target == 'testpypi' }}"
    assert testpypi["environment"] == {
        "name": "testpypi",
        "url": "https://test.pypi.org/p/swbt-python",
    }
    assert testpypi["permissions"] == {"contents": "read", "id-token": "write"}
    assert "actions/download-artifact@v6" in _uses(testpypi)
    assert "pypa/gh-action-pypi-publish@release/v1" in _uses(testpypi)
    testpypi_publish = testpypi["steps"][-1]
    assert testpypi_publish["with"]["repository-url"] == "https://test.pypi.org/legacy/"

    assert pypi["if"] == (
        "${{ inputs.target == 'pypi' && github.ref_type == 'tag' && "
        "startsWith(github.ref_name, 'v') }}"
    )
    assert pypi["environment"] == {
        "name": "pypi",
        "url": "https://pypi.org/p/swbt-python",
    }
    assert pypi["permissions"] == {"contents": "read", "id-token": "write"}
    assert "actions/download-artifact@v6" in _uses(pypi)
    assert "pypa/gh-action-pypi-publish@release/v1" in _uses(pypi)


def test_publish_workflow_does_not_use_password_uploads_or_hardware_tests() -> None:
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "secrets.PYPI" not in text
    assert "twine upload" not in text
    assert "pytest -m hardware" not in text
    assert "pytest -m bumble" not in text


def test_publishing_doc_records_manual_publish_boundaries() -> None:
    text = PUBLISHING_DOC.read_text(encoding="utf-8")

    assert "内部運用手順" in text
    assert "手元の `twine upload` は使わない" in text
    assert "`v*` tag を作るだけでは公開されない" in text
    assert "gh workflow run publish.yml --ref vX.Y.Z -f target=pypi" in text
    assert "target=pypi" in text
    assert "version-specific endpoint" in text
    assert "Trusted Publisher" in text
    assert "実機 smoke" in text


def test_pypi_release_skill_delegates_runbook_details_to_internal_doc() -> None:
    text = PYPI_RELEASE_SKILL.read_text(encoding="utf-8")

    assert "spec/publishing.md" in text
    assert len(text.splitlines()) <= 40
    assert "Version Policy" not in text
    assert "Release PR" not in text
    assert "Production Publish" not in text
    assert "https://pypi.org/pypi/swbt-python/X.Y.Z/json" not in text
    assert "dist\\swbt_python-X.Y.Z" not in text
