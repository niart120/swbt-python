import asyncio
import json
import sys
from pathlib import Path
from typing import Any, TextIO

import pytest

from swbt import ControllerColors, DiagnosticsConfig, InputState, ProController
from swbt.protocol.output_report import OutputReport
from swbt.protocol.subcommand import SubcommandResponder

_CONTROLLER_COLOR_ADDRESS = 0x6050
_CONTROLLER_COLOR_SIZE = 12
_CONTROLLER_COLOR_TAIL_ADDRESS = _CONTROLLER_COLOR_ADDRESS + _CONTROLLER_COLOR_SIZE
_FACTORY_SENSOR_CALIBRATION_ADDRESS = 0x6020
_FACTORY_SENSOR_CALIBRATION_BYTES = bytes.fromhex(
    "00 00 00 00 00 00 00 40 00 40 00 40 00 00 00 00 00 00 3b 34 3b 34 3b 34"
)
_DEFAULT_DEVICE_INFO_DATA = bytes.fromhex("04 00 03 02 00 00 00 00 00 00 03 02")
_DEVICE_INFO_DATA_TAIL_0101 = bytes.fromhex("04 00 03 02 00 00 00 00 00 00 01 01")
_DEVICE_INFO_SIZE = 12
_DIAGNOSTIC_CONTROLLER_COLORS = ControllerColors(
    body=0xFF0000,
    buttons=0x0000FF,
    left_grip=0xFF00FF,
    right_grip=0xFF8000,
)
_UI_OBSERVATION_HOLD_SECONDS = 30.0


@pytest.mark.hardware
def test_switch_reads_sentinel_controller_color_profile(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Record a custom controller color SPI reply during a real Switch handshake.

    A pytest pass proves that the Switch requested a SPI range covering the
    controller color block and that swbt-python replied with the configured 12
    bytes. Human-visible Switch UI color reflection must still be recorded in
    spec/hardware-test-log.md.
    """
    expected_colors = _DIAGNOSTIC_CONTROLLER_COLORS
    expected_color_bytes = expected_colors.to_spi_bytes()
    trace_path = swbt_hardware_artifact_dir / "controller-colors-sentinel.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_controller_color_checkpoint",
                body_color=_format_rgb(expected_colors.body),
                buttons_color=_format_rgb(expected_colors.buttons),
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_switch_screen="controller_search_or_change_grip_order",
                left_grip_color=_format_rgb(expected_colors.left_grip),
                operation="operator_prepare_sentinel_color_observation",
                right_grip_color=_format_rgb(expected_colors.right_grip),
                wait_seconds=_UI_OBSERVATION_HOLD_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: sentinel controller color observation; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"holding {_UI_OBSERVATION_HOLD_SECONDS:.0f}s after SPI reply\n"
            )
            sys.stderr.flush()

            pad = ProController(
                adapter=swbt_bumble_adapter,
                controller_colors=expected_colors,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_spi_probe(
                pad,
                trace,
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_controller_color_cleanup",
                    connection_state=pad.status().connection_state,
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected")
    assert _contains_event(
        events, "device_info_reply", device_info_data=_DEFAULT_DEVICE_INFO_DATA.hex()
    )
    assert _contains_event(events, "subcommand_reply_tx", subcommand_id="0x10")
    assert _contains_event(
        events,
        "factory_sensor_calibration_spi_reply",
        calibration_bytes=_FACTORY_SENSOR_CALIBRATION_BYTES.hex(),
        matches_expected_calibration=True,
    )
    assert _contains_event(events, "report_tx", report_id="0x21", reason="subcommand_reply")
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        matches_expected_controller_colors=True,
    )
    assert _contains_event(
        events,
        "manual_controller_color_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
    )
    assert _contains_event(
        events,
        "manual_controller_color_cleanup",
        connection_state="closed",
    )
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_reads_sentinel_controller_color_profile_with_zero_tail_byte(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Record the old 0x01/0x01 profile while returning 0x00 after the color block."""
    expected_colors = _DIAGNOSTIC_CONTROLLER_COLORS
    expected_color_bytes = expected_colors.to_spi_bytes()
    trace_path = swbt_hardware_artifact_dir / "controller-colors-sentinel-zero-tail.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_controller_color_checkpoint",
                body_color=_format_rgb(expected_colors.body),
                buttons_color=_format_rgb(expected_colors.buttons),
                controller_color_tail_byte="0x00",
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_switch_screen="controller_search_or_change_grip_order",
                left_grip_color=_format_rgb(expected_colors.left_grip),
                operation="operator_prepare_sentinel_color_observation_with_zero_tail",
                right_grip_color=_format_rgb(expected_colors.right_grip),
                wait_seconds=_UI_OBSERVATION_HOLD_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: sentinel controller color observation with "
                "controller_color_tail_byte=0x00; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"holding {_UI_OBSERVATION_HOLD_SECONDS:.0f}s after SPI reply\n"
            )
            sys.stderr.flush()

            pad = ProController(
                adapter=swbt_bumble_adapter,
                controller_colors=expected_colors,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_spi_probe(
                pad,
                trace,
                controller_color_tail_byte=0x00,
                device_info_data=_DEVICE_INFO_DATA_TAIL_0101,
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_controller_color_cleanup",
                    connection_state=pad.status().connection_state,
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected")
    assert _contains_event(
        events, "device_info_reply", device_info_data=_DEVICE_INFO_DATA_TAIL_0101.hex()
    )
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        controller_color_tail_byte="0x00",
        matches_expected_controller_colors=True,
    )
    assert _contains_event(
        events,
        "manual_controller_color_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
    )
    assert _contains_event(
        events,
        "manual_controller_color_cleanup",
        connection_state="closed",
    )
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_reads_sentinel_controller_color_profile_with_device_info_address(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
    swbt_device_info_address: bytes,
) -> None:
    """Record the old 0x01/0x01 profile while sending a non-zero device-info address."""
    expected_colors = _DIAGNOSTIC_CONTROLLER_COLORS
    expected_color_bytes = expected_colors.to_spi_bytes()
    expected_address_hex = swbt_device_info_address.hex()
    device_info_data = (
        bytes.fromhex("04 00 03 02") + swbt_device_info_address + bytes.fromhex("01 01")
    )
    trace_path = swbt_hardware_artifact_dir / "controller-colors-sentinel-device-info-address.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_controller_color_checkpoint",
                body_color=_format_rgb(expected_colors.body),
                buttons_color=_format_rgb(expected_colors.buttons),
                device_info_data=device_info_data.hex(),
                device_info_address=expected_address_hex,
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_switch_screen="controller_search_or_change_grip_order",
                left_grip_color=_format_rgb(expected_colors.left_grip),
                operation="operator_prepare_sentinel_color_observation_with_device_info_address",
                right_grip_color=_format_rgb(expected_colors.right_grip),
                wait_seconds=_UI_OBSERVATION_HOLD_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: sentinel controller color observation with "
                f"device_info_address={expected_address_hex}; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"holding {_UI_OBSERVATION_HOLD_SECONDS:.0f}s after SPI reply\n"
            )
            sys.stderr.flush()

            pad = ProController(
                adapter=swbt_bumble_adapter,
                controller_colors=expected_colors,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_spi_probe(
                pad,
                trace,
                device_info_data=device_info_data,
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_controller_color_cleanup",
                    connection_state=pad.status().connection_state,
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected")
    assert _contains_event(
        events,
        "device_info_reply",
        device_info_data=device_info_data.hex(),
        profile_bluetooth_address_bytes=expected_address_hex,
    )
    assert _contains_event(events, "subcommand_reply_tx", subcommand_id="0x10")
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        matches_expected_controller_colors=True,
    )
    assert _contains_event(
        events,
        "manual_controller_color_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
    )
    assert _contains_event(
        events,
        "manual_controller_color_cleanup",
        connection_state="closed",
    )
    assert not _contains_event(events, "error")


@pytest.mark.hardware
def test_switch_reads_sentinel_controller_color_profile_with_device_info_tail_0x03_0x02(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
    swbt_device_info_address: bytes,
) -> None:
    """Record the sentinel profile while using the 0x03/0x02 device-info tail variant."""
    expected_colors = _DIAGNOSTIC_CONTROLLER_COLORS
    expected_color_bytes = expected_colors.to_spi_bytes()
    device_info_data = (
        bytes.fromhex("04 00 03 02") + swbt_device_info_address + bytes.fromhex("03 02")
    )
    trace_path = (
        swbt_hardware_artifact_dir / "controller-colors-sentinel-device-info-tail-0302.jsonl"
    )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            _record_probe_event(
                trace,
                "manual_controller_color_checkpoint",
                body_color=_format_rgb(expected_colors.body),
                buttons_color=_format_rgb(expected_colors.buttons),
                device_info_data=device_info_data.hex(),
                expected_controller_color_bytes=expected_color_bytes.hex(),
                expected_switch_screen="controller_search_or_change_grip_order",
                left_grip_color=_format_rgb(expected_colors.left_grip),
                operation="operator_prepare_sentinel_color_observation_with_device_info_tail_0302",
                right_grip_color=_format_rgb(expected_colors.right_grip),
                wait_seconds=_UI_OBSERVATION_HOLD_SECONDS,
            )
            sys.stderr.write(
                "SWBT hardware: sentinel controller color observation with "
                f"device_info_data={device_info_data.hex()}; "
                "expected_switch_screen=controller_search_or_change_grip_order; "
                f"holding {_UI_OBSERVATION_HOLD_SECONDS:.0f}s after SPI reply\n"
            )
            sys.stderr.flush()

            pad = ProController(
                adapter=swbt_bumble_adapter,
                controller_colors=expected_colors,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            _install_spi_probe(
                pad,
                trace,
                device_info_data=device_info_data,
                expected_controller_color_bytes=expected_color_bytes,
            )
            try:
                await pad.connect(timeout=60.0, allow_pairing=True)
                await _wait_for_controller_color_spi_reply(
                    trace_path,
                    expected_controller_color_bytes=expected_color_bytes,
                    timeout_seconds=25.0,
                )
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    operation="controller_color_spi_reply_observed",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
                await asyncio.sleep(_UI_OBSERVATION_HOLD_SECONDS)
                _record_probe_event(
                    trace,
                    "manual_controller_color_checkpoint",
                    hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
                    operation="ui_observation_hold_complete",
                    report_0x21_count=pad.status().report_counters.get(0x21, 0),
                    report_0x30_count=pad.status().report_counters.get(0x30, 0),
                )
            finally:
                await pad.close(neutral=True)
                _record_probe_event(
                    trace,
                    "manual_controller_color_cleanup",
                    connection_state=pad.status().connection_state,
                )

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "connected")
    assert _contains_event(
        events,
        "device_info_reply",
        device_info_data=device_info_data.hex(),
    )
    assert _contains_event(events, "subcommand_reply_tx", subcommand_id="0x10")
    assert _contains_event(
        events,
        "controller_color_spi_reply",
        controller_color_bytes=expected_color_bytes.hex(),
        matches_expected_controller_colors=True,
    )
    assert _contains_event(
        events,
        "manual_controller_color_checkpoint",
        operation="ui_observation_hold_complete",
        hold_seconds=_UI_OBSERVATION_HOLD_SECONDS,
    )
    assert _contains_event(
        events,
        "manual_controller_color_cleanup",
        connection_state="closed",
    )
    assert not _contains_event(events, "error")


class RecordingSubcommandResponder(SubcommandResponder):
    """Wrap a responder and record SPI read reply bytes for hardware diagnostics."""

    def __init__(
        self,
        inner: SubcommandResponder,
        trace: TextIO,
        *,
        controller_color_tail_byte: int | None = None,
        device_info_bluetooth_address: bytes | None = None,
        device_info_data: bytes | None = None,
        expected_controller_color_bytes: bytes,
    ) -> None:
        """Create a recording wrapper around an existing subcommand responder."""
        self._inner = inner
        self._trace = trace
        self._controller_color_tail_byte = controller_color_tail_byte
        self._device_info_bluetooth_address = device_info_bluetooth_address
        self._device_info_data = device_info_data
        self._expected_controller_color_bytes = expected_controller_color_bytes

    def respond(self, output_report: OutputReport, *, state: InputState, timer: int = 0) -> bytes:
        """Return the inner responder reply and emit SPI read observations."""
        reply = self._inner.respond(output_report, state=state, timer=timer)
        if output_report.subcommand_id == 0x02:
            reply = self._with_device_info_data(reply)
            reply = self._with_device_info_bluetooth_address(reply)
            self._record_device_info_reply(reply)
        if output_report.subcommand_id == 0x10:
            reply = self._with_controller_color_tail_byte(output_report.subcommand_payload, reply)
            self._record_spi_reply(output_report.subcommand_payload, reply)
        return reply

    def _with_device_info_bluetooth_address(self, reply: bytes) -> bytes:
        if self._device_info_bluetooth_address is None:
            return reply
        updated = bytearray(reply)
        updated[19:25] = self._device_info_bluetooth_address
        return bytes(updated)

    def _with_device_info_data(self, reply: bytes) -> bytes:
        if self._device_info_data is None:
            return reply
        updated = bytearray(reply)
        updated[15 : 15 + _DEVICE_INFO_SIZE] = self._device_info_data
        return bytes(updated)

    def _with_controller_color_tail_byte(self, payload: bytes, reply: bytes) -> bytes:
        if self._controller_color_tail_byte is None or len(payload) < 5:
            return reply
        address = int.from_bytes(payload[0:4], "little")
        size = payload[4]
        tail_offset = _CONTROLLER_COLOR_TAIL_ADDRESS - address
        if tail_offset < 0 or tail_offset >= size:
            return reply
        updated = bytearray(reply)
        updated[20 + tail_offset] = self._controller_color_tail_byte
        return bytes(updated)

    def _record_device_info_reply(self, reply: bytes) -> None:
        device_info = reply[15 : 15 + _DEVICE_INFO_SIZE]
        fields: dict[str, object] = {
            "controller_type": _format_optional_byte(device_info, 2),
            "device_info_data": device_info.hex(),
            "device_info_tail_byte_0": _format_optional_byte(device_info, 10),
            "device_info_tail_byte_1": _format_optional_byte(device_info, 11),
            "profile_bluetooth_address_bytes": device_info[4:10].hex(),
            "tail_bytes": device_info[10:12].hex(),
        }
        _record_probe_event(self._trace, "device_info_reply", **fields)

    def _record_spi_reply(self, payload: bytes, reply: bytes) -> None:
        if len(payload) < 5:
            return

        address = int.from_bytes(payload[0:4], "little")
        size = payload[4]
        read_data = reply[20 : 20 + size]
        fields: dict[str, object] = {
            "address": f"0x{address:06x}",
            "read_data": read_data.hex(),
            "request_prefix": payload[:5].hex(),
            "size": size,
        }
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
                size=size,
            )
        color_offset = _CONTROLLER_COLOR_ADDRESS - address
        if color_offset >= 0 and color_offset + _CONTROLLER_COLOR_SIZE <= len(read_data):
            controller_color_bytes = read_data[color_offset : color_offset + _CONTROLLER_COLOR_SIZE]
            fields.update(
                {
                    "controller_color_bytes": controller_color_bytes.hex(),
                    "matches_expected_controller_colors": (
                        controller_color_bytes == self._expected_controller_color_bytes
                    ),
                }
            )
        tail_offset = _CONTROLLER_COLOR_TAIL_ADDRESS - address
        if 0 <= tail_offset < len(read_data):
            fields["controller_color_tail_byte"] = f"0x{read_data[tail_offset]:02x}"
        _record_probe_event(self._trace, "controller_color_spi_reply", **fields)


def _install_spi_probe(
    pad: ProController,
    trace: TextIO,
    *,
    controller_color_tail_byte: int | None = None,
    device_info_bluetooth_address: bytes | None = None,
    device_info_data: bytes | None = None,
    expected_controller_color_bytes: bytes,
) -> None:
    dispatcher = pad._output_report_dispatcher
    dispatcher.subcommand_responder = RecordingSubcommandResponder(
        dispatcher.subcommand_responder,
        trace,
        controller_color_tail_byte=controller_color_tail_byte,
        device_info_bluetooth_address=device_info_bluetooth_address,
        device_info_data=device_info_data,
        expected_controller_color_bytes=expected_controller_color_bytes,
    )


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


def _format_rgb(value: int) -> str:
    return f"0x{value:06x}"


def _format_optional_byte(data: bytes, index: int) -> str | None:
    if index >= len(data):
        return None
    return f"0x{data[index]:02x}"
