"""Shared virtual IMU calibration values."""

from dataclasses import dataclass
from math import degrees, isfinite, radians
from struct import pack

from swbt.errors import InvalidInputError


@dataclass(frozen=True)
class AccelerometerCalibration:
    """Virtual accelerometer zero and reference values for factory SPI."""

    zero_raw: tuple[int, int, int] = (0, 0, 0)
    reference_raw: tuple[int, int, int] = (0x4000, 0x4000, 0x4000)

    @property
    def reference_acceleration_g(self) -> float:
        """Return the fixed reference acceleration in G."""
        return 4.0

    @property
    def g_per_raw(self) -> float:
        """Return the fixed accelerometer sensitivity in G per raw unit."""
        return 1 / 4096

    def to_spi_bytes(self) -> bytes:
        """Return accelerometer zero XYZ followed by reference XYZ as Int16LE."""
        return pack("<6h", *self.zero_raw, *self.reference_raw)

    def accelerations_to_raw(
        self,
        accelerations_g: tuple[float, float, float],
    ) -> tuple[int, int, int]:
        """Convert XYZ accelerations in G to raw values."""
        values = tuple(
            self._validate_acceleration(f"{axis}_g", value)
            for axis, value in zip("xyz", accelerations_g, strict=True)
        )
        return tuple(
            zero + round(value / self.g_per_raw)
            for zero, value in zip(self.zero_raw, values, strict=True)
        )

    def raw_to_accelerations(
        self,
        raw: tuple[int, int, int],
    ) -> tuple[float, float, float]:
        """Convert XYZ raw values to accelerations in G."""
        return tuple(
            (value - zero) * self.g_per_raw
            for zero, value in zip(self.zero_raw, raw, strict=True)
        )

    @staticmethod
    def _validate_acceleration(name: str, value: object) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            msg = f"{name} must be a finite number: {value}"
            raise InvalidInputError(msg)
        return float(value)


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
        x_rad_s = self._validate_rate("x_rad_s", rates_rad_s[0])
        y_rad_s = self._validate_rate("y_rad_s", rates_rad_s[1])
        z_rad_s = self._validate_rate("z_rad_s", rates_rad_s[2])
        return (
            self.zero_raw[0] + round(degrees(x_rad_s) / self.dps_per_raw),
            self.zero_raw[1] + round(degrees(y_rad_s) / self.dps_per_raw),
            self.zero_raw[2] + round(degrees(z_rad_s) / self.dps_per_raw),
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

    @staticmethod
    def _validate_rate(name: str, value: object) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            msg = f"{name} must be a finite number: {value}"
            raise InvalidInputError(msg)
        return float(value)


DEFAULT_ACCELEROMETER_CALIBRATION = AccelerometerCalibration()
DEFAULT_GYRO_CALIBRATION = GyroCalibration()
