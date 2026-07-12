"""Stateful compatibility wrapper for quaternion IMU report packing."""

from collections.abc import Callable
from time import monotonic_ns

from swbt.imu import GyroCalibration
from swbt.input import IMUFrame
from swbt.protocol.imu_report import ImuEncodingState, encode_quaternion_imu


class QuaternionMotionPacker:
    """Pack the quaternion motion format requested by IMU modes 0x02..0x05."""

    def __init__(self, *, clock_ns: Callable[[], int] = monotonic_ns) -> None:
        """Create a stateful orientation packer."""
        self._clock_ns = clock_ns
        self.reset()

    def reset(self) -> None:
        """Reset accumulated orientation and timing."""
        self._state = ImuEncodingState()

    def pack(
        self,
        frames: tuple[IMUFrame, IMUFrame, IMUFrame],
        *,
        gyro_calibration: GyroCalibration,
    ) -> bytes:
        """Return one 36-byte packing-mode-2 motion block."""
        result = encode_quaternion_imu(
            state=self._state,
            frames=frames,
            gyro_calibration=gyro_calibration,
            now_ns=self._clock_ns(),
        )
        self._state = result.state
        return result.block
