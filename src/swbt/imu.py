"""Shared virtual IMU calibration values."""

from dataclasses import dataclass
from math import degrees, radians
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

    def gyro_rates_to_raw(
        self,
        rates_rad_s: tuple[float, float, float],
    ) -> tuple[int, int, int]:
        """Convert XYZ angular velocities in radians per second to raw values."""
        return (
            self.zero_raw[0] + round(degrees(rates_rad_s[0]) / self.dps_per_raw),
            self.zero_raw[1] + round(degrees(rates_rad_s[1]) / self.dps_per_raw),
            self.zero_raw[2] + round(degrees(rates_rad_s[2]) / self.dps_per_raw),
        )

    def raw_to_gyro_rates(
        self,
        raw: tuple[int, int, int],
    ) -> tuple[float, float, float]:
        """Convert XYZ raw values to angular velocities in radians per second."""
        return (
            radians((raw[0] - self.zero_raw[0]) * self.dps_per_raw),
            radians((raw[1] - self.zero_raw[1]) * self.dps_per_raw),
            radians((raw[2] - self.zero_raw[2]) * self.dps_per_raw),
        )


DEFAULT_GYRO_CALIBRATION = GyroCalibration()
