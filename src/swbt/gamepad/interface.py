"""Abstract public gamepad interface."""

from abc import ABC, abstractmethod
from types import TracebackType

from swbt.diagnostics import GamepadStatus
from swbt.gamepad.connection import ConnectionResult
from swbt.input import Button, IMUFrame, InputState, Stick


class SwitchGamepad(ABC):
    """Shared public interface for NX-compatible virtual gamepads.

    Use this abstract base class for type annotations. Construct
    ``ProController``, ``JoyConL``, or ``JoyConR`` for a concrete virtual
    controller.
    """

    async def __aenter__(self) -> "SwitchGamepad":
        """Open the gamepad for an async context manager.

        Returns:
            SwitchGamepad: This gamepad after resources have been opened.
        """
        await self.open()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close the gamepad when leaving an async context manager.

        Args:
            exc_type: Exception type from the managed block, if one was raised.
            exc: Exception instance from the managed block, if one was raised.
            traceback: Traceback from the managed block, if one was raised.
        """
        _ = (exc_type, exc, traceback)
        await self.close(neutral=True)

    @abstractmethod
    async def open(self) -> None:
        """Open the configured transport.

        Opening prepares transport callbacks, diagnostics metadata, and the report
        loop. It does not start HID advertising, pairing, or active reconnect.

        Raises:
            TransportOpenError: The configured transport cannot be opened.
            Exception: Unexpected lower-layer transport failures are propagated
                after cleanup.
        """

    @abstractmethod
    async def pair(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Start pairing advertising and wait for a host connection.

        Args:
            timeout: Maximum seconds to wait for a connection. ``None`` waits until
                the host connects.

        Raises:
            ConnectionTimeoutError: The timeout elapsed before a connection completed.
            ClosedError: The transport was unavailable after opening.
        """

    @abstractmethod
    async def reconnect(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Reconnect with exactly one bonded peer and raise on failure.

        Args:
            timeout: Maximum seconds for the active reconnect attempt. ``None`` uses
                the transport default.

        Raises:
            ConnectionFailedError: No single bonded peer was available or reconnect failed.
            ConnectionTimeoutError: The active reconnect attempt timed out.
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """

    @abstractmethod
    async def try_reconnect(
        self,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> ConnectionResult:
        """Try active reconnect with exactly one bonded peer.

        Args:
            timeout: Maximum seconds for the active reconnect attempt. ``None`` uses
                the transport default.

        Returns:
            ConnectionResult: Reconnect route, status, selected peer, and peer count.

        Raises:
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """

    @abstractmethod
    async def connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> None:
        """Connect using bonded reconnect first, then optional pairing fallback.

        Args:
            timeout: Maximum seconds for each connection attempt. ``None`` uses the
                lower layer default.
            allow_pairing: If ``True``, run pairing when no bonded peer is available.

        Raises:
            ConnectionFailedError: The connection attempt finished without connecting.
            ConnectionTimeoutError: The connection attempt timed out.
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """

    @abstractmethod
    async def try_connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> ConnectionResult:
        """Try bonded reconnect first, then optional pairing fallback.

        Args:
            timeout: Maximum seconds for each connection attempt. ``None`` uses the
                lower layer default.
            allow_pairing: If ``True``, run pairing when no bonded peer is available.

        Returns:
            ConnectionResult: Route and status chosen by reconnect or pairing fallback.

        Raises:
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """

    @abstractmethod
    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state.

        Args:
            neutral: If ``True``, send a trailing neutral report before disconnect
                when a connection is active.
        """

    @abstractmethod
    async def press(self, *buttons: Button) -> None:
        """Add buttons to the current input state.

        Args:
            buttons: Buttons to add to the current button set.

        Raises:
            InvalidInputError: Any value is not a ``Button``.
            UnsupportedInputError: The controller profile does not support a button.

        This updates local state only and does not send an immediate input report.
        """

    @abstractmethod
    async def apply(self, state: InputState) -> None:
        """Replace the current input state without immediate transmission.

        Args:
            state: Complete input state to commit.

        Raises:
            InvalidInputError: ``state`` is not an ``InputState``.
            UnsupportedInputError: The controller profile does not support part of
                the supplied state.
        """

    @abstractmethod
    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> None:
        """Replace one or both stick positions without immediate transmission.

        Args:
            left: Optional replacement for the left stick.
            right: Optional replacement for the right stick.

        Raises:
            InvalidInputError: ``left`` or ``right`` is not a ``Stick``.
            UnsupportedInputError: The controller profile does not support a supplied stick.
        """

    @abstractmethod
    async def lstick(self, stick: Stick) -> None:
        """Replace the left stick position without immediate transmission.

        Args:
            stick: Replacement for the left stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.
            UnsupportedInputError: The controller profile does not support left stick input.
        """

    @abstractmethod
    async def rstick(self, stick: Stick) -> None:
        """Replace the right stick position without immediate transmission.

        Args:
            stick: Replacement for the right stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.
            UnsupportedInputError: The controller profile does not support right stick input.
        """

    @abstractmethod
    async def imu(self, *frames: IMUFrame) -> None:
        """Replace IMU frames without immediate transmission.

        Args:
            frames: One ``IMUFrame`` to repeat across all three IMU slots, or exactly
                three frames to store in order.

        Raises:
            InvalidInputError: The frame count is not one or three, or any value is
                not an ``IMUFrame``.
        """

    @abstractmethod
    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state.

        Args:
            buttons: Buttons to remove from the current button set.

        Raises:
            InvalidInputError: Any value is not a ``Button``.
            UnsupportedInputError: The controller profile does not support a button.
        """

    @abstractmethod
    async def neutral(self) -> None:
        """Return local input state to ``InputState.neutral()`` without immediate transmission."""

    @abstractmethod
    async def tap(self, *buttons: Button, duration: float = 0.08) -> None:
        """Send a short connected button action.

        Args:
            buttons: Buttons to press for the tap.
            duration: Seconds to keep the buttons pressed before release.

        Raises:
            ClosedError: The gamepad is not open and cannot send input reports.
            InvalidInputError: Any value is not a ``Button``.
            UnsupportedInputError: The controller profile does not support a button.
        """

    @abstractmethod
    def status(self) -> GamepadStatus:
        """Return the current gamepad status.

        Returns:
            GamepadStatus: Connection state, report counters, rumble bytes, and last error.
        """

    @abstractmethod
    def snapshot(self) -> InputState:
        """Return the latest committed input state.

        Returns:
            InputState: Immutable snapshot of the current input state.
        """
