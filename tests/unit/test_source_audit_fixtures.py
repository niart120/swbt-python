"""Mechanical checks for the structured source-audit fixture."""

import tomllib
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "unit" / "fixtures" / "source_audit" / "switch_protocol_values.toml"

ALLOWED_CLASSIFICATIONS = {
    "source fact",
    "implementation fact",
    "hardware observation",
    "inference",
    "unverified hypothesis",
}
ALLOWED_STATUSES = {
    "configurable",
    "handoff-ready",
    "hardware-observed-only",
    "implementation-policy",
    "profile-boundary-policy",
    "profile-default-policy",
    "profile-policy",
    "session-state-policy",
    "source-backed-hardware-observed",
    "source-backed-lifecycle-policy",
    "source-backed-profile-policy",
    "stable",
    "stable-profile-core",
    "stable-raw-only",
    "stable-sdp-policy",
    "stable-virtual-profile",
    "version-pinned",
}
REQUIRED_ENTRY_IDS = {
    "input_report_0x30_layout",
    "button_bit_and_stick_pack",
    "output_report_parser_layout",
    "subcommand_reply_0x21_layout",
    "subcommand_reply_payloads",
    "device_info_swbt_pro_profile",
    "device_info_grip_color_tail_0302",
    "joycon_device_info_profile",
    "device_info_local_bluetooth_address_wiring",
    "factory_accelerometer_calibration_layout",
    "factory_gyro_calibration_layout",
    "joycon_spi_device_type_values",
    "joycon_default_controller_color_profile",
    "joycon_standard_button_mapping",
    "joycon_standard_stick_availability",
    "subcommand_report_mode_session_state",
    "subcommand_imu_vibration_enable_state",
    "profile_aware_trigger_buttons_elapsed",
    "protocol_ready_player_lights_policy",
    "subcommand_nfc_ir_mcu_state",
    "subcommand_nfc_ir_mcu_state_ack_policy",
    "pro_controller_imu_enable_mode_02_observation",
    "pro_controller_imu_mode_02_quaternion_format",
    "profile_aware_bumble_sdp_boundary",
    "joycontrol_sdp_record_policy",
    "spi_flash_boundary_and_seed_map",
    "raw_rumble_payload",
    "hid_report_descriptor",
    "bumble_hid_device_api",
    "bumble_classic_visibility",
    "bumble_l2cap_connection_events",
    "bumble_reference_classic_link_policy",
    "bumble_acl_packet_queue_drain_boundary",
    "bumble_hidp_output_report_boundary",
    "btstack_reference_hid_sdp_policy",
    "swbt_daemon_reference_discovery_identity",
    "swbt_daemon_reference_discovery_identity_hci",
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
        assert item
        values.append(item)
    return values


def test_source_audit_fixture_covers_unit_009_inventory() -> None:
    entries = _fixture_entries()
    entry_ids = {entry["id"] for entry in entries}

    assert entry_ids >= REQUIRED_ENTRY_IDS
    assert len(entry_ids) == len(entries)


def test_source_audit_entries_have_structured_fields() -> None:
    for entry in _fixture_entries():
        assert isinstance(entry.get("id"), str)
        assert entry["id"]
        assert isinstance(entry.get("fixture_name"), str)
        assert entry["fixture_name"]
        assert isinstance(entry.get("area"), str)
        assert entry["area"]
        assert isinstance(entry.get("value"), str)
        assert entry["value"]
        assert entry["classification"] in ALLOWED_CLASSIFICATIONS
        assert entry["status"] in ALLOWED_STATUSES
        _string_list(entry, "source")
        _string_list(entry, "handoff")


def test_source_audit_sources_are_paths_or_urls() -> None:
    for entry in _fixture_entries():
        for source in _string_list(entry, "source"):
            if source.startswith(("http://", "https://")):
                parsed = urlparse(source)
                assert parsed.scheme in {"http", "https"}
                assert parsed.netloc
            else:
                assert "\\" in source or "/" in source or ":" in source


def test_hardware_observations_have_condition_and_observation_status() -> None:
    for entry in _fixture_entries():
        if entry["classification"] == "hardware observation":
            assert entry["status"] == "hardware-observed-only"
            condition = entry.get("condition")
            assert isinstance(condition, str)
            assert condition
