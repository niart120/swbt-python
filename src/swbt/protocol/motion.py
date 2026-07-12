"""Motion report packing selected by the host IMU mode."""

from collections.abc import Callable
from math import cos, sin, sqrt
from struct import pack_into
from time import monotonic_ns

from swbt.imu import GyroCalibration
from swbt.input import IMUFrame

_Quaternion = tuple[float, float, float, float]


class QuaternionMotionPacker:
    """Pack the quaternion motion format requested by IMU modes 0x02..0x05."""

    def __init__(self, *, clock_ns: Callable[[], int] = monotonic_ns) -> None:
        """Create a stateful orientation packer."""
        self._clock_ns = clock_ns
        self.reset()

    def reset(self) -> None:
        """Reset accumulated orientation and timing."""
        self._previous_ns: int | None = None
        self._orientation: _Quaternion = (0.0, 0.0, 0.0, 1.0)

    def pack(
        self,
        frames: tuple[IMUFrame, IMUFrame, IMUFrame],
        *,
        gyro_calibration: GyroCalibration,
    ) -> bytes:
        """Return one 36-byte packing-mode-2 motion block."""
        now_ns = self._clock_ns()
        elapsed_seconds = 0.0
        if self._previous_ns is not None:
            elapsed_seconds = max(0, now_ns - self._previous_ns) / 1_000_000_000
        self._previous_ns = now_ns

        newest = frames[-1]
        rates = gyro_calibration.raw_to_gyro_rates((newest.gyro_x, newest.gyro_y, newest.gyro_z))
        self._orientation = _advance_orientation(
            self._orientation,
            rates,
            elapsed_seconds,
        )
        return _pack_mode_2(frames, self._orientation, timestamp_ms=now_ns // 1_000_000)


def _advance_orientation(
    orientation: _Quaternion,
    rates_rad_s: tuple[float, float, float],
    elapsed_seconds: float,
) -> _Quaternion:
    rotation = tuple(rate * elapsed_seconds for rate in rates_rad_s)
    magnitude = sqrt(sum(value * value for value in rotation))
    if magnitude == 0:
        return orientation
    half_angle = magnitude / 2
    vector_scale = sin(half_angle) / magnitude
    delta = (
        rotation[0] * vector_scale,
        rotation[1] * vector_scale,
        rotation[2] * vector_scale,
        cos(half_angle),
    )
    return _normalize(_hamilton_product(orientation, delta))


def _hamilton_product(left: _Quaternion, right: _Quaternion) -> _Quaternion:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return (
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry + ly * rw + lz * rx - lx * rz,
        lw * rz + lz * rw + lx * ry - ly * rx,
        lw * rw - lx * rx - ly * ry - lz * rz,
    )


def _normalize(value: _Quaternion) -> _Quaternion:
    inverse = 1 / sqrt(sum(component * component for component in value))
    return (value[0] * inverse, value[1] * inverse, value[2] * inverse, value[3] * inverse)


def _pack_mode_2(
    frames: tuple[IMUFrame, IMUFrame, IMUFrame],
    orientation: _Quaternion,
    *,
    timestamp_ms: int,
) -> bytes:
    result = bytearray(36)
    for offset, frame in zip((0, 12, 24), frames, strict=True):
        pack_into("<3h", result, offset, frame.accel_x, frame.accel_y, frame.accel_z)

    max_index = max(range(4), key=lambda index: abs(orientation[index]))
    sign = -1 if orientation[max_index] < 0 else 1
    components = [
        int(orientation[(max_index + index + 1) & 3] * sign * 0x40000000) >> 10
        for index in range(3)
    ]

    _put_bits(result, 48, 2, 2)
    _put_bits(result, 50, 2, max_index)
    _put_bits(result, 52, 21, components[0])
    _put_bits(result, 73, 21, components[1])
    _put_bits(result, 94, 2, components[2])
    _put_bits(result, 144, 19, components[2] >> 2)
    _put_bits(result, 271, 11, timestamp_ms)
    _put_bits(result, 282, 6, 3)
    return bytes(result)


def _put_bits(target: bytearray, start: int, width: int, value: int) -> None:
    masked = value & ((1 << width) - 1)
    for bit in range(width):
        if masked & (1 << bit):
            absolute = start + bit
            target[absolute // 8] |= 1 << (absolute % 8)
