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
    InvalidProfileError,
    SwbtError,
    TransportOpenError,
    UnsupportedInputError,
)
from swbt.gamepad import (
    ConnectionResult,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    DirectSwitchGamepad,
    JoyConL,
    JoyConR,
    PeriodicSwitchGamepad,
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
    "DirectJoyConL",
    "DirectJoyConR",
    "DirectProController",
    "DirectSwitchGamepad",
    "GamepadStatus",
    "IMUFrame",
    "InputState",
    "InvalidInputError",
    "InvalidKeyStoreError",
    "InvalidProfileError",
    "JoyConL",
    "JoyConR",
    "PeriodicSwitchGamepad",
    "ProController",
    "Stick",
    "SwbtError",
    "SwitchGamepad",
    "TransportOpenError",
    "UnsupportedInputError",
    "list_adapters",
)
