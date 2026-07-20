"""Manual hardware gate for the Pro Controller exp local profile lifecycle."""

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

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

_PROFILE_FILENAME = "exp-local-pro-profile.json"
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
        Literal["direct_pro", "direct_joycon_l", "direct_joycon_r"],
        Button,
    ],
    ...,
] = (
    ("pro", DirectProController, "direct_pro", Button.A),
    ("joycon-l", DirectJoyConL, "direct_joycon_l", Button.L),
    ("joycon-r", DirectJoyConR, "direct_joycon_r", Button.R),
)


@pytest.mark.hardware
def test_switch_exp_local_profile_fresh_pairing_and_close(
    swbt_bumble_adapter: str,
    swbt_exp_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Create a fresh profile, pair it, and close without restoring the address."""
    profile_path = swbt_hardware_artifact_dir / _PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "exp-local-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh exp profile already exists; use a new --swbt-hardware-artifact-dir")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await ProController.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                exp_local_address=swbt_exp_local_address,
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
    target = swbt_exp_local_address.upper()
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == "pro"
    assert payload["identity"] == {
        "kind": "exp-local-address",
        "address": target,
    }
    assert payload["key_store"]["namespaces"][target]
    preparation = _first_event(events, "exp_local_identity_prepared")
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
def test_switch_exp_local_profile_reuses_target_after_normal_close(
    swbt_bumble_adapter: str,
    swbt_exp_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reuse the fresh profile and prove that close left the target active."""
    profile_path = swbt_hardware_artifact_dir / _PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "exp-local-active-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip(
            "exp profile is missing; run the fresh pairing test first with the same "
            "--swbt-hardware-artifact-dir"
        )
    original_profile = profile_path.read_bytes()
    target = swbt_exp_local_address.upper()
    payload = json.loads(original_profile)
    if payload.get("identity", {}).get("address") != target:
        pytest.fail("existing exp profile does not match --swbt-exp-local-address")

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
        "exp_local_identity_prepared",
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
@pytest.mark.parametrize(("side", "controller_cls", "controller_kind"), _JOYCON_CASES)
def test_switch_joycon_exp_local_profile_fresh_pairing_and_close(
    side: JoyConSide,
    controller_cls: type[JoyConL] | type[JoyConR],
    controller_kind: Literal["joycon_l", "joycon_r"],
    swbt_bumble_adapter: str,
    swbt_exp_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Create one side-specific Joy-Con profile, pair, and close cleanly."""
    profile_path = swbt_hardware_artifact_dir / f"exp-local-joycon-{side}-profile.json"
    trace_path = swbt_hardware_artifact_dir / f"exp-local-joycon-{side}-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh exp profile already exists; use a new artifact directory")

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await controller_cls.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                exp_local_address=swbt_exp_local_address,
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
    target = swbt_exp_local_address.upper()
    assert payload["format"] == "swbt.profile"
    assert payload["schema_version"] == 1
    assert payload["controller_kind"] == controller_kind
    assert payload["identity"] == {
        "kind": "exp-local-address",
        "address": target,
    }
    assert payload["key_store"]["namespaces"][target]
    preparation = _first_event(events, "exp_local_identity_prepared")
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
def test_switch_joycon_exp_local_profile_reuses_target_after_normal_close(
    side: JoyConSide,
    controller_cls: type[JoyConL] | type[JoyConR],
    controller_kind: Literal["joycon_l", "joycon_r"],
    swbt_bumble_adapter: str,
    swbt_exp_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reuse one side-specific Joy-Con profile without pairing fallback."""
    profile_path = swbt_hardware_artifact_dir / f"exp-local-joycon-{side}-profile.json"
    trace_path = swbt_hardware_artifact_dir / f"exp-local-joycon-{side}-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip("Joy-Con exp profile is missing; run the matching fresh pairing test first")
    original_profile = profile_path.read_bytes()
    target = swbt_exp_local_address.upper()
    payload = json.loads(original_profile)
    if payload.get("identity", {}).get("address") != target:
        pytest.fail("existing exp profile does not match --swbt-exp-local-address")
    if payload.get("controller_kind") != controller_kind:
        pytest.fail("existing exp profile does not match the requested Joy-Con side")

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
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "exp_local_identity_prepared",
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
def test_switch_direct_exp_local_profile_fresh_pairing_send_and_close(
    name: str,
    controller_cls: type[DirectProController] | type[DirectJoyConL] | type[DirectJoyConR],
    controller_kind: Literal["direct_pro", "direct_joycon_l", "direct_joycon_r"],
    button: Button,
    swbt_bumble_adapter: str,
    swbt_exp_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Pair one Direct controller, send input, and close it neutrally."""
    profile_path = swbt_hardware_artifact_dir / f"exp-local-direct-{name}-profile.json"
    trace_path = swbt_hardware_artifact_dir / f"exp-local-direct-{name}-fresh-pairing.jsonl"
    if profile_path.exists():
        pytest.fail("fresh Direct exp profile already exists; use a new artifact directory")
    sent_state = InputState.neutral().with_buttons([button])

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad: DirectController = await controller_cls.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                exp_local_address=swbt_exp_local_address,
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
                await pad.send(sent_state)
                assert pad.snapshot() == sent_state
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    events = _read_jsonl(trace_path)
    target = swbt_exp_local_address.upper()
    assert payload["controller_kind"] == controller_kind
    assert payload["identity"]["address"] == target
    assert payload["key_store"]["namespaces"][target]
    assert _contains_event(events, "exp_local_identity_prepared")
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)


@pytest.mark.hardware
@pytest.mark.parametrize(
    ("name", "controller_cls", "controller_kind", "button"),
    _DIRECT_CASES,
)
def test_switch_direct_exp_local_profile_reuses_target_after_normal_close(
    name: str,
    controller_cls: type[DirectProController] | type[DirectJoyConL] | type[DirectJoyConR],
    controller_kind: Literal["direct_pro", "direct_joycon_l", "direct_joycon_r"],
    button: Button,
    swbt_bumble_adapter: str,
    swbt_exp_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect one Direct controller without pairing fallback and send input."""
    profile_path = swbt_hardware_artifact_dir / f"exp-local-direct-{name}-profile.json"
    trace_path = swbt_hardware_artifact_dir / f"exp-local-direct-{name}-reconnect.jsonl"
    if not profile_path.exists():
        pytest.skip("Direct exp profile is missing; run the matching fresh pairing test first")
    original_profile = profile_path.read_bytes()
    target = swbt_exp_local_address.upper()
    payload = json.loads(original_profile)
    if payload.get("identity", {}).get("address") != target:
        pytest.fail("existing Direct exp profile does not match --swbt-exp-local-address")
    if payload.get("controller_kind") != controller_kind:
        pytest.fail("existing Direct exp profile does not match the requested controller")
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
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "exp_local_identity_prepared",
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
