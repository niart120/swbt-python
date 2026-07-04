from collections.abc import Callable

import pytest

from swbt.errors import InvalidInputError
from swbt.input import IMUFrame, InputState, Stick


def test_neutral_input_state_has_no_buttons_center_sticks_and_neutral_imu() -> None:
    state = InputState.neutral()

    assert state.buttons == frozenset()
    assert state.left_stick == Stick.center()
    assert state.right_stick == Stick.center()
    assert state.imu_frames == (IMUFrame.neutral(),) * 3


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
