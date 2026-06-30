"""Input report sender used by SwitchGamepad."""

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
        input_report_builder: InputReportBuilder | None = None,
    ) -> None:
        """Create a report loop helper."""
        self._transport = transport
        self._state_store = state_store
        self._input_report_builder = input_report_builder or InputReportBuilder()
        self._timer = 0

    async def send_current_input(self) -> None:
        """Send one 0x30 input report for the current state."""
        state = await self._state_store.snapshot()
        report = self._input_report_builder.build_0x30(state, timer=self._timer)
        self._timer = (self._timer + 1) & 0xFF
        await self._transport.send_interrupt(report)
