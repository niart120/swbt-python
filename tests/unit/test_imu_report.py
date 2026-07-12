import pytest

from swbt.imu import GyroCalibration
from swbt.input import IMUFrame
from swbt.protocol.imu_report import (
    ImuEncodingState,
    ImuMode,
    encode_disabled_imu,
    encode_quaternion_imu,
    encode_standard_imu,
)
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.protocol.session import SwitchHidSessionState


def test_quaternion_encoding_is_deterministic_for_explicit_state_and_time() -> None:
    frames = (
        IMUFrame.raw(accel=(1, 2, 3), gyro=(100, 200, 300)),
        IMUFrame.raw(accel=(4, 5, 6), gyro=(400, 500, 600)),
        IMUFrame.raw(accel=(7, 8, 9), gyro=(700, 800, 900)),
    )
    state = ImuEncodingState(previous_report_ns=1_000_000_000)
    profile = default_controller_profile()

    first = encode_quaternion_imu(
        state=state,
        frames=frames,
        gyro_calibration=profile.gyro_calibration,
        now_ns=1_008_000_000,
    )
    second = encode_quaternion_imu(
        state=state,
        frames=frames,
        gyro_calibration=profile.gyro_calibration,
        now_ns=1_008_000_000,
    )

    assert first == second
    assert len(first.block) == 36
    assert first.state.previous_report_ns == 1_008_000_000
    assert state.previous_report_ns == 1_000_000_000


def test_standard_encoding_preserves_three_raw_frames_without_calibration() -> None:
    frames = (
        IMUFrame.raw(accel=(1, -2, 3), gyro=(-4, 5, -6)),
        IMUFrame.raw(accel=(7, -8, 9), gyro=(-10, 11, -12)),
        IMUFrame.raw(accel=(13, -14, 15), gyro=(-16, 17, -18)),
    )

    block = encode_standard_imu(frames)

    assert block == bytes.fromhex(
        "01 00 fe ff 03 00 fc ff 05 00 fa ff "
        "07 00 f8 ff 09 00 f6 ff 0b 00 f4 ff "
        "0d 00 f2 ff 0f 00 f0 ff 11 00 ee ff"
    )


@pytest.mark.parametrize("active_sample_index", range(3))
def test_quaternion_encoding_uses_each_gyro_sample_and_preserves_acceleration(
    active_sample_index: int,
) -> None:
    samples = tuple(
        IMUFrame.raw(
            accel=(index + 1, index + 2, index + 3),
            gyro=(0, 0, 1000 if index == active_sample_index else 0),
        )
        for index in range(3)
    )
    frames = (samples[0], samples[1], samples[2])

    result = encode_quaternion_imu(
        state=ImuEncodingState(previous_report_ns=0),
        frames=frames,
        gyro_calibration=GyroCalibration(),
        now_ns=1_000_000_000,
    )

    assert result.state.orientation[2] > 0
    assert result.block[0:6] == bytes.fromhex("01 00 02 00 03 00")
    assert result.block[12:18] == bytes.fromhex("02 00 03 00 04 00")
    assert result.block[24:30] == bytes.fromhex("03 00 04 00 05 00")


def test_quaternion_encoding_uses_the_active_gyro_calibration() -> None:
    frame = IMUFrame.gyro(0, 0, 1000)
    frames = (frame, frame, frame)
    state = ImuEncodingState(previous_report_ns=0)

    default_result = encode_quaternion_imu(
        state=state,
        frames=frames,
        gyro_calibration=GyroCalibration(),
        now_ns=1_000_000_000,
    )
    offset_result = encode_quaternion_imu(
        state=state,
        frames=frames,
        gyro_calibration=GyroCalibration(zero_raw=(0, 0, 1000)),
        now_ns=1_000_000_000,
    )

    assert default_result.state.orientation[2] > 0
    assert offset_result.state.orientation == (0.0, 0.0, 0.0, 1.0)


def test_quaternion_encoding_uses_zero_elapsed_time_initially_and_when_clock_recedes() -> None:
    frame = IMUFrame.raw(accel=(1, 2, 3), gyro=(0, 0, 1000))
    frames = (frame, frame, frame)
    original_frames = frames

    initial = encode_quaternion_imu(
        state=ImuEncodingState(),
        frames=frames,
        gyro_calibration=GyroCalibration(),
        now_ns=100,
    )
    receded = encode_quaternion_imu(
        state=ImuEncodingState(previous_report_ns=200),
        frames=frames,
        gyro_calibration=GyroCalibration(),
        now_ns=100,
    )

    assert initial.state.orientation == (0.0, 0.0, 0.0, 1.0)
    assert receded.state.orientation == (0.0, 0.0, 0.0, 1.0)
    assert initial.state.previous_report_ns == 100
    assert receded.state.previous_report_ns == 100
    assert frames == original_frames


def test_initial_and_disabled_imu_mode_encode_a_zero_block_and_reset_state() -> None:
    session_state = SwitchHidSessionState()
    frame = IMUFrame.gyro(100, 200, 300)
    frames = (frame, frame, frame)
    rotated_state = ImuEncodingState(
        orientation=(0.1, 0.2, 0.3, 0.9),
        previous_report_ns=123,
    )

    result = encode_disabled_imu()

    assert session_state.imu_mode is ImuMode.DISABLED
    assert session_state.imu_enabled is False
    assert result.block == bytes(36)
    assert result.state == ImuEncodingState()
    assert rotated_state.previous_report_ns == 123
    assert frames == (frame, frame, frame)
