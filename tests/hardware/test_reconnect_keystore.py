import asyncio
import json
import sys
from pathlib import Path
from typing import Any, TextIO

import pytest

from swbt import DiagnosticsConfig, SwitchGamepad

_INITIAL_PAIRING_OPERATOR_WAIT_SECONDS = 5.0
_ACTIVE_RECONNECT_OPERATOR_WAIT_SECONDS = 5.0
_INCOMING_OPERATOR_WAIT_SECONDS = 5.0


@pytest.mark.hardware
def test_switch_pairing_writes_reconnect_key_store(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Create the key store used by reconnect characterization.

    Run this while the Switch is on the controller search / change grip order
    screen. The active reconnect test must be run later from HOME or another
    normal screen with the same artifact directory.
    """
    key_store_path = _reconnect_key_store_path(swbt_hardware_artifact_dir)
    pair_trace_path = swbt_hardware_artifact_dir / "reconnect-initial-pair.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        await _pair_with_key_store(
            adapter=swbt_bumble_adapter,
            key_store_path=key_store_path,
            trace_path=pair_trace_path,
        )

    asyncio.run(run())

    pair_events = _read_jsonl(pair_trace_path)

    assert key_store_path.exists()
    assert _contains_event(
        pair_events,
        "manual_reconnect_checkpoint",
        operation="operator_prepare_initial_pairing",
        expected_switch_screen="controller_search_or_change_grip_order",
    )
    assert _contains_event(pair_events, "key_store_update", status="succeeded")
    assert _contains_event(pair_events, "transport_close_complete", adapter=swbt_bumble_adapter)


@pytest.mark.hardware
def test_switch_active_reconnect_with_existing_key_store_records_result(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Characterize active reconnect from an existing key store.

    Run this after `test_switch_pairing_writes_reconnect_key_store`, while the
    Switch is on HOME or another normal screen. A pytest pass proves active
    reconnect attempt/result trace and cleanup only. `timeout` or `failed` is a
    valid characterized result and must not be reported as active reconnect
    success.
    """
    key_store_path = _reconnect_key_store_path(swbt_hardware_artifact_dir)
    reconnect_trace_path = swbt_hardware_artifact_dir / "active-reconnect-attempt.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "reconnect key store is missing; run "
            "test_switch_pairing_writes_reconnect_key_store first with the same "
            "--swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with reconnect_trace_path.open("w", encoding="utf-8") as trace:
            await _wait_for_operator_condition(
                trace,
                operation="operator_prepare_active_reconnect",
                expected_switch_screen="home_or_normal_screen_not_change_grip_order",
                wait_seconds=_ACTIVE_RECONNECT_OPERATOR_WAIT_SECONDS,
            )
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                _record_probe_event(
                    trace,
                    "manual_reconnect_checkpoint",
                    operation="active_reconnect_result",
                    peer_address=result.peer_address,
                    route=result.route,
                    status=result.status,
                )
                if result.status == "connected":
                    await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    reconnect_events = _read_jsonl(reconnect_trace_path)

    assert key_store_path.exists()
    assert _contains_event(
        reconnect_events,
        "manual_reconnect_checkpoint",
        operation="operator_prepare_active_reconnect",
        expected_switch_screen="home_or_normal_screen_not_change_grip_order",
    )
    assert _contains_event(reconnect_events, "bonded_peers_discovered", selection="selected")
    assert _contains_event(reconnect_events, "active_reconnect_attempt", route="active_reconnect")
    result_event = _first_event(reconnect_events, "active_reconnect_result")
    assert result_event.get("route") == "active_reconnect"
    assert result_event.get("status") == "connected"
    assert _contains_event(
        reconnect_events,
        "l2cap_channel_open",
        channel="control",
        psm="0x0011",
    )
    assert _contains_event(
        reconnect_events,
        "l2cap_channel_open",
        channel="interrupt",
        psm="0x0013",
    )
    assert _contains_event(reconnect_events, "connected", adapter=swbt_bumble_adapter)
    assert not _contains_event(reconnect_events, "classic_pairing")
    assert not _contains_event(reconnect_events, "key_store_update")
    assert not _contains_event(reconnect_events, "advertising_start")
    assert _contains_event(
        reconnect_events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
def test_switch_incoming_connection_trace_stays_separate_from_active_reconnect(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Characterize incoming connection trace separately from active reconnect.

    A pytest pass proves that this route does not emit active reconnect events.
    It does not prove pairing-free incoming bond reuse; `classic_pairing` and
    `key_store_update` in the trace must be classified in the hardware log.
    """
    key_store_path = _reconnect_key_store_path(swbt_hardware_artifact_dir)
    incoming_trace_path = swbt_hardware_artifact_dir / "incoming-reconnect-attempt.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "reconnect key store is missing; run "
            "test_switch_pairing_writes_reconnect_key_store first with the same "
            "--swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with incoming_trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _wait_for_operator_condition(
                    trace,
                    operation="operator_prepare_incoming_connection",
                    expected_switch_screen="controller_search_or_change_grip_order",
                    wait_seconds=_INCOMING_OPERATOR_WAIT_SECONDS,
                )
                await pad.pair(timeout=60.0)
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    incoming_events = _read_jsonl(incoming_trace_path)
    incoming_event_names = {event.get("event") for event in incoming_events}

    assert key_store_path.exists()
    assert _contains_event(
        incoming_events,
        "manual_reconnect_checkpoint",
        operation="operator_prepare_incoming_connection",
        expected_switch_screen="controller_search_or_change_grip_order",
    )
    assert _contains_event(incoming_events, "incoming_connection", route="incoming")
    assert "active_reconnect_attempt" not in incoming_event_names
    assert "active_reconnect_result" not in incoming_event_names
    assert _contains_event(incoming_events, "transport_close_complete", adapter=swbt_bumble_adapter)


async def _pair_with_key_store(
    *,
    adapter: str,
    key_store_path: Path,
    trace_path: Path,
) -> None:
    with trace_path.open("w", encoding="utf-8") as trace:
        await _wait_for_operator_condition(
            trace,
            operation="operator_prepare_initial_pairing",
            expected_switch_screen="controller_search_or_change_grip_order",
            wait_seconds=_INITIAL_PAIRING_OPERATOR_WAIT_SECONDS,
        )
        pad = SwitchGamepad(
            adapter=adapter,
            key_store_path=str(key_store_path),
            diagnostics=DiagnosticsConfig(trace_writer=trace),
        )
        try:
            result = await pad.try_connect(
                timeout=60.0,
                allow_pairing=True,
            )
            _record_probe_event(
                trace,
                "manual_reconnect_checkpoint",
                operation="initial_connect_result",
                peer_address=result.peer_address,
                route=result.route,
                status=result.status,
            )
            await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
        finally:
            await pad.close(neutral=True)


async def _wait_for_event(
    trace_path: Path,
    event_name: str,
    *,
    timeout_seconds: float,
) -> None:
    async with asyncio.timeout(timeout_seconds):
        while True:
            if _contains_event(_read_jsonl(trace_path), event_name):
                return
            await asyncio.sleep(0.05)


def _delete_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


def _reconnect_key_store_path(artifact_dir: Path) -> Path:
    return artifact_dir / "reconnect-key-store.json"


async def _wait_for_operator_condition(
    trace: TextIO,
    *,
    operation: str,
    expected_switch_screen: str,
    wait_seconds: float,
) -> None:
    _record_probe_event(
        trace,
        "manual_reconnect_checkpoint",
        operation=operation,
        expected_switch_screen=expected_switch_screen,
        wait_seconds=wait_seconds,
    )
    sys.stderr.write(
        "SWBT hardware: "
        f"{operation}; expected_switch_screen={expected_switch_screen}; "
        f"waiting {wait_seconds:.0f}s\n"
    )
    sys.stderr.flush()
    await asyncio.sleep(wait_seconds)


def _record_probe_event(trace: TextIO, event: str, **fields: object) -> None:
    payload: dict[str, object] = {"event": event}
    payload.update(fields)
    trace.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    trace.write("\n")
    trace.flush()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _contains_event(
    events: list[dict[str, Any]],
    event_name: str,
    **expected_fields: object,
) -> bool:
    return any(
        event.get("event") == event_name
        and all(event.get(key) == value for key, value in expected_fields.items())
        for event in events
    )


def _first_event(events: list[dict[str, Any]], event_name: str) -> dict[str, Any]:
    for event in events:
        if event.get("event") == event_name:
            return event
    msg = f"missing event: {event_name}"
    raise AssertionError(msg)
