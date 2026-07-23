import asyncio
import json
from pathlib import Path

import pytest
from bumble.keys import PairingKeys

from swbt import (
    ConnectionFailedError,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    JoyConL,
    JoyConR,
    ProController,
)
from swbt.protocol.profiles.base import ControllerKind
from swbt.transport._bumble_key_store import _PairingProfileKeyStore
from swbt.transport._pairing_profile import LocalAddress, PairingProfile


def _pairing_keys(marker: int) -> PairingKeys:
    return PairingKeys(
        link_key=PairingKeys.Key(bytes([marker]) * 16, authenticated=True),
        link_key_type=4,
    )


def test_profile_key_store_update_preserves_identity_and_namespace_generations(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "pro.json"
    target = LocalAddress.parse("02:12:34:56:78:9A")
    PairingProfile.create_new(profile_path, target)
    key_store = _PairingProfileKeyStore(
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
                local_address="02:12:34:56:78:9A",
                pair_timeout=0.25,
            )

        retry = ProController(adapter="usb:0", profile_path=str(profile_path))
        await retry.pair(timeout=0.5)

    asyncio.run(run())

    assert PairingProfile.load(profile_path).local_address == LocalAddress.parse(
        "02:12:34:56:78:9A"
    )
    assert attempts == [
        (str(profile_path), 0.25),
        (str(profile_path), 0.5),
    ]
    assert closed_profiles == [str(profile_path)]


@pytest.mark.parametrize(
    "controller_cls",
    [
        ProController,
        JoyConL,
        JoyConR,
        DirectProController,
        DirectJoyConL,
        DirectJoyConR,
    ],
)
def test_create_profile_without_local_address_uses_adapter_default_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    controller_cls: type[
        ProController | JoyConL | JoyConR | DirectProController | DirectJoyConL | DirectJoyConR
    ],
) -> None:
    profile_path = tmp_path / f"{controller_cls.__name__}.json"
    attempts: list[float | None] = []

    async def fake_pair(
        self: object,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> None:
        _ = self
        attempts.append(timeout)

    monkeypatch.setattr(controller_cls, "pair", fake_pair)

    async def run() -> None:
        pad = await controller_cls.create_profile(
            adapter="usb:0",
            profile_path=str(profile_path),
            pair_timeout=0.25,
        )
        await pad.close()

    asyncio.run(run())

    profile = PairingProfile.load(profile_path)
    assert profile.local_address is None
    assert profile.key_store_namespaces == {}
    assert attempts == [0.25]


def test_joycon_l_create_profile_saves_kind_and_leaves_profile_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "joycon-l.json"
    attempts: list[float | None] = []

    async def fail_pair(
        self: JoyConL,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> None:
        _ = self
        attempts.append(timeout)
        msg = "pairing failed"
        raise ConnectionFailedError(msg)

    async def fake_close(self: JoyConL, *, neutral: bool = True) -> None:
        _ = (self, neutral)

    monkeypatch.setattr(JoyConL, "pair", fail_pair)
    monkeypatch.setattr(JoyConL, "close", fake_close)

    async def run() -> None:
        with pytest.raises(ConnectionFailedError, match="pairing failed"):
            await JoyConL.create_profile(
                adapter="usb:0",
                profile_path=str(profile_path),
                local_address="02:12:34:56:78:9A",
                pair_timeout=0.25,
            )

    asyncio.run(run())

    profile = PairingProfile.load(profile_path)
    assert profile.controller_kind is ControllerKind.JOYCON_LEFT
    assert attempts == [0.25]
    retry = JoyConL(adapter="usb:0", profile_path=str(profile_path))
    assert retry._runtime._config.profile_path == str(profile_path)


def test_joycon_r_create_profile_saves_kind_and_leaves_profile_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "joycon-r.json"
    attempts: list[float | None] = []

    async def fail_pair(
        self: JoyConR,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> None:
        _ = self
        attempts.append(timeout)
        msg = "pairing failed"
        raise ConnectionFailedError(msg)

    async def fake_close(self: JoyConR, *, neutral: bool = True) -> None:
        _ = (self, neutral)

    monkeypatch.setattr(JoyConR, "pair", fail_pair)
    monkeypatch.setattr(JoyConR, "close", fake_close)

    async def run() -> None:
        with pytest.raises(ConnectionFailedError, match="pairing failed"):
            await JoyConR.create_profile(
                adapter="usb:0",
                profile_path=str(profile_path),
                local_address="02:12:34:56:78:9A",
                pair_timeout=0.25,
            )

    asyncio.run(run())

    profile = PairingProfile.load(profile_path)
    assert profile.controller_kind is ControllerKind.JOYCON_RIGHT
    assert attempts == [0.25]
    retry = JoyConR(adapter="usb:0", profile_path=str(profile_path))
    assert retry._runtime._config.profile_path == str(profile_path)


@pytest.mark.parametrize(
    ("controller_cls", "controller_kind", "serialized_kind"),
    [
        (DirectProController, ControllerKind.PRO_CONTROLLER, "pro"),
        (DirectJoyConL, ControllerKind.JOYCON_LEFT, "joycon_l"),
        (DirectJoyConR, ControllerKind.JOYCON_RIGHT, "joycon_r"),
    ],
)
def test_direct_create_profile_saves_kind_and_leaves_profile_for_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    controller_cls: type[DirectProController | DirectJoyConL | DirectJoyConR],
    controller_kind: ControllerKind,
    serialized_kind: str,
) -> None:
    """Direct profile creation leaves a reusable profile after pairing failure."""
    profile_path = tmp_path / f"{controller_kind.value}.json"
    attempts: list[float | None] = []

    async def fail_pair(
        self: DirectProController | DirectJoyConL | DirectJoyConR,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> None:
        _ = self
        attempts.append(timeout)
        msg = "pairing failed"
        raise ConnectionFailedError(msg)

    async def fake_close(
        self: DirectProController | DirectJoyConL | DirectJoyConR,
        *,
        neutral: bool = True,
    ) -> None:
        _ = (self, neutral)

    monkeypatch.setattr(controller_cls, "pair", fail_pair)
    monkeypatch.setattr(controller_cls, "close", fake_close)

    async def run() -> None:
        with pytest.raises(ConnectionFailedError, match="pairing failed"):
            await controller_cls.create_profile(
                adapter="usb:0",
                profile_path=str(profile_path),
                local_address="02:12:34:56:78:9A",
                pair_timeout=0.25,
            )

    asyncio.run(run())

    profile = PairingProfile.load(profile_path)
    assert profile.controller_kind is controller_kind
    assert (
        json.loads(profile_path.read_text(encoding="utf-8"))["controller_kind"] == serialized_kind
    )
    assert attempts == [0.25]
    retry = controller_cls(adapter="usb:0", profile_path=str(profile_path))
    assert retry._runtime._config.profile_path == str(profile_path)
    assert retry._runtime._report_loop is None
