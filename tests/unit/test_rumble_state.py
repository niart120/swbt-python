import pytest

from swbt.errors import ProtocolError
from swbt.protocol.rumble import RumbleState


def test_rumble_state_keeps_raw_rumble_bytes() -> None:
    state = RumbleState.from_raw(bytes.fromhex("00 01 40 40 00 01 40 40"), updated_at_ns=123)

    assert state.raw == bytes.fromhex("00 01 40 40 00 01 40 40")
    assert state.updated_at_ns == 123


def test_rumble_state_rejects_non_8_byte_payload() -> None:
    with pytest.raises(ProtocolError):
        RumbleState.from_raw(b"\x00", updated_at_ns=123)
