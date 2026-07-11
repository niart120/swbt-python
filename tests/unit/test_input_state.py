from collections.abc import Callable
from math import inf, nan, radians
from typing import cast

import pytest

from swbt.errors import InvalidInputError
from swbt.input import Button, IMUFrame, InputState, Stick


def test_neutral_input_state_has_no_buttons_center_sticks_and_neutral_imu() -> None:
    state = InputState.neutral()

    assert state.buttons == frozenset()
    assert state.left_stick == Stick.center()
    assert state.right_stick == Stick.center()
    assert state.imu_frames == (IMUFrame.neutral(),) * 3


def test_button_model_includes_single_joycon_sl_and_sr() -> None:
    assert Button.SL.name == "SL"
    assert Button.SR.name == "SR"


@pytest.mark.parametrize(("x", "y"), [(-1, 2048), (4096, 2048), (2048, -1), (2048, 4096)])
def test_stick_raw_rejects_values_outside_12_bit_range(x: int, y: int) -> None:
    with pytest.raises(InvalidInputError):
        Stick.raw(x=x, y=y)


@pytest.mark.parametrize(("x", "y"), [(-1, 2048), (4096, 2048), (2048, -1), (2048, 4096)])
def test_stick_constructor_rejects_values_outside_12_bit_range(x: int, y: int) -> None:
    with pytest.raises(InvalidInputError):
        Stick(x=x, y=y)


@pytest.mark.parametrize(
    ("value", "expected_raw"),
    [
        (-1.0, 0),
        (0.0, 2048),
        (1.0, 4095),
    ],
)
def test_stick_normalized_converts_endpoints_to_raw_values(value: float, expected_raw: int) -> None:
    assert Stick.normalized(x=value, y=value) == Stick.raw(x=expected_raw, y=expected_raw)


@pytest.mark.parametrize(("x", "y"), [(-1.01, 0.0), (1.01, 0.0), (0.0, -1.01), (0.0, 1.01)])
def test_stick_normalized_rejects_values_outside_unit_range(x: float, y: float) -> None:
    with pytest.raises(InvalidInputError):
        Stick.normalized(x=x, y=y)


@pytest.mark.parametrize(
    ("x", "y"),
    [
        (0.0, 1.0),
        (0.25, -0.5),
        (1.0, 1.0),
    ],
)
def test_stick_tilt_matches_normalized_values(x: float, y: float) -> None:
    assert Stick.tilt(x, y) == Stick.normalized(x=x, y=y)


@pytest.mark.parametrize(("x", "y"), [(-1.01, 0.0), (1.01, 0.0), (0.0, -1.01), (0.0, 1.01)])
def test_stick_tilt_rejects_values_outside_unit_range(x: float, y: float) -> None:
    with pytest.raises(InvalidInputError):
        Stick.tilt(x, y)


def test_stick_direction_shorthands_return_full_tilt_values() -> None:
    assert Stick.up() == Stick.tilt(0.0, 1.0)
    assert Stick.down() == Stick.tilt(0.0, -1.0)
    assert Stick.left() == Stick.tilt(-1.0, 0.0)
    assert Stick.right() == Stick.tilt(1.0, 0.0)


def test_stick_direction_shorthands_accept_partial_amounts() -> None:
    assert Stick.up(0.5) == Stick.tilt(0.0, 0.5)
    assert Stick.down(0.5) == Stick.tilt(0.0, -0.5)
    assert Stick.left(0.25) == Stick.tilt(-0.25, 0.0)
    assert Stick.right(0.25) == Stick.tilt(0.25, 0.0)
    assert Stick.up(0.0) == Stick.center()


@pytest.mark.parametrize("factory", [Stick.up, Stick.down, Stick.left, Stick.right])
@pytest.mark.parametrize("amount", [-0.01, 1.01])
def test_stick_direction_shorthands_reject_amounts_outside_unit_range(
    factory: Callable[[float], Stick],
    amount: float,
) -> None:
    with pytest.raises(InvalidInputError):
        factory(amount)


@pytest.mark.parametrize("value", [-32769, 32768])
def test_imu_frame_constructor_rejects_values_outside_i16_range(value: int) -> None:
    with pytest.raises(InvalidInputError):
        IMUFrame(
            accel_x=value,
            accel_y=0,
            accel_z=0,
            gyro_x=0,
            gyro_y=0,
            gyro_z=0,
        )


def test_imu_frame_raw_defaults_to_neutral_and_sets_accel_and_gyro_axes() -> None:
    assert IMUFrame.raw() == IMUFrame.neutral()
    assert IMUFrame.raw(accel=(0, 0, 4096)) == IMUFrame(
        accel_x=0,
        accel_y=0,
        accel_z=4096,
        gyro_x=0,
        gyro_y=0,
        gyro_z=0,
    )
    assert IMUFrame.raw(gyro=(100, 0, -100)) == IMUFrame(
        accel_x=0,
        accel_y=0,
        accel_z=0,
        gyro_x=100,
        gyro_y=0,
        gyro_z=-100,
    )
    assert IMUFrame.raw(accel=(1, 2, 3), gyro=(4, 5, 6)) == IMUFrame(
        accel_x=1,
        accel_y=2,
        accel_z=3,
        gyro_x=4,
        gyro_y=5,
        gyro_z=6,
    )


@pytest.mark.parametrize(
    ("accel", "gyro"),
    [
        ((1, 2), None),
        ((1, 2, 3, 4), None),
        (None, (1, 2)),
        (None, (1, 2, 3, 4)),
    ],
)
def test_imu_frame_raw_rejects_axis_tuples_that_are_not_three_values(
    accel: tuple[int, ...] | None,
    gyro: tuple[int, ...] | None,
) -> None:
    with pytest.raises(InvalidInputError):
        IMUFrame.raw(
            accel=cast("tuple[int, int, int] | None", accel),
            gyro=cast("tuple[int, int, int] | None", gyro),
        )


@pytest.mark.parametrize("value", [-32769, 32768])
def test_imu_frame_raw_rejects_values_outside_i16_range(value: int) -> None:
    with pytest.raises(InvalidInputError):
        IMUFrame.raw(accel=(0, 0, value))
    with pytest.raises(InvalidInputError):
        IMUFrame.raw(gyro=(value, 0, 0))


def test_imu_frame_gyro_and_accel_shorthands_match_raw_construction() -> None:
    assert IMUFrame.gyro(100, 0, -100) == IMUFrame.raw(gyro=(100, 0, -100))
    assert IMUFrame.gyro(x=100) == IMUFrame.raw(gyro=(100, 0, 0))
    assert IMUFrame.accel(0, 0, 4096) == IMUFrame.raw(accel=(0, 0, 4096))
    assert IMUFrame.accel(z=4096) == IMUFrame.raw(accel=(0, 0, 4096))


def test_imu_frame_converts_three_axis_gyro_rates_between_rad_s_and_raw() -> None:
    rates = (radians(7.0), radians(-14.0), radians(0.07))

    frame = IMUFrame.gyro_rate(
        x_rad_s=rates[0],
        y_rad_s=rates[1],
        z_rad_s=rates[2],
    )

    assert frame == IMUFrame.gyro(100, -200, 1)
    assert frame.to_gyro_rate() == pytest.approx(rates)


def test_imu_frame_with_gyro_rate_preserves_accelerometer_axes() -> None:
    frame = IMUFrame.accel(1, 2, 3)

    updated = frame.with_gyro_rate(
        x_rad_s=radians(7.0),
        y_rad_s=radians(-14.0),
        z_rad_s=radians(0.07),
    )

    assert updated == IMUFrame.raw(accel=(1, 2, 3), gyro=(100, -200, 1))


def test_imu_frame_gyro_rate_accepts_i16_boundaries_and_rejects_out_of_range() -> None:
    frame = IMUFrame.gyro_rate(
        x_rad_s=radians(IMUFrame.MIN * 0.070),
        y_rad_s=radians(IMUFrame.MAX * 0.070),
    )

    assert frame == IMUFrame.gyro(IMUFrame.MIN, IMUFrame.MAX, 0)

    invalid_rates = (
        radians((IMUFrame.MIN - 1) * 0.070),
        radians((IMUFrame.MAX + 1) * 0.070),
        -inf,
        inf,
        nan,
    )
    for rate in invalid_rates:
        with pytest.raises(InvalidInputError):
            IMUFrame.gyro_rate(x_rad_s=rate)


def test_imu_frame_converts_three_axis_acceleration_between_g_and_raw() -> None:
    frame = IMUFrame.accel_g(x_g=1.0, y_g=-0.5, z_g=4.0)

    assert frame == IMUFrame.accel(4096, -2048, 16384)
    assert frame.to_accel_g() == pytest.approx((1.0, -0.5, 4.0))


def test_imu_frame_with_accel_g_preserves_gyroscope_axes() -> None:
    frame = IMUFrame.gyro(100, -200, 300)

    updated = frame.with_accel_g(x_g=1.0, y_g=-0.5, z_g=0.25)

    assert updated == IMUFrame.raw(accel=(4096, -2048, 1024), gyro=(100, -200, 300))


def test_imu_frame_accel_g_accepts_i16_boundaries_and_rejects_out_of_range() -> None:
    frame = IMUFrame.accel_g(x_g=IMUFrame.MIN / 4096, y_g=IMUFrame.MAX / 4096)

    assert frame == IMUFrame.accel(IMUFrame.MIN, IMUFrame.MAX, 0)

    for acceleration in ((IMUFrame.MIN - 1) / 4096, (IMUFrame.MAX + 1) / 4096, -inf, inf, nan):
        with pytest.raises(InvalidInputError):
            IMUFrame.accel_g(x_g=acceleration)


def test_imu_frame_update_helpers_preserve_the_opposite_sensor_axes() -> None:
    frame = IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, -100)

    assert frame == IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, -100))
    assert frame.with_accel(1, 2, 3) == IMUFrame.raw(accel=(1, 2, 3), gyro=(100, 0, -100))


def test_input_state_with_imu_repeats_one_frame_and_preserves_buttons_and_sticks() -> None:
    left_stick = Stick.up()
    right_stick = Stick.right()
    initial = (
        InputState.neutral()
        .with_buttons([Button.A])
        .with_sticks(
            left_stick=left_stick,
            right_stick=right_stick,
        )
    )
    frame = IMUFrame.gyro(100, 0, 0)

    state = initial.with_imu(frame)

    assert state.buttons == frozenset({Button.A})
    assert state.left_stick == left_stick
    assert state.right_stick == right_stick
    assert state.imu_frames == (frame, frame, frame)


def test_input_state_with_imu_sets_three_frames_in_order() -> None:
    frames = (
        IMUFrame.gyro(100, 0, 0),
        IMUFrame.gyro(120, 0, 0),
        IMUFrame.gyro(140, 0, 0),
    )

    assert InputState.neutral().with_imu(*frames).imu_frames == frames


@pytest.mark.parametrize(
    "frames", [(), (IMUFrame.neutral(), IMUFrame.neutral()), (IMUFrame.neutral(),) * 4]
)
def test_input_state_with_imu_rejects_invalid_frame_counts(frames: tuple[IMUFrame, ...]) -> None:
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_imu(*frames)


def test_input_state_with_imu_rejects_non_imu_frame_values() -> None:
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_imu(cast("IMUFrame", Stick.center()))


def test_input_state_with_gyro_repeats_one_sample_and_preserves_accel_axes() -> None:
    initial = InputState.neutral().with_accel((0, 0, 4096))

    state = initial.with_gyro((100, 0, 0))

    assert state.imu_frames == (IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, 0)),) * 3


def test_input_state_with_gyro_sets_three_samples_in_order_and_preserves_accel_axes() -> None:
    initial = InputState.neutral().with_accel(
        (0, 0, 4096),
        (0, 0, 4090),
        (0, 0, 4080),
    )

    state = initial.with_gyro((100, 0, 0), (120, 0, 0), (140, 0, 0))

    assert state.imu_frames == (
        IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, 0)),
        IMUFrame.raw(accel=(0, 0, 4090), gyro=(120, 0, 0)),
        IMUFrame.raw(accel=(0, 0, 4080), gyro=(140, 0, 0)),
    )


def test_input_state_with_accel_repeats_one_sample_and_preserves_gyro_axes() -> None:
    initial = InputState.neutral().with_gyro((100, 0, -100))

    state = initial.with_accel((0, 0, 4096))

    assert state.imu_frames == (IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, -100)),) * 3


def test_input_state_with_accel_sets_three_samples_in_order_and_preserves_gyro_axes() -> None:
    initial = InputState.neutral().with_gyro((100, 0, 0), (120, 0, 0), (140, 0, 0))

    state = initial.with_accel(
        (0, 0, 4096),
        (0, 0, 4090),
        (0, 0, 4080),
    )

    assert state.imu_frames == (
        IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, 0)),
        IMUFrame.raw(accel=(0, 0, 4090), gyro=(120, 0, 0)),
        IMUFrame.raw(accel=(0, 0, 4080), gyro=(140, 0, 0)),
    )


@pytest.mark.parametrize(
    "samples",
    [
        (),
        ((100, 0, 0), (120, 0, 0)),
        ((100, 0, 0),) * 4,
    ],
)
def test_input_state_with_gyro_and_accel_reject_invalid_sample_counts(
    samples: tuple[tuple[int, int, int], ...],
) -> None:
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_gyro(*samples)
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_accel(*samples)


@pytest.mark.parametrize("sample", [(100, 0), (100, 0, 0, 0)])
def test_input_state_with_gyro_and_accel_reject_invalid_sample_shapes(
    sample: tuple[int, ...],
) -> None:
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_gyro(cast("tuple[int, int, int]", sample))
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_accel(cast("tuple[int, int, int]", sample))


@pytest.mark.parametrize("value", [-32769, 32768])
def test_input_state_with_gyro_and_accel_reject_values_outside_i16_range(value: int) -> None:
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_gyro((value, 0, 0))
    with pytest.raises(InvalidInputError):
        InputState.neutral().with_accel((0, 0, value))
