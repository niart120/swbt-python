import asyncio
import inspect

from swbt.input import Button, IMUFrame, InputState
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


def test_imu_mode_transition_and_ack_share_periodic_send_lock() -> None:
    class BlockingStateStore(InputStateStore):
        def __init__(self) -> None:
            super().__init__(InputState.neutral().with_imu(IMUFrame.accel(z=4096)))
            self.snapshot_entered = asyncio.Event()
            self.release_snapshot = asyncio.Event()
            self._block_next_snapshot = True

        async def snapshot(self) -> InputState:
            if self._block_next_snapshot:
                self._block_next_snapshot = False
                self.snapshot_entered.set()
                await self.release_snapshot.wait()
            return await super().snapshot()

    async def run() -> None:
        transport = FakeHidTransport()
        await transport.open()
        profile = default_controller_profile()
        state_store = BlockingStateStore()
        session = SwitchHidSession(profile)
        report_loop = ReportLoop(
            transport=transport,
            state_store=state_store,
            input_report_builder=InputReportBuilder(profile),
            session=session,
        )

        periodic = asyncio.create_task(report_loop.send_current_input())
        await state_store.snapshot_entered.wait()

        def enable_quaternion_and_build_ack() -> bytes:
            session.set_imu_mode(0x02)
            reply = bytearray(50)
            reply[0] = 0x21
            reply[14] = 0x40
            return bytes(reply)

        ack = asyncio.create_task(
            report_loop.send_subcommand_reply(enable_quaternion_and_build_ack)
        )
        await asyncio.sleep(0)
        state_store.release_snapshot.set()
        await periodic
        await ack
        await report_loop.send_current_input()

        reports = transport.sent_interrupt_reports
        assert reports[0][0] == 0x30
        assert reports[0][13:49] == bytes(36)
        assert reports[1][0] == 0x21
        assert reports[1][14] == 0x40
        assert reports[2][0] == 0x30
        assert reports[2][19] & 0x0F == 0x0E

    asyncio.run(run())


def test_periodic_loop_waits_for_slow_send_and_uses_latest_state_after_release() -> None:
    class BlockingFakeHidTransport(FakeHidTransport):
        def __init__(self) -> None:
            super().__init__()
            self.first_send_started = asyncio.Event()
            self.release_first_send = asyncio.Event()
            self.send_attempts = 0

        async def send_interrupt(self, payload: bytes) -> None:
            self.send_attempts += 1
            if self.send_attempts == 1:
                self.first_send_started.set()
                await self.release_first_send.wait()
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = BlockingFakeHidTransport()
        await transport.open()
        profile = default_controller_profile()
        state_store = InputStateStore()
        report_loop = ReportLoop(
            transport=transport,
            state_store=state_store,
            input_report_builder=InputReportBuilder(profile),
            session=SwitchHidSession(profile),
            report_period_us=1_000,
        )

        report_loop.start()
        await transport.first_send_started.wait()
        await asyncio.sleep(0.01)

        assert transport.send_attempts == 1

        await state_store.apply(InputState.neutral().with_buttons([Button.X]))
        transport.release_first_send.set()
        reports = await transport.wait_for_interrupt_report_count(2)
        await report_loop.stop()

        assert reports[0][3:6] == bytes.fromhex("00 00 00")
        assert reports[1][3:6] == bytes.fromhex("02 00 00")

    asyncio.run(run())
