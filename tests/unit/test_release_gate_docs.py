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
        "Pro Controller / Joy-Con L / Joy-Con R",
        "`key_store_path` を分ける",
        "Joy-Con R、reconnect、通常入力反映は未検証",
    ):
        assert token in text

    for row in (
        "| Old API | New API | Notes |",
        "|---|---|---|",
        "| `SwitchGamepad(...)` | `ProController(...)` | "
        "`SwitchGamepad` は shared interface / 型注釈用。 |",
        '| `JoyCon("left", ...)` | `JoyConL(...)` | 左 Joy-Con 相当の concrete controller。 |',
        '| `JoyCon("right", ...)` | `JoyConR(...)` | 右 Joy-Con 相当の concrete controller。 |',
        "| `SwitchGamepadConfig(...)` | public API から削除 | "
        "internal runtime / test setup 専用。 |",
        "| `transport=FakeHidTransport` | internal tests only | "
        "利用者向け constructor には transport injection を出さない。 |",
    ):
        assert row in text

    assert 'version = "0.2.0"' in pyproject_text
    assert 'name = "swbt-python"' in lock_text
    assert 'version = "0.2.0"' in lock_text
