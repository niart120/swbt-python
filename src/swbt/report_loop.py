"""Input report sender used by SwitchGamepad."""

import asyncio
from collections.abc import Awaitable, Callable
from contextlib import suppress
from inspect import isawaitable
from time import monotonic, monotonic_ns
from typing import cast

from swbt.diagnostics import DiagnosticsRecorder
from swbt.input import InputState
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.session import SwitchHidSession
from swbt.state_store import InputStateStore
from swbt.transport.base import HidDeviceTransport

REPLY_PERIODIC_HOLDOFF_SECONDS = 0.3
ReplyBuilder = Callable[[], bytes | Awaitable[bytes]]


def _user_input_enabled_by_default() -> bool:
    return True


class ReportSender:
    """Serialize input reports and subcommand replies for one HID session."""

    def __init__(
        self,
        *,
        transport: HidDeviceTransport,
        input_report_builder: InputReportBuilder,
        session: SwitchHidSession,
        diagnostics: DiagnosticsRecorder | None = None,
        clock_ns: Callable[[], int] = monotonic_ns,
        monotonic_time: Callable[[], float] = monotonic,
        _sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """Create a session-scoped serialized report sender."""
        self._transport = transport
        self._input_report_builder = input_report_builder
        self._session = session
        self._diagnostics = diagnostics
        self._clock_ns = clock_ns
        self._monotonic_time = monotonic_time
        self._sleep = _sleep
        self._timer = 0
        self._send_lock = asyncio.Lock()
        self._automatic_input_holdoff_until = 0.0

    async def send_input(
        self,
        state: InputState,
        *,
        reason: str = "input",
        commit_state_store: InputStateStore | None = None,
    ) -> None:
        """Send one input state and optionally commit it before releasing the send lock."""
        async with self._send_lock:
            await self._send_input_locked(
                state,
                reason=reason,
                commit_state_store=commit_state_store,
            )

    async def send_current_input(
        self,
        state_store: InputStateStore,
        *,
        reason: str = "input",
    ) -> None:
        """Snapshot and send the current input state under the shared send lock."""
        async with self._send_lock:
            state = await state_store.snapshot()
            await self._send_input_locked(state, reason=reason)

    async def send_automatic_input(self, state: InputState, *, reason: str) -> bool:
        """Send one automatic input unless a recent reply still holds it off."""
        async with self._send_lock:
            if self._is_automatic_input_held_off():
                return False
            await self._send_input_locked(state, reason=reason)
            return True

    async def wait_until_automatic_input_ready(self) -> None:
        """Wait until automatic input is no longer held off by an accepted reply."""
        while True:
            async with self._send_lock:
                remaining = self._automatic_input_holdoff_until - self._monotonic_time()
                if remaining <= 0:
                    return
            await self._sleep(remaining)

    async def send_subcommand_reply(self, build_report: ReplyBuilder) -> bytes:
        """Build and send a subcommand reply under the shared send lock."""
        async with self._send_lock:
            built = build_report()
            if isawaitable(built):
                report = await cast("Awaitable[bytes]", built)
            else:
                report = built
            await self._send_subcommand_report_locked(report)
            self._hold_off_automatic_input_after_reply()
            return report

    async def _send_subcommand_report_locked(self, report: bytes) -> None:
        reply = bytearray(report)
        if reply and reply[0] == 0x21:
            reply[1] = self._timer
        await self._send_report(bytes(reply), reason="subcommand_reply")
        if reply and reply[0] == 0x21:
            self._advance_timer()

    async def _send_input_locked(
        self,
        state: InputState,
        *,
        reason: str,
        commit_state_store: InputStateStore | None = None,
    ) -> None:
        imu_block = self._session.encode_imu(state.imu_frames, now_ns=self._clock_ns())
        report = self._input_report_builder.build_0x30(
            state,
            timer=self._timer,
            imu_block=imu_block,
        )
        await self._send_report(report, reason=reason)
        if commit_state_store is not None:
            await commit_state_store.apply(state)
        self._advance_timer()

    async def _send_report(self, report: bytes, *, reason: str) -> None:
        await self._transport.send_interrupt(report)
        if self._diagnostics is not None:
            self._diagnostics.record_report_tx(report_id=report[0], reason=reason)

    def _advance_timer(self) -> None:
        self._timer = (self._timer + 1) & 0xFF

    def _hold_off_automatic_input_after_reply(self) -> None:
        self._automatic_input_holdoff_until = (
            self._monotonic_time() + REPLY_PERIODIC_HOLDOFF_SECONDS
        )

    def _is_automatic_input_held_off(self) -> bool:
        return self._monotonic_time() < self._automatic_input_holdoff_until


class ReportLoop:
    """Send input reports from the current input state."""

    def __init__(
        self,
        *,
        transport: HidDeviceTransport,
        state_store: InputStateStore,
        input_report_builder: InputReportBuilder,
        session: SwitchHidSession,
        report_period_us: int = 8000,
        diagnostics: DiagnosticsRecorder | None = None,
        clock_ns: Callable[[], int] = monotonic_ns,
        _sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        sender: ReportSender | None = None,
    ) -> None:
        """Create a report loop helper."""
        self._state_store = state_store
        self._report_period_ns = report_period_us * 1_000
        self._clock_ns = clock_ns
        self._sleep = _sleep
        self._sender = sender or ReportSender(
            transport=transport,
            input_report_builder=input_report_builder,
            session=session,
            diagnostics=diagnostics,
            clock_ns=clock_ns,
        )
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        """Start periodic input report transmission."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="swbt-report-loop")

    async def stop(self) -> None:
        """Stop periodic input report transmission."""
        if self._task is None:
            return
        task = self._task
        self._task = None
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def send_current_input(self, *, reason: str = "input") -> None:
        """Send one 0x30 input report for the current state."""
        await self._sender.send_current_input(self._state_store, reason=reason)

    async def send_subcommand_reply(self, build_report: ReplyBuilder) -> bytes:
        """Apply a subcommand transition and send its reply under the send lock."""
        return await self._sender.send_subcommand_reply(build_report)

    async def send_next_report(self) -> None:
        """Send current periodic input unless a recent reply holds it off."""
        state = await self._state_store.snapshot()
        await self._sender.send_automatic_input(state, reason="periodic")

    async def _run(self) -> None:
        next_deadline_ns = self._clock_ns() + self._report_period_ns
        while True:
            while (remaining_ns := next_deadline_ns - self._clock_ns()) > 0:
                await self._sleep(remaining_ns / 1_000_000_000)
            await self.send_next_report()
            next_deadline_ns += self._report_period_ns
            now_ns = self._clock_ns()
            if next_deadline_ns < now_ns:
                elapsed_periods = (
                    now_ns - next_deadline_ns + self._report_period_ns - 1
                ) // self._report_period_ns
                next_deadline_ns += elapsed_periods * self._report_period_ns
