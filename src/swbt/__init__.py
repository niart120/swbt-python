"""Python API for virtual NX-compatible input devices."""

from swbt.adapter_discovery import AdapterInfo, list_adapters
from swbt.diagnostics import DiagnosticsConfig, GamepadStatus
from swbt.errors import (
    AdapterDiscoveryError,
    ClosedError,
    ConnectionFailedError,
    ConnectionTimeoutError,
    InvalidInputError,
    InvalidKeyStoreError,
    SwbtError,
    TransportOpenError,
    UnsupportedInputError,
)
from swbt.gamepad import (
    ConnectionResult,
    JoyConL,
    JoyConR,
    ProController,
    SwitchGamepad,
)
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.profiles.base import ControllerColors

__all__ = (
    "AdapterDiscoveryError",
    "AdapterInfo",
    "Button",
    "ClosedError",
    "ConnectionFailedError",
    "ConnectionResult",
    "ConnectionTimeoutError",
    "ControllerColors",
    "DiagnosticsConfig",
    "GamepadStatus",
    "IMUFrame",
    "InputState",
    "InvalidInputError",
    "InvalidKeyStoreError",
    "JoyConL",
    "JoyConR",
    "ProController",
    "Stick",
    "SwbtError",
    "SwitchGamepad",
    "TransportOpenError",
    "UnsupportedInputError",
    "list_adapters",
)
