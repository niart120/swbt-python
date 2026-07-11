"""Shared virtual IMU calibration values."""

from dataclasses import dataclass
from struct import pack


@dataclass(frozen=True)
class GyroCalibration:
    """Virtual gyroscope zero, reference, and fixed conversion scale."""

    zero_raw: tuple[int, int, int] = (0, 0, 0)
    reference_raw: tuple[int, int, int] = (0x343B, 0x343B, 0x343B)

    @property
    def dps_per_raw(self) -> float:
        """Return the fixed gyroscope sensitivity in degrees per second per raw unit."""
        return 0.070

    def to_spi_bytes(self) -> bytes:
        """Return gyro zero XYZ followed by reference XYZ as signed Int16LE."""
        return pack("<6h", *self.zero_raw, *self.reference_raw)


DEFAULT_GYRO_CALIBRATION = GyroCalibration()
