"""Single Joy-Con-compatible protocol profiles."""

from dataclasses import dataclass, field

from swbt.protocol.buttons import (
    JOYCON_LEFT_BUTTON_BITS,
    JOYCON_RIGHT_BUTTON_BITS,
    ButtonBitMap,
)
from swbt.protocol.profiles.base import (
    ControllerColors,
    ControllerKind,
    ControllerProfile,
    HidSdpPolicy,
)

_JOYCON_IMU_ENABLE_MODES = (0x00, 0x01, 0x02, 0x03, 0x04, 0x05)


def _joycontrol_hid_sdp_policy() -> HidSdpPolicy:
    return HidSdpPolicy(
        service_name="Wireless Gamepad",
        service_description="Gamepad",
        provider_name="Nintendo",
        device_release_number=0x0100,
        bluetooth_profile_version=0x0100,
        country_code=0x00,
        remote_wake=None,
        profile_version=0x0100,
        normally_connectable=False,
        boot_device=True,
        ssr_host_max_latency=0x0640,
        ssr_host_min_timeout=0x0320,
    )


def _joycon_left_controller_colors() -> ControllerColors:
    return ControllerColors(
        body=0x00B2FF,
        buttons=0x323232,
        left_grip=0x00B2FF,
        right_grip=0x00B2FF,
    )


def _joycon_right_controller_colors() -> ControllerColors:
    return ControllerColors(
        body=0xFF3B30,
        buttons=0x323232,
        left_grip=0xFF3B30,
        right_grip=0xFF3B30,
    )


@dataclass(frozen=True)
class JoyConLeftProfile(ControllerProfile):
    """Protocol defaults for a single left Joy-Con profile."""

    kind: ControllerKind = ControllerKind.JOYCON_LEFT
    device_name: str = "Joy-Con (L)"
    device_type: int = 0x01
    device_info_tail: bytes = b"\x01\x01"
    hid_sdp_policy: HidSdpPolicy = field(default_factory=_joycontrol_hid_sdp_policy)
    controller_colors: ControllerColors = field(default_factory=_joycon_left_controller_colors)
    button_bits: ButtonBitMap = field(default_factory=lambda: JOYCON_LEFT_BUTTON_BITS)
    imu_enable_modes: tuple[int, ...] = _JOYCON_IMU_ENABLE_MODES
    supports_left_stick: bool = True
    supports_right_stick: bool = False


@dataclass(frozen=True)
class JoyConRightProfile(ControllerProfile):
    """Protocol defaults for a single right Joy-Con profile."""

    kind: ControllerKind = ControllerKind.JOYCON_RIGHT
    device_name: str = "Joy-Con (R)"
    device_type: int = 0x02
    device_info_tail: bytes = b"\x01\x01"
    hid_sdp_policy: HidSdpPolicy = field(default_factory=_joycontrol_hid_sdp_policy)
    controller_colors: ControllerColors = field(default_factory=_joycon_right_controller_colors)
    button_bits: ButtonBitMap = field(default_factory=lambda: JOYCON_RIGHT_BUTTON_BITS)
    imu_enable_modes: tuple[int, ...] = _JOYCON_IMU_ENABLE_MODES
    supports_left_stick: bool = False
    supports_right_stick: bool = True
