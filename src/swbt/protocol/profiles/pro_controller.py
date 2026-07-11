"""Pro Controller-compatible protocol profile."""

from dataclasses import dataclass, field

from swbt.imu import DEFAULT_GYRO_CALIBRATION, GyroCalibration
from swbt.protocol.buttons import PRO_CONTROLLER_BUTTON_BITS, ButtonBitMap
from swbt.protocol.profiles.base import ControllerKind, ControllerProfile


@dataclass(frozen=True)
class ProControllerProfile(ControllerProfile):
    """Protocol defaults for a Pro Controller compatible report shape."""

    kind: ControllerKind = ControllerKind.PRO_CONTROLLER
    device_name: str = "Pro Controller"
    device_type: int = 0x03
    device_info_tail: bytes = b"\x03\x02"
    button_bits: ButtonBitMap = field(default_factory=lambda: PRO_CONTROLLER_BUTTON_BITS)
    gyro_calibration: GyroCalibration = DEFAULT_GYRO_CALIBRATION
    imu_enable_modes: tuple[int, ...] = (0x00, 0x01, 0x02)
    supports_left_stick: bool = True
    supports_right_stick: bool = True


def default_controller_profile() -> ProControllerProfile:
    """Return the default Pro Controller compatible profile."""
    return ProControllerProfile()
