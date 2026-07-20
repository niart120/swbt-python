"""Manual hardware gate for the Pro Controller exp local profile lifecycle."""

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from swbt import DiagnosticsConfig, ProController

_PROFILE_FILENAME = "exp-local-pro-profile.json"


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
    assert _contains_event(
        events,
        "bumble_device_initialized",
        local_bluetooth_address=target.replace(":", "").lower(),
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
    assert _contains_event(
        events,
        "bumble_device_initialized",
        local_bluetooth_address=target.replace(":", "").lower(),
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
