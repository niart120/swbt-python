"""Abstract public gamepad interface."""

from abc import ABC, abstractmethod
from types import TracebackType

from swbt.diagnostics import GamepadStatus
from swbt.gamepad.connection import ConnectionResult
from swbt.input import Button, IMUFrame, InputState, Stick


class SwitchGamepad(ABC):
    """Shared public interface for NX-compatible virtual gamepads."""

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
        """Open the configured transport."""

    @abstractmethod
    async def pair(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Start pairing advertising and wait for a host connection."""

    @abstractmethod
    async def reconnect(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Reconnect with exactly one bonded peer and raise on failure."""

    @abstractmethod
    async def try_reconnect(
        self,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> ConnectionResult:
        """Try active reconnect with exactly one bonded peer."""

    @abstractmethod
    async def connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> None:
        """Connect using bonded reconnect first, then optional pairing fallback."""

    @abstractmethod
    async def try_connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> ConnectionResult:
        """Try bonded reconnect first, then optional pairing fallback."""

    @abstractmethod
    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state."""

    @abstractmethod
    async def press(self, *buttons: Button) -> None:
        """Add buttons to the current input state."""

    @abstractmethod
    async def apply(self, state: InputState) -> None:
        """Replace the current input state without immediate transmission."""

    @abstractmethod
    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> None:
        """Replace one or both stick positions without immediate transmission."""

    @abstractmethod
    async def lstick(self, stick: Stick) -> None:
        """Replace the left stick position without immediate transmission."""

    @abstractmethod
    async def rstick(self, stick: Stick) -> None:
        """Replace the right stick position without immediate transmission."""

    @abstractmethod
    async def imu(self, *frames: IMUFrame) -> None:
        """Replace IMU frames without immediate transmission."""

    @abstractmethod
    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state."""

    @abstractmethod
    async def neutral(self) -> None:
        """Return local input state to ``InputState.neutral()`` without immediate transmission."""

    @abstractmethod
    async def tap(self, *buttons: Button, duration: float = 0.08) -> None:
        """Send a short connected button action."""

    @abstractmethod
    def status(self) -> GamepadStatus:
        """Return the current gamepad status."""

    @abstractmethod
    def snapshot(self) -> InputState:
        """Return the latest committed input state."""
