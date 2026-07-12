from swbt.protocol.imu_report import ImuEncodingState, ImuMode
from swbt.protocol.session import SwitchHidSessionState, apply_imu_mode_request


def test_repeated_accepted_imu_mode_request_starts_a_new_encoding_epoch() -> None:
    original = SwitchHidSessionState(
        report_mode=0x30,
        report_mode_supported=True,
        imu_mode=ImuMode.QUATERNION_1,
        imu_encoding_state=ImuEncodingState(
            orientation=(0.1, 0.2, 0.3, 0.9),
            previous_report_ns=123,
        ),
        vibration_enabled=True,
    )

    updated = apply_imu_mode_request(
        original,
        requested_mode=0x02,
        accepted_modes=(0x00, 0x01, 0x02, 0x03, 0x04, 0x05),
    )

    assert updated.imu_mode is ImuMode.QUATERNION_1
    assert updated.imu_encoding_state == ImuEncodingState()
    assert updated.report_mode == 0x30
    assert updated.report_mode_supported is True
    assert updated.vibration_enabled is True
    assert original.imu_encoding_state.previous_report_ns == 123
