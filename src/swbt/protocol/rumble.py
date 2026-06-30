"""Raw rumble state."""

from dataclasses import dataclass

from swbt.errors import ProtocolError


@dataclass(frozen=True)
class RumbleState:
    """Raw 8-byte rumble payload with receive timestamp."""

    raw: bytes
    updated_at_ns: int

    @classmethod
    def from_raw(cls, raw: bytes, *, updated_at_ns: int) -> "RumbleState":
        """Create rumble state from an 8-byte payload."""
        if len(raw) != 8:
            msg = f"rumble payload must be 8 bytes: {len(raw)}"
            raise ProtocolError(msg)
        return cls(raw=bytes(raw), updated_at_ns=updated_at_ns)
