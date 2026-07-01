"""In-memory HID transport for integration tests."""

import asyncio
from typing import Literal

from swbt.errors import ClosedError
from swbt.transport.base import (
    ConnectedCallback,
    ControlDataCallback,
    DisconnectedCallback,
    InterruptDataCallback,
)


class FakeHidTransport:
    """Record transport operations without opening Bluetooth resources."""

    def __init__(self) -> None:
        """Create a closed fake transport."""
        self._is_open = False
        self._open_count = 0
        self._close_count = 0
        self._events: list[str] = []
        self._control_channel_open = False
        self._interrupt_channel_open = False
        self._connected_emitted = False
        self._sent_interrupt_reports: list[bytes] = []
        self._sent_control_reports: list[bytes] = []
        self._interrupt_report_event = asyncio.Event()
        self._interrupt_callback: InterruptDataCallback | None = None
        self._control_callback: ControlDataCallback | None = None
        self._connected_callback: ConnectedCallback | None = None
        self._disconnected_callback: DisconnectedCallback | None = None

    @property
    def is_open(self) -> bool:
        """Return whether the fake transport is open."""
        return self._is_open

    @property
    def open_count(self) -> int:
        """Return the number of state-changing open calls."""
        return self._open_count

    @property
    def close_count(self) -> int:
        """Return the number of state-changing close calls."""
        return self._close_count

    @property
    def events(self) -> tuple[str, ...]:
        """Return transport lifecycle events in order."""
        return tuple(self._events)

    @property
    def sent_interrupt_reports(self) -> tuple[bytes, ...]:
        """Return interrupt reports sent by the gamepad."""
        return tuple(self._sent_interrupt_reports)

    @property
    def sent_control_reports(self) -> tuple[bytes, ...]:
        """Return control reports sent by the gamepad."""
        return tuple(self._sent_control_reports)

    async def open(self) -> None:
        """Open the fake transport."""
        if self._is_open:
            return
        self._is_open = True
        self._open_count += 1
        self._events.append("open")

    async def start_advertising(self) -> None:
        """Record an advertising transition."""
        self._require_open()
        self._events.append("start_advertising")

    async def close(self) -> None:
        """Close the fake transport."""
        if not self._is_open:
            return
        self._is_open = False
        self._control_channel_open = False
        self._interrupt_channel_open = False
        self._connected_emitted = False
        self._close_count += 1
        self._events.append("close")

    async def connect(self) -> None:
        """Emit a fake host connection event."""
        self._require_open()
        self._control_channel_open = True
        self._interrupt_channel_open = True
        await self._emit_connected_once()

    async def open_l2cap_channel(self, channel: Literal["control", "interrupt"]) -> None:
        """Emit one fake L2CAP channel-open event."""
        self._require_open()
        if channel == "control":
            self._control_channel_open = True
            self._events.append("l2cap_control_open")
        else:
            self._interrupt_channel_open = True
            self._events.append("l2cap_interrupt_open")
        await self._emit_connected_once()

    async def disconnect(self, reason: int | None = None) -> None:
        """Emit a fake host disconnection event."""
        self._require_open()
        self._control_channel_open = False
        self._interrupt_channel_open = False
        self._connected_emitted = False
        self._events.append("disconnected")
        if self._disconnected_callback is not None:
            await self._disconnected_callback(reason)

    async def inject_interrupt_data(self, payload: bytes) -> None:
        """Inject host-to-device data into the registered interrupt callback."""
        self._require_open()
        self._events.append("interrupt_rx")
        if self._interrupt_callback is not None:
            await self._interrupt_callback(bytes(payload))

    async def send_interrupt(self, payload: bytes) -> None:
        """Record an interrupt report."""
        self._require_open()
        self._sent_interrupt_reports.append(bytes(payload))
        self._interrupt_report_event.set()

    async def wait_for_interrupt_report_count(
        self,
        count: int,
        *,
        max_wait: float = 0.5,
    ) -> tuple[bytes, ...]:
        """Wait until at least count interrupt reports have been recorded."""
        async with asyncio.timeout(max_wait):
            while len(self._sent_interrupt_reports) < count:
                self._interrupt_report_event.clear()
                if len(self._sent_interrupt_reports) >= count:
                    break
                await self._interrupt_report_event.wait()
        return self.sent_interrupt_reports

    async def wait_for_interrupt_report_id(
        self,
        report_id: int,
        *,
        max_wait: float = 0.5,
    ) -> bytes:
        """Wait until an interrupt report with report_id has been recorded."""
        async with asyncio.timeout(max_wait):
            while True:
                for report in self._sent_interrupt_reports:
                    if report and report[0] == report_id:
                        return report
                self._interrupt_report_event.clear()
                await self._interrupt_report_event.wait()

    async def send_control(self, payload: bytes) -> None:
        """Record a control report."""
        self._require_open()
        self._sent_control_reports.append(bytes(payload))

    def on_interrupt_data(self, callback: InterruptDataCallback) -> None:
        """Register an interrupt data callback."""
        self._interrupt_callback = callback

    def on_control_data(self, callback: ControlDataCallback) -> None:
        """Register a control data callback."""
        self._control_callback = callback

    def on_connected(self, callback: ConnectedCallback) -> None:
        """Register a connection callback."""
        self._connected_callback = callback

    def on_disconnected(self, callback: DisconnectedCallback) -> None:
        """Register a disconnection callback."""
        self._disconnected_callback = callback

    def _require_open(self) -> None:
        if not self._is_open:
            msg = "fake transport is not open"
            raise ClosedError(msg)

    async def _emit_connected_once(self) -> None:
        if (
            self._connected_emitted
            or not self._control_channel_open
            or not self._interrupt_channel_open
        ):
            return
        self._connected_emitted = True
        self._events.append("connected")
        if self._connected_callback is not None:
            await self._connected_callback()
