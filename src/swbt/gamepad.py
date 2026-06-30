"""Public gamepad API."""

import asyncio
from dataclasses import dataclass
from types import TracebackType

from swbt.errors import TransportOpenError
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
        self._lifecycle_lock = asyncio.Lock()
        self._connected_event = asyncio.Event()
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
            if self._transport is None:
                msg = "a transport must be provided until Bumble transport is implemented"
                raise TransportOpenError(msg)
            self._register_transport_callbacks()
            self._connected_event.clear()
            await self._transport.open()
            self._is_open = True

    async def wait_connected(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Wait until the transport reports a completed connection."""
        if timeout is None:
            await self._connected_event.wait()
            return
        async with asyncio.timeout(timeout):
            await self._connected_event.wait()

    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state."""
        async with self._lifecycle_lock:
            if not self._is_open or self._transport is None:
                return
            if neutral:
                await self._send_trailing_neutral_if_connected()
            await self._transport.close()
            self._is_open = False

    def _register_transport_callbacks(self) -> None:
        if self._transport is None:
            return
        self._transport.on_interrupt_data(self._handle_interrupt_data)
        self._transport.on_control_data(self._handle_control_data)
        self._transport.on_connected(self._handle_connected)
        self._transport.on_disconnected(self._handle_disconnected)

    async def _send_trailing_neutral_if_connected(self) -> None:
        return None

    async def _handle_interrupt_data(self, payload: bytes) -> None:
        _ = payload

    async def _handle_control_data(self, payload: bytes) -> None:
        _ = payload

    async def _handle_connected(self) -> None:
        self._connected_event.set()

    async def _handle_disconnected(self, reason: int | None) -> None:
        _ = reason
