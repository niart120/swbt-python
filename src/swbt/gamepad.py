"""Public gamepad API."""

import asyncio
from dataclasses import dataclass
from types import TracebackType
from typing import Literal

from swbt.diagnostics import DiagnosticsConfig, DiagnosticsRecorder, GamepadStatus
from swbt.errors import ClosedError, ConnectionTimeoutError, SwbtError
from swbt.input import Button, InputState
from swbt.protocol.output_report import OutputReportParser
from swbt.protocol.subcommand import SubcommandResponder, UnsupportedSubcommandError
from swbt.report_loop import ReportLoop
from swbt.state_store import InputStateStore
from swbt.transport.base import DisconnectRequestResult, HidDeviceTransport

DISCONNECT_REQUEST_TIMEOUT_SECONDS = 0.25

ConnectionRoute = Literal["active_reconnect", "pairing"]
ConnectionStatus = Literal["connected", "no_bond", "ambiguous_bond", "timeout", "failed"]


@dataclass(frozen=True)
class ConnectionResult:
    """Result of an explicit connection strategy."""

    route: ConnectionRoute
    status: ConnectionStatus
    peer_address: str | None = None
    peer_count: int | None = None


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
        self._disconnect_event = asyncio.Event()
        self._connection_state = "closed"
        self._is_open = False
        self._close_in_progress = False

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
            self._diagnostics.record_run_metadata(
                adapter=self._config.adapter,
                key_store_path=self._config.key_store_path,
            )
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
                self._connection_state = "opened"
                self._is_open = True
            except Exception:
                self._connection_state = "failed"
                await transport.close()
                self._report_loop = None
                self._is_open = False
                raise

    async def pair(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Start initial-pairing advertising and wait for a host connection."""
        if not self._is_open:
            await self.open()
        if self._transport is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        self._connection_state = "advertising"
        await self._transport.start_advertising()
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

    async def reconnect(self, timeout: float | None = None) -> ConnectionResult:  # noqa: ASYNC109
        """Try active reconnect with exactly one bonded peer."""
        if not self._is_open:
            await self.open()
        if self._transport is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        peers = await self._transport.list_bonded_peers()
        selection = self._bonded_peer_selection(len(peers))
        self._diagnostics.record_event(
            "bonded_peers_discovered",
            peer_count=len(peers),
            selection=selection,
        )
        if not peers:
            self._diagnostics.record_event(
                "active_reconnect_result",
                peer_count=0,
                route="active_reconnect",
                status="no_bond",
            )
            return ConnectionResult(
                route="active_reconnect",
                status="no_bond",
                peer_count=0,
            )
        if len(peers) > 1:
            self._diagnostics.record_event(
                "active_reconnect_result",
                peer_count=len(peers),
                route="active_reconnect",
                status="ambiguous_bond",
            )
            return ConnectionResult(
                route="active_reconnect",
                status="ambiguous_bond",
                peer_count=len(peers),
            )

        peer = peers[0]
        self._connection_state = "reconnecting"
        self._connected_event.clear()
        self._diagnostics.record_event(
            "active_reconnect_attempt",
            peer_address=peer.address,
            route="active_reconnect",
        )
        try:
            await self._transport.connect_bonded_peer(
                peer.address,
                connect_timeout=timeout,
            )
            await self._wait_for_reconnect_connected(max_wait=timeout)
        except TimeoutError:
            self._diagnostics.record_event(
                "active_reconnect_result",
                failure_reason="connection_timeout",
                peer_address=peer.address,
                route="active_reconnect",
                status="timeout",
            )
            await self.close(neutral=True)
            return ConnectionResult(
                route="active_reconnect",
                status="timeout",
                peer_address=peer.address,
                peer_count=1,
            )
        except asyncio.CancelledError as error:
            if self._current_task_is_cancelling():
                raise
            return await self._record_active_reconnect_transport_error(
                error,
                peer_address=peer.address,
            )
        except Exception as error:  # noqa: BLE001
            return await self._record_active_reconnect_transport_error(
                error,
                peer_address=peer.address,
            )

        self._diagnostics.record_event(
            "active_reconnect_result",
            peer_address=peer.address,
            route="active_reconnect",
            status="connected",
        )
        return ConnectionResult(
            route="active_reconnect",
            status="connected",
            peer_address=peer.address,
            peer_count=1,
        )

    async def connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> ConnectionResult:
        """Connect using bonded reconnect first, then optional pairing fallback."""
        reconnect_result = await self.reconnect(timeout=timeout)
        if reconnect_result.status != "no_bond" or not allow_pairing:
            return reconnect_result
        self._diagnostics.record_event(
            "connect_pairing_fallback",
            reason="no_bond",
            route="pairing",
        )
        await self.pair(timeout=timeout)
        return ConnectionResult(route="pairing", status="connected")

    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state."""
        async with self._lifecycle_lock:
            if not self._is_open or self._transport is None:
                return
            self._close_in_progress = True
            try:
                self._connection_state = "disconnecting"
                if neutral:
                    await self._send_trailing_neutral_if_connected()
                if self._report_loop is not None:
                    await self._report_loop.stop()
                self._disconnect_event.clear()
                try:
                    disconnect_result = await self._transport.request_disconnect()
                except ClosedError as error:
                    disconnect_result = DisconnectRequestResult(
                        status="unavailable",
                        reason="transport_closed",
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                self._record_disconnect_request_result(disconnect_result)
                if disconnect_result.status == "requested":
                    disconnect_closed = await self._wait_for_disconnect_request_closed()
                    if disconnect_closed:
                        self._diagnostics.record_event(
                            "disconnect_request_terminal",
                            status="closed",
                        )
                    else:
                        self._diagnostics.record_event(
                            "disconnect_request_terminal",
                            status="timeout",
                            timeout=DISCONNECT_REQUEST_TIMEOUT_SECONDS,
                        )
                await self._transport.close()
                self._report_loop = None
                self._is_open = False
                self._connection_state = "closed"
            finally:
                self._close_in_progress = False

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

    async def _wait_for_disconnect_request_closed(self) -> bool:
        try:
            async with asyncio.timeout(DISCONNECT_REQUEST_TIMEOUT_SECONDS):
                await self._disconnect_event.wait()
                return True
        except TimeoutError:
            return False

    async def _wait_for_reconnect_connected(self, *, max_wait: float | None) -> None:
        if max_wait is None:
            await self._connected_event.wait()
            return
        try:
            async with asyncio.timeout(max_wait):
                await self._connected_event.wait()
        except TimeoutError as error:
            self._diagnostics.record_event(
                "connection_timeout",
                route="active_reconnect",
                state=self._connection_state,
                timeout=max_wait,
            )
            raise TimeoutError from error

    @staticmethod
    def _bonded_peer_selection(peer_count: int) -> str:
        if peer_count == 0:
            return "none"
        if peer_count == 1:
            return "selected"
        return "ambiguous"

    @staticmethod
    def _current_task_is_cancelling() -> bool:
        task = asyncio.current_task()
        return task is not None and task.cancelling() > 0

    async def _record_active_reconnect_transport_error(
        self,
        error: BaseException,
        *,
        peer_address: str,
    ) -> ConnectionResult:
        self._diagnostics.record_event(
            "active_reconnect_result",
            error_type=type(error).__name__,
            failure_reason="transport_error",
            message=str(error),
            peer_address=peer_address,
            route="active_reconnect",
            status="failed",
        )
        self._diagnostics.record_error(error, recoverable=True)
        await self.close(neutral=True)
        return ConnectionResult(
            route="active_reconnect",
            status="failed",
            peer_address=peer_address,
            peer_count=1,
        )

    def _record_disconnect_request_result(self, result: DisconnectRequestResult) -> None:
        fields: dict[str, object] = {"status": result.status}
        if result.channels:
            fields["channels"] = list(result.channels)
        if result.reason is not None:
            fields["reason"] = result.reason
        if result.error_type is not None:
            fields["error_type"] = result.error_type
        if result.message is not None:
            fields["message"] = result.message
        self._diagnostics.record_event("disconnect_request", **fields)

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
        previous_state = self._connection_state
        if previous_state == "advertising":
            self._diagnostics.record_event(
                "incoming_connection",
                previous_state=previous_state,
                route="incoming",
            )
        self._connection_state = "connected"
        self._connected_event.set()
        if self._report_loop is not None:
            self._report_loop.start()

    async def _handle_disconnected(self, reason: int | None) -> None:
        self._diagnostics.record_event("disconnected", reason=reason)
        self._connected_event.clear()
        try:
            await self._state_store.neutral()
            if self._report_loop is not None:
                await self._report_loop.stop()
                self._report_loop = None
            if self._close_in_progress:
                return
            if self._transport is not None and self._is_open:
                await self._transport.close()
            self._is_open = False
            self._connection_state = "closed"
            self._diagnostics.record_event(
                "reconnect_disabled",
                next_state=self._connection_state,
                reason=reason,
            )
        finally:
            self._disconnect_event.set()

    def _ensure_transport(self) -> HidDeviceTransport:
        if self._transport is None:
            from swbt.transport.bumble import BumbleHidTransport  # noqa: PLC0415

            self._transport = BumbleHidTransport(
                adapter=self._config.adapter,
                device_name=self._config.device_name,
                key_store_path=self._config.key_store_path,
                diagnostics=self._diagnostics,
            )
        return self._transport
