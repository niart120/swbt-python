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
    assert "Bumble 0.0.230" in text
    assert "### 未確認構成" in text
    assert "Linux" in text
    assert "macOS" in text


def test_readme_documents_dedicated_adapter_and_driver_notes() -> None:
    text = README.read_text(encoding="utf-8")

    assert "専用 USB Bluetooth dongle" in text
    assert "https://niart120.github.io/swbt-python/hardware/" in text
    assert "WinUSB" in text
    assert "troubleshooting" in text


def test_readme_reflects_button_a_and_neutral_observation() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Button A" in text
    assert "neutral" in text
    assert "入力残りなし" in text
    assert "D-pad" in text
    assert "active bond reuse reconnect" in text


def test_readme_records_current_switch_model_and_firmware_evidence() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Switch 2" in text
    assert "22.1.0" in text
    assert "model / firmware は未記録" not in text


def test_readme_links_public_docs_with_https_urls() -> None:
    text = README.read_text(encoding="utf-8")

    for docs_url in (
        "https://niart120.github.io/swbt-python/",
        "https://niart120.github.io/swbt-python/api/",
        "https://niart120.github.io/swbt-python/usage/",
        "https://niart120.github.io/swbt-python/hardware/",
        "https://niart120.github.io/swbt-python/hardware-test-log/",
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
        "docs/hardware-test-log.md",
        "docs/agent-brief.md",
    ):
        assert f"]({docs_path})" not in text
        assert f"`{docs_path}`" not in text


def test_readme_keeps_detailed_hardware_and_key_store_guidance_in_docs() -> None:
    text = README.read_text(encoding="utf-8")

    for detailed_phrase in (
        "| 項目 | 値 |",
        "OS 標準 Bluetooth stack",
        "libusb 権限設定",
        "複数の接続先",
        "swbt-probe pair",
    ):
        assert detailed_phrase not in text
