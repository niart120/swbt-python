import asyncio

from swbt.gamepad.protocol_handshake import ProtocolHandshake
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.protocol.session import SwitchHidSession
from swbt.report_loop import ReportSender
from swbt.transport.fake import FakeHidTransport


def test_handshake_sends_neutral_immediately_after_start() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        profile = default_controller_profile()
        session = SwitchHidSession(profile)
        sender = ReportSender(
            transport=transport,
            input_report_builder=InputReportBuilder(profile),
            session=session,
        )
        handshake = ProtocolHandshake(
            sender=sender,
            session=session,
            report_period_us=8_000,
            on_outcome=lambda _outcome: None,
        )

        handshake.start()
        report = await transport.wait_for_interrupt_report_id(0x30)
        await handshake.stop()

        assert report[3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_handshake_switches_to_report_period_neutral_after_supported_mode() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        profile = default_controller_profile()
        session = SwitchHidSession(profile)
        sender = ReportSender(
            transport=transport,
            input_report_builder=InputReportBuilder(profile),
            session=session,
        )
        handshake = ProtocolHandshake(
            sender=sender,
            session=session,
            report_period_us=1_000,
            bootstrap_retry_seconds=10.0,
            on_outcome=lambda _outcome: None,
        )

        handshake.start()
        await transport.wait_for_interrupt_report_id(0x30)
        transport.clear_sent_interrupt_reports()
        handshake.subcommand_received(0x03)
        session.set_report_mode(0x30, supported=True)
        handshake.protocol_state_updated()

        report = await transport.wait_for_interrupt_report_id(0x30)
        await handshake.stop()

        assert report[3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_handshake_publishes_ready_only_after_its_task_is_collected() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        profile = default_controller_profile()
        session = SwitchHidSession(profile)
        sender = ReportSender(
            transport=transport,
            input_report_builder=InputReportBuilder(profile),
            session=session,
        )
        outcomes = []
        handshake = ProtocolHandshake(
            sender=sender,
            session=session,
            report_period_us=8_000,
            on_outcome=outcomes.append,
        )

        handshake.start()
        await transport.wait_for_interrupt_report_id(0x30)
        await handshake.complete_ready()

        assert handshake._task is not None
        assert handshake._task.done()
        assert [outcome.state for outcome in outcomes] == ["ready"]

    asyncio.run(run())


def test_handshake_sender_failure_publishes_failed_outcome_without_task_leak() -> None:
    class SendError(RuntimeError):
        pass

    class FailingTransport(FakeHidTransport):
        async def send_interrupt(self, payload: bytes) -> None:
            _ = payload
            raise SendError

    async def run() -> None:
        transport = FailingTransport()
        await transport.open()
        profile = default_controller_profile()
        session = SwitchHidSession(profile)
        sender = ReportSender(
            transport=transport,
            input_report_builder=InputReportBuilder(profile),
            session=session,
        )
        outcomes = []
        handshake = ProtocolHandshake(
            sender=sender,
            session=session,
            report_period_us=8_000,
            on_outcome=outcomes.append,
        )

        handshake.start()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert handshake._task is not None
        assert handshake._task.done()
        assert outcomes[0].state == "failed"
        assert isinstance(outcomes[0].error, SendError)

    asyncio.run(run())
