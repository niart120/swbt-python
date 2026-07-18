"""Public gamepad facade."""

from swbt.gamepad.connection import ConnectionResult, ConnectionStatus
from swbt.gamepad.constants import DISCONNECT_REQUEST_TIMEOUT_SECONDS
from swbt.gamepad.core import (
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    JoyConL,
    JoyConR,
    ProController,
)
from swbt.gamepad.interface import (
    DirectSwitchGamepad,
    PeriodicSwitchGamepad,
    SwitchGamepad,
)

__all__ = (
    "DISCONNECT_REQUEST_TIMEOUT_SECONDS",
    "ConnectionResult",
    "ConnectionStatus",
    "DirectJoyConL",
    "DirectJoyConR",
    "DirectProController",
    "DirectSwitchGamepad",
    "JoyConL",
    "JoyConR",
    "PeriodicSwitchGamepad",
    "ProController",
    "SwitchGamepad",
)
