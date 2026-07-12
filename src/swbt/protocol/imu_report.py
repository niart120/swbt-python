"""Pure IMU wire encoding from explicit state and report time."""

from dataclasses import dataclass
from enum import IntEnum
from math import cos, sin, sqrt
from struct import pack_into

from swbt.imu import GyroCalibration
from swbt.input import IMUFrame

_Quaternion = tuple[float, float, float, float]
_IDENTITY_QUATERNION: _Quaternion = (0.0, 0.0, 0.0, 1.0)


class ImuMode(IntEnum):
    """Host-selected IMU wire mode."""

    DISABLED = 0x00
    STANDARD = 0x01
    QUATERNION_1 = 0x02
    QUATERNION_2 = 0x03
    QUATERNION_3 = 0x04
    QUATERNION_4 = 0x05


@dataclass(frozen=True)
class ImuEncodingState:
    """State required to encode the next quaternion IMU block."""

    orientation: _Quaternion = _IDENTITY_QUATERNION
    previous_report_ns: int | None = None


@dataclass(frozen=True)
class ImuEncodingResult:
    """One encoded IMU block and the state for the next report."""

    block: bytes
    state: ImuEncodingState


def encode_disabled_imu() -> ImuEncodingResult:
    """Encode the disabled IMU block and reset its encoding state."""
    return ImuEncodingResult(block=bytes(36), state=ImuEncodingState())


def encode_imu_block(
    *,
    state: ImuEncodingState,
    mode: ImuMode,
    frames: tuple[IMUFrame, IMUFrame, IMUFrame],
    gyro_calibration: GyroCalibration,
    now_ns: int,
) -> ImuEncodingResult:
    """Encode one IMU block for the explicit host-selected mode."""
    if mode is ImuMode.DISABLED:
        return encode_disabled_imu()
    if mode is ImuMode.STANDARD:
        return ImuEncodingResult(
            block=encode_standard_imu(frames),
            state=ImuEncodingState(),
        )
    return encode_quaternion_imu(
        state=state,
        frames=frames,
        gyro_calibration=gyro_calibration,
        now_ns=now_ns,
    )


def encode_standard_imu(frames: tuple[IMUFrame, IMUFrame, IMUFrame]) -> bytes:
    """Encode three raw six-axis frames as signed Int16LE values."""
    result = bytearray(36)
    for offset, frame in zip((0, 12, 24), frames, strict=True):
        pack_into(
            "<6h",
            result,
            offset,
            frame.accel_x,
            frame.accel_y,
            frame.accel_z,
            frame.gyro_x,
            frame.gyro_y,
            frame.gyro_z,
        )
    return bytes(result)


def encode_quaternion_imu(
    *,
    state: ImuEncodingState,
    frames: tuple[IMUFrame, IMUFrame, IMUFrame],
    gyro_calibration: GyroCalibration,
    now_ns: int,
) -> ImuEncodingResult:
    """Encode one 36-byte packing-mode-2 block without mutating inputs."""
    elapsed_seconds = 0.0
    if state.previous_report_ns is not None:
        elapsed_seconds = max(0, now_ns - state.previous_report_ns) / 1_000_000_000

    orientation = state.orientation
    sample_seconds = elapsed_seconds / len(frames)
    for frame in frames:
        rates = gyro_calibration.raw_to_gyro_rates((frame.gyro_x, frame.gyro_y, frame.gyro_z))
        orientation = _next_orientation(orientation, rates, sample_seconds)

    next_state = ImuEncodingState(
        orientation=orientation,
        previous_report_ns=now_ns,
    )
    return ImuEncodingResult(
        block=_pack_mode_2(frames, orientation, timestamp_ms=now_ns // 1_000_000),
        state=next_state,
    )


def _next_orientation(
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
