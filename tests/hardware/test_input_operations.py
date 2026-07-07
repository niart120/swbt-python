import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any, Literal, TextIO

import pytest

from swbt import Button, DiagnosticsConfig, InputState, ProController, Stick
from swbt.protocol.input_report import InputReportBuilder

_OPERATOR_WAIT_SECONDS = 5.0
_VISIBLE_REPORT_HOLD_COUNT = 30
_STICK_ENTRY_SETTLE_SECONDS = 1.5
_STICK_VISIBLE_REPORT_HOLD_COUNT = 120
_NEUTRAL_REPORT_HOLD_COUNT = 8
_STICK_CIRCLE_STEPS = 32
_STICK_CIRCLE_STEP_SECONDS = 0.15


@pytest.mark.hardware
def test_switch_input_operation_sequence_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send input reports and leave trace checkpoints for manual UI observation.

    A pytest pass from this test does not prove that the Switch UI reflected the
    input. The human-visible UI result must be recorded in spec/hardware-test-log.md.
    """
    trace_path = swbt_hardware_artifact_dir / "input-operation-sequence.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
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
    in spec/hardware-test-log.md.
    """
    trace_path = swbt_hardware_artifact_dir / "post-handshake-input.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
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


@pytest.mark.hardware
def test_switch_input_semantics_pairing_writes_fresh_key_store(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Recreate the key store used by unit_013 active reconnect input checks.

    Run this while the Switch is on the controller search / change grip order
    screen. This test sends no non-neutral input.
    """
    key_store_path = _input_semantics_key_store_path(swbt_hardware_artifact_dir)
    trace_path = swbt_hardware_artifact_dir / "input-semantics-fresh-pairing.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        with trace_path.open("w", encoding="utf-8") as trace:
            await _wait_for_operator_condition(
                trace,
                operation="operator_prepare_input_semantics_fresh_pairing",
                expected_switch_screen="controller_search_or_change_grip_order",
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            pad = ProController(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_connect(timeout=60.0, allow_pairing=True)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="fresh_pairing_connect_result",
                    peer_address=result.peer_address,
                    route=result.route,
                    status=result.status,
                )
                await _wait_for_event(trace_path, "key_store_update", timeout_seconds=10.0)
                await _wait_for_full_handshake(trace_path, timeout_seconds=20.0)
                _record_handshake_checkpoint(pad, trace)
                await asyncio.sleep(0.5)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert key_store_path.exists()
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="operator_prepare_input_semantics_fresh_pairing",
        expected_switch_screen="controller_search_or_change_grip_order",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="fresh_pairing_connect_result",
        route="pairing",
        status="connected",
    )
    assert _contains_event(events, "key_store_update", status="succeeded")
    assert _contains_full_handshake(events)
    assert _contains_event(events, "manual_input_checkpoint", operation="handshake_complete")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_button_check_after_active_reconnect_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Enter the Switch button check screen via active reconnect and Button A.

    A pytest pass proves active reconnect, report transmission checkpoints, and
    cleanup only. The human-visible UI result must be recorded in
    spec/hardware-test-log.md.
    """
    key_store_path = _input_semantics_key_store_path(swbt_hardware_artifact_dir)
    trace_path = swbt_hardware_artifact_dir / "active-reconnect-button-check.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "input semantics key store is missing; run "
            "test_switch_input_semantics_pairing_writes_fresh_key_store first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            await _wait_for_operator_condition(
                trace,
                operation="operator_prepare_button_check_selection",
                expected_switch_screen="input_device_check_button_operation_selection",
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            pad = ProController(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_input_check(pad, trace)
                await _wait_for_full_handshake(trace_path, timeout_seconds=20.0)
                _record_handshake_checkpoint(pad, trace)

                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="button_check_enter_with_a_start",
                )
                await pad.tap(Button.A, duration=0.35)
                await asyncio.sleep(0.75)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="button_check_enter_with_a_complete",
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
                    minimum_count=hold_start_count + _VISIBLE_REPORT_HOLD_COUNT,
                    timeout_seconds=3.0,
                )
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="hold_lr_reports_sent",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )

                await pad.release(Button.L, Button.R)
                await _send_neutral_and_record(
                    pad, trace, operation="button_check_neutral_complete"
                )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_full_handshake(events)
    assert _contains_event(events, "manual_input_checkpoint", operation="handshake_complete")
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="button_check_enter_with_a_complete",
    )
    assert _contains_event(events, "manual_input_checkpoint", operation="hold_lr_reports_sent")
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="button_check_neutral_complete",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_button_check_lr_and_dpad_after_active_reconnect_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send LR and D-pad button check observations in one active reconnect run."""
    key_store_path = _input_semantics_key_store_path(swbt_hardware_artifact_dir)
    trace_path = swbt_hardware_artifact_dir / "active-reconnect-button-check-lr-dpad.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "input semantics key store is missing; run "
            "test_switch_input_semantics_pairing_writes_fresh_key_store first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            await _wait_for_operator_condition(
                trace,
                operation="operator_prepare_button_check_lr_dpad_selection",
                expected_switch_screen="input_device_check_button_operation_selection",
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            pad = ProController(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_input_check(pad, trace)
                await _wait_for_full_handshake(trace_path, timeout_seconds=20.0)
                _record_handshake_checkpoint(pad, trace)

                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="button_check_lr_dpad_enter_with_a_start",
                )
                await pad.tap(Button.A, duration=0.35)
                await asyncio.sleep(0.75)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation="button_check_lr_dpad_enter_with_a_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )

                await _hold_buttons_and_record(
                    pad,
                    trace,
                    buttons=(Button.R,),
                    operation="hold_r_only",
                )
                await _send_neutral_and_record(
                    pad,
                    trace,
                    operation="button_check_after_r_only_neutral_complete",
                )

                await _hold_buttons_and_record(
                    pad,
                    trace,
                    buttons=(Button.L,),
                    operation="hold_l_only",
                )
                await _send_neutral_and_record(
                    pad,
                    trace,
                    operation="button_check_after_l_only_neutral_complete",
                )

                await _hold_buttons_and_record(
                    pad,
                    trace,
                    buttons=(Button.L, Button.R),
                    operation="hold_lr_together",
                )
                await _send_neutral_and_record(
                    pad,
                    trace,
                    operation="button_check_after_lr_together_neutral_complete",
                )

                for direction, button in (
                    ("up", Button.DPAD_UP),
                    ("right", Button.DPAD_RIGHT),
                    ("down", Button.DPAD_DOWN),
                    ("left", Button.DPAD_LEFT),
                ):
                    await _hold_buttons_and_record(
                        pad,
                        trace,
                        buttons=(button,),
                        operation=f"hold_dpad_{direction}",
                    )
                    await _send_neutral_and_record(
                        pad,
                        trace,
                        operation=f"button_check_after_dpad_{direction}_neutral_complete",
                    )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_full_handshake(events)
    assert _contains_event(events, "manual_input_checkpoint", operation="handshake_complete")
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="button_check_lr_dpad_enter_with_a_complete",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_r_only_reports_sent",
        expected_button_bytes="400000",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_l_only_reports_sent",
        expected_button_bytes="000040",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_lr_together_reports_sent",
        expected_button_bytes="400040",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="button_check_after_lr_together_neutral_complete",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_dpad_up_reports_sent",
        expected_button_bytes="000002",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_dpad_right_reports_sent",
        expected_button_bytes="000004",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_dpad_down_reports_sent",
        expected_button_bytes="000001",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="hold_dpad_left_reports_sent",
        expected_button_bytes="000008",
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation="button_check_after_dpad_left_neutral_complete",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "error")


@pytest.mark.hardware
@pytest.mark.parametrize("stick_name", ["left", "right"])
def test_switch_stick_calibration_after_active_reconnect_for_manual_reflection(
    stick_name: Literal["left", "right"],
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Enter stick calibration via active reconnect, then send hold and circle input.

    A pytest pass proves active reconnect, report transmission checkpoints, and
    cleanup only. The human-visible UI result must be recorded in
    spec/hardware-test-log.md.
    """
    key_store_path = _input_semantics_key_store_path(swbt_hardware_artifact_dir)
    trace_path = swbt_hardware_artifact_dir / f"active-reconnect-{stick_name}-stick.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "input semantics key store is missing; run "
            "test_switch_input_semantics_pairing_writes_fresh_key_store first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            await _wait_for_operator_condition(
                trace,
                operation=f"operator_prepare_{stick_name}_stick_calibration_selection",
                expected_switch_screen="stick_calibration_selection",
                stick=stick_name,
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            pad = ProController(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_input_check(pad, trace)
                await _wait_for_full_handshake(trace_path, timeout_seconds=20.0)
                _record_handshake_checkpoint(pad, trace)

                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation=f"{stick_name}_stick_calibration_enter_with_a_start",
                    stick=stick_name,
                )
                await pad.tap(Button.A, duration=0.35)
                await asyncio.sleep(_STICK_ENTRY_SETTLE_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation=f"{stick_name}_stick_calibration_enter_with_a_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    settle_seconds=_STICK_ENTRY_SETTLE_SECONDS,
                    stick=stick_name,
                )

                await pad.apply(_stick_state(stick_name, Stick.normalized(x=1.0, y=0.0)))
                hold_start_count = pad.status().report_counters.get(0x30, 0)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    hold_report_count=_STICK_VISIBLE_REPORT_HOLD_COUNT,
                    operation=f"{stick_name}_stick_hold_start",
                    report_0x30_count=hold_start_count,
                    stick=stick_name,
                )
                await _wait_for_report_counter(
                    pad,
                    report_id=0x30,
                    minimum_count=hold_start_count + _STICK_VISIBLE_REPORT_HOLD_COUNT,
                    timeout_seconds=5.0,
                )
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    hold_report_count=_STICK_VISIBLE_REPORT_HOLD_COUNT,
                    operation=f"{stick_name}_stick_hold_reports_sent",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    stick=stick_name,
                )

                await _send_stick_circle(pad, stick_name=stick_name)
                _record_probe_event(
                    trace,
                    "manual_input_checkpoint",
                    operation=f"{stick_name}_stick_circle_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    stick=stick_name,
                    step_seconds=_STICK_CIRCLE_STEP_SECONDS,
                    steps=_STICK_CIRCLE_STEPS,
                )
                await _send_neutral_and_record(
                    pad,
                    trace,
                    operation=f"{stick_name}_stick_neutral_complete",
                    stick=stick_name,
                )
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_full_handshake(events)
    assert _contains_event(events, "manual_input_checkpoint", operation="handshake_complete")
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation=f"{stick_name}_stick_calibration_enter_with_a_complete",
        stick=stick_name,
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation=f"{stick_name}_stick_hold_reports_sent",
        stick=stick_name,
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation=f"{stick_name}_stick_circle_complete",
        stick=stick_name,
    )
    assert _contains_event(
        events,
        "manual_input_checkpoint",
        operation=f"{stick_name}_stick_neutral_complete",
        stick=stick_name,
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
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
    pad: ProController,
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


async def _active_reconnect_for_input_check(pad: ProController, trace: TextIO) -> None:
    result = await pad.try_reconnect(timeout=60.0)
    _record_probe_event(
        trace,
        "manual_input_checkpoint",
        operation="active_reconnect_result",
        peer_address=result.peer_address,
        route=result.route,
        status=result.status,
    )
    assert result.route == "active_reconnect"
    assert result.status == "connected"


async def _hold_buttons_and_record(
    pad: ProController,
    trace: TextIO,
    *,
    buttons: tuple[Button, ...],
    operation: str,
) -> None:
    await pad.press(*buttons)
    hold_start_count = pad.status().report_counters.get(0x30, 0)
    expected_button_bytes = _current_button_bytes(pad)
    _record_probe_event(
        trace,
        "manual_input_checkpoint",
        expected_button_bytes=expected_button_bytes,
        operation=f"{operation}_start",
        report_0x30_count=hold_start_count,
    )
    await _wait_for_report_counter(
        pad,
        report_id=0x30,
        minimum_count=hold_start_count + _VISIBLE_REPORT_HOLD_COUNT,
        timeout_seconds=3.0,
    )
    _record_probe_event(
        trace,
        "manual_input_checkpoint",
        expected_button_bytes=expected_button_bytes,
        operation=f"{operation}_reports_sent",
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
    )
    await pad.release(*buttons)


def _current_button_bytes(pad: ProController) -> str:
    report = InputReportBuilder().build_0x30(pad.snapshot())
    return report[3:6].hex()


def _record_handshake_checkpoint(pad: ProController, trace: TextIO) -> None:
    _record_probe_event(
        trace,
        "manual_input_checkpoint",
        operation="handshake_complete",
        last_subcommand_id=_format_optional_hex(pad.status().last_subcommand_id),
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
        report_0x21_count=pad.status().report_counters.get(0x21, 0),
    )


async def _send_neutral_and_record(
    pad: ProController,
    trace: TextIO,
    *,
    operation: str,
    stick: str | None = None,
) -> None:
    await pad.neutral()
    assert pad.snapshot() == InputState.neutral()
    neutral_start_count = pad.status().report_counters.get(0x30, 0)
    await _wait_for_report_counter(
        pad,
        report_id=0x30,
        minimum_count=neutral_start_count + _NEUTRAL_REPORT_HOLD_COUNT,
        timeout_seconds=2.0,
    )
    fields: dict[str, object] = {
        "operation": operation,
        "report_0x30_count": pad.status().report_counters.get(0x30, 0),
    }
    if stick is not None:
        fields["stick"] = stick
    _record_probe_event(trace, "manual_input_checkpoint", **fields)


async def _send_stick_circle(
    pad: ProController,
    *,
    stick_name: Literal["left", "right"],
) -> None:
    for step in range(_STICK_CIRCLE_STEPS):
        angle = 2 * math.pi * step / _STICK_CIRCLE_STEPS
        await pad.apply(
            _stick_state(
                stick_name,
                Stick.normalized(x=math.cos(angle), y=math.sin(angle)),
            )
        )
        await asyncio.sleep(_STICK_CIRCLE_STEP_SECONDS)


def _stick_state(stick_name: Literal["left", "right"], stick: Stick) -> InputState:
    if stick_name == "left":
        return InputState.neutral().with_sticks(left_stick=stick)
    return InputState.neutral().with_sticks(right_stick=stick)


def _input_semantics_key_store_path(artifact_dir: Path) -> Path:
    return artifact_dir / "input-semantics-key-store.json"


def _delete_file_if_exists(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        return


async def _wait_for_operator_condition(
    trace: TextIO,
    *,
    operation: str,
    expected_switch_screen: str,
    wait_seconds: float,
    stick: str | None = None,
) -> None:
    fields: dict[str, object] = {
        "expected_switch_screen": expected_switch_screen,
        "operation": operation,
        "wait_seconds": wait_seconds,
    }
    if stick is not None:
        fields["stick"] = stick
    _record_probe_event(trace, "manual_input_checkpoint", **fields)
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


def _contains_active_reconnect_success(events: list[dict[str, Any]]) -> bool:
    return (
        _contains_event(events, "active_reconnect_attempt", route="active_reconnect")
        and _contains_event(
            events,
            "active_reconnect_result",
            route="active_reconnect",
            status="connected",
        )
        and _contains_event(
            events,
            "manual_input_checkpoint",
            operation="active_reconnect_result",
            route="active_reconnect",
            status="connected",
        )
        and _contains_event(events, "connected")
    )
