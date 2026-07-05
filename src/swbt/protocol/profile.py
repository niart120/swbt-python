"""Fixed protocol profile values for the controller shape."""

from dataclasses import dataclass, field

from swbt.errors import InvalidInputError

SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR = bytes(
    (
        0x05,
        0x01,
        0x15,
        0x00,
        0x09,
        0x04,
        0xA1,
        0x01,
        0x85,
        0x30,
        0x05,
        0x01,
        0x05,
        0x09,
        0x19,
        0x01,
        0x29,
        0x0A,
        0x15,
        0x00,
        0x25,
        0x01,
        0x75,
        0x01,
        0x95,
        0x0A,
        0x55,
        0x00,
        0x65,
        0x00,
        0x81,
        0x02,
        0x05,
        0x09,
        0x19,
        0x0B,
        0x29,
        0x0E,
        0x15,
        0x00,
        0x25,
        0x01,
        0x75,
        0x01,
        0x95,
        0x04,
        0x81,
        0x02,
        0x75,
        0x01,
        0x95,
        0x02,
        0x81,
        0x03,
        0x0B,
        0x01,
        0x00,
        0x01,
        0x00,
        0xA1,
        0x00,
        0x0B,
        0x30,
        0x00,
        0x01,
        0x00,
        0x0B,
        0x31,
        0x00,
        0x01,
        0x00,
        0x0B,
        0x32,
        0x00,
        0x01,
        0x00,
        0x0B,
        0x35,
        0x00,
        0x01,
        0x00,
        0x15,
        0x00,
        0x27,
        0xFF,
        0xFF,
        0x00,
        0x00,
        0x75,
        0x10,
        0x95,
        0x04,
        0x81,
        0x02,
        0xC0,
        0x0B,
        0x39,
        0x00,
        0x01,
        0x00,
        0x15,
        0x00,
        0x25,
        0x07,
        0x35,
        0x00,
        0x46,
        0x3B,
        0x01,
        0x65,
        0x14,
        0x75,
        0x04,
        0x95,
        0x01,
        0x81,
        0x02,
        0x05,
        0x09,
        0x19,
        0x0F,
        0x29,
        0x12,
        0x15,
        0x00,
        0x25,
        0x01,
        0x75,
        0x01,
        0x95,
        0x04,
        0x81,
        0x02,
        0x75,
        0x08,
        0x95,
        0x34,
        0x81,
        0x03,
        0x06,
        0x00,
        0xFF,
        0x85,
        0x21,
        0x09,
        0x01,
        0x75,
        0x08,
        0x95,
        0x3F,
        0x81,
        0x03,
        0x85,
        0x81,
        0x09,
        0x02,
        0x75,
        0x08,
        0x95,
        0x3F,
        0x81,
        0x03,
        0x85,
        0x01,
        0x09,
        0x03,
        0x75,
        0x08,
        0x95,
        0x3F,
        0x91,
        0x83,
        0x85,
        0x10,
        0x09,
        0x04,
        0x75,
        0x08,
        0x95,
        0x3F,
        0x91,
        0x83,
        0x85,
        0x80,
        0x09,
        0x05,
        0x75,
        0x08,
        0x95,
        0x3F,
        0x91,
        0x83,
        0x85,
        0x82,
        0x09,
        0x06,
        0x75,
        0x08,
        0x95,
        0x3F,
        0x91,
        0x83,
        0xC0,
    )
)


@dataclass(frozen=True)
class ControllerColors:
    """Controller body, button, and grip colors stored in virtual SPI.

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
        """Return body, button, and grip colors in Switch SPI RGB order."""
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
class ProControllerProfile:
    """Protocol defaults for a Pro Controller compatible report shape."""

    battery_connection: int = 0x91
    vibrator_input: int = 0x00
    bluetooth_address: bytes = b"\x00\x00\x00\x00\x00\x00"
    hid_report_descriptor: bytes = SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR
    controller_colors: ControllerColors = field(default_factory=ControllerColors)
