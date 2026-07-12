from swbt.input import IMUFrame
from swbt.protocol.imu_report import ImuEncodingState, encode_quaternion_imu
from swbt.protocol.profiles.pro_controller import default_controller_profile


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
