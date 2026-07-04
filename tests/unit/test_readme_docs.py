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
    assert "OS 標準 Bluetooth stack" in text
    assert "WinUSB" in text
    assert "libusb" in text


def test_readme_reflects_button_a_and_neutral_observation() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Button A" in text
    assert "neutral" in text
    assert "対象機器 UI" in text
    assert "入力残りなし" in text
    assert "2026-07-02" in text


def test_readme_records_current_switch_model_and_firmware_evidence() -> None:
    text = README.read_text(encoding="utf-8")

    assert "Switch 2" in text
    assert "22.1.0" in text
    assert "model / firmware は未記録" not in text
