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
)
from swbt.gamepad import ConnectionResult, SwitchGamepad, SwitchGamepadConfig
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.profile import ControllerColors
from swbt.transport.base import BondedPeer, DisconnectRequestResult, HidDeviceTransport

__all__ = (
    "AdapterDiscoveryError",
    "AdapterInfo",
    "BondedPeer",
    "Button",
    "ClosedError",
    "ConnectionFailedError",
    "ConnectionResult",
    "ConnectionTimeoutError",
    "ControllerColors",
    "DiagnosticsConfig",
    "DisconnectRequestResult",
    "GamepadStatus",
    "HidDeviceTransport",
    "IMUFrame",
    "InputState",
    "InvalidInputError",
    "InvalidKeyStoreError",
    "Stick",
    "SwbtError",
    "SwitchGamepad",
    "SwitchGamepadConfig",
    "TransportOpenError",
    "list_adapters",
)
