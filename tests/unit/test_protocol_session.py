import pytest

from swbt.errors import ProtocolError
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


@pytest.mark.parametrize(
    ("current_mode", "requested_mode", "expected_mode"),
    [
        (ImuMode.DISABLED, 0x01, ImuMode.STANDARD),
        (ImuMode.STANDARD, 0x02, ImuMode.QUATERNION_1),
        (ImuMode.QUATERNION_1, 0x01, ImuMode.STANDARD),
        (ImuMode.QUATERNION_1, 0x00, ImuMode.DISABLED),
        (ImuMode.DISABLED, 0x02, ImuMode.QUATERNION_1),
    ],
)
def test_imu_mode_transitions_do_not_carry_encoding_state(
    current_mode: ImuMode,
    requested_mode: int,
    expected_mode: ImuMode,
) -> None:
    original = SwitchHidSessionState(
        imu_mode=current_mode,
        imu_encoding_state=ImuEncodingState(
            orientation=(0.1, 0.2, 0.3, 0.9),
            previous_report_ns=123,
        ),
    )

    updated = apply_imu_mode_request(
        original,
        requested_mode=requested_mode,
        accepted_modes=(0x00, 0x01, 0x02, 0x03, 0x04, 0x05),
    )

    assert updated.imu_mode is expected_mode
    assert updated.imu_enabled is (expected_mode is not ImuMode.DISABLED)
    assert updated.imu_encoding_state == ImuEncodingState()
    assert original.imu_encoding_state.previous_report_ns == 123


def test_unsupported_imu_mode_request_leaves_session_state_unchanged() -> None:
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

    with pytest.raises(ProtocolError, match="unsupported enable IMU value: 0x06"):
        apply_imu_mode_request(
            original,
            requested_mode=0x06,
            accepted_modes=(0x00, 0x01, 0x02, 0x03, 0x04, 0x05),
        )

    assert original.imu_mode is ImuMode.QUATERNION_1
    assert original.imu_encoding_state.previous_report_ns == 123
    assert original.report_mode == 0x30
    assert original.vibration_enabled is True
