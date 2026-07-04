"""Release gate documentation checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RISKS = ROOT / "spec" / "initial" / "risks.md"


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
