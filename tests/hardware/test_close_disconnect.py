import asyncio
import json
from pathlib import Path
from typing import Any, TextIO

import pytest

from swbt import Button, DiagnosticsConfig, InputState, SwitchGamepad


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
            try:
                await pad.pair(timeout=60.0)
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


@pytest.mark.hardware
def test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Exercise registration-screen exit then close for manual UI observation.

    A pytest pass proves the on-wire sequence and cleanup only. The human-visible
    Switch UI state after Button A and after disconnect must be recorded in
    spec/hardware-test-log.md.
    """
    trace_path = swbt_hardware_artifact_dir / "post-handshake-a-close.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                _record_probe_event(
                    trace,
                    "manual_close_checkpoint",
                    operation="operator_expected_registration_screen",
                )
                await pad.pair(timeout=60.0)
                await _wait_for_full_handshake(trace_path, timeout_seconds=20.0)
                _record_probe_event(
                    trace,
                    "manual_close_checkpoint",
                    operation="full_handshake_complete",
                    last_subcommand_id=_format_optional_hex(pad.status().last_subcommand_id),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                )

                _record_probe_event(
                    trace,
                    "manual_close_checkpoint",
                    operation="tap_a_exit_pairing_screen_start",
                )
                await pad.tap(Button.A, duration=0.35)
                await asyncio.sleep(1.0)
                _record_probe_event(
                    trace,
                    "manual_close_checkpoint",
                    operation="tap_a_exit_pairing_screen_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )

                await pad.neutral()
                assert pad.snapshot() == InputState.neutral()
                neutral_start_count = pad.status().report_counters.get(0x30, 0)
                await _wait_for_report_counter(
                    pad,
                    report_id=0x30,
                    minimum_count=neutral_start_count + 8,
                    timeout_seconds=2.0,
                )
                _record_probe_event(
                    trace,
                    "manual_close_checkpoint",
                    operation="neutral_after_a_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )

                _record_probe_event(trace, "manual_close_checkpoint", operation="close_start")
            finally:
                await pad.close(neutral=True)
                _record_probe_event(trace, "manual_close_checkpoint", operation="close_complete")
                await asyncio.sleep(2.0)
                _record_probe_event(
                    trace,
                    "manual_close_checkpoint",
                    operation="post_close_ui_observation_window_complete",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_full_handshake(events)
    assert _contains_event(events, "manual_close_checkpoint", operation="full_handshake_complete")
    assert _contains_event(
        events,
        "manual_close_checkpoint",
        operation="tap_a_exit_pairing_screen_complete",
    )
    assert _contains_event(events, "manual_close_checkpoint", operation="neutral_after_a_complete")
    assert _contains_event(events, "manual_close_checkpoint", operation="close_start")
    assert _contains_event(events, "disconnect_request")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "manual_close_checkpoint", operation="close_complete")

    close_start = _first_event_index(events, "manual_close_checkpoint", operation="close_start")
    trailing_neutral = _first_event_index_after(
        events,
        close_start,
        "report_tx",
        report_id="0x30",
        reason="input",
    )
    disconnect_request = _first_event_index_after(events, trailing_neutral, "disconnect_request")
    transport_close = _first_event_index_after(
        events,
        disconnect_request,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )
    close_complete = _first_event_index_after(
        events,
        transport_close,
        "manual_close_checkpoint",
        operation="close_complete",
    )

    assert close_start < trailing_neutral < disconnect_request < transport_close < close_complete
    assert not _contains_event(events, "error")


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


async def _wait_for_full_handshake(trace_path: Path, *, timeout_seconds: float) -> None:
    async with asyncio.timeout(timeout_seconds):
        while True:
            if _contains_full_handshake(_read_jsonl(trace_path)):
                return
            await asyncio.sleep(0.05)


async def _wait_for_report_counter(
    pad: SwitchGamepad,
    *,
    report_id: int,
    minimum_count: int,
    timeout_seconds: float,
) -> None:
    interval_seconds = 0.01
    attempts = max(1, int(timeout_seconds / interval_seconds))

    for _ in range(attempts):
        if pad.status().report_counters.get(report_id, 0) >= minimum_count:
            return
        await asyncio.sleep(interval_seconds)

    current_count = pad.status().report_counters.get(report_id, 0)
    msg = f"report 0x{report_id:02x} count stayed at {current_count}, expected {minimum_count}"
    raise TimeoutError(msg)


def _contains_full_handshake(events: list[dict[str, Any]]) -> bool:
    subcommands = [
        event.get("subcommand_id") for event in events if event.get("event") == "subcommand_rx"
    ]
    required = {"0x02", "0x08", "0x10", "0x03", "0x04", "0x40", "0x48", "0x21", "0x30"}
    return required.issubset(set(subcommands)) and _all_observed_subcommands_have_replies(events)


def _all_observed_subcommands_have_replies(events: list[dict[str, Any]]) -> bool:
    reply_keys = {
        (event.get("packet_id"), event.get("subcommand_id"))
        for event in events
        if event.get("event") == "subcommand_reply_tx"
    }
    return all(
        (event.get("packet_id"), event.get("subcommand_id")) in reply_keys
        for event in events
        if event.get("event") == "subcommand_rx"
    )


def _format_optional_hex(value: int | None) -> str | None:
    if value is None:
        return None
    return f"0x{value:02x}"
