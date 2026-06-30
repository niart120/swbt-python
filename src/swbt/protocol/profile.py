"""Fixed protocol profile values for the controller shape."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProControllerProfile:
    """Protocol defaults for a Pro Controller compatible report shape."""

    battery_connection: int = 0x91
    vibrator_input: int = 0x00
    bluetooth_address: bytes = b"\x00\x00\x00\x00\x00\x00"
