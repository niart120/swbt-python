import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Literal, TextIO

import pytest

from swbt import Button, DiagnosticsConfig, InputState, JoyCon
from swbt.protocol.output_report import OutputReport
from swbt.protocol.subcommand import SubcommandResponder, SubcommandSessionState

_OPERATOR_WAIT_SECONDS = 5.0
_ORDER_BUTTON_HOLD_SECONDS = 5.0
_ORDER_BUTTON_MIN_REPORT_COUNT = 30
_NEUTRAL_REPORT_HOLD_COUNT = 8
_UI_OBSERVATION_HOLD_SECONDS = 10.0


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

            pad = JoyCon(
                side,
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
    assert _device_info_address_matches_bumble_local_address(events)
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


class RecordingDeviceInfoResponder(SubcommandResponder):
    """Wrap a responder and record device-info reply bytes for hardware diagnostics."""

    def __init__(self, inner: SubcommandResponder, trace: TextIO, *, side: str) -> None:
        """Create a recording wrapper around an existing subcommand responder."""
        self._inner = inner
        self._trace = trace
        self._side = side

    @property
    def session_state(self) -> SubcommandSessionState:
        """Return the wrapped responder session state."""
        return self._inner.session_state

    def respond(self, output_report: OutputReport, *, state: InputState, timer: int = 0) -> bytes:
        """Return the inner responder reply and emit device-info observations."""
        reply = self._inner.respond(output_report, state=state, timer=timer)
        if output_report.subcommand_id == 0x02:
            self._record_device_info_reply(reply)
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


def _install_device_info_probe(pad: JoyCon, trace: TextIO, *, side: str) -> None:
    dispatcher = pad._output_report_dispatcher
    dispatcher.subcommand_responder = RecordingDeviceInfoResponder(
        dispatcher.subcommand_responder,
        trace,
        side=side,
    )


async def _send_order_buttons(pad: JoyCon, trace: TextIO, *, side: str) -> None:
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


async def _wait_for_report_counter(
    pad: JoyCon,
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


def _device_info_address_matches_bumble_local_address(events: list[dict[str, Any]]) -> bool:
    local_address = None
    device_info_address = None
    for event in events:
        if event.get("event") == "bumble_device_initialized":
            local_address = event.get("local_bluetooth_address")
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
