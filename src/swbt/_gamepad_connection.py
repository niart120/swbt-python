"""Connection workflow for SwitchGamepad."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from swbt.diagnostics import DiagnosticsRecorder
from swbt.errors import (
    ClosedError,
    ConnectionFailedError,
    ConnectionTimeoutError,
    InvalidKeyStoreError,
)
from swbt.transport.base import HidDeviceTransport

ConnectionRoute = Literal["active_reconnect", "pairing"]
ConnectionStatus = Literal["connected", "no_bond", "timeout", "failed"]

EnsureOpen = Callable[[], Awaitable[None]]
TransportProvider = Callable[[], HidDeviceTransport | None]
StateSetter = Callable[[str], None]
EventClearer = Callable[[], None]
WaitForConnected = Callable[[float | None], Awaitable[None]]
CloseNeutral = Callable[[], Awaitable[None]]
PairWithTimeout = Callable[[float | None], Awaitable[None]]


@dataclass(frozen=True)
class ConnectionResult:
    """Result of an explicit connection strategy.

    Attributes:
        route: Connection path that produced the result.
        status: Outcome of the connection attempt.
        peer_address: Address of the bonded peer used for reconnect, when one was selected.
        peer_count: Number of bonded peers observed while selecting a reconnect target.
    """

    route: ConnectionRoute
    status: ConnectionStatus
    peer_address: str | None = None
    peer_count: int | None = None


@dataclass
class ConnectionWorkflow:
    """Run active reconnect and pairing fallback workflows."""

    clear_connected: EventClearer
    close_neutral: CloseNeutral
    diagnostics: DiagnosticsRecorder
    ensure_open: EnsureOpen
    get_transport: TransportProvider
    key_store_path: str | None
    pair: PairWithTimeout
    set_connection_state: StateSetter
    transport_was_injected: bool
    wait_for_connected: WaitForConnected

    async def try_reconnect(
        self,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> ConnectionResult:
        """Try active reconnect with exactly one bonded peer."""
        await self.ensure_open()
        transport = self._transport()
        if self.key_store_path is None and not self.transport_was_injected:
            self.diagnostics.record_event(
                "reconnect_key_store_unavailable",
                reason="key_store_path_none",
                route="active_reconnect",
            )
        peers = await transport.list_bonded_peers()
        if len(peers) > 1:
            self.diagnostics.record_event(
                "invalid_key_store",
                peer_count=len(peers),
                reason="multiple_current_peers",
            )
            msg = "key store contains multiple current peers"
            raise InvalidKeyStoreError(msg)
        selection = _bonded_peer_selection(len(peers))
        self.diagnostics.record_event(
            "bonded_peers_discovered",
            peer_count=len(peers),
            selection=selection,
        )
        if not peers:
            self.diagnostics.record_event(
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
        peer = peers[0]
        self.set_connection_state("reconnecting")
        self.clear_connected()
        self.diagnostics.record_event(
            "active_reconnect_attempt",
            peer_address=peer.address,
            route="active_reconnect",
        )
        try:
            await transport.connect_bonded_peer(
                peer.address,
                connect_timeout=timeout,
            )
            await self.wait_for_connected(timeout)
        except TimeoutError:
            self.diagnostics.record_event(
                "active_reconnect_result",
                failure_reason="connection_timeout",
                peer_address=peer.address,
                route="active_reconnect",
                status="timeout",
            )
            await self.close_neutral()
            return ConnectionResult(
                route="active_reconnect",
                status="timeout",
                peer_address=peer.address,
                peer_count=1,
            )
        except asyncio.CancelledError as error:
            if _current_task_is_cancelling():
                raise
            return await self._record_transport_error(error, peer_address=peer.address)
        except Exception as error:  # noqa: BLE001
            return await self._record_transport_error(error, peer_address=peer.address)

        self.diagnostics.record_event(
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

    async def try_connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> ConnectionResult:
        """Try bonded reconnect first, then optional pairing fallback."""
        reconnect_result = await self.try_reconnect(timeout=timeout)
        if reconnect_result.status != "no_bond" or not allow_pairing:
            return reconnect_result
        self.diagnostics.record_event(
            "connect_pairing_fallback",
            reason="no_bond",
            route="pairing",
        )
        try:
            await self.pair(timeout)
        except ConnectionTimeoutError:
            return ConnectionResult(route="pairing", status="timeout")
        return ConnectionResult(route="pairing", status="connected")

    def _transport(self) -> HidDeviceTransport:
        transport = self.get_transport()
        if transport is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        return transport

    async def _record_transport_error(
        self,
        error: BaseException,
        *,
        peer_address: str,
    ) -> ConnectionResult:
        self.diagnostics.record_event(
            "active_reconnect_result",
            error_type=type(error).__name__,
            failure_reason="transport_error",
            message=str(error),
            peer_address=peer_address,
            route="active_reconnect",
            status="failed",
        )
        self.diagnostics.record_error(error, recoverable=True)
        await self.close_neutral()
        return ConnectionResult(
            route="active_reconnect",
            status="failed",
            peer_address=peer_address,
            peer_count=1,
        )


def raise_if_connection_failed(result: ConnectionResult) -> None:
    """Raise the public connection error for a non-connected result."""
    if result.status == "connected":
        return
    if result.status == "timeout":
        msg = "connection timed out"
        raise ConnectionTimeoutError(msg)
    msg = f"connection failed: {result.status}"
    raise ConnectionFailedError(msg)


def _bonded_peer_selection(peer_count: int) -> str:
    if peer_count == 0:
        return "none"
    return "selected"


def _current_task_is_cancelling() -> bool:
    task = asyncio.current_task()
    return task is not None and task.cancelling() > 0
