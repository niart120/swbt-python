"""Python API for virtual NX-compatible input devices."""

from swbt.diagnostics import DiagnosticsConfig, GamepadStatus
from swbt.errors import (
    ClosedError,
    ConnectionFailedError,
    ConnectionTimeoutError,
    InvalidInputError,
    SwbtError,
    TransportOpenError,
)
from swbt.gamepad import ConnectionResult, SwitchGamepad, SwitchGamepadConfig
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.transport.base import BondedPeer, DisconnectRequestResult, HidDeviceTransport

__all__ = (
    "BondedPeer",
    "Button",
    "ClosedError",
    "ConnectionFailedError",
    "ConnectionResult",
    "ConnectionTimeoutError",
    "DiagnosticsConfig",
    "DisconnectRequestResult",
    "GamepadStatus",
    "HidDeviceTransport",
    "IMUFrame",
    "InputState",
    "InvalidInputError",
    "Stick",
    "SwbtError",
    "SwitchGamepad",
    "SwitchGamepadConfig",
    "TransportOpenError",
)
