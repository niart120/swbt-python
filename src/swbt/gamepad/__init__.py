"""Public gamepad facade."""

from swbt.gamepad.connection import ConnectionResult, ConnectionStatus
from swbt.gamepad.constants import DISCONNECT_REQUEST_TIMEOUT_SECONDS
from swbt.gamepad.core import JoyCon, SwitchGamepad, SwitchGamepadConfig

__all__ = (
    "DISCONNECT_REQUEST_TIMEOUT_SECONDS",
    "ConnectionResult",
    "ConnectionStatus",
    "JoyCon",
    "SwitchGamepad",
    "SwitchGamepadConfig",
)
