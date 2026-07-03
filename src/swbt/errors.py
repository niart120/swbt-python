"""Exception types exposed by swbt."""


class SwbtError(Exception):
    """Base exception for swbt errors."""


class TransportOpenError(SwbtError):
    """Raised when a transport cannot be opened."""


class ConnectionTimeoutError(SwbtError):
    """Raised when waiting for a connection times out."""


class ConnectionFailedError(SwbtError):
    """Raised when a connection attempt finishes without a connection."""


class ProtocolError(SwbtError):
    """Raised when protocol bytes cannot be parsed or produced."""


class ClosedError(SwbtError):
    """Raised when an operation requires an open controller."""


class InvalidInputError(SwbtError):
    """Raised when user-provided input values are outside the supported range."""
