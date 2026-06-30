import pytest

from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.input_report import InputReportBuilder


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
