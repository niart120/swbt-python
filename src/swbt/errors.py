"""Exception types exposed by swbt."""


class SwbtError(Exception):
    """Base exception for swbt errors."""


class TransportOpenError(SwbtError):
    """Raised when a transport cannot be opened."""


class AdapterDiscoveryError(SwbtError):
    """Raised when no-open adapter discovery cannot enumerate USB devices.

    Args:
        message: Human-readable failure message.
        platform: Host platform string captured at discovery time.
        backend: Discovery backend identifier.
        libusb_available: Whether libusb availability is known at the failure point.
        bumble_version: Installed Bumble package version when available.

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
        """Initialize adapter discovery failure metadata.

        Args:
            message: Human-readable failure message.
            platform: Host platform string captured at discovery time.
            backend: Discovery backend identifier.
            libusb_available: Whether libusb availability is known at the failure point.
            bumble_version: Installed Bumble package version when available.
        """
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


class InvalidProfileError(SwbtError):
    """Raised when an exp local address profile is invalid or unsupported."""


class ProfileControllerMismatchError(InvalidProfileError):
    """Raised when a profile belongs to a different concrete controller kind."""

    def __init__(
        self,
        *,
        expected_controller_kind: str,
        actual_controller_kind: str,
    ) -> None:
        """Initialize expected and actual profile controller kinds."""
        message = (
            "profile controller_kind mismatch: "
            f"expected {expected_controller_kind!r}, got {actual_controller_kind!r}"
        )
        super().__init__(message)
        self.expected_controller_kind = expected_controller_kind
        self.actual_controller_kind = actual_controller_kind


class ExpLocalAddressRecoveryRequired(SwbtError):  # noqa: N818
    """Raised when a volatile write may have changed the adapter identity."""

    def __init__(self, *, target_address: str, stage: str) -> None:
        """Initialize the target and failure stage requiring physical recovery."""
        message = (
            "exp local address preparation became uncertain after write started; "
            "unplug and reconnect the USB dongle before retrying"
        )
        super().__init__(message)
        self.target_address = target_address
        self.stage = stage


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
        """Initialize unsupported input details.

        Args:
            message: Human-readable failure message.
            profile_kind: Controller profile identity that rejected the input.
            buttons: Unsupported button names.
            sticks: Unsupported stick side names.
        """
        super().__init__(message)
        self.profile_kind = profile_kind
        self.buttons = buttons
        self.sticks = sticks
