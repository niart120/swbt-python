"""Python API for virtual NX-compatible input devices."""

from swbt.diagnostics import DiagnosticsConfig, GamepadStatus
from swbt.gamepad import ConnectionResult, SwitchGamepad, SwitchGamepadConfig
from swbt.input import Button, IMUFrame, InputState, Stick

__all__ = (
    "Button",
    "ConnectionResult",
    "DiagnosticsConfig",
    "GamepadStatus",
    "IMUFrame",
    "InputState",
    "Stick",
    "SwitchGamepad",
    "SwitchGamepadConfig",
)
