"""Transport protocol shared by gamepad and transport implementations."""

from collections.abc import Awaitable, Callable
from typing import Protocol

InterruptDataCallback = Callable[[bytes], Awaitable[None]]
ControlDataCallback = Callable[[bytes], Awaitable[None]]
ConnectedCallback = Callable[[], Awaitable[None]]
DisconnectedCallback = Callable[[int | None], Awaitable[None]]


class HidDeviceTransport(Protocol):
    """Abstract HID device transport used by SwitchGamepad."""

    async def open(self) -> None:
        """Open transport resources without waiting for a host connection."""

    async def start_advertising(self) -> None:
        """Enter the host-discoverable state."""

    async def close(self) -> None:
        """Close transport resources."""

    async def send_interrupt(self, payload: bytes) -> None:
        """Send one HID interrupt report."""

    async def send_control(self, payload: bytes) -> None:
        """Send one HID control report."""

    def on_interrupt_data(self, callback: InterruptDataCallback) -> None:
        """Register a callback for interrupt-channel host data."""

    def on_control_data(self, callback: ControlDataCallback) -> None:
        """Register a callback for control-channel host data."""

    def on_connected(self, callback: ConnectedCallback) -> None:
        """Register a callback for transport connection completion."""

    def on_disconnected(self, callback: DisconnectedCallback) -> None:
        """Register a callback for transport disconnection."""
