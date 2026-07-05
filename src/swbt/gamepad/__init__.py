"""Public gamepad facade."""

from swbt.gamepad.connection import ConnectionResult, ConnectionStatus
from swbt.gamepad.core import JoyCon, SwitchGamepad, SwitchGamepadConfig

DISCONNECT_REQUEST_TIMEOUT_SECONDS = 0.25

__all__ = (
    "DISCONNECT_REQUEST_TIMEOUT_SECONDS",
    "ConnectionResult",
    "ConnectionStatus",
    "JoyCon",
    "SwitchGamepad",
    "SwitchGamepadConfig",
)
