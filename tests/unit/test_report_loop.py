import asyncio

from swbt.report_loop import ReportLoop
from swbt.state_store import InputStateStore
from swbt.transport.fake import FakeHidTransport


def test_subcommand_reply_uses_shared_timer_sequence() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        report_loop = ReportLoop(
            transport=transport,
            state_store=InputStateStore(),
        )
        reply = bytearray(50)
        reply[0] = 0x21
        reply[1] = 0xAA

        await report_loop.send_current_input()
        report_loop.queue_reply(bytes(reply))
        await report_loop.send_next_report()
        await report_loop.send_current_input()

        reports = transport.sent_interrupt_reports

        assert reports[0][0:2] == bytes.fromhex("30 00")
        assert reports[1][0:2] == bytes.fromhex("21 01")
        assert reports[2][0:2] == bytes.fromhex("30 02")

    asyncio.run(run())


def test_subcommand_reply_holds_off_following_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        report_loop = ReportLoop(
            transport=transport,
            state_store=InputStateStore(),
        )
        reply = bytes([0x21, *([0] * 49)])

        report_loop.queue_reply(reply)
        await report_loop.send_next_report()
        report_count_after_reply = len(transport.sent_interrupt_reports)

        await report_loop.send_next_report()

        assert len(transport.sent_interrupt_reports) == report_count_after_reply

    asyncio.run(run())
