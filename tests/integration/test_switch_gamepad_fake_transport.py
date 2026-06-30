import asyncio

from swbt import Button, SwitchGamepad
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
        assert transport.events == ("open", "close")

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

            assert transport.events == ("open", "connected")

    asyncio.run(run())
