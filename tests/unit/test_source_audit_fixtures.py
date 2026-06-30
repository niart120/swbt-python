"""Source audit fixture checks."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "unit" / "fixtures" / "source_audit" / "switch_protocol_values.toml"

ALLOWED_CLASSIFICATIONS = {
    "source fact",
    "implementation fact",
    "hardware observation",
    "inference",
    "unverified hypothesis",
}

REQUIRED_ENTRY_IDS = {
    "input_report_0x30_layout",
    "button_bit_and_stick_pack",
    "output_report_parser_layout",
    "subcommand_reply_0x21_layout",
    "subcommand_reply_payloads",
    "device_info_swbt_pro_profile",
    "spi_flash_boundary_and_seed_map",
    "raw_rumble_payload",
    "hid_report_descriptor",
    "bumble_hid_device_api",
    "bumble_classic_visibility",
    "report_period_default",
    "swbt_python_adapter_driver_boundary",
    "swbt_daemon_csr8510_winusb_observation",
}


def _fixture_entries() -> list[dict[str, object]]:
    data = tomllib.loads(FIXTURE.read_text(encoding="utf-8"))
    raw_entries = data["entry"]
    assert isinstance(raw_entries, list)

    entries: list[dict[str, object]] = []
    for raw_entry in raw_entries:
        assert isinstance(raw_entry, dict)
        entries.append(raw_entry)
    return entries


def _string_list(entry: dict[str, object], key: str) -> list[str]:
    raw_value = entry[key]
    assert isinstance(raw_value, list)
    values: list[str] = []
    for item in raw_value:
        assert isinstance(item, str)
        values.append(item)
    return values


def _entry_by_id(entry_id: str) -> dict[str, object]:
    for entry in _fixture_entries():
        if entry["id"] == entry_id:
            return entry
    raise AssertionError


def test_source_audit_fixture_covers_unit_009_inventory() -> None:
    entries = _fixture_entries()
    entry_ids = {entry["id"] for entry in entries}

    assert entry_ids >= REQUIRED_ENTRY_IDS
    assert len(entry_ids) == len(entries)


def test_source_audit_entries_have_classification_source_and_handoff() -> None:
    for entry in _fixture_entries():
        assert entry["classification"] in ALLOWED_CLASSIFICATIONS
        assert isinstance(entry["fixture_name"], str)
        assert isinstance(entry["value"], str)
        assert isinstance(entry["status"], str)
        assert _string_list(entry, "source")
        assert _string_list(entry, "handoff")


def test_hardware_observations_are_condition_scoped() -> None:
    for entry in _fixture_entries():
        if entry["classification"] == "hardware observation":
            assert entry["status"] == "hardware-observed-only"
            assert isinstance(entry["condition"], str)
            assert entry["condition"]


def test_swbt_python_adapter_boundary_is_condition_scoped_observation() -> None:
    entry = _entry_by_id("swbt_python_adapter_driver_boundary")

    assert entry["classification"] == "hardware observation"
    assert entry["status"] == "hardware-observed-only"
    condition = entry["condition"]
    value = entry["value"]

    assert isinstance(condition, str)
    assert isinstance(value, str)
    assert "open/close only" in condition
    assert "input reflection remain unverified" in value


def test_default_report_period_remains_configurable() -> None:
    entry = _entry_by_id("report_period_default")

    assert entry["classification"] == "inference"
    assert entry["status"] == "configurable"
