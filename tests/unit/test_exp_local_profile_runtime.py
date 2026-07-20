import asyncio
import json
from io import StringIO
from pathlib import Path

import pytest

from swbt import (
    DiagnosticsConfig,
    ExpLocalAddressRecoveryRequired,
    InvalidProfileError,
    ProController,
)
from swbt.gamepad import runtime as gamepad_runtime
from swbt.gamepad import transport_factory as gamepad_transport_factory
from swbt.transport._exp_local_address import ExpLocalAddress, ExpLocalProfile
from swbt.transport._exp_local_identity import ExpLocalIdentityPreparationResult
from swbt.transport.base import HidDeviceTransport
from swbt.transport.fake import FakeHidTransport


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


def test_profile_target_is_forwarded_to_bumble_power_on_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "pro.json"
    target = ExpLocalAddress.parse("02:12:34:56:78:9A")
    ExpLocalProfile.create_new(profile_path, target)
    captured: dict[str, object] = {}
    expected_transport = FakeHidTransport()

    async def successful_preparation(
        *,
        adapter: str,
        target: ExpLocalAddress,
    ) -> ExpLocalIdentityPreparationResult:
        captured["prepared"] = (adapter, str(target))
        return ExpLocalIdentityPreparationResult(
            status="already_active",
            current_address=str(target),
            target_address=str(target),
        )

    def create_transport(
        *,
        adapter: str,
        device_name: str,
        profile: object,
        diagnostics: object,
        key_store_path: str | None,
        profile_path: str | None,
        expected_local_bluetooth_address: bytes | None,
    ) -> HidDeviceTransport:
        captured.update(
            {
                "adapter": adapter,
                "device_name": device_name,
                "profile": profile,
                "diagnostics": diagnostics,
                "key_store_path": key_store_path,
                "profile_path": profile_path,
                "expected_local_bluetooth_address": expected_local_bluetooth_address,
            }
        )
        return expected_transport

    monkeypatch.setattr(
        gamepad_runtime,
        "prepare_exp_local_identity",
        successful_preparation,
    )
    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        create_transport,
    )
    trace = StringIO()
    pad = ProController(
        adapter="usb:0",
        profile_path=str(profile_path),
        diagnostics=DiagnosticsConfig(trace_writer=trace),
    )

    asyncio.run(pad._runtime._prepare_exp_local_profile())
    transport = pad._runtime._ensure_transport()

    assert transport is expected_transport
    assert captured["prepared"] == ("usb:0", "02:12:34:56:78:9A")
    assert captured["key_store_path"] is None
    assert captured["profile_path"] == str(profile_path)
    assert captured["expected_local_bluetooth_address"] == bytes.fromhex("02 12 34 56 78 9A")
    assert json.loads(trace.getvalue()) == {
        "event": "exp_local_identity_prepared",
        "current_address": "02:12:34:56:78:9A",
        "status": "already_active",
        "target_address": "02:12:34:56:78:9A",
    }
