import asyncio
import json
from pathlib import Path
from typing import Any, TextIO

import pytest

from swbt import Button, DiagnosticsConfig, InputState, SwitchGamepad


@pytest.mark.hardware
def test_switch_input_operation_sequence_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send input reports and leave trace checkpoints for manual UI observation.

    A pytest pass from this test does not prove that the Switch UI reflected the
    input. The human-visible UI result must be recorded in docs/hardware-test-log.md.
    """
    trace_path = swbt_hardware_artifact_dir / "input-operation-sequence.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.pair(timeout=60.0)
                await _wait_for_event(trace_path, "subcommand_reply_tx", timeout_seconds=15.0)

                _record_probe_event(trace, "manual_input_checkpoint", operation="tap_a_start")
                await pad.tap(Button.A, duration=0.25)
                await asyncio.sleep(0.5)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="tap_a_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )

                await pad.press(Button.L, Button.R)
                hold_start_count = pad.status().report_counters.get(0x30, 0)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="hold_lr_start",
                    report_0x30_count=hold_start_count,
                )
                await _wait_for_report_counter(
                    pad,
                    report_id=0x30,
                    minimum_count=hold_start_count + 30,
                    timeout_seconds=2.0,
                )
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="hold_lr_reports_sent",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )

                await pad.release(Button.L, Button.R)
                await pad.neutral()
                assert pad.snapshot() == InputState.neutral()
                neutral_start_count = pad.status().report_counters.get(0x30, 0)
                await _wait_for_report_counter(
                    pad,
                    report_id=0x30,
                    minimum_count=neutral_start_count + 3,
                    timeout_seconds=2.0,
                )
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="neutral_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected")
    assert _contains_event(events, "subcommand_reply_tx")
    assert _contains_event(events, "manual_input_checkpoint", operation="tap_a_complete")
    assert _contains_event(events, "manual_input_checkpoint", operation="hold_lr_reports_sent")
    assert _contains_event(events, "manual_input_checkpoint", operation="neutral_complete")
    assert _count_events(events, "report_tx", report_id="0x30") >= 6
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_input_after_full_handshake_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send Button A only after the observed Switch handshake has completed.

    A pytest pass from this test proves the handshake sequence and report
    transmission checkpoints only. The human-visible UI result must be recorded
    in docs/hardware-test-log.md.
    """
    trace_path = swbt_hardware_artifact_dir / "post-handshake-input.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.pair(timeout=60.0)
                await _wait_for_full_handshake(trace_path, timeout_seconds=20.0)

                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="handshake_complete",
                    last_subcommand_id=_format_optional_hex(pad.status().last_subcommand_id),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                )
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="post_handshake_tap_a_start",
                )
                await pad.tap(Button.A, duration=0.35)
                await asyncio.sleep(0.75)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="post_handshake_tap_a_complete",
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
                    "manual_input_checkpoint",
                    operation="post_handshake_neutral_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected")
    assert _contains_full_handshake(events)
    assert _contains_event(events, "manual_input_checkpoint", operation="handshake_complete")
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="post_handshake_tap_a_complete",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="post_handshake_neutral_complete",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "error")


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
    for event in events:
        if event.get("event") != event_name:
            continue
        if all(event.get(key) == value for key, value in expected_fields.items()):
            return True
    return False


def _count_events(
    events: list[dict[str, Any]],
    event_name: str,
    **expected_fields: object,
) -> int:
    return sum(
        1
        for event in events
        if event.get("event") == event_name
        and all(event.get(key) == value for key, value in expected_fields.items())
    )


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
