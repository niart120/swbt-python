"""Button bit maps for Switch-compatible controller profiles."""

from collections.abc import Mapping
from types import MappingProxyType

from swbt.input import Button

ButtonBitMap = Mapping[Button, tuple[int, int]]

PRO_CONTROLLER_BUTTON_BITS: ButtonBitMap = MappingProxyType(
    {
        Button.Y: (3, 0x01),
        Button.X: (3, 0x02),
        Button.B: (3, 0x04),
        Button.A: (3, 0x08),
        Button.R: (3, 0x40),
        Button.ZR: (3, 0x80),
        Button.MINUS: (4, 0x01),
        Button.PLUS: (4, 0x02),
        Button.RIGHT_STICK: (4, 0x04),
        Button.LEFT_STICK: (4, 0x08),
        Button.HOME: (4, 0x10),
        Button.CAPTURE: (4, 0x20),
        Button.DPAD_DOWN: (5, 0x01),
        Button.DPAD_UP: (5, 0x02),
        Button.DPAD_RIGHT: (5, 0x04),
        Button.DPAD_LEFT: (5, 0x08),
        Button.L: (5, 0x40),
        Button.ZL: (5, 0x80),
    }
)

JOYCON_LEFT_BUTTON_BITS: ButtonBitMap = MappingProxyType(
    {
        Button.MINUS: (4, 0x01),
        Button.LEFT_STICK: (4, 0x08),
        Button.CAPTURE: (4, 0x20),
        Button.DPAD_DOWN: (5, 0x01),
        Button.DPAD_UP: (5, 0x02),
        Button.DPAD_RIGHT: (5, 0x04),
        Button.DPAD_LEFT: (5, 0x08),
        Button.SR: (5, 0x10),
        Button.SL: (5, 0x20),
        Button.L: (5, 0x40),
        Button.ZL: (5, 0x80),
    }
)

JOYCON_RIGHT_BUTTON_BITS: ButtonBitMap = MappingProxyType(
    {
        Button.Y: (3, 0x01),
        Button.X: (3, 0x02),
        Button.B: (3, 0x04),
        Button.A: (3, 0x08),
        Button.SR: (3, 0x10),
        Button.SL: (3, 0x20),
        Button.R: (3, 0x40),
        Button.ZR: (3, 0x80),
        Button.PLUS: (4, 0x02),
        Button.RIGHT_STICK: (4, 0x04),
        Button.HOME: (4, 0x10),
    }
)
