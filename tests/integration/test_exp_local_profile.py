import asyncio
import json
from pathlib import Path

import pytest
from bumble.keys import PairingKeys

from swbt import ConnectionFailedError, ProController
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


def test_pairing_failure_leaves_profile_available_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "pro.json"
    attempts: list[tuple[str, float | None]] = []
    closed_profiles: list[str] = []

    async def fake_pair(
        self: ProController,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> None:
        configured_path = self._runtime._config.profile_path
        assert configured_path is not None
        attempts.append((configured_path, timeout))
        if len(attempts) == 1:
            msg = "pairing failed"
            raise ConnectionFailedError(msg)

    async def fake_close(self: ProController, *, neutral: bool = True) -> None:
        _ = neutral
        configured_path = self._runtime._config.profile_path
        assert configured_path is not None
        closed_profiles.append(configured_path)

    monkeypatch.setattr(ProController, "pair", fake_pair)
    monkeypatch.setattr(ProController, "close", fake_close)

    async def run() -> None:
        with pytest.raises(ConnectionFailedError, match="pairing failed"):
            await ProController.create_profile(
                adapter="usb:0",
                profile_path=str(profile_path),
                exp_local_address="02:12:34:56:78:9A",
                pair_timeout=0.25,
            )

        retry = ProController(adapter="usb:0", profile_path=str(profile_path))
        await retry.pair(timeout=0.5)

    asyncio.run(run())

    assert ExpLocalProfile.load(profile_path).exp_local_address == ExpLocalAddress.parse(
        "02:12:34:56:78:9A"
    )
    assert attempts == [
        (str(profile_path), 0.25),
        (str(profile_path), 0.5),
    ]
    assert closed_profiles == [str(profile_path)]
