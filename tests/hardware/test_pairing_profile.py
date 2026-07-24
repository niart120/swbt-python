"""Manual hardware gate for the Pro Controller pairing profile lifecycle."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Literal, TextIO

import pytest

from swbt import (
    Button,
    DiagnosticsConfig,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    InputState,
    JoyConL,
    JoyConR,
    ProController,
)

_PROFILE_FILENAME = "pairing-profile-pro.json"
_ADAPTER_DEFAULT_PROFILE_FILENAME = "pairing-profile-adapter-default-pro.json"
_DIRECT_INPUT_OBSERVATION_SECONDS = 30.0
type JoyConSide = Literal["left", "right"]
type JoyConController = JoyConL | JoyConR
type DirectController = DirectProController | DirectJoyConL | DirectJoyConR

_JOYCON_CASES: tuple[
    tuple[JoyConSide, type[JoyConL] | type[JoyConR], Literal["joycon_l", "joycon_r"]],
    ...,
] = (
    ("left", JoyConL, "joycon_l"),
    ("right", JoyConR, "joycon_r"),
)

_DIRECT_CASES: tuple[
    tuple[
        str,
        type[DirectProController] | type[DirectJoyConL] | type[DirectJoyConR],
        Literal["pro", "joycon_l", "joycon_r"],
        Button,
    ],
    ...,
] = (
    ("pro", DirectProController, "pro", Button.A),
    ("joycon-l", DirectJoyConL, "joycon_l", Button.L),
    ("joycon-r", DirectJoyConR, "joycon_r", Button.R),
)


@pytest.mark.hardware
def test_switch_pairing_profile_fresh_pairing_and_close(
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Create a fresh profile, pair it, and close without restoring the address."""
    profile_path = swbt_hardware_artifact_dir / _PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "pairing-profile-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh pairing profile already exists; use a new --swbt-hardware-artifact-dir")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await ProController.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                local_address=swbt_local_address,
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    events = _read_jsonl(trace_path)
    target = swbt_local_address.upper()
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == "pro"
    assert payload["identity"] == {
        "kind": "exp-local-address",
        "address": target,
    }
    assert payload["key_store"]["namespaces"][target]
    preparation = _first_event(events, "adapter_identity_prepared")
    assert preparation["status"] in {"rewritten", "already_active"}
    assert preparation["target_address"] == target
    assert _contains_event(events, "bumble_device_initialized")
    assert _contains_event(
        events,
        "local_bluetooth_address_configured",
        address=target.replace(":", "").lower(),
    )
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
def test_switch_pairing_profile_reuses_target_after_normal_close(
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reuse the fresh profile and prove that close left the target active."""
    profile_path = swbt_hardware_artifact_dir / _PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "pairing-profile-active-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip(
            "pairing profile is missing; run the fresh pairing test first with the same "
            "--swbt-hardware-artifact-dir"
        )
    original_profile = profile_path.read_bytes()
    target = swbt_local_address.upper()
    payload = json.loads(original_profile)
    if payload.get("identity", {}).get("address") != target:
        pytest.fail("existing pairing profile does not match --swbt-local-address")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "adapter_identity_prepared",
        status="already_active",
        target_address=target,
    )
    assert _contains_event(events, "bumble_device_initialized")
    assert _contains_event(
        events,
        "local_bluetooth_address_configured",
        address=target.replace(":", "").lower(),
    )
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
def test_switch_adapter_default_profile_fresh_pairing_and_close(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Pair with the adapter's current public address and close transport resources."""
    profile_path = swbt_hardware_artifact_dir / _ADAPTER_DEFAULT_PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "pairing-profile-adapter-default-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh pairing profile already exists; use a new --swbt-hardware-artifact-dir")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await ProController.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind="pro_controller")
    namespaces = payload["key_store"]["namespaces"]
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == "pro"
    assert payload["identity"] == {"kind": "adapter-default"}
    assert len(namespaces) == 1
    current_address = next(iter(namespaces))
    assert namespaces[current_address]
    assert not _contains_event(events, "adapter_identity_prepared")
    assert _contains_event(events, "bumble_device_initialized")
    assert _contains_event(
        events,
        "local_bluetooth_address_configured",
        address=current_address.replace(":", "").lower(),
    )
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
def test_switch_adapter_default_profile_reuses_address_after_normal_close(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect with the current adapter address without pairing fallback."""
    profile_path = swbt_hardware_artifact_dir / _ADAPTER_DEFAULT_PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "pairing-profile-adapter-default-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip(
            "adapter-default pairing profile is missing; run the fresh pairing test first "
            "with the same --swbt-hardware-artifact-dir"
        )
    original_profile = profile_path.read_bytes()
    payload = json.loads(original_profile)
    if payload.get("identity") != {"kind": "adapter-default"}:
        pytest.fail("existing pairing profile is not an adapter-default profile")
    namespaces = payload.get("key_store", {}).get("namespaces", {})
    if not isinstance(namespaces, dict) or len(namespaces) != 1:
        pytest.fail("adapter-default pairing profile must contain one paired namespace")
    current_address = next(iter(namespaces))
    if not isinstance(current_address, str):
        pytest.fail("adapter-default pairing namespace must be a Bluetooth address string")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind="pro_controller")
    assert profile_path.read_bytes() == original_profile
    assert not _contains_event(events, "adapter_identity_prepared")
    assert _contains_event(events, "bumble_device_initialized")
    assert _contains_event(
        events,
        "local_bluetooth_address_configured",
        address=current_address.replace(":", "").lower(),
    )
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
def test_switch_direct_adapter_default_profile_stops_automatic_reports_after_ready(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect Direct Pro and stop requested report mode after protocol readiness."""
    profile_path = swbt_hardware_artifact_dir / _ADAPTER_DEFAULT_PROFILE_FILENAME
    trace_path = (
        swbt_hardware_artifact_dir / "pairing-profile-direct-adapter-default-reconnect.jsonl"
    )
    if not profile_path.exists():
        pytest.skip(
            "adapter-default pairing profile is missing; run the fresh pairing test first "
            "with the same --swbt-hardware-artifact-dir"
        )
    original_profile = profile_path.read_bytes()
    payload = json.loads(original_profile)
    if payload.get("identity") != {"kind": "adapter-default"}:
        pytest.fail("existing pairing profile is not an adapter-default profile")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = DirectProController(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind="pro_controller")
    _assert_direct_stops_automatic_reports_after_ready(events)
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
@pytest.mark.parametrize(("side", "controller_cls", "controller_kind"), _JOYCON_CASES)
def test_switch_joycon_adapter_default_profile_fresh_pairing_and_close(
    side: JoyConSide,
    controller_cls: type[JoyConL] | type[JoyConR],
    controller_kind: Literal["joycon_l", "joycon_r"],
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Pair one Joy-Con profile with the adapter's current public address."""
    profile_path = (
        swbt_hardware_artifact_dir / f"pairing-profile-adapter-default-joycon-{side}.json"
    )
    trace_path = (
        swbt_hardware_artifact_dir
        / f"pairing-profile-adapter-default-joycon-{side}-fresh-pairing.jsonl"
    )
    if profile_path.exists():
        pytest.fail("fresh Joy-Con profile already exists; use a new artifact directory")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await controller_cls.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind=f"joycon_{side}")
    namespaces = payload["key_store"]["namespaces"]
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == controller_kind
    assert payload["identity"] == {"kind": "adapter-default"}
    assert len(namespaces) == 1
    assert namespaces[next(iter(namespaces))]
    assert not _contains_event(events, "adapter_identity_prepared")
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
@pytest.mark.parametrize(("side", "controller_cls", "controller_kind"), _JOYCON_CASES)
def test_switch_joycon_adapter_default_profile_reuses_address_after_normal_close(
    side: JoyConSide,
    controller_cls: type[JoyConL] | type[JoyConR],
    controller_kind: Literal["joycon_l", "joycon_r"],
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect one adapter-default Joy-Con profile without pairing fallback."""
    profile_path = (
        swbt_hardware_artifact_dir / f"pairing-profile-adapter-default-joycon-{side}.json"
    )
    trace_path = (
        swbt_hardware_artifact_dir
        / f"pairing-profile-adapter-default-joycon-{side}-reconnect.jsonl"
    )
    if not profile_path.exists():
        pytest.skip("adapter-default Joy-Con profile is missing; run the matching fresh test first")
    original_profile = profile_path.read_bytes()
    payload = json.loads(original_profile)
    if payload.get("identity") != {"kind": "adapter-default"}:
        pytest.fail("existing Joy-Con profile is not an adapter-default profile")
    if payload.get("controller_kind") != controller_kind:
        pytest.fail("existing pairing profile does not match the requested Joy-Con side")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad: JoyConController = controller_cls(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind=f"joycon_{side}")
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
@pytest.mark.parametrize(("side", "controller_cls", "controller_kind"), _JOYCON_CASES)
def test_switch_joycon_pairing_profile_fresh_pairing_and_close(
    side: JoyConSide,
    controller_cls: type[JoyConL] | type[JoyConR],
    controller_kind: Literal["joycon_l", "joycon_r"],
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Create one side-specific Joy-Con profile, pair, and close cleanly."""
    profile_path = swbt_hardware_artifact_dir / f"pairing-profile-joycon-{side}.json"
    trace_path = swbt_hardware_artifact_dir / f"pairing-profile-joycon-{side}-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh pairing profile already exists; use a new artifact directory")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await controller_cls.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                local_address=swbt_local_address,
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind=f"joycon_{side}")
    target = swbt_local_address.upper()
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == controller_kind
    assert payload["identity"] == {
        "kind": "exp-local-address",
        "address": target,
    }
    assert payload["key_store"]["namespaces"][target]
    preparation = _first_event(events, "adapter_identity_prepared")
    assert preparation["status"] in {"rewritten", "already_active"}
    assert preparation["target_address"] == target
    assert _contains_event(events, "bumble_device_initialized")
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
@pytest.mark.parametrize(("side", "controller_cls", "controller_kind"), _JOYCON_CASES)
def test_switch_joycon_pairing_profile_reuses_target_after_normal_close(
    side: JoyConSide,
    controller_cls: type[JoyConL] | type[JoyConR],
    controller_kind: Literal["joycon_l", "joycon_r"],
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reuse one side-specific Joy-Con profile without pairing fallback."""
    profile_path = swbt_hardware_artifact_dir / f"pairing-profile-joycon-{side}.json"
    trace_path = swbt_hardware_artifact_dir / f"pairing-profile-joycon-{side}-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip("Joy-Con pairing profile is missing; run the matching fresh pairing test first")
    original_profile = profile_path.read_bytes()
    target = swbt_local_address.upper()
    payload = json.loads(original_profile)
    if payload.get("identity", {}).get("address") != target:
        pytest.fail("existing pairing profile does not match --swbt-local-address")
    if payload.get("controller_kind") != controller_kind:
        pytest.fail("existing pairing profile does not match the requested Joy-Con side")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad: JoyConController = controller_cls(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(events, profile_kind=f"joycon_{side}")
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "adapter_identity_prepared",
        status="already_active",
        target_address=target,
    )
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
@pytest.mark.parametrize(
    ("name", "controller_cls", "controller_kind", "button"),
    _DIRECT_CASES,
)
def test_switch_direct_pairing_profile_fresh_pairing_holds_input_before_close(
    name: str,
    controller_cls: type[DirectProController] | type[DirectJoyConL] | type[DirectJoyConR],
    controller_kind: Literal["pro", "joycon_l", "joycon_r"],
    button: Button,
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Pair one Direct controller and hold sent input before neutral close.

    A pytest pass proves enqueue, pre-close ordering, profile state, and cleanup.
    Human-visible Switch input reflection during the observation window must
    still be recorded in spec/hardware-test-log.md.
    """
    profile_path = swbt_hardware_artifact_dir / f"pairing-profile-direct-{name}.json"
    trace_path = swbt_hardware_artifact_dir / f"pairing-profile-direct-{name}-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh Direct pairing profile already exists; use a new artifact directory")
    sent_state = InputState.neutral().with_buttons([button])

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_direct_input_observation_start(trace, name=name, button=button)
            pad: DirectController = await controller_cls.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                local_address=swbt_local_address,
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
                await pad.send(sent_state)
                assert pad.snapshot() == sent_state
                await _hold_direct_input_before_close(
                    pad,
                    trace,
                    name=name,
                    button=button,
                )
            finally:
                _record_probe_event(
                    trace,
                    "manual_direct_input_checkpoint",
                    operation="close_start",
                )
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_direct_input_cleanup",
                    connection_state=pad.status().connection_state,
                )

    asyncio.run(run())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(
        events,
        profile_kind=_runtime_profile_kind(controller_kind),
    )
    _assert_direct_stops_automatic_reports_after_ready(events)
    target = swbt_local_address.upper()
    assert payload["controller_kind"] == controller_kind
    assert payload["identity"]["address"] == target
    assert payload["key_store"]["namespaces"][target]
    assert _contains_event(events, "adapter_identity_prepared")
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)
    _assert_direct_input_observation_order(events, button=button)


@pytest.mark.hardware
@pytest.mark.parametrize(
    ("name", "controller_cls", "controller_kind", "button"),
    _DIRECT_CASES,
)
def test_switch_direct_pairing_profile_reuses_target_after_normal_close(
    name: str,
    controller_cls: type[DirectProController] | type[DirectJoyConL] | type[DirectJoyConR],
    controller_kind: Literal["pro", "joycon_l", "joycon_r"],
    button: Button,
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect one Direct controller without pairing fallback and send input."""
    profile_path = swbt_hardware_artifact_dir / f"pairing-profile-direct-{name}.json"
    trace_path = swbt_hardware_artifact_dir / f"pairing-profile-direct-{name}-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip("Direct pairing profile is missing; run the matching fresh pairing test first")
    original_profile = profile_path.read_bytes()
    target = swbt_local_address.upper()
    payload = json.loads(original_profile)
    if payload.get("identity", {}).get("address") != target:
        pytest.fail("existing Direct pairing profile does not match --swbt-local-address")
    if payload.get("controller_kind") != controller_kind:
        pytest.fail("existing Direct pairing profile does not match the requested controller")
    sent_state = InputState.neutral().with_buttons([button])

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad: DirectController = controller_cls(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await pad.send(sent_state)
                assert pad.snapshot() == sent_state
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    _assert_protocol_ready_handshake(
        events,
        profile_kind=_runtime_profile_kind(controller_kind),
    )
    _assert_direct_stops_automatic_reports_after_ready(events)
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "adapter_identity_prepared",
        status="already_active",
        target_address=target,
    )
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)


def _record_direct_input_observation_start(
    trace: TextIO,
    *,
    name: str,
    button: Button,
) -> None:
    _record_probe_event(
        trace,
        "manual_direct_input_checkpoint",
        button=button.name,
        controller=name,
        expected_switch_screen="controller_search_or_change_grip_order",
        observation_seconds=_DIRECT_INPUT_OBSERVATION_SECONDS,
        operation="operator_prepare_input_observation",
    )
    sys.stderr.write(
        "SWBT hardware: Direct input reflection observation; "
        "expected_switch_screen=controller_search_or_change_grip_order; "
        f"controller={name}; button={button.name}; "
        f"holding {_DIRECT_INPUT_OBSERVATION_SECONDS:.0f}s before close\n"
    )
    sys.stderr.flush()


async def _hold_direct_input_before_close(
    pad: DirectController,
    trace: TextIO,
    *,
    name: str,
    button: Button,
) -> None:
    _record_probe_event(
        trace,
        "manual_direct_input_checkpoint",
        button=button.name,
        controller=name,
        operation="direct_input_enqueued",
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
    )
    await asyncio.sleep(_DIRECT_INPUT_OBSERVATION_SECONDS)
    _record_probe_event(
        trace,
        "manual_direct_input_checkpoint",
        button=button.name,
        controller=name,
        observation_seconds=_DIRECT_INPUT_OBSERVATION_SECONDS,
        operation="pre_close_observation_window_complete",
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
    )


def _assert_direct_input_observation_order(
    events: list[dict[str, Any]],
    *,
    button: Button,
) -> None:
    operator_prepare = _first_event_index(
        events,
        "manual_direct_input_checkpoint",
        button=button.name,
        expected_switch_screen="controller_search_or_change_grip_order",
        observation_seconds=_DIRECT_INPUT_OBSERVATION_SECONDS,
        operation="operator_prepare_input_observation",
    )
    direct_report = _first_event_index(
        events,
        "report_tx",
        reason="direct",
        report_id="0x30",
    )
    enqueued = _first_event_index(
        events,
        "manual_direct_input_checkpoint",
        button=button.name,
        operation="direct_input_enqueued",
    )
    observation_complete = _first_event_index(
        events,
        "manual_direct_input_checkpoint",
        button=button.name,
        observation_seconds=_DIRECT_INPUT_OBSERVATION_SECONDS,
        operation="pre_close_observation_window_complete",
    )
    close_start = _first_event_index(
        events,
        "manual_direct_input_checkpoint",
        operation="close_start",
    )
    transport_close = _first_event_index(events, "transport_close_complete")
    cleanup = _first_event_index(
        events,
        "manual_direct_input_cleanup",
        connection_state="closed",
    )
    assert (
        operator_prepare
        < direct_report
        < enqueued
        < observation_complete
        < close_start
        < transport_close
        < cleanup
    )


def _record_probe_event(trace: TextIO, event: str, **fields: object) -> None:
    payload: dict[str, object] = {"event": event}
    payload.update(fields)
    trace.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    trace.write("\n")
    trace.flush()


async def _wait_for_event(
    trace_path: Path,
    event_name: str,
    *,
    timeout_seconds: float,
) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_seconds
    while loop.time() < deadline:
        try:
            events = _read_jsonl(trace_path)
        except FileNotFoundError:
            pass
        else:
            if _contains_event(events, event_name):
                return
        await asyncio.sleep(0.1)
    msg = f"timed out waiting for {event_name}"
    raise AssertionError(msg)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _first_event(events: list[dict[str, Any]], event_name: str) -> dict[str, Any]:
    for event in events:
        if event.get("event") == event_name:
            return event
    msg = f"missing event: {event_name}"
    raise AssertionError(msg)


def _first_event_index(
    events: list[dict[str, Any]],
    event_name: str,
    **expected: object,
) -> int:
    for index, event in enumerate(events):
        if event.get("event") != event_name:
            continue
        if all(event.get(key) == value for key, value in expected.items()):
            return index
    msg = f"missing event: {event_name} {expected}"
    raise AssertionError(msg)


def _contains_event(
    events: list[dict[str, Any]],
    event_name: str,
    **expected: object,
) -> bool:
    return any(
        event.get("event") == event_name
        and all(event.get(key) == value for key, value in expected.items())
        for event in events
    )


def _assert_protocol_ready_handshake(
    events: list[dict[str, Any]],
    *,
    profile_kind: str,
) -> None:
    bootstrap_report_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event") == "report_tx" and event.get("reason") == "handshake_bootstrap"
    ]
    bootstrap_stop_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event") == "handshake_bootstrap_stopped"
    ]
    received = [
        (event.get("packet_id"), event.get("subcommand_id"))
        for event in events
        if event.get("event") == "subcommand_rx"
    ]
    replied = [
        (event.get("packet_id"), event.get("subcommand_id"))
        for event in events
        if event.get("event") == "subcommand_reply_tx"
    ]
    ready_indexes = [
        index for index, event in enumerate(events) if event.get("event") == "protocol_ready"
    ]

    assert bootstrap_report_indexes
    assert len(bootstrap_stop_indexes) == 1
    bootstrap_stop_index = bootstrap_stop_indexes[0]
    bootstrap_stop = events[bootstrap_stop_index]
    assert bootstrap_stop.get("reason") == "subcommand_received"
    assert bootstrap_report_indexes[-1] < bootstrap_stop_index
    assert received
    assert bootstrap_stop.get("subcommand_id") == received[0][1]
    assert replied == received
    assert len(ready_indexes) == 1

    ready_index = ready_indexes[0]
    ready = events[ready_index]
    assert ready.get("profile_kind") == profile_kind
    assert ready.get("report_mode") == "0x30"
    assert ready.get("player_lights") not in (None, "0x00")
    assert {"0x03", "0x30"} <= set(ready.get("observed_subcommands", []))
    assert ready_index > 0
    assert events[ready_index - 1].get("event") == "subcommand_reply_tx"


def _runtime_profile_kind(
    controller_kind: Literal["pro", "joycon_l", "joycon_r"],
) -> str:
    return {
        "pro": "pro_controller",
        "joycon_l": "joycon_left",
        "joycon_r": "joycon_right",
    }[controller_kind]


def _assert_direct_stops_automatic_reports_after_ready(
    events: list[dict[str, Any]],
) -> None:
    ready_index = _first_event_index(events, "protocol_ready")
    automatic_report_indexes = [
        index
        for index, event in enumerate(events)
        if event.get("event") == "report_tx" and event.get("reason") == "periodic"
    ]

    assert automatic_report_indexes
    assert automatic_report_indexes[-1] < ready_index
