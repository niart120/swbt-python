"""Base profile types shared by Switch-compatible controller shapes."""

from dataclasses import dataclass, field
from enum import Enum

from swbt.errors import InvalidInputError, UnsupportedInputError
from swbt.imu import (
    DEFAULT_ACCELEROMETER_CALIBRATION,
    DEFAULT_GYRO_CALIBRATION,
    AccelerometerCalibration,
    GyroCalibration,
)
from swbt.input import Button, InputState, Stick
from swbt.protocol.buttons import PRO_CONTROLLER_BUTTON_BITS, ButtonBitMap
from swbt.protocol.descriptors import SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR


@dataclass(frozen=True)
class ControllerColors:
    """Controller body, button, and grip colors stored in virtual SPI.

    Args:
        body: Body color as a 24-bit RGB integer.
        buttons: Button color as a 24-bit RGB integer.
        left_grip: Left grip color as a 24-bit RGB integer.
        right_grip: Right grip color as a 24-bit RGB integer.

    Attributes:
        body: Body color as a 24-bit RGB integer.
        buttons: Button color as a 24-bit RGB integer.
        left_grip: Left grip color as a 24-bit RGB integer.
        right_grip: Right grip color as a 24-bit RGB integer.
    """

    body: int = 0x323232
    buttons: int = 0xFFFFFF
    left_grip: int = 0x00B2FF
    right_grip: int = 0xFF3B30

    def __post_init__(self) -> None:
        """Validate 24-bit RGB color values."""
        self._validate_rgb("body", self.body)
        self._validate_rgb("buttons", self.buttons)
        self._validate_rgb("left_grip", self.left_grip)
        self._validate_rgb("right_grip", self.right_grip)

    def to_spi_bytes(self) -> bytes:
        """Return body, button, and grip colors in Switch SPI RGB order.

        Returns:
            bytes: Four RGB colors encoded as 12 bytes in body, buttons, left grip,
                right grip order.
        """
        return (
            self.body.to_bytes(3, "big")
            + self.buttons.to_bytes(3, "big")
            + self.left_grip.to_bytes(3, "big")
            + self.right_grip.to_bytes(3, "big")
        )

    @staticmethod
    def _validate_rgb(name: str, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFFFF:
            msg = f"{name} must be a 24-bit RGB integer"
            raise InvalidInputError(msg)


@dataclass(frozen=True)
class HidSdpPolicy:
    """Classic HID SDP attributes associated with a controller profile."""

    service_name: str | None = None
    service_description: str | None = None
    provider_name: str | None = None
    device_release_number: int | None = None
    bluetooth_profile_version: int = 0x0101
    parser_version: int = 0x0111
    device_subclass: int = 0x08
    country_code: int = 0x21
    virtual_cable: bool = True
    reconnect_initiate: bool = True
    remote_wake: bool | None = True
    profile_version: int = 0x0101
    supervision_timeout: int = 0x0C80
    normally_connectable: bool = True
    boot_device: bool = False
    ssr_host_max_latency: int = 0xFFFF
    ssr_host_min_timeout: int = 0xFFFF

    def __post_init__(self) -> None:
        """Validate SDP scalar values."""
        for name in (
            "bluetooth_profile_version",
            "parser_version",
            "profile_version",
            "supervision_timeout",
            "ssr_host_max_latency",
            "ssr_host_min_timeout",
        ):
            self._validate_uint16(name, getattr(self, name))
        if self.device_release_number is not None:
            self._validate_uint16("device_release_number", self.device_release_number)
        self._validate_byte("device_subclass", self.device_subclass)
        self._validate_byte("country_code", self.country_code)

    @staticmethod
    def _validate_uint16(name: str, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFFFF:
            msg = f"{name} must be a 16-bit integer"
            raise InvalidInputError(msg)

    @staticmethod
    def _validate_byte(name: str, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFF:
            msg = f"{name} must be a byte integer"
            raise InvalidInputError(msg)


@dataclass(frozen=True)
class ControllerProfile:
    """Protocol defaults for a Switch-compatible controller shape."""

    kind: "ControllerKind"
    device_name: str = "Pro Controller"
    device_type: int = 0x03
    device_info_firmware_version: bytes = b"\x04\x00"
    device_info_marker: int = 0x02
    device_info_tail: bytes = b"\x03\x02"
    default_report_period_us: int = 8000
    battery_connection: int = 0x80
    vibrator_input: int = 0x00
    hid_report_descriptor: bytes = SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR
    hid_sdp_policy: HidSdpPolicy = field(default_factory=HidSdpPolicy)
    controller_colors: ControllerColors = field(default_factory=ControllerColors)
    accelerometer_calibration: AccelerometerCalibration = DEFAULT_ACCELEROMETER_CALIBRATION
    gyro_calibration: GyroCalibration = DEFAULT_GYRO_CALIBRATION
    button_bits: ButtonBitMap = field(default_factory=lambda: PRO_CONTROLLER_BUTTON_BITS)
    imu_enable_modes: tuple[int, ...] = (0x00, 0x01)
    supports_left_stick: bool = True
    supports_right_stick: bool = True

    def __post_init__(self) -> None:
        """Validate byte-sized identity values."""
        self._validate_byte("device_type", self.device_type)
        self._validate_byte("device_info_marker", self.device_info_marker)
        if (
            not isinstance(self.default_report_period_us, int)
            or isinstance(self.default_report_period_us, bool)
            or self.default_report_period_us <= 0
        ):
            msg = "default_report_period_us must be a positive integer"
            raise InvalidInputError(msg)
        if len(self.device_info_firmware_version) != 2:
            msg = "device_info_firmware_version must be 2 bytes"
            raise InvalidInputError(msg)
        if len(self.device_info_tail) != 2:
            msg = "device_info_tail must be 2 bytes"
            raise InvalidInputError(msg)

    def build_device_info(self, bluetooth_address: bytes) -> bytes:
        """Return the 12-byte payload for subcommand 0x02."""
        if len(bluetooth_address) != 6:
            msg = "bluetooth_address must be 6 bytes"
            raise InvalidInputError(msg)
        return (
            self.device_info_firmware_version
            + bytes((self.device_type, self.device_info_marker))
            + bytes(bluetooth_address)
            + self.device_info_tail
        )

    def button_bit(self, button: Button) -> tuple[int, int]:
        """Return the report byte offset and mask for a supported button."""
        try:
            return self.button_bits[button]
        except KeyError as error:
            raise self._unsupported_input_error(buttons=(button,)) from error

    def validate_input_state(self, state: InputState) -> None:
        """Raise when the state cannot be represented by this profile."""
        unsupported_buttons = tuple(
            sorted(
                (button for button in state.buttons if button not in self.button_bits),
                key=lambda button: button.name,
            )
        )
        unsupported_sticks: list[str] = []
        if not self.supports_left_stick and state.left_stick != Stick.center():
            unsupported_sticks.append("left")
        if not self.supports_right_stick and state.right_stick != Stick.center():
            unsupported_sticks.append("right")
        if unsupported_buttons or unsupported_sticks:
            raise self._unsupported_input_error(
                buttons=unsupported_buttons,
                sticks=tuple(unsupported_sticks),
            )

    def validate_buttons(self, buttons: tuple[Button, ...]) -> None:
        """Raise when requested buttons are not supported by this profile."""
        unsupported_buttons = tuple(
            sorted(
                (button for button in buttons if button not in self.button_bits),
                key=lambda button: button.name,
            )
        )
        if unsupported_buttons:
            raise self._unsupported_input_error(buttons=unsupported_buttons)

    def validate_requested_sticks(self, *, left: bool = False, right: bool = False) -> None:
        """Raise when a requested stick side is not supported by this profile."""
        unsupported_sticks: list[str] = []
        if left and not self.supports_left_stick:
            unsupported_sticks.append("left")
        if right and not self.supports_right_stick:
            unsupported_sticks.append("right")
        if unsupported_sticks:
            raise self._unsupported_input_error(sticks=tuple(unsupported_sticks))

    @staticmethod
    def _validate_byte(name: str, value: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 0xFF:
            msg = f"{name} must be a byte integer"
            raise InvalidInputError(msg)

    def _unsupported_input_error(
        self,
        *,
        buttons: tuple[Button, ...] = (),
        sticks: tuple[str, ...] = (),
    ) -> UnsupportedInputError:
        parts: list[str] = []
        if buttons:
            parts.append("buttons=" + ",".join(button.name for button in buttons))
        if sticks:
            parts.append("sticks=" + ",".join(sticks))
        detail = "; ".join(parts) if parts else "input"
        return UnsupportedInputError(
            f"{self.device_name} does not support {detail}",
            profile_kind=self.kind.value,
            buttons=tuple(button.name for button in buttons),
            sticks=sticks,
        )


class ControllerKind(Enum):
    """Controller profile identity."""

    PRO_CONTROLLER = "pro_controller"
    JOYCON_LEFT = "joycon_left"
    JOYCON_RIGHT = "joycon_right"
