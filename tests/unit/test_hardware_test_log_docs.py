"""Hardware test log documentation checks."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HARDWARE_LOG = ROOT / "spec" / "hardware-test-log.md"


def test_hardware_test_log_has_run_entry_template_fields() -> None:
    text = HARDWARE_LOG.read_text(encoding="utf-8")

    required_fields = [
        "OS",
        "environment",
        "adapter",
        "dongle",
        "driver",
        "Python",
        "Bumble",
        "swbt-python",
        "Switch model",
        "Switch firmware",
        "report period",
        "command / test",
        "approval",
        "result",
        "artifact",
        "cleanup",
        "notes",
    ]

    assert "## Run Entry Template" in text
    assert "### YYYY-MM-DD: short title" in text
    for field in required_fields:
        assert f"- {field}:" in text


def test_hardware_test_log_has_support_matrix_columns() -> None:
    text = HARDWARE_LOG.read_text(encoding="utf-8")

    expected_columns = [
        "OS",
        "Bluetooth dongle",
        "Driver",
        "Adapter",
        "Switch model",
        "Firmware",
        "Pairing",
        "L2CAP",
        "Subcommands",
        "Input reflected",
        "Result source",
        "Last updated",
        "Notes",
    ]

    assert "## Hardware Matrix" in text
    matrix_header = next(
        line for line in text.splitlines() if line.startswith("| OS | Bluetooth dongle |")
    )
    for column in expected_columns:
        assert f"| {column} " in matrix_header


def test_hardware_test_log_matrix_records_current_switch_model_and_firmware() -> None:
    text = HARDWARE_LOG.read_text(encoding="utf-8")

    windows_row = next(
        line for line in text.splitlines() if line.startswith("| Windows | CSR8510 A10 |")
    )

    assert "| Switch 2 |" in windows_row
    assert "| 22.1.0 |" in windows_row
