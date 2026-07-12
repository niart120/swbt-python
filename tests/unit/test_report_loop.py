import asyncio
import inspect

from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.protocol.session import SwitchHidSession
from swbt.report_loop import ReportLoop
from swbt.state_store import InputStateStore
from swbt.transport.fake import FakeHidTransport


def test_report_loop_requires_injected_input_report_builder() -> None:
    signature = inspect.signature(ReportLoop)

    assert signature.parameters["input_report_builder"].default is inspect.Parameter.empty


def test_subcommand_reply_uses_shared_timer_sequence() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        profile = default_controller_profile()
        report_loop = ReportLoop(
            transport=transport,
            state_store=InputStateStore(),
            input_report_builder=InputReportBuilder(profile),
            session=SwitchHidSession(profile),
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
        profile = default_controller_profile()
        report_loop = ReportLoop(
            transport=transport,
            state_store=InputStateStore(),
            input_report_builder=InputReportBuilder(profile),
            session=SwitchHidSession(profile),
        )
        reply = bytes([0x21, *([0] * 49)])

        report_loop.queue_reply(reply)
        await report_loop.send_next_report()
        report_count_after_reply = len(transport.sent_interrupt_reports)

        await report_loop.send_next_report()

        assert len(transport.sent_interrupt_reports) == report_count_after_reply

    asyncio.run(run())
