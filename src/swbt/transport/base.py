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
    """Result of a best-effort remote HID disconnect request.

    Args:
        status: Outcome of the remote disconnect request.
        channels: Transport channels that accepted the request.
        reason: Optional stable reason for an unavailable or failed request.
        error_type: Exception type name for a failed request.
        message: Human-readable failure detail.

    Attributes:
        status: Outcome of the remote disconnect request.
        channels: Transport channels that accepted the request.
        reason: Optional stable reason for an unavailable or failed request.
        error_type: Exception type name for a failed request.
        message: Human-readable failure detail.
    """

    status: DisconnectRequestStatus
    channels: tuple[str, ...] = ()
    reason: str | None = None
    error_type: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class BondedPeer:
    """Peer address discovered from a transport key store.

    Args:
        address: Bluetooth address of the bonded peer.

    Attributes:
        address: Bluetooth address of the bonded peer.
    """

    address: str


class HidDeviceTransport(Protocol):
    """Abstract HID device transport used by concrete gamepads."""

    async def open(self) -> None:
        """Open transport resources without waiting for a host connection.

        Raises:
            TransportOpenError: Transport resources or the adapter cannot be opened.
            Exception: Implementation-specific lower-layer failures.
        """

    async def start_advertising(self) -> None:
        """Enter the host-discoverable state.

        Raises:
            Exception: Implementation-specific advertising failures.
        """

    async def close(self) -> None:
        """Close transport resources."""

    async def request_disconnect(self) -> DisconnectRequestResult:
        """Request a remote HID/L2CAP disconnect when the transport supports it.

        Returns:
            DisconnectRequestResult: Best-effort disconnect request result.
        """

    def local_bluetooth_address(self) -> bytes | None:
        """Return the local controller address for Device Info, when available.

        Returns:
            bytes | None: Six-byte Bluetooth address, or ``None`` when unavailable.
        """

    async def list_bonded_peers(self) -> tuple[BondedPeer, ...]:
        """Return current reconnect candidates.

        Implementations must return zero or one peer. A transport that stores
        multiple historical peers must expose only the current reconnect target
        here. Multiple current peers are an invalid transport or key-store state
        and should raise InvalidKeyStoreError rather than returning multiple
        BondedPeer values.

        Returns:
            tuple[BondedPeer, ...]: Zero or one current reconnect candidate.

        Raises:
            InvalidKeyStoreError: More than one current reconnect candidate exists.
        """

    async def connect_bonded_peer(
        self,
        peer_address: str,
        *,
        connect_timeout: float | None,
    ) -> None:
        """Start an active reconnect attempt to a bonded peer.

        Args:
            peer_address: Bluetooth address selected from ``list_bonded_peers()``.
            connect_timeout: Maximum seconds for the reconnect attempt. ``None``
                uses the transport default.

        Raises:
            TimeoutError: The reconnect attempt timed out.
            Exception: Implementation-specific reconnect failures.
        """

    async def send_interrupt(self, payload: bytes) -> None:
        """Send one HID interrupt report.

        Args:
            payload: HID interrupt report bytes to send.

        Raises:
            Exception: Implementation-specific send failures.
        """

    async def send_control(self, payload: bytes) -> None:
        """Send one HID control report.

        Args:
            payload: HID control report bytes to send.

        Raises:
            Exception: Implementation-specific send failures.
        """

    def on_interrupt_data(self, callback: InterruptDataCallback) -> None:
        """Register a callback for interrupt-channel host data.

        Args:
            callback: Async callback that receives raw interrupt-channel bytes.
        """

    def on_control_data(self, callback: ControlDataCallback) -> None:
        """Register a callback for control-channel host data.

        Args:
            callback: Async callback that receives raw control-channel bytes.
        """

    def on_connected(self, callback: ConnectedCallback) -> None:
        """Register a callback for transport connection completion.

        Args:
            callback: Async callback invoked after host connection completion.
        """

    def on_disconnected(self, callback: DisconnectedCallback) -> None:
        """Register a callback for transport disconnection.

        Args:
            callback: Async callback invoked with an optional disconnect reason code.
        """
