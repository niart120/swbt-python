"""README documentation checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


def test_readme_documents_confirmed_and_unconfirmed_hardware() -> None:
    text = README.read_text(encoding="utf-8")

    assert "確認済み構成はまだありません" not in text
    assert "### 確認済み構成" in text
    assert "Windows" in text
    assert "CSR8510 A10" in text
    assert "WinUSB" in text
    assert "`usb:0`" in text
    assert "### 試験的構成" in text
    assert "Linux" in text
    assert "macOS" in text
    assert "experimental" in text
    assert "手順は Hardware Guide に整備されています" in text
    assert "動作検証されていないことに留意してください" in text
    assert "unsupported" not in text
    assert "experimental" + " target" not in text
    assert "準備" + "候補" not in text
    assert "supported としては" + "扱いません" not in text
    assert "試す前に" + "確認すること" not in text


def test_readme_documents_dedicated_adapter_and_driver_notes() -> None:
    text = README.read_text(encoding="utf-8")

    assert "専用 USB Bluetooth dongle" in text
    assert "https://niart120.github.io/swbt-python/hardware/" in text
    assert "https://zadig.akeo.ie/" in text
    assert "Zadig" in text
    assert "WinUSB" in text
    assert "WinUSB / libwdi driver" in text
    assert "通常 Bluetooth 機能" in text
    assert "troubleshooting" in text


def test_readme_reflects_button_a_and_neutral_observation() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Button A" in text
    assert "neutral" in text
    assert "入力残りなし" in text
    assert "D-pad" in text
    assert "reconnect" in text


def test_readme_records_current_switch_model_and_firmware_evidence() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Switch 2" in text
    assert "22.1.0" in text
    assert "model / firmware は未記録" not in text


def test_readme_documents_single_joycon_public_api_and_scope() -> None:
    text = README.read_text(encoding="utf-8")

    for token in (
        "### 単体 Joy-Con L/R",
        "JoyConL(...)",
        "JoyConR(...)",
        "from swbt import Button, JoyConL, Stick",
        'key_store_path="switch-left-joycon-bond.json"',
        "await left.tap(Button.SR, Button.SL)",
        "`UnsupportedInputError`",
        "SR+SL を送ります",
        "Pro Controller、Joy-Con L、Joy-Con R では `key_store_path` を分けてください",
        "`JoyConPair` は未実装",
        "Switch UI で Joy-Con として登録",
        "Joy-Con R、reconnect",
        "SDP 完全一致",
        "OS / dongle / firmware をまたぐ互換性は未検証",
    ):
        assert token in text

    assert "JoyConLeftProfile" not in text
    assert "JoyConRightProfile" not in text
    assert 'JoyCon("' not in text
    assert "SwitchGamepad(" not in text


def test_readme_links_public_docs_with_https_urls() -> None:
    text = README.read_text(encoding="utf-8")

    for docs_url in (
        "https://niart120.github.io/swbt-python/",
        "https://niart120.github.io/swbt-python/api/",
        "https://niart120.github.io/swbt-python/usage/",
        "https://niart120.github.io/swbt-python/hardware/",
        "https://niart120.github.io/swbt-python/agent-brief/",
    ):
        assert docs_url in text


def test_readme_avoids_relative_markdown_links_for_pypi_rendering() -> None:
    text = README.read_text(encoding="utf-8")

    for docs_path in (
        "docs/index.md",
        "docs/api.md",
        "docs/usage.md",
        "docs/hardware.md",
        "docs/agent-brief.md",
    ):
        assert f"]({docs_path})" not in text
        assert f"`{docs_path}`" not in text


def test_readme_keeps_detailed_hardware_and_key_store_guidance_in_docs() -> None:
    text = README.read_text(encoding="utf-8")

    for detailed_phrase in (
        "| 項目 | 値 |",
        "libusb 権限設定",
        "apt install libusb-1.0-0",
        "brew install libusb",
        "bluetoothHostControllerSwitchBehavior",
        "複数の接続先",
        "swbt-probe pair",
        "full observed subcommand handshake",
        "active bond reuse reconnect",
        "pairing-free incoming bond reuse",
    ):
        assert detailed_phrase not in text
