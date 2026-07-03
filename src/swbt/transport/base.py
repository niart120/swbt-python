"""Transport protocol shared by gamepad and transport implementations."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol

InterruptDataCallback = Callable[[bytes], Awaitable[None]]
ControlDataCallback = Callable[[bytes], Awaitable[None]]
ConnectedCallback = Callable[[], Awaitable[None]]
DisconnectedCallback = Callable[[int | None], Awaitable[None]]
DisconnectRequestStatus = Literal["requested", "unavailable", "failed"]


@dataclass(frozen=True)
class DisconnectRequestResult:
    """Result of a best-effort remote HID disconnect request."""

    status: DisconnectRequestStatus
    channels: tuple[str, ...] = ()
    reason: str | None = None
    error_type: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class BondedPeer:
    """Peer address discovered from a transport key store."""

    address: str


class HidDeviceTransport(Protocol):
    """Abstract HID device transport used by SwitchGamepad."""

    async def open(self) -> None:
        """Open transport resources without waiting for a host connection."""

    async def start_advertising(self) -> None:
        """Enter the host-discoverable state."""

    async def close(self) -> None:
        """Close transport resources."""

    async def request_disconnect(self) -> DisconnectRequestResult:
        """Request a remote HID/L2CAP disconnect when the transport supports it."""

    async def list_bonded_peers(self) -> tuple[BondedPeer, ...]:
        """Return current reconnect candidates.

        Implementations must return zero or one peer. A transport that stores
        multiple historical peers must expose only the current reconnect target
        here. Multiple current peers are an invalid transport or key-store state
        and should raise InvalidKeyStoreError rather than returning multiple
        BondedPeer values.
        """

    async def connect_bonded_peer(
        self,
        peer_address: str,
        *,
        connect_timeout: float | None,
    ) -> None:
        """Start an active reconnect attempt to a bonded peer."""

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
