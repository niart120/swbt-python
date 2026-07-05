"""Exception types exposed by swbt."""


class SwbtError(Exception):
    """Base exception for swbt errors."""


class TransportOpenError(SwbtError):
    """Raised when a transport cannot be opened."""


class AdapterDiscoveryError(SwbtError):
    """Raised when no-open adapter discovery cannot enumerate USB devices.

    Attributes:
        platform: Host platform string captured at discovery time.
        backend: Discovery backend identifier.
        libusb_available: Whether libusb availability is known at the failure point.
        bumble_version: Installed Bumble package version when available.
    """

    def __init__(
        self,
        message: str,
        *,
        platform: str,
        backend: str = "bumble-usb",
        libusb_available: bool | None = None,
        bumble_version: str | None = None,
    ) -> None:
        """Initialize adapter discovery failure metadata."""
        super().__init__(message)
        self.platform = platform
        self.backend = backend
        self.libusb_available = libusb_available
        self.bumble_version = bumble_version


class ConnectionTimeoutError(SwbtError):
    """Raised when waiting for a connection times out."""


class ConnectionFailedError(SwbtError):
    """Raised when a connection attempt finishes without a connection."""


class InvalidKeyStoreError(SwbtError):
    """Raised when a key store has an unsupported or invalid shape."""


class ProtocolError(SwbtError):
    """Raised when protocol bytes cannot be parsed or produced."""


class ClosedError(SwbtError):
    """Raised when an operation requires an open controller."""


class InvalidInputError(SwbtError):
    """Raised when user-provided input values are outside the supported range."""


class UnsupportedInputError(InvalidInputError):
    """Raised when a controller profile does not support a requested input."""

    def __init__(
        self,
        message: str,
        *,
        profile_kind: str,
        buttons: tuple[str, ...] = (),
        sticks: tuple[str, ...] = (),
    ) -> None:
        """Initialize unsupported input details."""
        super().__init__(message)
        self.profile_kind = profile_kind
        self.buttons = buttons
        self.sticks = sticks
