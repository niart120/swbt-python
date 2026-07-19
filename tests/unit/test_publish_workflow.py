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


def test_production_publish_stages_distributions_in_github_release_first() -> None:
    workflow = _load_workflow(PUBLISH_WORKFLOW)

    draft = workflow["jobs"]["create-github-release"]
    pypi = workflow["jobs"]["publish-to-pypi"]
    release = workflow["jobs"]["publish-github-release"]
    draft_commands = _run_commands(draft)
    release_commands = _run_commands(release)
    draft_release_steps = {
        step["name"]: step
        for step in draft["steps"]
        if step.get("name")
        in {"Create or reuse draft release", "Upload distributions to draft release"}
    }
    publish_release_step = next(
        step for step in release["steps"] if step.get("name") == "Publish draft release"
    )

    production_condition = (
        "${{ inputs.target == 'pypi' && github.ref_type == 'tag' && "
        "startsWith(github.ref_name, 'v') }}"
    )
    assert draft["if"] == production_condition
    assert draft["needs"] == ["validate", "build"]
    assert draft["permissions"] == {"contents": "write"}
    assert "actions/download-artifact@v6" in _uses(draft)
    assert 'gh release create "${TAG}" --verify-tag --draft --generate-notes' in draft_commands
    assert 'gh release upload "${GITHUB_REF_NAME}" dist/* --clobber' in draft_commands
    assert "already published" in draft_commands
    assert draft_release_steps["Create or reuse draft release"]["env"]["GH_REPO"] == (
        "${{ github.repository }}"
    )
    assert draft_release_steps["Upload distributions to draft release"]["env"]["GH_REPO"] == (
        "${{ github.repository }}"
    )

    assert pypi["needs"] == ["create-github-release"]

    assert release["if"] == production_condition
    assert release["needs"] == ["publish-to-pypi"]
    assert release["permissions"] == {"contents": "write"}
    assert 'gh release edit "${GITHUB_REF_NAME}" --draft=false --latest' in release_commands
    assert publish_release_step["env"]["GH_REPO"] == "${{ github.repository }}"


def test_publish_workflow_does_not_use_password_uploads_or_hardware_tests() -> None:
    text = PUBLISH_WORKFLOW.read_text(encoding="utf-8")

    assert "secrets.PYPI" not in text
    assert "twine upload" not in text
    assert "pytest -m hardware" not in text
    assert "pytest -m bumble" not in text
