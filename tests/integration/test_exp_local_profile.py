import asyncio
import json
from pathlib import Path

from bumble.keys import PairingKeys

from swbt.transport._bumble_key_store import _ExpLocalProfileKeyStore
from swbt.transport._exp_local_address import ExpLocalAddress, ExpLocalProfile


def _pairing_keys(marker: int) -> PairingKeys:
    return PairingKeys(
        link_key=PairingKeys.Key(bytes([marker]) * 16, authenticated=True),
        link_key_type=4,
    )


def test_profile_key_store_update_preserves_identity_and_namespace_generations(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "pro.json"
    target = ExpLocalAddress.parse("02:12:34:56:78:9A")
    ExpLocalProfile.create_new(profile_path, target)
    key_store = _ExpLocalProfileKeyStore(
        profile_path=profile_path,
        namespace=str(target),
    )
    first_peer = "01:02:03:04:05:06"
    second_peer = "0A:0B:0C:0D:0E:0F"

    async def update_keys() -> None:
        await key_store.update(first_peer, _pairing_keys(1))
        await key_store.update(second_peer, _pairing_keys(2))

    asyncio.run(update_keys())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == "pro"
    assert payload["identity"] == {
        "kind": "exp-local-address",
        "address": "02:12:34:56:78:9A",
    }
    namespaces = payload["key_store"]["namespaces"]
    assert namespaces[str(target)][second_peer]["link_key"]["value"] == "02" * 16
    previous_namespace = f"swbt.previous::{target}"
    assert namespaces[previous_namespace][first_peer]["link_key"]["value"] == "01" * 16
    assert asyncio.run(key_store.get_all()) == [
        (second_peer, _pairing_keys(2)),
    ]
