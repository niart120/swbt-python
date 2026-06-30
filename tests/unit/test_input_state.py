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
