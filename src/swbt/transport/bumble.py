"""Bumble-backed HID transport."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from swbt.diagnostics import DiagnosticsRecorder
from swbt.errors import ClosedError, TransportOpenError
from swbt.transport.base import (
    ConnectedCallback,
    ControlDataCallback,
    DisconnectedCallback,
    InterruptDataCallback,
)


class _BumbleHandle(Protocol):
    async def close(self) -> None:
        """Close the opened Bumble resource."""


_OpenTransport = Callable[[str], Awaitable[_BumbleHandle]]


class BumbleHidTransport:
    """HID transport boundary that keeps Bumble imports local to this module."""

    def __init__(
        self,
        *,
        adapter: str,
        diagnostics: DiagnosticsRecorder | None = None,
        _open_transport: _OpenTransport | None = None,
    ) -> None:
        """Create a Bumble transport for an adapter string."""
        self._adapter = adapter
        self._diagnostics = diagnostics
        self._open_transport = _open_transport or _default_open_transport
        self._handle: _BumbleHandle | None = None
        self._interrupt_callback: InterruptDataCallback | None = None
        self._control_callback: ControlDataCallback | None = None
        self._connected_callback: ConnectedCallback | None = None
        self._disconnected_callback: DisconnectedCallback | None = None

    async def open(self) -> None:
        """Open the configured Bumble adapter."""
        if self._handle is not None:
            return
        self._record_event("transport_open_start", adapter=self._adapter)
        try:
            self._handle = await self._open_transport(self._adapter)
        except Exception as error:
            self._record_error(error)
            msg = f"failed to open Bumble adapter: {self._adapter}"
            raise TransportOpenError(msg) from error
        self._record_event("transport_open_complete", adapter=self._adapter)

    async def start_advertising(self) -> None:
        """Record entry into discoverable/connectable state."""
        self._require_open()
        self._record_event("advertising_start", adapter=self._adapter)

    async def close(self) -> None:
        """Close the Bumble adapter if it is open."""
        if self._handle is None:
            return
        handle = self._handle
        self._handle = None
        await handle.close()
        self._record_event("transport_close_complete", adapter=self._adapter)

    async def send_interrupt(self, payload: bytes) -> None:
        """Send one interrupt report."""
        _ = payload
        self._require_open()
        msg = "Bumble interrupt channel is not connected"
        raise ClosedError(msg)

    async def send_control(self, payload: bytes) -> None:
        """Send one control report."""
        _ = payload
        self._require_open()
        msg = "Bumble control channel is not connected"
        raise ClosedError(msg)

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
        if self._handle is None:
            msg = "Bumble transport is not open"
            raise ClosedError(msg)

    def _record_event(self, event: str, **fields: object) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record_event(event, **fields)

    def _record_error(self, error: Exception) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record_error(error, recoverable=False)


async def _default_open_transport(adapter: str) -> _BumbleHandle:
    from bumble.transport import open_transport  # noqa: PLC0415

    return await open_transport(adapter)
