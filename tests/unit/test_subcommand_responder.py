import pytest

from swbt.input import InputState
from swbt.protocol.output_report import OutputReport, OutputReportParser
from swbt.protocol.profile import ControllerColors, JoyConLeftProfile, ProControllerProfile
from swbt.protocol.subcommand import (
    SubcommandResponder,
    SubcommandSessionState,
    UnsupportedSubcommandError,
)

NEUTRAL_RUMBLE = bytes.fromhex("00 01 40 40 00 01 40 40")


def _subcommand_report(subcommand_id: int, payload: bytes = b"") -> OutputReport:
    return OutputReportParser().parse(
        bytes((0x01, 0x0A)) + NEUTRAL_RUMBLE + bytes((subcommand_id,)) + payload
    )


def _reply(subcommand_id: int, payload: bytes = b"") -> bytes:
    return SubcommandResponder().respond(
        _subcommand_report(subcommand_id, payload), state=InputState.neutral()
    )


@pytest.mark.parametrize("subcommand_id", [0x03, 0x08, 0x30, 0x40, 0x48])
def test_simple_ack_subcommands_build_0x21_reply(subcommand_id: int) -> None:
    reply = _reply(subcommand_id, payload=b"\x01")

    assert len(reply) == 50
    assert reply[0] == 0x21
    assert reply[13] == 0x80
    assert reply[14] == subcommand_id
    assert reply[15:] == bytes(35)


def test_device_info_subcommand_builds_profile_reply() -> None:
    reply = _reply(0x02)

    assert reply[13] == 0x82
    assert reply[14] == 0x02
    assert reply[15:27] == bytes.fromhex("04 00 03 02 00 00 00 00 00 00 03 02")
    assert reply[27:] == bytes(23)


def test_device_info_subcommand_uses_configured_profile() -> None:
    responder = SubcommandResponder(profile=JoyConLeftProfile())

    reply = responder.respond(_subcommand_report(0x02), state=InputState.neutral())

    assert reply[13] == 0x82
    assert reply[14] == 0x02
    assert reply[15:27] == bytes.fromhex("04 00 01 02 00 00 00 00 00 00 01 01")
    assert reply[27:] == bytes(23)


def test_device_info_subcommand_uses_caller_bluetooth_address() -> None:
    responder = SubcommandResponder(
        device_info_bluetooth_address=bytes.fromhex("01 23 45 67 89 ab")
    )

    reply = responder.respond(_subcommand_report(0x02), state=InputState.neutral())

    assert reply[15:27] == bytes.fromhex("04 00 03 02 01 23 45 67 89 ab 03 02")


def test_trigger_buttons_elapsed_subcommand_builds_pairing_reply() -> None:
    reply = _reply(0x04)

    assert reply[13] == 0x83
    assert reply[14] == 0x04
    assert reply[15:29] == bytes.fromhex("2c 01 2c 01 00 00 00 00 00 00 00 00 00 00")
    assert reply[29:] == bytes(21)


def test_set_input_report_mode_updates_session_state() -> None:
    session_state = SubcommandSessionState()
    responder = SubcommandResponder(session_state=session_state)

    reply = responder.respond(_subcommand_report(0x03, payload=b"\x30"), state=InputState.neutral())

    assert reply[13] == 0x80
    assert reply[14] == 0x03
    assert session_state.report_mode == 0x30
    assert session_state.report_mode_supported is True
    assert session_state.unsupported_report_mode is None


def test_unsupported_input_report_mode_is_recorded_without_coercing_to_0x30() -> None:
    session_state = SubcommandSessionState()
    responder = SubcommandResponder(session_state=session_state)

    reply = responder.respond(_subcommand_report(0x03, payload=b"\x3f"), state=InputState.neutral())

    assert reply[13] == 0x80
    assert reply[14] == 0x03
    assert session_state.report_mode == 0x3F
    assert session_state.report_mode_supported is False
    assert session_state.unsupported_report_mode == 0x3F


def test_enable_imu_updates_session_state() -> None:
    session_state = SubcommandSessionState()
    responder = SubcommandResponder(session_state=session_state)

    responder.respond(_subcommand_report(0x40, payload=b"\x01"), state=InputState.neutral())
    assert session_state.imu_enabled is True

    responder.respond(_subcommand_report(0x40, payload=b"\x00"), state=InputState.neutral())
    assert session_state.imu_enabled is False


def test_enable_vibration_updates_session_state() -> None:
    session_state = SubcommandSessionState()
    responder = SubcommandResponder(session_state=session_state)

    responder.respond(_subcommand_report(0x48, payload=b"\x01"), state=InputState.neutral())
    assert session_state.vibration_enabled is True

    responder.respond(_subcommand_report(0x48, payload=b"\x00"), state=InputState.neutral())
    assert session_state.vibration_enabled is False


def test_controller_profile_does_not_hold_mutable_subcommand_session_state() -> None:
    profile = ProControllerProfile()

    assert not hasattr(profile, "report_mode")
    assert not hasattr(profile, "imu_enabled")
    assert not hasattr(profile, "vibration_enabled")


def test_spi_flash_read_subcommand_returns_request_prefix_and_seed_data() -> None:
    reply = _reply(0x10, payload=bytes.fromhex("12 60 00 00 01"))

    assert reply[13] == 0x90
    assert reply[14] == 0x10
    assert reply[15:21] == bytes.fromhex("12 60 00 00 01 03")
    assert reply[21:] == bytes(29)


def test_spi_flash_read_subcommand_returns_custom_controller_colors() -> None:
    profile = ProControllerProfile(
        controller_colors=ControllerColors(
            body=0x112233,
            buttons=0x445566,
            left_grip=0x778899,
            right_grip=0xAABBCC,
        )
    )
    responder = SubcommandResponder(profile=profile)
    report = _subcommand_report(0x10, payload=bytes.fromhex("50 60 00 00 0c"))

    reply = responder.respond(report, state=InputState.neutral())

    assert reply[13] == 0x90
    assert reply[14] == 0x10
    assert reply[15:32] == bytes.fromhex("50 60 00 00 0c 11 22 33 44 55 66 77 88 99 aa bb cc")
    assert reply[32:] == bytes(18)


def test_mcu_config_subcommand_builds_config_reply() -> None:
    reply = _reply(0x21, payload=b"\x01")

    assert reply[13] == 0xA0
    assert reply[14] == 0x21
    assert reply[15:49] == bytes.fromhex(
        "01 00 ff 00 08 00 1b 01 00 00 00 00 00 00 00 00 00 00 00 00 "
        "00 00 00 00 00 00 00 00 00 00 00 00 00 c8"
    )
    assert reply[49] == 0x00


def test_unsupported_subcommand_error_keeps_diagnostic_fields() -> None:
    report = _subcommand_report(0x99, payload=b"\x01\x02")

    with pytest.raises(UnsupportedSubcommandError) as exc_info:
        SubcommandResponder().respond(report, state=InputState.neutral())

    assert exc_info.value.subcommand_id == 0x99
    assert exc_info.value.payload == b"\x01\x02"
