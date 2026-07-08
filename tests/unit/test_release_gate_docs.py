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
        "`SwitchGamepad(...)` ではコントローラーを作成できなくなりました",
        "`JoyCon(\"left\", ...)` / `JoyCon(\"right\", ...)`",
        "`transport=...`、`profile=...`、`device_name=...`",
        "`ConnectionResult` は `route`、`status`、`peer_address`、`peer_count`",
        "トレース出力設定の `diagnostics`",
        "`key_store_path` を分けてください",
        "Joy-Con R、再接続、通常入力反映は未検証",
    ):
        assert token in text

    for row in (
        "| Old API | New API | Notes |",
        "|---|---|---|",
        "| `SwitchGamepad(...)` | `ProController(...)` | "
        "`SwitchGamepad` は共通インターフェース / 型注釈用。 |",
        '| `JoyCon("left", ...)` | `JoyConL(...)` | Joy-Con（L）相当の具象コントローラー。 |',
        '| `JoyCon("right", ...)` | `JoyConR(...)` | Joy-Con（R）相当の具象コントローラー。 |',
        "| `SwitchGamepadConfig(...)` | 公開 API から削除 | "
        "内部実行時 / テスト設定専用。 |",
        "| `transport=FakeHidTransport` | 内部テストのみ | "
        "利用者向け生成 API では transport の差し替えを受け付けない。 |",
    ):
        assert row in text

    assert 'version = "0.2.0"' in pyproject_text
    assert 'name = "swbt-python"' in lock_text
    assert 'version = "0.2.0"' in lock_text
