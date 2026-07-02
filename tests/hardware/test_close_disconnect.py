import asyncio
import json
from pathlib import Path
from typing import Any, TextIO

import pytest

from swbt import DiagnosticsConfig, SwitchGamepad


@pytest.mark.hardware
def test_switch_close_requests_disconnect_after_neutral(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Characterize connected close ordering on a real Switch link.

    A pytest pass proves trace ordering and cleanup. It does not prove that every
    Switch firmware treats Bumble channel disconnect helpers as a graceful close.
    """
    trace_path = swbt_hardware_artifact_dir / "close-disconnect.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            await pad.open()
            try:
                await pad.wait_connected(timeout=60.0)
                _record_probe_event(trace, "manual_close_checkpoint", operation="close_start")
            finally:
                await pad.close(neutral=True)
                _record_probe_event(trace, "manual_close_checkpoint", operation="close_complete")

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "manual_close_checkpoint", operation="close_start")
    assert _contains_event(events, "disconnect_request")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "manual_close_checkpoint", operation="close_complete")

    close_start = _first_event_index(events, "manual_close_checkpoint", operation="close_start")
    disconnect_request = _first_event_index(events, "disconnect_request")
    transport_close = _first_event_index(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )
    close_complete = _first_event_index(
        events,
        "manual_close_checkpoint",
        operation="close_complete",
    )

    trailing_neutral = _first_event_index_after(
        events,
        close_start,
        "report_tx",
        report_id="0x30",
        reason="input",
    )
    assert close_start < trailing_neutral < disconnect_request < transport_close < close_complete

    request_event = events[disconnect_request]
    assert request_event.get("status") in {"requested", "unavailable", "failed"}
    if request_event.get("status") == "requested":
        terminal = _first_event_index_after(
            events,
            disconnect_request,
            "disconnect_request_terminal",
        )
        assert terminal < transport_close
        assert events[terminal].get("status") in {"closed", "timeout"}


def _record_probe_event(trace: TextIO, event: str, **fields: object) -> None:
    payload: dict[str, object] = {"event": event}
    payload.update(fields)
    trace.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    trace.write("\n")
    trace.flush()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _first_event_index(
    events: list[dict[str, Any]],
    event_name: str,
    **expected_fields: object,
) -> int:
    return _first_event_index_after(events, -1, event_name, **expected_fields)


def _first_event_index_after(
    events: list[dict[str, Any]],
    start_index: int,
    event_name: str,
    **expected_fields: object,
) -> int:
    for index, event in enumerate(events[start_index + 1 :], start=start_index + 1):
        if event.get("event") != event_name:
            continue
        if all(event.get(key) == value for key, value in expected_fields.items()):
            return index
    msg = f"missing event after index {start_index}: {event_name} {expected_fields}"
    raise AssertionError(msg)
