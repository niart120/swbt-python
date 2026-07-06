"""Release gate documentation checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RISKS = ROOT / "spec" / "initial" / "risks.md"
RELEASE_NOTES = ROOT / "docs" / "release-notes.md"
PYPROJECT = ROOT / "pyproject.toml"
UV_LOCK = ROOT / "uv.lock"


def test_risks_document_release_gate_confirmed_and_unconfirmed_scope() -> None:
    text = RISKS.read_text(encoding="utf-8")

    assert "## 11. Initial release gate の確認済み / 未確認境界" in text
    assert "Windows" in text
    assert "CSR8510 A10" in text
    assert "WinUSB" in text
    assert "Switch 2" in text
    assert "22.1.0" in text
    assert "Linux" in text
    assert "macOS" in text
    assert "pairing-free incoming bond reuse" in text


def test_release_notes_document_rearchitecture_breaking_change_and_version_target() -> None:
    text = RELEASE_NOTES.read_text(encoding="utf-8")
    pyproject_text = PYPROJECT.read_text(encoding="utf-8")
    lock_text = UV_LOCK.read_text(encoding="utf-8")

    for token in (
        "## 0.2.0",
        "Breaking changes",
        "Migration",
        "`SwitchGamepad(...)`",
        "`ProController(...)`",
        "`JoyCon(\"left\", ...)`",
        "`JoyConL(...)`",
        "`JoyCon(\"right\", ...)`",
        "`JoyConR(...)`",
        "`SwitchGamepadConfig(...)`",
        "public API では廃止",
        "`transport=FakeHidTransport`",
        "internal tests only",
        "Pro Controller / Joy-Con L / Joy-Con R",
        "`key_store_path` を分ける",
        "Joy-Con R、reconnect、通常入力反映は未検証",
    ):
        assert token in text

    assert 'version = "0.2.0"' in pyproject_text
    assert 'name = "swbt-python"' in lock_text
    assert 'version = "0.2.0"' in lock_text
