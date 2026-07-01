import asyncio
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest

from swbt import DiagnosticsConfig, SwitchGamepad


@pytest.mark.hardware
def test_switch_pairing_l2cap_records_diagnostics(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    trace_path = swbt_hardware_artifact_dir / "pairing-l2cap.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.open()
                await pad.wait_connected(timeout=60.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]

    assert _contains_event(events, "run_metadata", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "bumble_runtime", bumble_version=version("bumble"))
    assert _contains_event(events, "transport_open_start", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "bumble_device_initialized",
        adapter=swbt_bumble_adapter,
        device_name="Pro Controller",
        class_of_device="0x002508",
    )
    assert _contains_event(events, "advertising_start", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "host_connection", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "classic_pairing", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "l2cap_channel_open",
        adapter=swbt_bumble_adapter,
        channel="control",
    )
    assert _contains_event(
        events,
        "l2cap_channel_open",
        adapter=swbt_bumble_adapter,
        channel="interrupt",
    )
    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)


@pytest.mark.hardware
def test_switch_subcommand_sequence_gets_0x21_replies(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    trace_path = swbt_hardware_artifact_dir / "subcommand-sequence.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.open()
                await pad.wait_connected(timeout=60.0)
                await _wait_for_subcommand_reply_trace(
                    trace_path,
                    timeout_seconds=15.0,
                )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "output_report_rx", report_id="0x01")
    assert _contains_event(events, "subcommand_rx")
    assert _contains_event(events, "subcommand_reply_tx")
    assert _contains_event(events, "report_tx", report_id="0x21", reason="subcommand_reply")
    assert not _contains_event(events, "unsupported_subcommand")


@pytest.mark.hardware
def test_switch_subcommand_observation_window_replies_to_all_observed_commands(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    trace_path = swbt_hardware_artifact_dir / "subcommand-observation-window.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.open()
                await pad.wait_connected(timeout=60.0)
                await _wait_for_subcommand_observation_window(
                    trace_path,
                    min_observation_seconds=5.0,
                    timeout_seconds=20.0,
                )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "output_report_rx", report_id="0x01")
    assert _contains_event(events, "subcommand_rx")
    assert not _contains_event(events, "unsupported_subcommand")
    assert not _contains_event(events, "error")
    assert _all_observed_subcommands_have_replies(events)
    assert _count_events(events, "report_tx", report_id="0x21", reason="subcommand_reply") >= (
        _count_events(events, "subcommand_reply_tx")
    )


async def _wait_for_subcommand_reply_trace(
    trace_path: Path,
    *,
    timeout_seconds: float,
) -> None:
    async with asyncio.timeout(timeout_seconds):
        while True:
            events = _read_jsonl(trace_path)
            if (
                _contains_event(events, "output_report_rx", report_id="0x01")
                and _contains_event(events, "subcommand_rx")
                and _contains_event(events, "subcommand_reply_tx")
                and _contains_event(
                    events, "report_tx", report_id="0x21", reason="subcommand_reply"
                )
            ):
                return
            await asyncio.sleep(0.05)


async def _wait_for_subcommand_observation_window(
    trace_path: Path,
    *,
    min_observation_seconds: float,
    timeout_seconds: float,
) -> None:
    loop = asyncio.get_running_loop()
    first_subcommand_at: float | None = None

    async with asyncio.timeout(timeout_seconds):
        while True:
            now = loop.time()
            events = _read_jsonl(trace_path)
            subcommand_count = _count_events(events, "subcommand_rx")

            if subcommand_count > 0 and first_subcommand_at is None:
                first_subcommand_at = now

            if first_subcommand_at is not None:
                observed_long_enough = now - first_subcommand_at >= min_observation_seconds
                replies_sent = _count_events(
                    events, "report_tx", report_id="0x21", reason="subcommand_reply"
                ) >= _count_events(events, "subcommand_reply_tx")
                if observed_long_enough and replies_sent:
                    return

            await asyncio.sleep(0.05)


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
