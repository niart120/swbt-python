"""Public connection result types."""

from dataclasses import dataclass
from typing import Literal

ConnectionRoute = Literal["active_reconnect", "pairing"]
ConnectionStatus = Literal["connected", "no_bond", "timeout", "failed"]


@dataclass(frozen=True)
class ConnectionResult:
    """Result of an explicit connection strategy.

    Args:
        route: Connection path that produced the result.
        status: Outcome of the connection attempt.
        peer_address: Address used for active reconnect, when one was selected.
        peer_count: Number of current peers observed while selecting a reconnect target.
    """

    route: ConnectionRoute
    status: ConnectionStatus
    peer_address: str | None = None
    peer_count: int | None = None
