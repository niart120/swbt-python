"""Validation and persistence types for exp local address profiles."""

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn, cast

from swbt.errors import InvalidProfileError

_ADDRESS_PATTERN = re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")
_RESERVED_INQUIRY_LAP_MIN = 0x9E8B00
_RESERVED_INQUIRY_LAP_MAX = 0x9E8B3F
_PROFILE_FORMAT = "swbt.profile"
_PROFILE_SCHEMA_VERSION = 1
_PROFILE_IDENTITY_KIND = "exp-local-address"
_PROFILE_CONTROLLER_KIND = "pro"

type KeyStoreNamespaces = dict[str, dict[str, object]]


def _invalid_profile(message: str, *, cause: Exception | None = None) -> NoReturn:
    if cause is None:
        raise InvalidProfileError(message)
    raise InvalidProfileError(message) from cause


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


@dataclass(frozen=True)
class ExpLocalProfile:
    """Validated version 1 profile envelope for a Pro Controller."""

    exp_local_address: ExpLocalAddress
    key_store_namespaces: KeyStoreNamespaces
    controller_kind: str = _PROFILE_CONTROLLER_KIND

    @classmethod
    def load(cls, path: str | Path) -> "ExpLocalProfile":
        """Load a supported profile without opening an adapter."""
        try:
            with Path(path).open(encoding="utf-8") as profile_file:
                payload: object = json.load(profile_file)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            _invalid_profile("profile is not valid UTF-8 JSON", cause=error)

        if not isinstance(payload, dict):
            _invalid_profile("profile root must be an object")
        if payload.get("format") != _PROFILE_FORMAT:
            _invalid_profile("profile format is unsupported")
        if payload.get("schema_version") != _PROFILE_SCHEMA_VERSION:
            _invalid_profile("profile schema_version is unsupported")
        if payload.get("controller_kind") != _PROFILE_CONTROLLER_KIND:
            _invalid_profile("profile controller_kind must be 'pro'")

        identity = payload.get("identity")
        if not isinstance(identity, dict):
            _invalid_profile("profile identity must be an object")
        if identity.get("kind") != _PROFILE_IDENTITY_KIND:
            _invalid_profile("profile identity kind is unsupported")
        address_value = identity.get("address")
        if not isinstance(address_value, str):
            _invalid_profile("profile identity address must be a string")
        try:
            address = ExpLocalAddress.parse(address_value)
        except ValueError as error:
            _invalid_profile(str(error), cause=error)

        key_store = payload.get("key_store")
        if not isinstance(key_store, dict):
            _invalid_profile("profile key_store must be an object")
        namespaces = key_store.get("namespaces")
        if not isinstance(namespaces, dict) or not all(
            isinstance(key, str) and isinstance(value, dict) for key, value in namespaces.items()
        ):
            _invalid_profile("profile key_store.namespaces must be an object map")

        return cls(
            exp_local_address=address,
            key_store_namespaces=cast("KeyStoreNamespaces", copy.deepcopy(namespaces)),
        )
