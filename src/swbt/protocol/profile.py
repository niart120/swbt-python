"""Internal compatibility imports for protocol profile implementations."""

from swbt.protocol.buttons import (
    JOYCON_LEFT_BUTTON_BITS,
    JOYCON_RIGHT_BUTTON_BITS,
    PRO_CONTROLLER_BUTTON_BITS,
    ButtonBitMap,
)
from swbt.protocol.descriptors import SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR
from swbt.protocol.profiles.base import (
    ControllerColors,
    ControllerKind,
    ControllerProfile,
    HidSdpPolicy,
)
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import (
    ProControllerProfile,
    default_controller_profile,
)

__all__ = (
    "JOYCON_LEFT_BUTTON_BITS",
    "JOYCON_RIGHT_BUTTON_BITS",
    "PRO_CONTROLLER_BUTTON_BITS",
    "SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR",
    "ButtonBitMap",
    "ControllerColors",
    "ControllerKind",
    "ControllerProfile",
    "HidSdpPolicy",
    "JoyConLeftProfile",
    "JoyConRightProfile",
    "ProControllerProfile",
    "default_controller_profile",
)
