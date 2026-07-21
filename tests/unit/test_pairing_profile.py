import json
from pathlib import Path

import pytest

from swbt import InvalidProfileError
from swbt.protocol.profiles.base import ControllerKind
from swbt.transport._pairing_profile import (
    LocalAddress,
    PairingProfile,
)


def test_local_address_accepts_individual_locally_administered_value() -> None:
    address = LocalAddress.parse("02:12:34:56:78:9a")

    assert str(address) == "02:12:34:56:78:9A"
    assert address.bytes == bytes.fromhex("02 12 34 56 78 9A")


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("02:12:34:56:78", "6 octets"),
        ("03:12:34:56:78:9A", "individual"),
        ("00:12:34:56:78:9A", "locally administered"),
        ("02:12:34:9E:8B:00", "reserved inquiry LAP"),
        ("02:12:34:9E:8B:33", "reserved inquiry LAP"),
        ("02:12:34:9E:8B:3F", "reserved inquiry LAP"),
    ],
)
def test_local_address_rejects_values_outside_profile_contract(
    value: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        LocalAddress.parse(value)


def test_local_address_allows_values_adjacent_to_reserved_lap() -> None:
    assert str(LocalAddress.parse("02:12:34:9E:8A:FF")) == "02:12:34:9E:8A:FF"
    assert str(LocalAddress.parse("02:12:34:9E:8B:40")) == "02:12:34:9E:8B:40"


def test_pairing_profile_loads_supported_pro_controller_envelope(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "format": "swbt.profile",
                "schema_version": 1,
                "controller_kind": "pro",
                "identity": {
                    "kind": "exp-local-address",
                    "address": "02:12:34:56:78:9a",
                },
                "key_store": {"namespaces": {"02:12:34:56:78:9A": {}}},
            }
        ),
        encoding="utf-8",
    )

    profile = PairingProfile.load(profile_path)

    assert str(profile.local_address) == "02:12:34:56:78:9A"
    assert profile.controller_kind is ControllerKind.PRO_CONTROLLER
    assert profile.key_store_namespaces == {"02:12:34:56:78:9A": {}}


@pytest.mark.parametrize(
    "payload",
    [
        {"02:12:34:56:78:9A": {}},
        {
            "format": "unknown",
            "schema_version": 1,
            "controller_kind": "pro",
            "identity": {
                "kind": "exp-local-address",
                "address": "02:12:34:56:78:9A",
            },
            "key_store": {"namespaces": {}},
        },
        {
            "format": "swbt.profile",
            "schema_version": 2,
            "controller_kind": "pro",
            "identity": {
                "kind": "exp-local-address",
                "address": "02:12:34:56:78:9A",
            },
            "key_store": {"namespaces": {}},
        },
        {
            "format": "swbt.profile",
            "schema_version": 1,
            "controller_kind": "unsupported_controller",
            "identity": {
                "kind": "exp-local-address",
                "address": "02:12:34:56:78:9A",
            },
            "key_store": {"namespaces": {}},
        },
        {
            "format": "swbt.profile",
            "schema_version": 1,
            "controller_kind": "pro",
            "identity": {
                "kind": "factory-address",
                "address": "02:12:34:56:78:9A",
            },
            "key_store": {"namespaces": {}},
        },
        {
            "format": "swbt.profile",
            "schema_version": 1,
            "controller_kind": "pro",
            "identity": {
                "kind": "exp-local-address",
                "address": "02:12:34:56:78:9A",
            },
            "key_store": {"namespaces": []},
        },
    ],
)
def test_pairing_profile_rejects_unsupported_envelope_before_adapter_open(
    tmp_path: Path,
    payload: object,
) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidProfileError):
        PairingProfile.load(profile_path)


def test_pairing_profile_rejects_malformed_json_before_adapter_open(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "profile.json"
    profile_path.write_text("{", encoding="utf-8")

    with pytest.raises(InvalidProfileError):
        PairingProfile.load(profile_path)


def test_pairing_profile_create_new_atomically_saves_empty_pro_envelope(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "profiles" / "pro.json"

    profile = PairingProfile.create_new(
        profile_path,
        LocalAddress.parse("02:12:34:56:78:9A"),
    )

    assert profile == PairingProfile.load(profile_path)
    assert json.loads(profile_path.read_text(encoding="utf-8")) == {
        "format": "swbt.profile",
        "schema_version": 1,
        "identity": {
            "kind": "exp-local-address",
            "address": "02:12:34:56:78:9A",
        },
        "controller_kind": "pro",
        "key_store": {
            "namespaces": {
                "02:12:34:56:78:9A": {},
                "swbt.previous::02:12:34:56:78:9A": {},
            }
        },
    }
    assert list(profile_path.parent.iterdir()) == [profile_path]


def test_pairing_profile_create_new_saves_joycon_l_controller_kind(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "joycon-l.json"

    profile = PairingProfile.create_new(
        profile_path,
        LocalAddress.parse("02:12:34:56:78:9A"),
        controller_kind=ControllerKind.JOYCON_LEFT,
    )

    assert profile.controller_kind is ControllerKind.JOYCON_LEFT
    assert PairingProfile.load(profile_path).controller_kind is ControllerKind.JOYCON_LEFT
    assert json.loads(profile_path.read_text(encoding="utf-8"))["controller_kind"] == "joycon_l"


def test_pairing_profile_create_new_saves_joycon_r_controller_kind(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "joycon-r.json"

    profile = PairingProfile.create_new(
        profile_path,
        LocalAddress.parse("02:12:34:56:78:9A"),
        controller_kind=ControllerKind.JOYCON_RIGHT,
    )

    assert profile.controller_kind is ControllerKind.JOYCON_RIGHT
    assert PairingProfile.load(profile_path).controller_kind is ControllerKind.JOYCON_RIGHT
    assert json.loads(profile_path.read_text(encoding="utf-8"))["controller_kind"] == "joycon_r"


@pytest.mark.parametrize(
    ("legacy_kind", "expected_kind", "normalized_kind"),
    [
        ("direct_pro", ControllerKind.PRO_CONTROLLER, "pro"),
        ("direct_joycon_l", ControllerKind.JOYCON_LEFT, "joycon_l"),
        ("direct_joycon_r", ControllerKind.JOYCON_RIGHT, "joycon_r"),
    ],
)
def test_pairing_profile_load_normalizes_legacy_direct_controller_kind(
    tmp_path: Path,
    legacy_kind: str,
    expected_kind: ControllerKind,
    normalized_kind: str,
) -> None:
    """A legacy profile does not retain the old reporting mode classification."""
    profile_path = tmp_path / f"{legacy_kind}.json"
    profile_path.write_text(
        json.dumps(
            {
                "format": "swbt.profile",
                "schema_version": 1,
                "controller_kind": legacy_kind,
                "identity": {
                    "kind": "exp-local-address",
                    "address": "02:12:34:56:78:9A",
                },
                "key_store": {"namespaces": {"02:12:34:56:78:9A": {}}},
            }
        ),
        encoding="utf-8",
    )

    profile = PairingProfile.load(profile_path)

    assert profile.controller_kind is expected_kind
    profile.save(profile_path)
    assert (
        json.loads(profile_path.read_text(encoding="utf-8"))["controller_kind"] == normalized_kind
    )


def test_pairing_profile_create_new_does_not_overwrite_existing_path(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "pro.json"
    original = b"existing profile"
    profile_path.write_bytes(original)

    with pytest.raises(FileExistsError):
        PairingProfile.create_new(
            profile_path,
            LocalAddress.parse("02:12:34:56:78:9A"),
        )

    assert profile_path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [profile_path]
