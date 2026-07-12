import asyncio
import json
import math
import sys
from pathlib import Path
from typing import Any, Literal, TextIO

import pytest

from swbt import Button, ControllerColors, DiagnosticsConfig, InputState, JoyConL, JoyConR, Stick
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.output_report import OutputReport
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.session import SwitchHidSessionState
from swbt.protocol.subcommand import SubcommandResponder

_OPERATOR_WAIT_SECONDS = 5.0
_ORDER_BUTTON_HOLD_SECONDS = 5.0
_ORDER_BUTTON_MIN_REPORT_COUNT = 30
_NEUTRAL_REPORT_HOLD_COUNT = 8
_UI_OBSERVATION_HOLD_SECONDS = 10.0
_VISIBLE_REPORT_HOLD_COUNT = 30
_STICK_VISIBLE_REPORT_HOLD_COUNT = 120
_STICK_CIRCLE_STEPS = 32
_STICK_CIRCLE_STEP_SECONDS = 0.15
_FACTORY_SENSOR_CALIBRATION_ADDRESS = 0x6020
_FACTORY_SENSOR_CALIBRATION_BYTES = bytes.fromhex(
    "00 00 00 00 00 00 00 40 00 40 00 40 00 00 00 00 00 00 3b 34 3b 34 3b 34"
)
_CUSTOM_JOYCON_LEFT_CONTROLLER_COLORS = ControllerColors(
    body=0xFF0000,
    buttons=0x0000FF,
    left_grip=0xFF00FF,
    right_grip=0xFF8000,
)
_CUSTOM_JOYCON_RIGHT_CONTROLLER_COLORS = ControllerColors(
    body=0x00FF00,
    buttons=0x8000FF,
    left_grip=0x00FFFF,
    right_grip=0xFFFF00,
)


def _joycon_class(side: Literal["left", "right"]) -> type[JoyConL] | type[JoyConR]:
    if side == "left":
        return JoyConL
    return JoyConR


@pytest.mark.hardware
@pytest.mark.parametrize("side", ["left", "right"])
def test_switch_joycon_profile_pairing_records_device_info(
    side: Literal["left", "right"],
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Record single Joy-Con profile identity during a real Switch handshake.

    A pytest pass proves the advertised device name, Switch connection, device-info
    reply bytes, an SR+SL order-screen input attempt, and cleanup. Human-visible
    Switch UI identity and order registration progress must still be recorded in
    spec/hardware-test-log.md.
    """
    expected_device_name = _expected_device_name(side)
    expected_device_type = _expected_device_type(side)
    key_store_path = swbt_hardware_artifact_dir / f"joycon-{side}-profile-key-store.json"
    trace_path = swbt_hardware_artifact_dir / f"joycon-{side}-profile-pairing.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_joycon_profile_checkpoint",
                expected_device_name=expected_device_name,
                expected_device_type=f"0x{expected_device_type:02x}",
                expected_switch_screen="controller_search_or_change_grip_order",
                operation="operator_prepare_joycon_profile_pairing",
                side=side,
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: Joy-Con profile pairing; "
                f"side={side}; expected_device_name={expected_device_name}; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"waiting {_OPERATOR_WAIT_SECONDS:.0f}s\n"
            )
            sys.stderr.flush()
            await asyncio.sleep(_OPERATOR_WAIT_SECONDS)

            pad = _joycon_class(side)(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_device_info_probe(pad, trace, side=side)
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_device_info_reply(
                    trace_path,
                    expected_device_type=expected_device_type,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="device_info_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side=side,
                )
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    last_subcommand_id=_format_optional_hex(pad.status().last_subcommand_id),
                    operation="order_input_window_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side=side,
                )
                await _send_order_buttons(pad, trace, side=side)
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side=side,
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side=side,
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert key_store_path.exists()
    assert _contains_event(
        events,
        "bumble_device_initialized",
        adapter=swbt_bumble_adapter,
        device_name=expected_device_name,
    )
    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "device_info_reply",
        controller_type=f"0x{expected_device_type:02x}",
        side=side,
        tail_bytes="0101",
    )
    assert _device_info_address_matches_configured_local_address(events)
    assert _contains_event(events, "subcommand_reply_tx", subcommand_id="0x02")
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=_expected_order_button_bytes(side),
        input_report_delta_at_least_minimum=True,
        operation="sr_sl_order_buttons_hold_reports_sent",
        side=side,
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="sr_sl_order_buttons_neutral_complete",
        side=side,
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
        side=side,
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side=side,
    )
    assert not _contains_event(events, "error")


@pytest.mark.hardware
@pytest.mark.parametrize("side", ["left", "right"])
def test_switch_joycon_profile_reads_default_controller_colors(
    side: Literal["left", "right"],
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Record Joy-Con default controller color SPI bytes during a real handshake."""
    expected_device_name = _expected_device_name(side)
    expected_device_type = _expected_device_type(side)
    expected_color_bytes = _expected_default_controller_color_bytes(side)
    key_store_path = swbt_hardware_artifact_dir / f"joycon-{side}-colors-key-store.json"
    trace_path = swbt_hardware_artifact_dir / f"joycon-{side}-default-controller-colors.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_joycon_profile_checkpoint",
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_device_name=expected_device_name,
                expected_device_type=f"0x{expected_device_type:02x}",
                expected_switch_screen="controller_search_or_change_grip_order",
                operation="operator_prepare_joycon_default_color_pairing",
                side=side,
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: Joy-Con default controller color; "
                f"side={side}; expected_device_name={expected_device_name}; "
                f"expected_controller_color_bytes={expected_color_bytes.hex()}; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"waiting {_OPERATOR_WAIT_SECONDS:.0f}s\n"
            )
            sys.stderr.flush()
            await asyncio.sleep(_OPERATOR_WAIT_SECONDS)

            pad = _joycon_class(side)(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_device_info_probe(
                pad,
                trace,
                side=side,
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_device_info_reply(
                    trace_path,
                    expected_device_type=expected_device_type,
                    timeout_seconds=25.0,
                )
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side=side,
                )
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                await _send_order_buttons(pad, trace, side=side)
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side=side,
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side=side,
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert key_store_path.exists()
    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "device_info_reply",
        controller_type=f"0x{expected_device_type:02x}",
        side=side,
        tail_bytes="0101",
    )
    assert _device_info_address_matches_configured_local_address(events)
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        matches_expected_controller_colors=True,
        side=side,
    )
    assert _contains_event(
        events,
        "factory_sensor_calibration_spi_reply",
        calibration_bytes=_FACTORY_SENSOR_CALIBRATION_BYTES.hex(),
        matches_expected_calibration=True,
        side=side,
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
        side=side,
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side=side,
    )
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_joycon_left_button_check_dpad_after_reconnect_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send Joy-Con L D-pad inputs on the Switch button check screen.

    Run this while the Switch is already inside the button operation check
    screen. Joy-Con L has no Button A in this profile, so this test does not try
    to enter the screen by itself.
    """
    key_store_path = swbt_hardware_artifact_dir / "joycon-left-profile-key-store.json"
    trace_path = swbt_hardware_artifact_dir / "joycon-left-button-check-dpad.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "Joy-Con L key store is missing; run "
            "test_switch_joycon_profile_pairing_records_device_info[left] first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_operator_condition(
                trace,
                operation="operator_prepare_joycon_left_button_check_dpad",
                expected_switch_screen="input_device_check_button_operation_screen",
                side="left",
            )
            pad = JoyConL(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_joycon_input_check(pad, trace, side="left")
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                _record_joycon_handshake_checkpoint(pad, trace, side="left")

                for direction, button, expected_button_bytes in (
                    ("up", Button.DPAD_UP, "000002"),
                    ("right", Button.DPAD_RIGHT, "000004"),
                    ("down", Button.DPAD_DOWN, "000001"),
                    ("left", Button.DPAD_LEFT, "000008"),
                ):
                    await _hold_joycon_buttons_and_record(
                        pad,
                        trace,
                        buttons=(button,),
                        expected_button_bytes=expected_button_bytes,
                        operation=f"hold_dpad_{direction}",
                        side="left",
                    )
                    await _send_joycon_neutral_and_record(
                        pad,
                        trace,
                        operation=f"button_check_after_dpad_{direction}_neutral_complete",
                        side="left",
                    )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side="left",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_order_input_window(events)
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="handshake_complete",
        side="left",
    )
    for direction, expected_button_bytes in (
        ("up", "000002"),
        ("right", "000004"),
        ("down", "000001"),
        ("left", "000008"),
    ):
        assert _contains_event(
            events,
            "manual_joycon_profile_checkpoint",
            expected_button_bytes=expected_button_bytes,
            operation=f"hold_dpad_{direction}_reports_sent",
            side="left",
        )
        assert _contains_event(
            events,
            "manual_joycon_profile_checkpoint",
            operation=f"button_check_after_dpad_{direction}_neutral_complete",
            side="left",
        )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side="left",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_joycon_left_stick_calibration_after_reconnect_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send Joy-Con L left stick hold and circle input on the calibration screen.

    Run this while the Switch is already inside the target stick calibration
    screen. Joy-Con L has no Button A in this profile, so this test does not try
    to enter the screen by itself.
    """
    key_store_path = swbt_hardware_artifact_dir / "joycon-left-profile-key-store.json"
    trace_path = swbt_hardware_artifact_dir / "joycon-left-stick-calibration.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "Joy-Con L key store is missing; run "
            "test_switch_joycon_profile_pairing_records_device_info[left] first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_operator_condition(
                trace,
                operation="operator_prepare_joycon_left_stick_calibration",
                expected_switch_screen="stick_calibration_screen",
                side="left",
            )
            pad = JoyConL(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_joycon_input_check(pad, trace, side="left")
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                _record_joycon_handshake_checkpoint(pad, trace, side="left")

                await pad.apply(_joycon_left_stick_state(Stick.normalized(x=1.0, y=0.0)))
                hold_start_count = pad.status().report_counters.get(0x30, 0)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_report_count=_STICK_VISIBLE_REPORT_HOLD_COUNT,
                    operation="left_stick_hold_start",
                    report_0x30_count=hold_start_count,
                    side="left",
                )
                await _wait_for_report_counter(
                    pad,
                    report_id=0x30,
                    minimum_count=hold_start_count + _STICK_VISIBLE_REPORT_HOLD_COUNT,
                    timeout_seconds=5.0,
                )
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_report_count=_STICK_VISIBLE_REPORT_HOLD_COUNT,
                    operation="left_stick_hold_reports_sent",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="left",
                )

                await _send_joycon_left_stick_circle(pad)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="left_stick_circle_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="left",
                    step_seconds=_STICK_CIRCLE_STEP_SECONDS,
                    steps=_STICK_CIRCLE_STEPS,
                )
                await _send_joycon_neutral_and_record(
                    pad,
                    trace,
                    operation="left_stick_neutral_complete",
                    side="left",
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side="left",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_order_input_window(events)
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="handshake_complete",
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="left_stick_hold_reports_sent",
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="left_stick_circle_complete",
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="left_stick_neutral_complete",
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side="left",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_joycon_right_button_check_abxy_after_reconnect_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send Joy-Con R ABXY inputs on the Switch button check screen."""
    key_store_path = swbt_hardware_artifact_dir / "joycon-right-profile-key-store.json"
    trace_path = swbt_hardware_artifact_dir / "joycon-right-button-check-abxy.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "Joy-Con R key store is missing; run "
            "test_switch_joycon_profile_pairing_records_device_info[right] first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_operator_condition(
                trace,
                operation="operator_prepare_joycon_right_button_check_abxy",
                expected_switch_screen="input_device_check_button_operation_selection",
                side="right",
            )
            pad = JoyConR(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_joycon_input_check(pad, trace, side="right")
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                _record_joycon_handshake_checkpoint(pad, trace, side="right")

                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="button_check_abxy_enter_with_a_start",
                    side="right",
                )
                await pad.tap(Button.A, duration=0.35)
                await asyncio.sleep(0.75)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="button_check_abxy_enter_with_a_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="right",
                )

                for name, button, expected_button_bytes in (
                    ("y", Button.Y, "010000"),
                    ("x", Button.X, "020000"),
                    ("b", Button.B, "040000"),
                    ("a", Button.A, "080000"),
                ):
                    await _hold_joycon_buttons_and_record(
                        pad,
                        trace,
                        buttons=(button,),
                        expected_button_bytes=expected_button_bytes,
                        operation=f"hold_button_{name}",
                        side="right",
                    )
                    await _send_joycon_neutral_and_record(
                        pad,
                        trace,
                        operation=f"button_check_after_{name}_neutral_complete",
                        side="right",
                    )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side="right",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_order_input_window(events)
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="handshake_complete",
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="button_check_abxy_enter_with_a_complete",
        side="right",
    )
    for name, expected_button_bytes in (
        ("y", "010000"),
        ("x", "020000"),
        ("b", "040000"),
        ("a", "080000"),
    ):
        assert _contains_event(
            events,
            "manual_joycon_profile_checkpoint",
            expected_button_bytes=expected_button_bytes,
            operation=f"hold_button_{name}_reports_sent",
            side="right",
        )
        assert _contains_event(
            events,
            "manual_joycon_profile_checkpoint",
            operation=f"button_check_after_{name}_neutral_complete",
            side="right",
        )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side="right",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_joycon_right_stick_calibration_after_reconnect_for_manual_reflection(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Send Joy-Con R right stick hold and circle input on the calibration screen."""
    key_store_path = swbt_hardware_artifact_dir / "joycon-right-profile-key-store.json"
    trace_path = swbt_hardware_artifact_dir / "joycon-right-stick-calibration.jsonl"
    if not key_store_path.exists():
        pytest.skip(
            "Joy-Con R key store is missing; run "
            "test_switch_joycon_profile_pairing_records_device_info[right] first "
            "with the same --swbt-hardware-artifact-dir"
        )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_operator_condition(
                trace,
                operation="operator_prepare_joycon_right_stick_calibration",
                expected_switch_screen="stick_calibration_screen",
                side="right",
            )
            pad = JoyConR(
                adapter=swbt_bumble_adapter,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await _active_reconnect_for_joycon_input_check(pad, trace, side="right")
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                _record_joycon_handshake_checkpoint(pad, trace, side="right")

                await pad.apply(_joycon_right_stick_state(Stick.normalized(x=1.0, y=0.0)))
                hold_start_count = pad.status().report_counters.get(0x30, 0)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_report_count=_STICK_VISIBLE_REPORT_HOLD_COUNT,
                    operation="right_stick_hold_start",
                    report_0x30_count=hold_start_count,
                    side="right",
                )
                await _wait_for_report_counter(
                    pad,
                    report_id=0x30,
                    minimum_count=hold_start_count + _STICK_VISIBLE_REPORT_HOLD_COUNT,
                    timeout_seconds=5.0,
                )
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_report_count=_STICK_VISIBLE_REPORT_HOLD_COUNT,
                    operation="right_stick_hold_reports_sent",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="right",
                )

                await _send_joycon_right_stick_circle(pad)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="right_stick_circle_complete",
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="right",
                    step_seconds=_STICK_CIRCLE_STEP_SECONDS,
                    steps=_STICK_CIRCLE_STEPS,
                )
                await _send_joycon_neutral_and_record(
                    pad,
                    trace,
                    operation="right_stick_neutral_complete",
                    side="right",
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side="right",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_active_reconnect_success(events)
    assert _contains_order_input_window(events)
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="handshake_complete",
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="right_stick_hold_reports_sent",
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="right_stick_circle_complete",
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="right_stick_neutral_complete",
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side="right",
    )
    assert _count_events(events, "report_tx", report_id="0x30") >= 10
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_joycon_left_profile_reads_custom_controller_colors(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Record Joy-Con L custom controller color SPI bytes during a real handshake."""
    expected_colors = _CUSTOM_JOYCON_LEFT_CONTROLLER_COLORS
    expected_color_bytes = expected_colors.to_spi_bytes()
    expected_device_name = _expected_device_name("left")
    expected_device_type = _expected_device_type("left")
    key_store_path = swbt_hardware_artifact_dir / "joycon-left-custom-colors-key-store.json"
    trace_path = swbt_hardware_artifact_dir / "joycon-left-custom-controller-colors.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_joycon_profile_checkpoint",
                body_color=_format_rgb(expected_colors.body),
                buttons_color=_format_rgb(expected_colors.buttons),
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_device_name=expected_device_name,
                expected_device_type=f"0x{expected_device_type:02x}",
                expected_switch_screen="controller_search_or_change_grip_order",
                left_grip_color=_format_rgb(expected_colors.left_grip),
                operation="operator_prepare_joycon_custom_color_pairing",
                right_grip_color=_format_rgb(expected_colors.right_grip),
                side="left",
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: Joy-Con L custom controller color; "
                f"expected_device_name={expected_device_name}; "
                f"expected_controller_color_bytes={expected_color_bytes.hex()}; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"waiting {_OPERATOR_WAIT_SECONDS:.0f}s\n"
            )
            sys.stderr.flush()
            await asyncio.sleep(_OPERATOR_WAIT_SECONDS)

            pad = JoyConL(
                adapter=swbt_bumble_adapter,
                controller_colors=expected_colors,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_device_info_probe(
                pad,
                trace,
                side="left",
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_device_info_reply(
                    trace_path,
                    expected_device_type=expected_device_type,
                    timeout_seconds=25.0,
                )
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="left",
                )
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                await _send_order_buttons(pad, trace, side="left")
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="left",
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side="left",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert key_store_path.exists()
    assert _contains_event(
        events,
        "bumble_device_initialized",
        adapter=swbt_bumble_adapter,
        device_name=expected_device_name,
    )
    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "device_info_reply",
        controller_type=f"0x{expected_device_type:02x}",
        side="left",
        tail_bytes="0101",
    )
    assert _device_info_address_matches_configured_local_address(events)
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        matches_expected_controller_colors=True,
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=_expected_order_button_bytes("left"),
        input_report_delta_at_least_minimum=True,
        operation="sr_sl_order_buttons_hold_reports_sent",
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
        side="left",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side="left",
    )
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_joycon_right_profile_reads_custom_controller_colors(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Record Joy-Con R custom controller color SPI bytes during a real handshake."""
    expected_colors = _CUSTOM_JOYCON_RIGHT_CONTROLLER_COLORS
    expected_color_bytes = expected_colors.to_spi_bytes()
    expected_device_name = _expected_device_name("right")
    expected_device_type = _expected_device_type("right")
    key_store_path = swbt_hardware_artifact_dir / "joycon-right-custom-colors-key-store.json"
    trace_path = swbt_hardware_artifact_dir / "joycon-right-custom-controller-colors.jsonl"

    async def run() -> None:
        _delete_file_if_exists(key_store_path)
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_joycon_profile_checkpoint",
                body_color=_format_rgb(expected_colors.body),
                buttons_color=_format_rgb(expected_colors.buttons),
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_device_name=expected_device_name,
                expected_device_type=f"0x{expected_device_type:02x}",
                expected_switch_screen="controller_search_or_change_grip_order",
                left_grip_color=_format_rgb(expected_colors.left_grip),
                operation="operator_prepare_joycon_custom_color_pairing",
                right_grip_color=_format_rgb(expected_colors.right_grip),
                side="right",
                wait_seconds=_OPERATOR_WAIT_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: Joy-Con R custom controller color; "
                f"expected_device_name={expected_device_name}; "
                f"expected_controller_color_bytes={expected_color_bytes.hex()}; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"waiting {_OPERATOR_WAIT_SECONDS:.0f}s\n"
            )
            sys.stderr.flush()
            await asyncio.sleep(_OPERATOR_WAIT_SECONDS)

            pad = JoyConR(
                adapter=swbt_bumble_adapter,
                controller_colors=expected_colors,
                key_store_path=str(key_store_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_device_info_probe(
                pad,
                trace,
                side="right",
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_device_info_reply(
                    trace_path,
                    expected_device_type=expected_device_type,
                    timeout_seconds=25.0,
                )
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="right",
                )
                await _wait_for_order_input_window(trace_path, timeout_seconds=20.0)
                await _send_order_buttons(pad, trace, side="right")
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                    side="right",
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_joycon_profile_cleanup",
                    connection_state=pad.status().connection_state,
                    side="right",
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert key_store_path.exists()
    assert _contains_event(
        events,
        "bumble_device_initialized",
        adapter=swbt_bumble_adapter,
        device_name=expected_device_name,
    )
    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "device_info_reply",
        controller_type=f"0x{expected_device_type:02x}",
        side="right",
        tail_bytes="0101",
    )
    assert _device_info_address_matches_configured_local_address(events)
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        matches_expected_controller_colors=True,
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=_expected_order_button_bytes("right"),
        input_report_delta_at_least_minimum=True,
        operation="sr_sl_order_buttons_hold_reports_sent",
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
        side="right",
    )
    assert _contains_event(
        events,
        "manual_joycon_profile_cleanup",
        connection_state="closed",
        side="right",
    )
    assert not _contains_event(events, "error")


class RecordingDeviceInfoResponder(SubcommandResponder):
    """Wrap a responder and record device-info reply bytes for hardware diagnostics."""

    def __init__(
        self,
        inner: SubcommandResponder,
        trace: TextIO,
        *,
        expected_controller_color_bytes: bytes | None = None,
        side: str,
    ) -> None:
        """Create a recording wrapper around an existing subcommand responder."""
        self._inner = inner
        self._trace = trace
        self._expected_controller_color_bytes = expected_controller_color_bytes
        self._side = side

    @property
    def session_state(self) -> SwitchHidSessionState:
        """Return the wrapped responder session state."""
        return self._inner.session_state

    def set_device_info_bluetooth_address(self, bluetooth_address: bytes) -> None:
        """Forward Device Info address updates to the wrapped responder."""
        self._inner.set_device_info_bluetooth_address(bluetooth_address)

    def respond(self, output_report: OutputReport, *, state: InputState, timer: int = 0) -> bytes:
        """Return the inner responder reply and emit device-info observations."""
        reply = self._inner.respond(output_report, state=state, timer=timer)
        if output_report.subcommand_id == 0x02:
            self._record_device_info_reply(reply)
        if output_report.subcommand_id == 0x10:
            self._record_spi_reply(output_report.subcommand_payload, reply)
        return reply

    def _record_device_info_reply(self, reply: bytes) -> None:
        device_info = reply[15:27]
        _record_probe_event(
            self._trace,
            "device_info_reply",
            controller_type=_format_optional_byte(device_info, 2),
            device_info_data=device_info.hex(),
            device_info_tail_byte_0=_format_optional_byte(device_info, 10),
            device_info_tail_byte_1=_format_optional_byte(device_info, 11),
            profile_bluetooth_address_bytes=device_info[4:10].hex(),
            side=self._side,
            tail_bytes=device_info[10:12].hex(),
        )

    def _record_spi_reply(self, payload: bytes, reply: bytes) -> None:
        if len(payload) < 5:
            return

        address = int.from_bytes(payload[0:4], "little")
        size = payload[4]
        read_data = reply[20 : 20 + size]
        calibration_offset = _FACTORY_SENSOR_CALIBRATION_ADDRESS - address
        calibration_size = len(_FACTORY_SENSOR_CALIBRATION_BYTES)
        if calibration_offset >= 0 and calibration_offset + calibration_size <= len(read_data):
            calibration_bytes = read_data[
                calibration_offset : calibration_offset + calibration_size
            ]
            _record_probe_event(
                self._trace,
                "factory_sensor_calibration_spi_reply",
                address=f"0x{address:06x}",
                calibration_bytes=calibration_bytes.hex(),
                matches_expected_calibration=(
                    calibration_bytes == _FACTORY_SENSOR_CALIBRATION_BYTES
                ),
                side=self._side,
                size=size,
            )
        if self._expected_controller_color_bytes is None:
            return
        color_offset = 0x6050 - address
        if color_offset < 0 or color_offset + 12 > len(read_data):
            return
        controller_color_bytes = read_data[color_offset : color_offset + 12]
        _record_probe_event(
            self._trace,
            "controller_color_spi_reply",
            address=f"0x{address:06x}",
            controller_color_bytes=controller_color_bytes.hex(),
            matches_expected_controller_colors=(
                controller_color_bytes == self._expected_controller_color_bytes
            ),
            read_data=read_data.hex(),
            request_prefix=payload[:5].hex(),
            side=self._side,
            size=size,
        )


def _install_device_info_probe(
    pad: JoyConL | JoyConR,
    trace: TextIO,
    *,
    expected_controller_color_bytes: bytes | None = None,
    side: str,
) -> None:
    dispatcher = pad._output_report_dispatcher
    dispatcher.subcommand_responder = RecordingDeviceInfoResponder(
        dispatcher.subcommand_responder,
        trace,
        expected_controller_color_bytes=expected_controller_color_bytes,
        side=side,
    )


async def _send_order_buttons(pad: JoyConL | JoyConR, trace: TextIO, *, side: str) -> None:
    await pad.press(Button.SR, Button.SL)
    report_0x30_count_before = pad.status().report_counters.get(0x30, 0)
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=_expected_order_button_bytes(side),
        hold_seconds=_ORDER_BUTTON_HOLD_SECONDS,
        min_report_count=_ORDER_BUTTON_MIN_REPORT_COUNT,
        report_0x30_count_before=report_0x30_count_before,
        operation="sr_sl_order_buttons_start",
        side=side,
    )
    await asyncio.sleep(_ORDER_BUTTON_HOLD_SECONDS)
    report_0x30_count_after = pad.status().report_counters.get(0x30, 0)
    input_report_delta = report_0x30_count_after - report_0x30_count_before
    assert input_report_delta >= _ORDER_BUTTON_MIN_REPORT_COUNT
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=_expected_order_button_bytes(side),
        hold_seconds=_ORDER_BUTTON_HOLD_SECONDS,
        input_report_delta=input_report_delta,
        input_report_delta_at_least_minimum=True,
        min_report_count=_ORDER_BUTTON_MIN_REPORT_COUNT,
        operation="sr_sl_order_buttons_hold_reports_sent",
        report_0x30_count=report_0x30_count_after,
        report_0x30_count_before=report_0x30_count_before,
        side=side,
    )
    await pad.release(Button.SR, Button.SL)
    assert pad.snapshot() == InputState.neutral()
    neutral_start_count = pad.status().report_counters.get(0x30, 0)
    await _wait_for_report_counter(
        pad,
        report_id=0x30,
        minimum_count=neutral_start_count + _NEUTRAL_REPORT_HOLD_COUNT,
        timeout_seconds=2.0,
    )
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        operation="sr_sl_order_buttons_neutral_complete",
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
        side=side,
    )


def _record_operator_condition(
    trace: TextIO,
    *,
    operation: str,
    expected_switch_screen: str,
    side: str,
) -> None:
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        expected_switch_screen=expected_switch_screen,
        operation=operation,
        side=side,
    )
    sys.stderr.write(
        "SWBT hardware: "
        f"{operation}; side={side}; expected_switch_screen={expected_switch_screen}; "
        "starting immediately\n"
    )
    sys.stderr.flush()


async def _active_reconnect_for_joycon_input_check(
    pad: JoyConL | JoyConR,
    trace: TextIO,
    *,
    side: str,
) -> None:
    result = await pad.try_reconnect(timeout=60.0)
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        operation="active_reconnect_result",
        peer_address=result.peer_address,
        route=result.route,
        side=side,
        status=result.status,
    )
    assert result.route == "active_reconnect"
    assert result.status == "connected"


def _record_joycon_handshake_checkpoint(
    pad: JoyConL | JoyConR,
    trace: TextIO,
    *,
    side: str,
) -> None:
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        operation="handshake_complete",
        last_subcommand_id=_format_optional_hex(pad.status().last_subcommand_id),
        report_0x21_count=pad.status().report_counters.get(0x21, 0),
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
        side=side,
    )


async def _hold_joycon_buttons_and_record(
    pad: JoyConL | JoyConR,
    trace: TextIO,
    *,
    buttons: tuple[Button, ...],
    expected_button_bytes: str,
    operation: str,
    side: str,
) -> None:
    await pad.press(*buttons)
    hold_start_count = pad.status().report_counters.get(0x30, 0)
    actual_button_bytes = _current_joycon_button_bytes(pad, side=side)
    assert actual_button_bytes == expected_button_bytes
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=expected_button_bytes,
        operation=f"{operation}_start",
        report_0x30_count=hold_start_count,
        side=side,
    )
    await _wait_for_report_counter(
        pad,
        report_id=0x30,
        minimum_count=hold_start_count + _VISIBLE_REPORT_HOLD_COUNT,
        timeout_seconds=3.0,
    )
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        expected_button_bytes=expected_button_bytes,
        operation=f"{operation}_reports_sent",
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
        side=side,
    )
    await pad.release(*buttons)


def _current_joycon_button_bytes(pad: JoyConL | JoyConR, *, side: str) -> str:
    profile = JoyConLeftProfile() if side == "left" else JoyConRightProfile()
    report = InputReportBuilder(profile).build_0x30(pad.snapshot())
    return report[3:6].hex()


async def _send_joycon_neutral_and_record(
    pad: JoyConL | JoyConR,
    trace: TextIO,
    *,
    operation: str,
    side: str,
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
    _record_probe_event(
        trace,
        "manual_joycon_profile_checkpoint",
        operation=operation,
        report_0x30_count=pad.status().report_counters.get(0x30, 0),
        side=side,
    )


async def _send_joycon_left_stick_circle(pad: JoyConL) -> None:
    for step in range(_STICK_CIRCLE_STEPS):
        angle = 2 * math.pi * step / _STICK_CIRCLE_STEPS
        await pad.apply(
            _joycon_left_stick_state(
                Stick.normalized(x=math.cos(angle), y=math.sin(angle)),
            )
        )
        await asyncio.sleep(_STICK_CIRCLE_STEP_SECONDS)


async def _send_joycon_right_stick_circle(pad: JoyConR) -> None:
    for step in range(_STICK_CIRCLE_STEPS):
        angle = 2 * math.pi * step / _STICK_CIRCLE_STEPS
        await pad.apply(
            _joycon_right_stick_state(
                Stick.normalized(x=math.cos(angle), y=math.sin(angle)),
            )
        )
        await asyncio.sleep(_STICK_CIRCLE_STEP_SECONDS)


def _joycon_left_stick_state(stick: Stick) -> InputState:
    return InputState.neutral().with_sticks(left_stick=stick)


def _joycon_right_stick_state(stick: Stick) -> InputState:
    return InputState.neutral().with_sticks(right_stick=stick)


async def _wait_for_device_info_reply(
    trace_path: Path,
    *,
    expected_device_type: int,
    timeout_seconds: float,
) -> None:
    expected_hex = f"0x{expected_device_type:02x}"
    async with asyncio.timeout(timeout_seconds):
        while True:
            if _contains_event(
                _read_jsonl(trace_path),
                "device_info_reply",
                controller_type=expected_hex,
                tail_bytes="0101",
            ):
                return
            await asyncio.sleep(0.05)


async def _wait_for_order_input_window(trace_path: Path, *, timeout_seconds: float) -> None:
    async with asyncio.timeout(timeout_seconds):
        while True:
            if _contains_order_input_window(_read_jsonl(trace_path)):
                return
            await asyncio.sleep(0.05)


async def _wait_for_controller_color_spi_reply(
    trace_path: Path,
    *,
    expected_controller_color_bytes: bytes,
    timeout_seconds: float,
) -> None:
    expected_hex = expected_controller_color_bytes.hex()
    async with asyncio.timeout(timeout_seconds):
        while True:
            if _contains_event(
                _read_jsonl(trace_path),
                "controller_color_spi_reply",
                controller_color_bytes=expected_hex,
                matches_expected_controller_colors=True,
            ):
                return
            await asyncio.sleep(0.05)


async def _wait_for_report_counter(
    pad: JoyConL | JoyConR,
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


def _expected_device_name(side: Literal["left", "right"]) -> str:
    if side == "left":
        return "Joy-Con (L)"
    return "Joy-Con (R)"


def _expected_device_type(side: Literal["left", "right"]) -> int:
    if side == "left":
        return 0x01
    return 0x02


def _expected_order_button_bytes(side: str) -> str:
    if side == "left":
        return "000030"
    return "300000"


def _expected_default_controller_color_bytes(side: str) -> bytes:
    if side == "left":
        return bytes.fromhex("00 b2 ff 32 32 32 00 b2 ff 00 b2 ff")
    return bytes.fromhex("ff 3b 30 32 32 32 ff 3b 30 ff 3b 30")


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
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


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
            "manual_joycon_profile_checkpoint",
            operation="active_reconnect_result",
            route="active_reconnect",
            status="connected",
        )
        and _contains_event(events, "connected")
    )


def _device_info_address_matches_configured_local_address(
    events: list[dict[str, Any]],
) -> bool:
    local_address = None
    device_info_address = None
    for event in events:
        if event.get("event") == "device_info_bluetooth_address_configured":
            local_address = event.get("address")
        if event.get("event") == "device_info_reply":
            device_info_address = event.get("profile_bluetooth_address_bytes")
    return (
        isinstance(local_address, str)
        and isinstance(device_info_address, str)
        and local_address != "000000000000"
        and local_address == device_info_address
    )


def _contains_order_input_window(events: list[dict[str, Any]]) -> bool:
    subcommands = [
        event.get("subcommand_id") for event in events if event.get("event") == "subcommand_rx"
    ]
    required = {"0x02", "0x08", "0x10", "0x03", "0x04", "0x40", "0x48", "0x30"}
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


def _format_optional_byte(data: bytes, index: int) -> str | None:
    if index >= len(data):
        return None
    return f"0x{data[index]:02x}"


def _format_optional_hex(value: int | None) -> str | None:
    if value is None:
        return None
    return f"0x{value:02x}"


def _format_rgb(value: int) -> str:
    return f"0x{value:06x}"
