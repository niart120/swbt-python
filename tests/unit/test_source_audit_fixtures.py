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
    assert "M3 pairing/L2CAP hardware test" in condition
    assert "SDP service-name M4 attempt" in condition
    assert "reset-state M4 attempt" in condition
    assert "link-policy M4 hardware test" in condition
    assert "link-policy-only M4 hardware test" in condition
    assert "observation-window M4 hardware test" in condition
    assert "discoverable / connectable" in value
    assert "Classic pairing" in value
    assert "HID control / interrupt L2CAP open" in value
    assert "SDP service-name" in value
    assert "reset-state attempts" in value
    assert "Classic default link policy 0x0005" in value
    assert "a2 01" in value
    assert "a1 21" in value
    assert "observation-window M4 run" in value
    assert "subcommand 0x02 x1 and 0x08 x8" in value
    assert "0x21 replies for all observed subcommands" in value
    assert "no unsupported_subcommand or error events" in value
    assert "no Bumble debug log packets-in-flight backlog matches" in value
    assert "without HID L2CAP MTU 100 re-registration" in value
    assert "0x8e/0x80 profile prefix change" in value
    assert "no SDP PSM query" in value
    assert "observed no HID CONTROL PDU" in value
    assert "output_report_rx" in value
    assert "no semantic input reflection" in condition
    assert "semantic input reflection" in value
    assert "key store behavior remain unverified" in value


def test_bumble_hidp_output_report_boundary_is_version_pinned_source_fact() -> None:
    entry = _entry_by_id("bumble_hidp_output_report_boundary")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "version-pinned"
    value = entry["value"]

    assert isinstance(value, str)
    assert "HIDP header byte" in value
    assert "EVENT_INTERRUPT_DATA" in value
    assert "EVENT_CONTROL_DATA" in value
    assert "SET_REPORT callback receives report_id separated" in value


def test_bumble_acl_packet_queue_boundary_is_implementation_policy() -> None:
    entry = _entry_by_id("bumble_acl_packet_queue_drain_boundary")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "implementation-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "hid.HID.send_data writes the HID interrupt PDU" in value
    assert "Host.send_acl_sdu" in value
    assert "DataPacketQueue exposes pending" in value
    assert "drain(connection_handle)" in value
    assert "does not inspect or drain the ACL queue per report" in value
    assert "Before an explicit disconnect" in value
    assert "connection.device.host.get_data_packet_queue(handle)" in value


def test_bumble_reference_classic_link_policy_is_implementation_policy() -> None:
    entry = _entry_by_id("bumble_reference_classic_link_policy")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "implementation-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "ROLE_SWITCH|SNIFF_MODE" in value
    assert "0x0005" in value
    assert "before connectable/discoverable advertising" in value
    assert "outgoing classic ACL" in value
    assert "not treated as an incoming Switch connection fix" in value


def test_btstack_reference_hid_sdp_policy_is_handoff_ready() -> None:
    entry = _entry_by_id("btstack_reference_hid_sdp_policy")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "handoff-ready"
    value = entry["value"]

    assert isinstance(value, str)
    assert "service name attribute 0x0100" in value
    assert "LanguageBaseAttributeIDList en/UTF-8/base 0x0100" in value
    assert "HID language base 0x0409/0x0100" in value
    assert "country code 0x21" in value
    assert "remote wake true" in value
    assert "supervision timeout 0x0c80" in value
    assert "SSR host max latency 0xffff" in value
    assert "SSR host min timeout 0xffff" in value


def test_default_report_period_remains_configurable() -> None:
    entry = _entry_by_id("report_period_default")

    assert entry["classification"] == "inference"
    assert entry["status"] == "configurable"


def test_pro_device_info_reference_and_current_tail_are_separated() -> None:
    reference = _entry_by_id("device_info_swbt_pro_profile")
    observation = _entry_by_id("device_info_grip_color_tail_0302")

    assert reference["classification"] == "implementation fact"
    assert observation["classification"] == "hardware observation"

    value = reference["value"]
    assert isinstance(value, str)
    assert "swbt-daemon reference" in value
    assert "tail=01 01" in value
    assert "Current swbt-python ProControllerProfile uses tail=03 02" in value
    assert "device_info_grip_color_tail_0302" in value


def test_joycon_device_info_profile_is_source_audited() -> None:
    entry = _entry_by_id("joycon_device_info_profile")

    assert entry["classification"] in {"source fact", "implementation fact"}
    assert entry["status"] == "stable-profile-core"
    value = entry["value"]

    assert isinstance(value, str)
    assert "JOYCON_L=0x01" in value
    assert "JOYCON_R=0x02" in value
    assert "marker=0x02" in value
    assert "tail=01 01" in value


def test_device_info_local_bluetooth_address_wiring_is_recorded() -> None:
    entry = _entry_by_id("device_info_local_bluetooth_address_wiring")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "implementation-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "transport.local_bluetooth_address()" in value
    assert "after pairing advertising or connection completion" in value
    assert "before power_on()" in value
    assert "Device Info" in value
    assert "Bumble Address bytes" in value
    assert "display order" in value


def test_joycon_spi_device_type_values_are_source_audited() -> None:
    entry = _entry_by_id("joycon_spi_device_type_values")

    assert entry["classification"] in {"source fact", "implementation fact"}
    assert entry["status"] == "stable-profile-core"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x6012" in value
    assert "JOYCON_L=0x01" in value
    assert "JOYCON_R=0x02" in value


def test_joycon_default_controller_colors_are_recorded() -> None:
    entry = _entry_by_id("joycon_default_controller_color_profile")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "profile-default-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x6050-0x605B" in value
    assert "body=0x00B2FF" in value
    assert "body=0xFF3B30" in value
    assert "controller_colors overrides" in value
    assert "not claimed as factory Joy-Con color bytes" in value


def test_joycon_standard_button_mapping_is_source_audited() -> None:
    entry = _entry_by_id("joycon_standard_button_mapping")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "stable-profile-core"
    value = entry["value"]

    assert isinstance(value, str)
    assert "byte3_right" in value
    assert "byte5_left" in value
    assert "SL" in value
    assert "SR" in value


def test_joycon_standard_stick_availability_is_recorded() -> None:
    entry = _entry_by_id("joycon_standard_stick_availability")

    assert entry["classification"] in {"source fact", "inference"}
    assert entry["status"] == "profile-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "JOYCON_L left stick only" in value
    assert "JOYCON_R right stick only" in value


def test_subcommand_report_mode_session_state_is_source_audited() -> None:
    entry = _entry_by_id("subcommand_report_mode_session_state")

    assert entry["classification"] in {"source fact", "implementation fact"}
    assert entry["status"] == "session-state-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x03" in value
    assert "0x30" in value
    assert "0x3F" in value
    assert "not coerced" in value


def test_subcommand_imu_vibration_enable_state_is_source_audited() -> None:
    entry = _entry_by_id("subcommand_imu_vibration_enable_state")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "session-state-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x40" in value
    assert "0x48" in value
    assert "0x00" in value
    assert "0x01" in value
    assert "SwitchHidSessionState" in value


def test_factory_gyro_calibration_layout_is_source_audited() -> None:
    entry = _entry_by_id("factory_gyro_calibration_layout")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "stable-virtual-profile"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x602c-0x6037" in value
    assert "zero_x,zero_y,zero_z,reference_x,reference_y,reference_z" in value
    assert "Int16LE" in value
    assert "zero=0" in value
    assert "reference=0x343b" in value
    assert "0.070 dps/raw" in value
    assert "816/936" in value


def test_factory_accelerometer_calibration_layout_is_source_audited() -> None:
    entry = _entry_by_id("factory_accelerometer_calibration_layout")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "stable-virtual-profile"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x6020-0x602b" in value
    assert "zero_x,zero_y,zero_z,reference_x,reference_y,reference_z" in value
    assert "Int16LE" in value
    assert "zero=0" in value
    assert "reference=0x4000" in value
    assert "reference acceleration=4.0 G" in value
    assert "1/4096 G/raw" in value
    assert "physical acceleration API" in value


def test_subcommand_nfc_ir_mcu_state_is_source_audited() -> None:
    entry = _entry_by_id("subcommand_nfc_ir_mcu_state")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "session-state-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x22" in value
    assert "NFC/IR MCU state" in value
    assert "0x00" in value
    assert "0x01" in value
    assert "0x02" in value


def test_subcommand_nfc_ir_mcu_state_ack_policy_is_recorded() -> None:
    entry = _entry_by_id("subcommand_nfc_ir_mcu_state_ack_policy")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "implementation-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "0x22" in value
    assert "ACK-compatible" in value
    assert "0x80" in value
    assert "reply-to 0x22" in value
    assert "does not model" in value


def test_joycon_imu_enable_mode_02_is_hardware_observed() -> None:
    entry = _entry_by_id("joycon_imu_enable_mode_02")

    assert entry["classification"] == "hardware observation"
    assert entry["status"] == "hardware-observed-only"
    value = entry["value"]

    assert isinstance(value, str)
    assert "Joy-Con (L)" in value
    assert "0x40" in value
    assert "0x02" in value
    assert "Joy-Con profiles" in value
    assert "Pro Controller" in value
    assert "SR+SL" in value


def test_pro_controller_imu_enable_mode_02_observation_is_hardware_observed() -> None:
    entry = _entry_by_id("pro_controller_imu_enable_mode_02_observation")

    assert entry["classification"] == "hardware observation"
    assert entry["status"] == "hardware-observed-only"
    value = entry["value"]

    assert isinstance(value, str)
    assert "ProController P2 hardware reruns" in value
    assert "device_name=Pro Controller" in value
    assert "class_of_device=0x002508" in value
    assert "ProCon toast" in value
    assert "0x40" in value
    assert "0x02" in value
    assert "a2010400014040000140404002" in value
    assert "hardware-observed compatibility mode" in value
    assert "SwitchHidSessionState.imu_mode" in value
    assert "does not supersede the 0x00/0x01 source fact" in value


def test_pro_controller_imu_mode_02_quaternion_format_is_source_audited() -> None:
    entry = _entry_by_id("pro_controller_imu_mode_02_quaternion_format")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "source-backed-hardware-observed"
    value = entry["value"]

    assert isinstance(value, str)
    assert "mode 0x01 selects StandardMotionPacker" in value
    assert "modes 0x02-0x05 select QuaternionMotionPacker" in value
    assert "three XYZ Int16LE acceleration samples" in value
    assert "signed 21-bit fixed-point components" in value
    assert "11-bit millisecond timestamp" in value
    assert "sample count 3" in value
    assert "left rotation, stop, right rotation, stop" in value
    assert "does not establish Joy-Con axis direction" in value
    assert "same mode dispatch and wire packer" in value


def test_profile_aware_bumble_sdp_boundary_is_source_audited() -> None:
    entry = _entry_by_id("profile_aware_bumble_sdp_boundary")

    assert entry["classification"] == "implementation fact"
    assert entry["status"] == "profile-boundary-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "ControllerProfile.hid_report_descriptor" in value
    assert "profile.device_name" in value
    assert "explicit device_name override" in value
    assert "Class of Device 0x002508" in value
    assert "Pro-compatible fixed" in value
    assert "joycontrol_sdp_record_policy" in value
    assert "Joy-Con descriptor bytes remain unaudited" in value


def test_joycontrol_sdp_record_policy_is_source_audited() -> None:
    entry = _entry_by_id("joycontrol_sdp_record_policy")

    assert entry["classification"] == "source fact"
    assert entry["status"] == "stable-sdp-policy"
    value = entry["value"]

    assert isinstance(value, str)
    assert "Wireless Gamepad" in value
    assert "Gamepad" in value
    assert "Nintendo" in value
    assert "0x0203=0x00" in value
    assert "0x020b=0x0100" in value
    assert "omits HID remote wake" in value
    assert "0x020d=false" in value
    assert "0x020e=true" in value
    assert "0x0640/0x0320" in value
    assert "not a new Joy-Con-specific descriptor source" in value
