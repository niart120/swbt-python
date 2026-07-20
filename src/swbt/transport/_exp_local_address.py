"""Validated local Bluetooth identity values for exp profiles."""

import re
from dataclasses import dataclass

_ADDRESS_PATTERN = re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")
_RESERVED_INQUIRY_LAP_MIN = 0x9E8B00
_RESERVED_INQUIRY_LAP_MAX = 0x9E8B3F


@dataclass(frozen=True)
class ExpLocalAddress:
    """An individual, locally administered six-octet Bluetooth address."""

    _octets: bytes

    @classmethod
    def parse(cls, value: str) -> "ExpLocalAddress":
        """Parse and validate the canonical exp profile address contract."""
        if _ADDRESS_PATTERN.fullmatch(value) is None:
            msg = "exp_local_address must contain 6 octets in XX:XX:XX:XX:XX:XX form"
            raise ValueError(msg)

        octets = bytes.fromhex(value.replace(":", ""))
        first_octet = octets[0]
        if first_octet & 0x01:
            msg = "exp_local_address must be an individual address"
            raise ValueError(msg)
        if not first_octet & 0x02:
            msg = "exp_local_address must be locally administered"
            raise ValueError(msg)

        lap = int.from_bytes(octets[3:], "big")
        if _RESERVED_INQUIRY_LAP_MIN <= lap <= _RESERVED_INQUIRY_LAP_MAX:
            msg = "exp_local_address must not use a reserved inquiry LAP"
            raise ValueError(msg)
        return cls(octets)

    @property
    def bytes(self) -> bytes:
        """Return the six address octets in display order."""
        return self._octets

    def __str__(self) -> str:
        """Return uppercase colon notation."""
        return self._octets.hex(":").upper()
