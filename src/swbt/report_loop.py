"""Input report sender used by SwitchGamepad."""

import asyncio
from collections import deque
from contextlib import suppress

from swbt.diagnostics import DiagnosticsRecorder
from swbt.protocol.input_report import InputReportBuilder
from swbt.state_store import InputStateStore
from swbt.transport.base import HidDeviceTransport

REPLY_PERIODIC_HOLDOFF_SECONDS = 0.3


class ReportLoop:
    """Send input reports from the current input state."""

    def __init__(
        self,
        *,
        transport: HidDeviceTransport,
        state_store: InputStateStore,
        input_report_builder: InputReportBuilder,
        report_period_us: int = 8000,
        diagnostics: DiagnosticsRecorder | None = None,
    ) -> None:
        """Create a report loop helper."""
        self._transport = transport
        self._state_store = state_store
        self._report_period_seconds = report_period_us / 1_000_000
        self._input_report_builder = input_report_builder
        self._diagnostics = diagnostics
        self._reply_queue: deque[bytes] = deque()
        self._timer = 0
        self._periodic_holdoff_until = 0.0
        self._send_lock = asyncio.Lock()
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
        async with self._send_lock:
            await self._send_current_input_locked(reason=reason)

    async def send_subcommand_reply(self, report: bytes) -> None:
        """Send one 0x21 subcommand reply with the shared report timer."""
        async with self._send_lock:
            await self._send_subcommand_reply_locked(report)
            self._holdoff_periodic_after_reply()

    def queue_reply(self, report: bytes) -> None:
        """Queue one subcommand reply for priority transmission."""
        self._reply_queue.append(bytes(report))

    async def send_next_report(self) -> None:
        """Send the next queued reply or current input report."""
        async with self._send_lock:
            if self._reply_queue:
                await self._send_subcommand_reply_locked(self._reply_queue.popleft())
                self._holdoff_periodic_after_reply()
                return
            if self._is_periodic_held_off():
                return
            await self._send_current_input_locked(reason="periodic")

    async def _send_current_input_locked(self, *, reason: str) -> None:
        state = await self._state_store.snapshot()
        report = self._input_report_builder.build_0x30(state, timer=self._timer)
        await self._send_report(report, reason=reason)
        self._advance_timer()

    async def _send_subcommand_reply_locked(self, report: bytes) -> None:
        reply = bytearray(report)
        if reply and reply[0] == 0x21:
            reply[1] = self._timer
        await self._send_report(bytes(reply), reason="subcommand_reply")
        if reply and reply[0] == 0x21:
            self._advance_timer()

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._report_period_seconds)
            await self.send_next_report()

    async def _send_report(self, report: bytes, *, reason: str) -> None:
        await self._transport.send_interrupt(report)
        report_id = report[0]
        if self._diagnostics is not None:
            self._diagnostics.record_report_tx(report_id=report_id, reason=reason)

    def _advance_timer(self) -> None:
        self._timer = (self._timer + 1) & 0xFF

    def _holdoff_periodic_after_reply(self) -> None:
        self._periodic_holdoff_until = (
            asyncio.get_running_loop().time() + REPLY_PERIODIC_HOLDOFF_SECONDS
        )

    def _is_periodic_held_off(self) -> bool:
        return asyncio.get_running_loop().time() < self._periodic_holdoff_until
