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
        "New public API",
        "v0.1.1 から利用者のコードに影響する破壊的変更",
        "`SwitchGamepad(...)` ではコントローラーを作成できなくなりました",
        "`SwitchGamepadConfig(...)` と `SwitchGamepad.from_config(...)`",
        "`SwitchGamepad(..., transport=...)` と `SwitchGamepad(..., device_name=...)`",
        "`HidDeviceTransport`、`BondedPeer`、`DisconnectRequestResult`",
        "トレース出力設定の `diagnostics`",
        "`key_store_path` を分けてください",
        "`list_adapters()` と `AdapterInfo`",
        "Joy-Con R は SR+SL 登録、`0x22` ACK 互換処理、"
        "active reconnect 後の ABXY 入力、利用者指定色を確認済み",
        "横持ち Joy-Con の UI 制約",
    ):
        assert token in text

    for row in (
        "| Old API | New API | Notes |",
        "|---|---|---|",
        "| `SwitchGamepad(...)` | `ProController(...)` | "
        "`SwitchGamepad` は共通インターフェース / 型注釈用。 |",
        "| `SwitchGamepadConfig(...)` | 各具象クラスの constructor 引数 | "
        "`from_config()` は公開 API から削除。 |",
        "| `SwitchGamepad(..., transport=...)` | 公開 API では移行先なし | "
        "transport 差し替えは内部テスト用。 |",
        "| `SwitchGamepad(..., device_name=...)` | "
        "`ProController(...)` / `JoyConL(...)` / `JoyConR(...)` | "
        "HID identity は具象クラスが選ぶ。 |",
        "| `from swbt import HidDeviceTransport, BondedPeer, DisconnectRequestResult` | "
        "公開 API から削除 | transport 内部型はトップレベル export しない。 |",
    ):
        assert row in text

    assert '`JoyCon("left", ...)`' not in text
    assert "`ConnectionResult` は `route`" not in text
    assert "利用者向け生成 API" not in text
    assert "Joy-Con R、再接続、通常入力反映は未検証" not in text

    assert 'version = "0.2.0"' in pyproject_text
    assert 'name = "swbt-python"' in lock_text
    assert 'version = "0.2.0"' in lock_text
