import asyncio
import json
from pathlib import Path
from typing import Any, TextIO

import pytest

from swbt import DiagnosticsConfig, SwitchGamepad


@pytest.mark.hardware
def test_switch_active_reconnect_with_key_store_records_result(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    key_store_path = swbt_hardware_artifact_dir / "active-reconnect-key-store.json"
    pair_trace_path = swbt_hardware_artifact_dir / "active-reconnect-initial-pair.jsonl"
    reconnect_trace_path = swbt_hardware_artifact_dir / "active-reconnect-attempt.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        await _pair_with_key_store(
            adapter=swbt_bumble_adapter,
            key_store_path=key_store_path,
            trace_path=pair_trace_path,
        )
        with reconnect_trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.reconnect(timeout=60.0)
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

    pair_events = _read_jsonl(pair_trace_path)
    reconnect_events = _read_jsonl(reconnect_trace_path)

    assert key_store_path.exists()
    assert _contains_event(pair_events, "key_store_update", status="succeeded")
    assert _contains_event(reconnect_events, "bonded_peers_discovered", selection="selected")
    assert _contains_event(reconnect_events, "active_reconnect_attempt", route="active_reconnect")
    result_event = _first_event(reconnect_events, "active_reconnect_result")
    assert result_event.get("route") == "active_reconnect"
    assert result_event.get("status") in {"connected", "timeout", "failed"}
    if result_event.get("status") != "connected":
        assert result_event.get("failure_reason") in {"connection_timeout", "transport_error"}
    assert not _contains_event(reconnect_events, "advertising_start")
    assert _contains_event(
        reconnect_events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
def test_switch_incoming_bond_reuse_trace_stays_separate_from_active_reconnect(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    key_store_path = swbt_hardware_artifact_dir / "incoming-reconnect-key-store.json"
    pair_trace_path = swbt_hardware_artifact_dir / "incoming-reconnect-initial-pair.jsonl"
    incoming_trace_path = swbt_hardware_artifact_dir / "incoming-reconnect-attempt.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        await _pair_with_key_store(
            adapter=swbt_bumble_adapter,
            key_store_path=key_store_path,
            trace_path=pair_trace_path,
        )
        with incoming_trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.pair(timeout=60.0)
                await asyncio.sleep(1.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    pair_events = _read_jsonl(pair_trace_path)
    incoming_events = _read_jsonl(incoming_trace_path)
    incoming_event_names = {event.get("event") for event in incoming_events}

    assert key_store_path.exists()
    assert _contains_event(pair_events, "key_store_update", status="succeeded")
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
        pad = SwitchGamepad(
            adapter=adapter,
            key_store_path=str(key_store_path),
            diagnostics=DiagnosticsConfig(trace_writer=trace),
        )
        try:
            result = await pad.connect(timeout=60.0, allow_pairing=True)
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
