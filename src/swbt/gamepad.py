"""Public gamepad API."""

import asyncio
from dataclasses import dataclass
from types import TracebackType

from swbt.diagnostics import DiagnosticsConfig, DiagnosticsRecorder, GamepadStatus
from swbt.errors import ClosedError, ConnectionTimeoutError, SwbtError
from swbt.input import Button, InputState
from swbt.protocol.output_report import OutputReportParser
from swbt.protocol.subcommand import SubcommandResponder, UnsupportedSubcommandError
from swbt.report_loop import ReportLoop
from swbt.state_store import InputStateStore
from swbt.transport.base import HidDeviceTransport


@dataclass(frozen=True)
class SwitchGamepadConfig:
    """Configuration used to construct a SwitchGamepad."""

    adapter: str = "usb:0"
    report_period_us: int = 8000
    device_name: str = "Pro Controller"
    key_store_path: str | None = None


class SwitchGamepad:
    """NX-compatible virtual gamepad API."""

    def __init__(
        self,
        *,
        adapter: str = "usb:0",
        report_period_us: int = 8000,
        device_name: str = "Pro Controller",
        key_store_path: str | None = None,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> None:
        """Create a gamepad object."""
        self._config = SwitchGamepadConfig(
            adapter=adapter,
            report_period_us=report_period_us,
            device_name=device_name,
            key_store_path=key_store_path,
        )
        self._transport = transport
        self._state_store = InputStateStore()
        self._diagnostics = DiagnosticsRecorder(
            trace_writer=diagnostics.trace_writer if diagnostics is not None else None
        )
        self._output_report_parser = OutputReportParser()
        self._subcommand_responder = SubcommandResponder()
        self._report_loop: ReportLoop | None = None
        self._lifecycle_lock = asyncio.Lock()
        self._connected_event = asyncio.Event()
        self._connection_state = "closed"
        self._is_open = False

    async def __aenter__(self) -> "SwitchGamepad":
        """Open the gamepad for an async context manager."""
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the gamepad when leaving an async context manager."""
        _ = (exc_type, exc, traceback)
        await self.close(neutral=True)

    async def open(self) -> None:
        """Open the configured transport."""
        async with self._lifecycle_lock:
            if self._is_open:
                return
            transport = self._ensure_transport()
            self._diagnostics.record_run_metadata(adapter=self._config.adapter)
            self._connection_state = "opening"
            self._register_transport_callbacks()
            self._connected_event.clear()
            try:
                await transport.open()
                self._report_loop = ReportLoop(
                    transport=transport,
                    state_store=self._state_store,
                    report_period_us=self._config.report_period_us,
                    diagnostics=self._diagnostics,
                )
                self._connection_state = "advertising"
                self._is_open = True
                await transport.start_advertising()
            except Exception:
                self._connection_state = "failed"
                await transport.close()
                self._report_loop = None
                self._is_open = False
                raise

    async def wait_connected(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Wait until the transport reports a completed connection."""
        if timeout is None:
            await self._connected_event.wait()
            return
        try:
            async with asyncio.timeout(timeout):
                await self._connected_event.wait()
        except TimeoutError as error:
            msg = "connection timed out"
            connection_error = ConnectionTimeoutError(msg)
            self._diagnostics.record_event(
                "connection_timeout",
                state=self._connection_state,
                timeout=timeout,
            )
            self._diagnostics.record_error(connection_error, recoverable=True)
            raise connection_error from error

    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state."""
        async with self._lifecycle_lock:
            if not self._is_open or self._transport is None:
                return
            self._connection_state = "disconnecting"
            if neutral:
                await self._send_trailing_neutral_if_connected()
            if self._report_loop is not None:
                await self._report_loop.stop()
            if self._connected_event.is_set():
                await self._transport.request_disconnect()
            await self._transport.close()
            self._report_loop = None
            self._is_open = False
            self._connection_state = "closed"

    async def press(self, *buttons: Button) -> None:
        """Add buttons to the current input state."""
        await self._state_store.press(*buttons)

    async def set_input(self, state: InputState) -> None:
        """Replace the current input state."""
        await self._state_store.set_input(state)

    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state."""
        await self._state_store.release(*buttons)

    async def neutral(self) -> None:
        """Return the current input state to neutral."""
        await self._state_store.neutral()

    async def tap(self, *buttons: Button, duration: float = 0.08) -> None:
        """Press buttons briefly and then release them."""
        await self.press(*buttons)
        await self._send_current_input()
        if duration > 0:
            await asyncio.sleep(duration)
        await self.release(*buttons)
        await self._send_current_input()

    def status(self) -> GamepadStatus:
        """Return the current gamepad status."""
        return GamepadStatus(
            connection_state=self._connection_state,
            report_counters=self._diagnostics.report_counters,
            last_subcommand_id=self._diagnostics.last_subcommand_id,
            raw_rumble=self._diagnostics.raw_rumble,
            last_error=self._diagnostics.last_error,
        )

    def snapshot(self) -> InputState:
        """Return the latest committed input state."""
        return self._state_store.current

    def _register_transport_callbacks(self) -> None:
        if self._transport is None:
            return
        self._transport.on_interrupt_data(self._handle_interrupt_data)
        self._transport.on_control_data(self._handle_control_data)
        self._transport.on_connected(self._handle_connected)
        self._transport.on_disconnected(self._handle_disconnected)

    async def _send_trailing_neutral_if_connected(self) -> None:
        await self._state_store.neutral()
        if self._report_loop is None or not self._connected_event.is_set():
            return
        await self._report_loop.send_current_input()

    async def _send_current_input(self) -> None:
        if self._report_loop is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        await self._report_loop.send_current_input()

    async def _handle_interrupt_data(self, payload: bytes) -> None:
        await self._handle_output_report_data(payload)

    async def _handle_control_data(self, payload: bytes) -> None:
        await self._handle_output_report_data(payload)

    async def _handle_output_report_data(self, payload: bytes) -> None:
        try:
            output_report = self._output_report_parser.parse(payload)
            subcommand_id = (
                f"0x{output_report.subcommand_id:02x}"
                if output_report.subcommand_id is not None
                else None
            )
            if output_report.rumble is not None:
                self._diagnostics.record_raw_rumble(output_report.rumble)
            self._diagnostics.record_event(
                "output_report_rx",
                length=len(payload),
                packet_id=output_report.packet_id,
                report_id=f"0x{output_report.report_id:02x}",
                subcommand_id=subcommand_id,
            )
            if output_report.subcommand_id is None:
                return
            self._diagnostics.record_subcommand_rx(
                packet_id=output_report.packet_id,
                subcommand_id=output_report.subcommand_id,
            )
            if self._report_loop is None:
                msg = "gamepad is not open"
                raise ClosedError(msg)
            state = await self._state_store.snapshot()
            try:
                reply = self._subcommand_responder.respond(output_report, state=state)
            except UnsupportedSubcommandError:
                self._diagnostics.record_event(
                    "unsupported_subcommand",
                    packet_id=output_report.packet_id,
                    payload=output_report.subcommand_payload.hex(),
                    subcommand_id=subcommand_id,
                )
                raise
            self._diagnostics.record_event(
                "subcommand_reply_tx",
                packet_id=output_report.packet_id,
                report_id=f"0x{reply[0]:02x}",
                subcommand_id=subcommand_id,
            )
            await self._report_loop.send_subcommand_reply(reply)
        except SwbtError as error:
            self._connection_state = "failed"
            self._diagnostics.record_error(error, recoverable=False)

    async def _handle_connected(self) -> None:
        self._connection_state = "connected"
        self._connected_event.set()
        if self._report_loop is not None:
            self._report_loop.start()

    async def _handle_disconnected(self, reason: int | None) -> None:
        self._diagnostics.record_event("disconnected", reason=reason)
        self._connected_event.clear()
        await self._state_store.neutral()
        if self._report_loop is not None:
            await self._report_loop.stop()
            self._report_loop = None
        if self._transport is not None and self._is_open:
            await self._transport.close()
        self._is_open = False
        self._connection_state = "closed"

    def _ensure_transport(self) -> HidDeviceTransport:
        if self._transport is None:
            from swbt.transport.bumble import BumbleHidTransport  # noqa: PLC0415

            self._transport = BumbleHidTransport(
                adapter=self._config.adapter,
                device_name=self._config.device_name,
                diagnostics=self._diagnostics,
            )
        return self._transport
