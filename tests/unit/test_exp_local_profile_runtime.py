import asyncio
from pathlib import Path

import pytest

from swbt import ExpLocalAddressRecoveryRequired, InvalidProfileError, ProController
from swbt.gamepad import runtime as gamepad_runtime
from swbt.gamepad import transport_factory as gamepad_transport_factory
from swbt.transport._exp_local_address import ExpLocalAddress, ExpLocalProfile


def test_recovery_required_stops_before_bumble_transport_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "pro.json"
    target = ExpLocalAddress.parse("02:12:34:56:78:9A")
    ExpLocalProfile.create_new(profile_path, target)
    events: list[str] = []

    async def fail_preparation(
        *,
        adapter: str,
        target: ExpLocalAddress,
    ) -> object:
        events.append(f"prepare:{adapter}:{target}")
        raise ExpLocalAddressRecoveryRequired(
            target_address=str(target),
            stage="reenumeration",
        )

    def fail_transport_creation(**_kwargs: object) -> object:
        events.append("transport_created")
        raise AssertionError

    monkeypatch.setattr(
        gamepad_runtime,
        "prepare_exp_local_identity",
        fail_preparation,
    )
    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        fail_transport_creation,
    )
    pad = ProController(adapter="usb:0", profile_path=str(profile_path))

    with pytest.raises(ExpLocalAddressRecoveryRequired):
        asyncio.run(pad.pair(timeout=0.1))

    assert events == ["prepare:usb:0:02:12:34:56:78:9A"]


def test_invalid_profile_stops_before_preparation_and_transport_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "invalid.json"
    profile_path.write_text('{"format": "unknown"}', encoding="utf-8")
    events: list[str] = []

    async def fail_preparation(**_kwargs: object) -> object:
        events.append("preparation_started")
        raise AssertionError

    def fail_transport_creation(**_kwargs: object) -> object:
        events.append("transport_created")
        raise AssertionError

    monkeypatch.setattr(
        gamepad_runtime,
        "prepare_exp_local_identity",
        fail_preparation,
    )
    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        fail_transport_creation,
    )
    pad = ProController(adapter="usb:0", profile_path=str(profile_path))

    with pytest.raises(InvalidProfileError):
        asyncio.run(pad.open())

    assert events == []
