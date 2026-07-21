import asyncio
import json
from io import StringIO
from pathlib import Path

import pytest

from swbt import (
    AdapterIdentityRecoveryRequired,
    DiagnosticsConfig,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    InvalidProfileError,
    JoyConL,
    JoyConR,
    ProController,
    ProfileControllerMismatchError,
)
from swbt.gamepad import runtime as gamepad_runtime
from swbt.gamepad import transport_factory as gamepad_transport_factory
from swbt.protocol.profiles.base import ControllerKind
from swbt.transport._adapter_identity import AdapterIdentityPreparationResult
from swbt.transport._pairing_profile import LocalAddress, PairingProfile
from swbt.transport.base import HidDeviceTransport
from swbt.transport.fake import FakeHidTransport


@pytest.mark.parametrize(
    ("controller_cls", "controller_kind"),
    [
        (ProController, ControllerKind.PRO_CONTROLLER),
        (JoyConL, ControllerKind.JOYCON_LEFT),
        (JoyConR, ControllerKind.JOYCON_RIGHT),
    ],
)
def test_recovery_required_stops_before_bumble_transport_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    controller_cls: type[ProController | JoyConL | JoyConR],
    controller_kind: ControllerKind,
) -> None:
    profile_path = tmp_path / f"{controller_kind.value}.json"
    target = LocalAddress.parse("02:12:34:56:78:9A")
    PairingProfile.create_new(
        profile_path,
        target,
        controller_kind=controller_kind,
    )
    events: list[str] = []

    async def fail_preparation(
        *,
        adapter: str,
        target: LocalAddress,
    ) -> object:
        events.append(f"prepare:{adapter}:{target}")
        raise AdapterIdentityRecoveryRequired(
            target_address=str(target),
            stage="reenumeration",
        )

    def fail_transport_creation(**_kwargs: object) -> object:
        events.append("transport_created")
        raise AssertionError

    monkeypatch.setattr(
        gamepad_runtime,
        "prepare_adapter_identity",
        fail_preparation,
    )
    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        fail_transport_creation,
    )
    pad = controller_cls(adapter="usb:0", profile_path=str(profile_path))

    with pytest.raises(AdapterIdentityRecoveryRequired):
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
        "prepare_adapter_identity",
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


def test_joycon_profile_kind_mismatch_stops_before_preparation_and_transport_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "pro.json"
    PairingProfile.create_new(
        profile_path,
        LocalAddress.parse("02:12:34:56:78:9A"),
    )
    events: list[str] = []

    async def fail_preparation(**_kwargs: object) -> object:
        events.append("preparation_started")
        raise AssertionError

    def fail_transport_creation(**_kwargs: object) -> object:
        events.append("transport_created")
        raise AssertionError

    monkeypatch.setattr(
        gamepad_runtime,
        "prepare_adapter_identity",
        fail_preparation,
    )
    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        fail_transport_creation,
    )
    pad = JoyConL(adapter="usb:0", profile_path=str(profile_path))

    with pytest.raises(ProfileControllerMismatchError) as mismatch:
        asyncio.run(pad.open())

    assert mismatch.value.expected_controller_kind == "joycon_left"
    assert mismatch.value.actual_controller_kind == "pro_controller"
    assert events == []


@pytest.mark.parametrize(
    ("controller_cls", "controller_kind"),
    [
        (DirectProController, ControllerKind.PRO_CONTROLLER),
        (DirectJoyConL, ControllerKind.JOYCON_LEFT),
        (DirectJoyConR, ControllerKind.JOYCON_RIGHT),
    ],
)
def test_direct_controller_reuses_profile_for_the_same_controller_shape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    controller_cls: type[DirectProController | DirectJoyConL | DirectJoyConR],
    controller_kind: ControllerKind,
) -> None:
    """Direct and periodic runtimes share pairing data for one controller shape."""
    profile_path = tmp_path / f"{controller_kind.value}.json"
    PairingProfile.create_new(
        profile_path,
        LocalAddress.parse("02:12:34:56:78:9A"),
        controller_kind=controller_kind,
    )

    async def prepare(**_kwargs: object) -> AdapterIdentityPreparationResult:
        return AdapterIdentityPreparationResult(
            status="already_active",
            current_address="02:12:34:56:78:9A",
            target_address="02:12:34:56:78:9A",
        )

    captured: dict[str, object] = {}
    transport = FakeHidTransport()

    def create_transport(
        *,
        profile_path: str | None,
        expected_local_bluetooth_address: bytes | None,
        **_kwargs: object,
    ) -> HidDeviceTransport:
        captured["profile_path"] = profile_path
        captured["expected_local_bluetooth_address"] = expected_local_bluetooth_address
        return transport

    monkeypatch.setattr(gamepad_runtime, "prepare_adapter_identity", prepare)
    monkeypatch.setattr(
        gamepad_transport_factory,
        "create_default_transport",
        create_transport,
    )
    pad = controller_cls(adapter="usb:0", profile_path=str(profile_path))

    asyncio.run(pad.open())

    assert pad._runtime._pairing_profile is not None
    assert pad._runtime._pairing_profile.controller_kind is controller_kind
    assert captured["profile_path"] == str(profile_path)
    assert captured["expected_local_bluetooth_address"] == bytes.fromhex("02 12 34 56 78 9A")
    assert transport.open_count == 1

    asyncio.run(pad.close())

    assert transport.close_count == 1


def test_profile_target_is_forwarded_to_bumble_power_on_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "pro.json"
    target = LocalAddress.parse("02:12:34:56:78:9A")
    PairingProfile.create_new(profile_path, target)
    captured: dict[str, object] = {}
    expected_transport = FakeHidTransport()

    async def successful_preparation(
        *,
        adapter: str,
        target: LocalAddress,
    ) -> AdapterIdentityPreparationResult:
        captured["prepared"] = (adapter, str(target))
        return AdapterIdentityPreparationResult(
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
        profile_path: str | None,
        expected_local_bluetooth_address: bytes | None,
    ) -> HidDeviceTransport:
        captured.update(
            {
                "adapter": adapter,
                "device_name": device_name,
                "profile": profile,
                "diagnostics": diagnostics,
                "profile_path": profile_path,
                "expected_local_bluetooth_address": expected_local_bluetooth_address,
            }
        )
        return expected_transport

    monkeypatch.setattr(
        gamepad_runtime,
        "prepare_adapter_identity",
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

    asyncio.run(pad._runtime._prepare_pairing_profile())
    transport = pad._runtime._ensure_transport()

    assert transport is expected_transport
    assert captured["prepared"] == ("usb:0", "02:12:34:56:78:9A")
    assert captured["profile_path"] == str(profile_path)
    assert captured["expected_local_bluetooth_address"] == bytes.fromhex("02 12 34 56 78 9A")
    assert json.loads(trace.getvalue()) == {
        "event": "adapter_identity_prepared",
        "current_address": "02:12:34:56:78:9A",
        "status": "already_active",
        "target_address": "02:12:34:56:78:9A",
    }
