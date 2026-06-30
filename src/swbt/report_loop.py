"""Input report sender used by SwitchGamepad."""

import asyncio
from contextlib import suppress

from swbt.protocol.input_report import InputReportBuilder
from swbt.state_store import InputStateStore
from swbt.transport.base import HidDeviceTransport


class ReportLoop:
    """Send input reports from the current input state."""

    def __init__(
        self,
        *,
        transport: HidDeviceTransport,
        state_store: InputStateStore,
        report_period_us: int = 8000,
        input_report_builder: InputReportBuilder | None = None,
    ) -> None:
        """Create a report loop helper."""
        self._transport = transport
        self._state_store = state_store
        self._report_period_seconds = report_period_us / 1_000_000
        self._input_report_builder = input_report_builder or InputReportBuilder()
        self._timer = 0
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

    async def send_current_input(self) -> None:
        """Send one 0x30 input report for the current state."""
        state = await self._state_store.snapshot()
        report = self._input_report_builder.build_0x30(state, timer=self._timer)
        self._timer = (self._timer + 1) & 0xFF
        await self._transport.send_interrupt(report)

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._report_period_seconds)
            await self.send_current_input()
