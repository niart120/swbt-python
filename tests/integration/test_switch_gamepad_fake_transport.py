import asyncio
import json
from io import StringIO

import pytest

from swbt import Button, DiagnosticsConfig, InputState, SwitchGamepad
from swbt.errors import ConnectionTimeoutError
from swbt.transport.fake import FakeHidTransport


def test_async_context_opens_and_closes_fake_transport() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        assert transport.is_open is False

        async with SwitchGamepad(transport=transport):
            assert transport.is_open is True
            assert transport.open_count == 1
            assert transport.close_count == 0

        assert transport.is_open is False
        assert transport.open_count == 1
        assert transport.close_count == 1
        assert transport.events == ("open", "start_advertising", "close")

    asyncio.run(run())


def test_press_buttons_are_reflected_in_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await pad.press(Button.L, Button.R)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[0] == 0x30
            assert report[3:6] == bytes.fromhex("40 00 40")

    asyncio.run(run())


def test_release_buttons_clears_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)

            await pad.press(Button.L, Button.R)
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("40 00 40")

            await pad.release(Button.L, Button.R)
            released_count = len(transport.sent_interrupt_reports)
            released_reports = await transport.wait_for_interrupt_report_count(released_count + 1)
            assert released_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_set_input_updates_snapshot_and_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        state = InputState.neutral().with_buttons([Button.X])

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await pad.set_input(state)

            assert pad.snapshot() == state

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            assert reports[-1][3:6] == bytes.fromhex("02 00 00")

    asyncio.run(run())


def test_neutral_updates_snapshot_and_clears_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pressed = InputState.neutral().with_buttons([Button.A])

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await pad.set_input(pressed)
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("08 00 00")

            await pad.neutral()
            assert pad.snapshot() == InputState.neutral()

            neutral_count = len(transport.sent_interrupt_reports)
            neutral_reports = await transport.wait_for_interrupt_report_count(neutral_count + 1)
            assert neutral_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_output_report_injection_sends_subcommand_reply() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)

            await transport.inject_interrupt_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02

    asyncio.run(run())


def test_control_output_report_injection_sends_subcommand_reply() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)

            await transport.inject_control_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02

    asyncio.run(run())


def test_subcommand_reply_queue_takes_priority_over_periodic_input() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with SwitchGamepad(transport=transport, report_period_us=100_000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)

            start_count = len(transport.sent_interrupt_reports)
            await transport.inject_interrupt_data(request_device_info)
            reports = await transport.wait_for_interrupt_report_count(start_count + 2)

            assert reports[start_count][0] == 0x21
            assert reports[start_count + 1][0] == 0x30

    asyncio.run(run())


def test_report_tx_counter_distinguishes_0x21_and_0x30() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with SwitchGamepad(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=1000,
        ) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await pad.press(Button.A)
            await transport.wait_for_interrupt_report_id(0x30)

            await transport.inject_interrupt_data(request_device_info)
            await transport.wait_for_interrupt_report_id(0x21)

        report_events = [
            json.loads(line)
            for line in trace.getvalue().splitlines()
            if json.loads(line)["event"] == "report_tx"
        ]

        assert {
            "event": "report_tx",
            "counter": 1,
            "reason": "periodic",
            "report_id": "0x30",
        } in report_events
        assert {
            "event": "report_tx",
            "counter": 1,
            "reason": "subcommand_reply",
            "report_id": "0x21",
        } in report_events

    asyncio.run(run())


def test_output_report_rx_and_subcommand_rx_share_packet_id() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 12 00 00 00 00 00 00 00 00 02")

        async with SwitchGamepad(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=1000,
        ) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await transport.inject_interrupt_data(request_device_info)
            await transport.wait_for_interrupt_report_id(0x21)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "output_report_rx",
            "length": 11,
            "packet_id": 0x12,
            "report_id": "0x01",
            "subcommand_id": "0x02",
        } in events
        assert {
            "event": "subcommand_rx",
            "packet_id": 0x12,
            "subcommand_id": "0x02",
        } in events
        assert {
            "event": "subcommand_reply_tx",
            "packet_id": 0x12,
            "report_id": "0x21",
            "subcommand_id": "0x02",
        } in events

    asyncio.run(run())


def test_status_returns_report_counters_last_subcommand_and_raw_rumble() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 2a 10 11 12 13 14 15 16 17 02")

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await pad.tap(Button.A, duration=0)

            await transport.inject_interrupt_data(request_device_info)
            await transport.wait_for_interrupt_report_id(0x21)

            status = pad.status()

            assert status.report_counters == {0x30: 2, 0x21: 1}
            assert status.last_subcommand_id == 0x02
            assert status.raw_rumble == bytes.fromhex("10 11 12 13 14 15 16 17")

    asyncio.run(run())


def test_close_with_neutral_records_trailing_neutral_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = SwitchGamepad(transport=transport, report_period_us=100_000)

        await pad.open()
        await transport.connect()
        await pad.wait_connected(timeout=1.0)
        await pad.press(Button.A)
        await pad.close(neutral=True)

        assert transport.is_open is False
        assert transport.sent_interrupt_reports[-1][0] == 0x30
        assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_fake_l2cap_channels_must_both_open_before_wait_connected_completes() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport) as pad:
            connected = asyncio.create_task(pad.wait_connected(timeout=1.0))
            await asyncio.sleep(0)

            await transport.open_l2cap_channel("control")
            await asyncio.sleep(0)

            assert connected.done() is False

            await transport.open_l2cap_channel("interrupt")
            await asyncio.wait_for(connected, timeout=0.1)

            assert transport.events == (
                "open",
                "start_advertising",
                "l2cap_control_open",
                "l2cap_interrupt_open",
                "connected",
            )

    asyncio.run(run())


def test_disconnect_callback_neutralizes_state_and_stops_report_loop() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)
            await pad.press(Button.A)
            await transport.wait_for_interrupt_report_id(0x30)

            await transport.disconnect(reason=0x13)

            report_count = len(transport.sent_interrupt_reports)
            await asyncio.sleep(0.01)

            assert pad.snapshot() == InputState.neutral()
            assert pad.status().connection_state == "closed"
            assert transport.is_open is False
            assert transport.close_count == 1
            assert len(transport.sent_interrupt_reports) == report_count

    asyncio.run(run())


def test_wait_connected_timeout_records_failure_position_in_trace() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()

        async with SwitchGamepad(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            with pytest.raises(ConnectionTimeoutError):
                await pad.wait_connected(timeout=0.001)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "connection_timeout",
            "state": "advertising",
            "timeout": 0.001,
        } in events

    asyncio.run(run())


def test_concurrent_press_and_release_preserve_button_state() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport, report_period_us=1000) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)

            await asyncio.gather(
                pad.press(Button.L),
                pad.press(Button.R),
                pad.press(Button.L, Button.R),
            )
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("40 00 40")

            await asyncio.gather(
                pad.release(Button.L),
                pad.release(Button.R),
                pad.release(Button.L, Button.R),
            )
            released_count = len(transport.sent_interrupt_reports)
            released_reports = await transport.wait_for_interrupt_report_count(released_count + 1)
            assert released_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_callback_exception_is_recorded_and_close_cleans_up() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        unsupported_subcommand = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 ff")
        pad = SwitchGamepad(transport=transport)

        await pad.open()
        await transport.connect()
        await pad.wait_connected(timeout=1.0)

        await transport.inject_interrupt_data(unsupported_subcommand)
        status = pad.status()

        assert status.connection_state == "failed"
        assert status.last_error is not None
        assert status.last_error.event == "error"
        assert status.last_error.error_type == "UnsupportedSubcommandError"

        await pad.close()
        assert transport.is_open is False

    asyncio.run(run())


def test_callback_exception_is_recorded_in_trace_and_status() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        unsupported_subcommand = bytes.fromhex("01 2a 00 00 00 00 00 00 00 00 ff 01 02")
        pad = SwitchGamepad(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        )

        await pad.open()
        await transport.connect()
        await pad.wait_connected(timeout=1.0)

        await transport.inject_interrupt_data(unsupported_subcommand)

        status = pad.status()
        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert status.connection_state == "failed"
        assert status.last_error is not None
        assert status.last_error.error_type == "UnsupportedSubcommandError"
        assert {
            "event": "unsupported_subcommand",
            "packet_id": 0x2A,
            "payload": "0102",
            "subcommand_id": "0xff",
        } in events
        assert {
            "event": "error",
            "error_type": "UnsupportedSubcommandError",
            "message": "unsupported subcommand: 0xff",
            "recoverable": False,
        } in events

        await pad.close()

    asyncio.run(run())


def test_tap_button_a_records_press_and_release_reports() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport) as pad:
            await transport.connect()
            await pad.wait_connected(timeout=1.0)

            await pad.tap(Button.A, duration=0)

            assert len(transport.sent_interrupt_reports) == 2
            pressed, released = transport.sent_interrupt_reports
            assert pressed[0] == 0x30
            assert pressed[3:6] == bytes.fromhex("08 00 00")
            assert released[0] == 0x30
            assert released[3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_wait_connected_completes_after_fake_connected_callback() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport) as pad:
            connected = asyncio.create_task(pad.wait_connected(timeout=1.0))
            await asyncio.sleep(0)

            assert connected.done() is False

            await transport.connect()
            await asyncio.wait_for(connected, timeout=0.1)

            assert transport.events == ("open", "start_advertising", "connected")

    asyncio.run(run())


def test_wait_connected_timeout_raises_connection_timeout_error() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport) as pad:
            with pytest.raises(ConnectionTimeoutError):
                await pad.wait_connected(timeout=0.001)

    asyncio.run(run())
