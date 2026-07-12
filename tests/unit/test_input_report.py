import pytest

from swbt.errors import UnsupportedInputError
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.subcommand import SubcommandSessionState


def _mode_2_component_2(report: bytes) -> int:
    motion = report[13:49]
    encoded = ((int.from_bytes(motion[18:21], "little") & 0x7FFFF) << 2) | (motion[11] >> 6)
    return encoded - (1 << 21) if encoded & (1 << 20) else encoded


def test_neutral_0x30_report_has_report_id_and_49_byte_length() -> None:
    report = InputReportBuilder().build_0x30(InputState.neutral())

    assert report[0] == 0x30
    assert len(report) == 49


def test_button_a_is_reflected_in_button_byte() -> None:
    report = InputReportBuilder().build_0x30(InputState.neutral().with_buttons([Button.A]))

    assert report[3] == 0x08
    assert report[4] == 0x00
    assert report[5] == 0x00


def test_buttons_l_and_r_are_reflected_together() -> None:
    report = InputReportBuilder().build_0x30(
        InputState.neutral().with_buttons([Button.L, Button.R])
    )

    assert report[3] == 0x40
    assert report[4] == 0x00
    assert report[5] == 0x40


def test_dpad_buttons_are_reflected_as_individual_bits() -> None:
    report = InputReportBuilder().build_0x30(
        InputState.neutral().with_buttons(
            [Button.DPAD_DOWN, Button.DPAD_UP, Button.DPAD_RIGHT, Button.DPAD_LEFT]
        )
    )

    assert report[3] == 0x00
    assert report[4] == 0x00
    assert report[5] == 0x0F


def test_stick_center_is_packed_as_12_bit_values() -> None:
    report = InputReportBuilder().build_0x30(InputState.neutral())

    assert report[6:9] == bytes.fromhex("00 08 80")
    assert report[9:12] == bytes.fromhex("00 08 80")


def test_custom_sticks_are_packed_as_12_bit_values() -> None:
    state = InputState.neutral().with_sticks(
        left_stick=Stick.raw(x=0x123, y=0xABC),
        right_stick=Stick.raw(x=0xFFF, y=0x000),
    )

    report = InputReportBuilder().build_0x30(state)

    assert report[6:9] == bytes.fromhex("23 c1 ab")
    assert report[9:12] == bytes.fromhex("ff 0f 00")


def test_imu_frames_are_packed_as_i16_little_endian_values() -> None:
    frame = IMUFrame(
        accel_x=1,
        accel_y=-2,
        accel_z=3,
        gyro_x=-4,
        gyro_y=5,
        gyro_z=-6,
    )
    state = InputState(
        buttons=frozenset(),
        left_stick=Stick.center(),
        right_stick=Stick.center(),
        imu_frames=(frame, frame, frame),
    )

    report = InputReportBuilder().build_0x30(state)

    assert report[13:25] == bytes.fromhex("01 00 fe ff 03 00 fc ff 05 00 fa ff")
    assert report[25:37] == bytes.fromhex("01 00 fe ff 03 00 fc ff 05 00 fa ff")
    assert report[37:49] == bytes.fromhex("01 00 fe ff 03 00 fc ff 05 00 fa ff")


def test_imu_mode_02_packs_identity_quaternion_instead_of_standard_gyro() -> None:
    session_state = SubcommandSessionState(imu_mode=0x02, imu_enabled=True)
    builder = InputReportBuilder(session_state=session_state, clock_ns=lambda: 0)
    state = InputState.neutral().with_accel((0, 0, 4096)).with_gyro((0, 0, 1234))

    report = builder.build_0x30(state)

    assert report[13:19] == bytes.fromhex("00 00 00 00 00 10")
    assert report[19] & 0x0F == 0x0E
    assert report[25:31] == bytes.fromhex("00 00 00 00 00 10")
    assert report[37:43] == bytes.fromhex("00 00 00 00 00 10")
    assert report[48] >> 2 == 3


@pytest.mark.parametrize("profile", [JoyConLeftProfile(), JoyConRightProfile()])
@pytest.mark.parametrize("imu_mode", [0x02, 0x03, 0x04, 0x05])
def test_joycon_quaternion_modes_use_mode_2_motion_packing(
    profile: JoyConLeftProfile | JoyConRightProfile,
    imu_mode: int,
) -> None:
    session_state = SubcommandSessionState(imu_mode=imu_mode, imu_enabled=True)
    builder = InputReportBuilder(
        profile,
        session_state=session_state,
        clock_ns=lambda: 0,
    )
    state = InputState.neutral().with_accel((0, 0, 4096))

    report = builder.build_0x30(state)

    assert report[19] & 0x0F == 0x0E
    assert report[48] >> 2 == 3


def test_imu_mode_02_quaternion_distinguishes_positive_and_negative_z_rotation() -> None:
    now_ns = 0

    def clock_ns() -> int:
        return now_ns

    session_state = SubcommandSessionState(imu_mode=0x02, imu_enabled=True)
    positive = InputReportBuilder(session_state=session_state, clock_ns=clock_ns)
    negative = InputReportBuilder(session_state=session_state, clock_ns=clock_ns)
    positive_state = InputState.neutral().with_gyro((0, 0, 1000))
    negative_state = InputState.neutral().with_gyro((0, 0, -1000))
    positive.build_0x30(positive_state)
    negative.build_0x30(negative_state)

    now_ns = 1_000_000_000
    positive_report = positive.build_0x30(positive_state)
    negative_report = negative.build_0x30(negative_state)

    assert positive_report[13:49] != negative_report[13:49]

    assert _mode_2_component_2(positive_report) > 0
    assert _mode_2_component_2(negative_report) < 0

    assert positive_report[13:49] != bytes(36)
    assert negative_report[13:49] != bytes(36)


def test_repeated_imu_mode_02_request_resets_quaternion_orientation() -> None:
    now_ns = 0

    def clock_ns() -> int:
        return now_ns

    session_state = SubcommandSessionState(imu_mode=0x02, imu_enabled=True)
    builder = InputReportBuilder(session_state=session_state, clock_ns=clock_ns)
    state = InputState.neutral().with_gyro((0, 0, 1000))
    initial_report = builder.build_0x30(state)

    now_ns = 1_000_000_000
    rotated_report = builder.build_0x30(state)
    assert _mode_2_component_2(rotated_report) > 0

    session_state.imu_mode_revision += 1
    now_ns = 2_000_000_000
    reset_report = builder.build_0x30(state)

    assert _mode_2_component_2(initial_report) == 0
    assert _mode_2_component_2(reset_report) == 0


@pytest.mark.parametrize(
    ("button", "button_bytes"),
    [
        (Button.Y, bytes.fromhex("01 00 00")),
        (Button.X, bytes.fromhex("02 00 00")),
        (Button.B, bytes.fromhex("04 00 00")),
        (Button.A, bytes.fromhex("08 00 00")),
        (Button.R, bytes.fromhex("40 00 00")),
        (Button.ZR, bytes.fromhex("80 00 00")),
        (Button.MINUS, bytes.fromhex("00 01 00")),
        (Button.PLUS, bytes.fromhex("00 02 00")),
        (Button.RIGHT_STICK, bytes.fromhex("00 04 00")),
        (Button.LEFT_STICK, bytes.fromhex("00 08 00")),
        (Button.HOME, bytes.fromhex("00 10 00")),
        (Button.CAPTURE, bytes.fromhex("00 20 00")),
        (Button.DPAD_DOWN, bytes.fromhex("00 00 01")),
        (Button.DPAD_UP, bytes.fromhex("00 00 02")),
        (Button.DPAD_RIGHT, bytes.fromhex("00 00 04")),
        (Button.DPAD_LEFT, bytes.fromhex("00 00 08")),
        (Button.L, bytes.fromhex("00 00 40")),
        (Button.ZL, bytes.fromhex("00 00 80")),
    ],
)
def test_all_exposed_buttons_pack_to_button_bytes(button: Button, button_bytes: bytes) -> None:
    report = InputReportBuilder().build_0x30(InputState.neutral().with_buttons([button]))

    assert report[3:6] == button_bytes


@pytest.mark.parametrize("button", [Button.SL, Button.SR])
def test_pro_controller_rejects_single_joycon_sl_sr_buttons(button: Button) -> None:
    with pytest.raises(UnsupportedInputError):
        InputReportBuilder().build_0x30(InputState.neutral().with_buttons([button]))


def test_joycon_left_profile_packs_supported_buttons() -> None:
    state = InputState.neutral().with_buttons(
        [
            Button.DPAD_DOWN,
            Button.DPAD_UP,
            Button.DPAD_RIGHT,
            Button.DPAD_LEFT,
            Button.L,
            Button.ZL,
            Button.MINUS,
            Button.CAPTURE,
            Button.LEFT_STICK,
            Button.SL,
            Button.SR,
        ]
    )

    report = InputReportBuilder(JoyConLeftProfile()).build_0x30(state)

    assert report[3:6] == bytes.fromhex("00 29 ff")


def test_joycon_right_profile_packs_supported_buttons() -> None:
    state = InputState.neutral().with_buttons(
        [
            Button.A,
            Button.B,
            Button.X,
            Button.Y,
            Button.R,
            Button.ZR,
            Button.PLUS,
            Button.HOME,
            Button.RIGHT_STICK,
            Button.SL,
            Button.SR,
        ]
    )

    report = InputReportBuilder(JoyConRightProfile()).build_0x30(state)

    assert report[3:6] == bytes.fromhex("ff 16 00")


def test_joycon_left_profile_rejects_unsupported_right_side_inputs() -> None:
    state = InputState.neutral().with_buttons([Button.A])

    with pytest.raises(UnsupportedInputError):
        InputReportBuilder(JoyConLeftProfile()).build_0x30(state)


def test_joycon_right_profile_rejects_unsupported_left_side_inputs() -> None:
    state = InputState.neutral().with_buttons([Button.DPAD_LEFT])

    with pytest.raises(UnsupportedInputError):
        InputReportBuilder(JoyConRightProfile()).build_0x30(state)


def test_joycon_profiles_reject_unsupported_non_neutral_sticks() -> None:
    left_state_with_right_stick = InputState.neutral().with_sticks(right_stick=Stick.right())
    right_state_with_left_stick = InputState.neutral().with_sticks(left_stick=Stick.left())

    with pytest.raises(UnsupportedInputError):
        InputReportBuilder(JoyConLeftProfile()).build_0x30(left_state_with_right_stick)
    with pytest.raises(UnsupportedInputError):
        InputReportBuilder(JoyConRightProfile()).build_0x30(right_state_with_left_stick)


def test_joycon_profiles_allow_their_supported_stick_side() -> None:
    left_report = InputReportBuilder(JoyConLeftProfile()).build_0x30(
        InputState.neutral().with_sticks(left_stick=Stick.up())
    )
    right_report = InputReportBuilder(JoyConRightProfile()).build_0x30(
        InputState.neutral().with_sticks(right_stick=Stick.right())
    )

    assert left_report[6:9] == bytes.fromhex("00 f8 ff")
    assert right_report[9:12] == bytes.fromhex("ff 0f 80")
