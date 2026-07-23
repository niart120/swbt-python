import pytest

from swbt.errors import ProtocolError
from swbt.input import IMUFrame, InputState
from swbt.protocol.imu_report import ImuEncodingState, ImuMode
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.output_report import OutputReport, OutputReportParser
from swbt.protocol.profiles.base import ControllerColors
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import ProControllerProfile
from swbt.protocol.session import SwitchHidSession
from swbt.protocol.subcommand import (
    SubcommandResponder,
    UnsupportedSubcommandError,
)

NEUTRAL_RUMBLE = bytes.fromhex("00 01 40 40 00 01 40 40")


def _subcommand_report(subcommand_id: int, payload: bytes = b"") -> OutputReport:
    return OutputReportParser().parse(
        bytes((0x01, 0x0A)) + NEUTRAL_RUMBLE + bytes((subcommand_id,)) + payload
    )


def _reply(subcommand_id: int, payload: bytes = b"") -> bytes:
    profile = ProControllerProfile()
    return SubcommandResponder(profile=profile).respond(
        _subcommand_report(subcommand_id, payload),
        state=InputState.neutral(),
        session=SwitchHidSession(profile),
    )


def test_default_reports_full_battery_without_charging_or_external_power() -> None:
    report = InputReportBuilder().build_0x30(InputState.neutral())
    reply = _reply(0x02)

    assert report[2] == 0x80
    assert reply[2] == 0x80


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


def test_device_info_subcommand_updates_bluetooth_address_without_new_responder() -> None:
    responder = SubcommandResponder()

    responder.set_device_info_bluetooth_address(bytes.fromhex("00 1b dc f9 9f 7d"))
    reply = responder.respond(_subcommand_report(0x02), state=InputState.neutral())

    assert reply[15:27] == bytes.fromhex("04 00 03 02 00 1b dc f9 9f 7d 03 02")


def test_trigger_buttons_elapsed_subcommand_builds_pairing_reply() -> None:
    reply = _reply(0x04)

    assert reply[13] == 0x83
    assert reply[14] == 0x04
    assert reply[15:29] == bytes.fromhex("2c 01 2c 01 00 00 00 00 00 00 00 00 00 00")
    assert reply[29:] == bytes(21)


def test_set_input_report_mode_updates_session_state() -> None:
    responder = SubcommandResponder()
    session = SwitchHidSession(ProControllerProfile())

    reply = responder.respond(
        _subcommand_report(0x03, payload=b"\x30"),
        state=InputState.neutral(),
        session=session,
    )

    assert reply[13] == 0x80
    assert reply[14] == 0x03
    assert session.state.report_mode == 0x30
    assert session.state.report_mode_supported is True
    assert session.state.unsupported_report_mode is None


def test_unsupported_input_report_mode_is_recorded_without_coercing_to_0x30() -> None:
    responder = SubcommandResponder()
    session = SwitchHidSession(ProControllerProfile())

    reply = responder.respond(
        _subcommand_report(0x03, payload=b"\x3f"),
        state=InputState.neutral(),
        session=session,
    )

    assert reply[13] == 0x80
    assert reply[14] == 0x03
    assert session.state.report_mode == 0x3F
    assert session.state.report_mode_supported is False
    assert session.state.unsupported_report_mode == 0x3F


def test_enable_imu_updates_session_state() -> None:
    responder = SubcommandResponder()
    session = SwitchHidSession(ProControllerProfile())

    responder.respond(
        _subcommand_report(0x40, payload=b"\x01"),
        state=InputState.neutral(),
        session=session,
    )
    assert session.state.imu_mode is ImuMode.STANDARD
    assert session.state.imu_enabled is True
    assert session.state.imu_encoding_state == ImuEncodingState()

    responder.respond(
        _subcommand_report(0x40, payload=b"\x00"),
        state=InputState.neutral(),
        session=session,
    )
    assert session.state.imu_mode is ImuMode.DISABLED
    assert session.state.imu_enabled is False
    assert session.state.imu_encoding_state == ImuEncodingState()


def test_joycon_enable_imu_mode_0x02_updates_session_state() -> None:
    profile = JoyConLeftProfile()
    responder = SubcommandResponder(profile=profile)
    session = SwitchHidSession(profile)

    reply = responder.respond(
        _subcommand_report(0x40, payload=b"\x02"),
        state=InputState.neutral(),
        session=session,
    )

    assert reply[13] == 0x80
    assert reply[14] == 0x40
    assert session.state.imu_mode is ImuMode.QUATERNION_1
    assert session.state.imu_enabled is True


@pytest.mark.parametrize("profile", [JoyConLeftProfile(), JoyConRightProfile()])
@pytest.mark.parametrize("imu_mode", [0x02, 0x03, 0x04, 0x05])
def test_joycon_profiles_accept_quaternion_imu_modes(
    profile: JoyConLeftProfile | JoyConRightProfile,
    imu_mode: int,
) -> None:
    responder = SubcommandResponder(profile=profile)
    session = SwitchHidSession(profile)

    reply = responder.respond(
        _subcommand_report(0x40, payload=bytes((imu_mode,))),
        state=InputState.neutral(),
        session=session,
    )

    assert reply[13:15] == bytes.fromhex("80 40")
    assert session.state.imu_mode is ImuMode(imu_mode)


def test_enable_imu_rejects_unknown_mode_with_profile_accepted_modes() -> None:
    profile = JoyConLeftProfile()
    responder = SubcommandResponder(profile=profile)

    with pytest.raises(
        ProtocolError,
        match="must be one of: 0x00, 0x01, 0x02, 0x03, 0x04, 0x05",
    ):
        responder.respond(
            _subcommand_report(0x40, payload=b"\x06"),
            state=InputState.neutral(),
            session=SwitchHidSession(profile),
        )


def test_pro_controller_enable_imu_mode_0x02_updates_session_state() -> None:
    profile = ProControllerProfile()
    responder = SubcommandResponder(profile=profile)
    session = SwitchHidSession(profile)

    reply = responder.respond(
        _subcommand_report(0x40, payload=b"\x02"),
        state=InputState.neutral(),
        session=session,
    )

    assert reply[13] == 0x80
    assert reply[14] == 0x40
    assert session.state.imu_mode is ImuMode.QUATERNION_1
    assert session.state.imu_enabled is True


@pytest.mark.parametrize("imu_mode", [0x02, 0x03, 0x04, 0x05])
def test_pro_controller_accepts_quaternion_imu_modes(imu_mode: int) -> None:
    profile = ProControllerProfile()
    responder = SubcommandResponder(profile=profile)
    session = SwitchHidSession(profile)

    reply = responder.respond(
        _subcommand_report(0x40, payload=bytes((imu_mode,))),
        state=InputState.neutral(),
        session=session,
    )

    assert reply[13:15] == bytes.fromhex("80 40")
    assert session.state.imu_mode is ImuMode(imu_mode)


def test_enable_vibration_updates_session_state() -> None:
    profile = ProControllerProfile()
    responder = SubcommandResponder(profile=profile)
    session = SwitchHidSession(profile)

    responder.respond(
        _subcommand_report(0x48, payload=b"\x01"),
        state=InputState.neutral(),
        session=session,
    )
    assert session.state.vibration_enabled is True

    responder.respond(
        _subcommand_report(0x48, payload=b"\x00"),
        state=InputState.neutral(),
        session=session,
    )
    assert session.state.vibration_enabled is False


def test_controller_profile_does_not_hold_mutable_subcommand_session_state() -> None:
    profile = ProControllerProfile()

    assert not hasattr(profile, "report_mode")
    assert not hasattr(profile, "imu_mode")
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


def test_spi_flash_read_does_not_change_imu_session_state() -> None:
    profile = ProControllerProfile()
    session = SwitchHidSession(profile)
    responder = SubcommandResponder(profile=profile)
    state = InputState.neutral()
    session.set_imu_mode(0x02)
    session.encode_imu(state.imu_frames, now_ns=1_000_000_000)
    session.encode_imu(state.imu_frames, now_ns=1_015_000_000)
    before = session.state

    reply = responder.respond(
        _subcommand_report(0x10, payload=bytes.fromhex("2c 60 00 00 0c")),
        state=state,
        session=session,
    )

    assert reply[13:15] == bytes((0x90, 0x10))
    assert session.state == before


def test_imu_mode_request_does_not_change_factory_calibration_or_raw_input() -> None:
    profile = ProControllerProfile()
    session = SwitchHidSession(profile)
    responder = SubcommandResponder(profile=profile)
    state = InputState.neutral().with_imu(
        IMUFrame.raw(accel=(1, 2, 3), gyro=(4, 5, 6)),
        IMUFrame.raw(accel=(7, 8, 9), gyro=(10, 11, 12)),
        IMUFrame.raw(accel=(13, 14, 15), gyro=(16, 17, 18)),
    )
    spi_read = _subcommand_report(0x10, payload=bytes.fromhex("20 60 00 00 18"))
    calibration_before = responder.respond(spi_read, state=state, session=session)

    responder.respond(
        _subcommand_report(0x40, payload=b"\x02"),
        state=state,
        session=session,
    )
    calibration_after = responder.respond(spi_read, state=state, session=session)

    assert session.state.imu_mode is ImuMode.QUATERNION_1
    assert calibration_after == calibration_before
    assert state.imu_frames == (
        IMUFrame.raw(accel=(1, 2, 3), gyro=(4, 5, 6)),
        IMUFrame.raw(accel=(7, 8, 9), gyro=(10, 11, 12)),
        IMUFrame.raw(accel=(13, 14, 15), gyro=(16, 17, 18)),
    )


def test_mcu_config_subcommand_builds_config_reply() -> None:
    reply = _reply(0x21, payload=b"\x01")

    assert reply[13] == 0xA0
    assert reply[14] == 0x21
    assert reply[15:49] == bytes.fromhex(
        "01 00 ff 00 08 00 1b 01 00 00 00 00 00 00 00 00 00 00 00 00 "
        "00 00 00 00 00 00 00 00 00 00 00 00 00 c8"
    )
    assert reply[49] == 0x00


@pytest.mark.parametrize("mode", [0x00, 0x01, 0x02])
def test_set_nfc_ir_mcu_state_acknowledges_supported_modes(mode: int) -> None:
    reply = _reply(0x22, payload=bytes((mode,)))

    assert reply[13] == 0x80
    assert reply[14] == 0x22
    assert reply[15:] == bytes(35)


def test_set_nfc_ir_mcu_state_rejects_unknown_mode() -> None:
    with pytest.raises(ProtocolError, match="NFC/IR MCU state"):
        _reply(0x22, payload=b"\x03")


def test_unsupported_subcommand_error_keeps_diagnostic_fields() -> None:
    report = _subcommand_report(0x99, payload=b"\x01\x02")

    with pytest.raises(UnsupportedSubcommandError) as exc_info:
        SubcommandResponder().respond(report, state=InputState.neutral())

    assert exc_info.value.subcommand_id == 0x99
    assert exc_info.value.payload == b"\x01\x02"
