"""Public abstract gamepad types and shared runtime delegation."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from types import TracebackType
from typing import ClassVar, Literal, Self

from swbt.diagnostics import DiagnosticsConfig, GamepadStatus
from swbt.gamepad._config import _GamepadConfig
from swbt.gamepad.connection import ConnectionResult
from swbt.gamepad.runtime import ControllerRuntime
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.profiles.base import ControllerColors, ControllerProfile
from swbt.transport._pairing_profile import LocalAddress, PairingProfile


class SwitchGamepad(ABC):
    """Shared public type for NX-compatible virtual gamepads.

    Use ``PeriodicSwitchGamepad`` or ``DirectSwitchGamepad`` when a type
    annotation must express who owns the input-report schedule. Common input
    operations commit local state on periodic gamepads; on direct gamepads they
    send one input report and commit only after transmission succeeds.

    Concrete controllers select a controller identity and initialize the
    internal runtime. This class implements the shared public operations by
    delegating stateful controller work to that runtime.
    """

    _profile: ClassVar[ControllerProfile]
    _reporting_mode: ClassVar[Literal["periodic", "direct"]] = "periodic"
    _runtime: ControllerRuntime

    @abstractmethod
    def __init__(self) -> None:
        """Define a concrete controller identity and public constructor."""

    def _initialize_runtime(
        self,
        *,
        adapter: str | None,
        profile_path: str | None,
        report_period_us: int | None,
        controller_colors: ControllerColors | None,
        diagnostics: DiagnosticsConfig | None,
    ) -> None:
        config = _GamepadConfig(
            adapter=adapter,
            profile_path=profile_path,
            profile=self._profile,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._runtime = ControllerRuntime(
            config,
            diagnostics=diagnostics,
            reporting_mode=self._reporting_mode,
        )

    @classmethod
    async def _create_pairing_profile(
        cls,
        *,
        profile_path: str,
        local_address: str | None,
        pair_timeout: float | None,
        construct: Callable[[], Self],
    ) -> Self:
        """Create a pairing profile, construct a controller, and pair it."""
        target = None if local_address is None else LocalAddress.parse(local_address)
        PairingProfile.create_new(
            profile_path,
            target,
            controller_kind=cls._profile.kind,
        )
        gamepad = construct()
        try:
            await gamepad.pair(timeout=pair_timeout)
        except BaseException:
            await gamepad.close(neutral=False)
            raise
        return gamepad

    async def __aenter__(self) -> Self:
        """Open the gamepad for an async context manager.

        Returns:
            This gamepad after resources have been opened.
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

    async def open(self) -> None:
        """Open the configured transport.

        Opening prepares transport callbacks, diagnostics metadata, and the
        reporting-type resources. It does not start HID advertising, pairing,
        or active reconnect.

        Raises:
            TransportOpenError: The configured transport cannot be opened.
            Exception: Unexpected lower-layer transport failures are propagated
                after cleanup.
        """
        await self._runtime.open()

    async def pair(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Start pairing and wait until the controller can accept normal input.

        Args:
            timeout: Maximum seconds for link connection, protocol initialization,
                and normal-input readiness. ``None`` waits without a deadline.

        Raises:
            ConnectionTimeoutError: The timeout elapsed before a connection completed.
            ClosedError: The transport was unavailable after opening.
        """
        await self._runtime.pair(timeout=timeout)

    async def reconnect(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Reconnect with one bonded peer and wait until normal input can begin.

        Args:
            timeout: Maximum seconds for the active reconnect attempt and
                normal-input readiness. ``None`` uses the transport default.

        Raises:
            ConnectionFailedError: No single bonded peer was available or reconnect failed.
            ConnectionTimeoutError: The reconnect or normal-input readiness timed out.
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """
        await self._runtime.reconnect(timeout=timeout)

    async def try_reconnect(
        self,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> ConnectionResult:
        """Try active reconnect with exactly one bonded peer.

        Args:
            timeout: Maximum seconds for the active reconnect attempt and
                normal-input readiness. ``None`` uses the transport default.

        Returns:
            Reconnect route, status, selected peer, and peer count. ``connected``
            means that normal input can begin.

        Raises:
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """
        return await self._runtime.try_reconnect(timeout=timeout)

    async def connect(
        self,
        *,
        timeout: float | None = None,  # noqa: ASYNC109
        allow_pairing: bool = False,
    ) -> None:
        """Connect by bonded reconnect or pairing and wait for normal-input readiness.

        Args:
            timeout: Maximum seconds for each connection attempt. ``None`` uses the
                lower layer default.
            allow_pairing: If ``True``, run pairing when no bonded peer is available.

        Raises:
            ConnectionFailedError: The connection attempt finished without connecting.
            ConnectionTimeoutError: The connection attempt timed out.
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """
        await self._runtime.connect(timeout=timeout, allow_pairing=allow_pairing)

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
            Route and status chosen by reconnect or pairing fallback. ``connected``
            means that normal input can begin.

        Raises:
            InvalidKeyStoreError: The key store cannot identify one current peer.
        """
        return await self._runtime.try_connect(
            timeout=timeout,
            allow_pairing=allow_pairing,
        )

    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state.

        Args:
            neutral: If ``True``, send a trailing neutral report before disconnect
                when a connection is active.
        """
        await self._runtime.close(neutral=neutral)

    async def press(self, *buttons: Button) -> None:
        """Add buttons to the current input state.

        Args:
            buttons: Buttons to add to the current button set.

        Raises:
            InvalidInputError: Any value is not a ``Button``.
            UnsupportedInputError: The controller profile does not support a button.

        Completion follows the reporting type: periodic gamepads commit local
        state, while direct gamepads send one input report and then commit.
        """
        await self._runtime.press(*buttons)

    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> None:
        """Replace one or both stick positions according to the reporting type.

        Args:
            left: Optional replacement for the left stick.
            right: Optional replacement for the right stick.

        Raises:
            InvalidInputError: ``left`` or ``right`` is not a ``Stick``.
            UnsupportedInputError: The controller profile does not support a supplied stick.
        """
        await self._runtime.sticks(left=left, right=right)

    async def lstick(self, stick: Stick) -> None:
        """Replace the left stick position according to the reporting type.

        Args:
            stick: Replacement for the left stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.
            UnsupportedInputError: The controller profile does not support left stick input.
        """
        await self._runtime.lstick(stick)

    async def rstick(self, stick: Stick) -> None:
        """Replace the right stick position according to the reporting type.

        Args:
            stick: Replacement for the right stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.
            UnsupportedInputError: The controller profile does not support right stick input.
        """
        await self._runtime.rstick(stick)

    async def imu(self, *frames: IMUFrame) -> None:
        """Replace IMU frames according to the reporting type.

        Args:
            frames: One ``IMUFrame`` to repeat across all three IMU slots, or exactly
                three frames to store in order.

        Raises:
            InvalidInputError: The frame count is not one or three, or any value is
                not an ``IMUFrame``.
        """
        await self._runtime.imu(*frames)

    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state.

        Args:
            buttons: Buttons to remove from the current button set.

        Raises:
            InvalidInputError: Any value is not a ``Button``.
            UnsupportedInputError: The controller profile does not support a button.
        """
        await self._runtime.release(*buttons)

    async def neutral(self) -> None:
        """Apply ``InputState.neutral()`` according to the reporting type."""
        await self._runtime.neutral()

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
        await self._runtime.tap(*buttons, duration=duration)

    def status(self) -> GamepadStatus:
        """Return the current gamepad status.

        Returns:
            Connection state, report counters, rumble bytes, and last error.
        """
        return self._runtime.status()

    def snapshot(self) -> InputState:
        """Return the latest committed input state.

        A periodic gamepad returns its latest local state. A direct gamepad
        returns the last state whose input report was sent successfully.

        Returns:
            Immutable snapshot of the current input state.
        """
        return self._runtime.snapshot()


class PeriodicSwitchGamepad(SwitchGamepad):
    """Abstract gamepad whose input report schedule is owned by the library."""

    async def apply(self, state: InputState) -> None:
        """Replace the current local input state without immediate transmission.

        Args:
            state: Complete input state to commit.

        Raises:
            InvalidInputError: ``state`` is not an ``InputState``.
            UnsupportedInputError: The controller profile does not support part of
                the supplied state.
        """
        await self._runtime.apply(state)

    @classmethod
    async def create_profile(
        cls,
        *,
        adapter: str,
        profile_path: str,
        local_address: str | None = None,
        pair_timeout: float | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> Self:
        """Create a new periodic pairing profile and pair it.

        Args:
            adapter: Bumble adapter moniker. An explicit local address may prepare
                volatile adapter identity state.
            profile_path: New path for the swbt-owned profile JSON.
            local_address: Optional individual locally administered Bluetooth address.
                ``None`` uses the adapter's current default address without rewriting it.
            pair_timeout: Maximum seconds for link connection and protocol initialization.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Returns:
            A periodic controller ready to accept normal input. The caller owns
            its lifetime.

        Raises:
            ValueError: ``local_address`` is invalid.
            FileExistsError: ``profile_path`` already exists.
            Exception: Profile preparation or pairing failed. The created profile remains
                available for a later retry.
        """
        return await cls._create_pairing_profile(
            profile_path=profile_path,
            local_address=local_address,
            pair_timeout=pair_timeout,
            construct=lambda: cls(
                adapter=adapter,  # ty: ignore[unknown-argument]
                profile_path=profile_path,  # ty: ignore[unknown-argument]
                report_period_us=report_period_us,  # ty: ignore[unknown-argument]
                controller_colors=controller_colors,  # ty: ignore[unknown-argument]
                diagnostics=diagnostics,  # ty: ignore[unknown-argument]
            ),
        )


class DirectSwitchGamepad(SwitchGamepad):
    """Abstract gamepad whose input report schedule is owned by the caller."""

    _reporting_mode = "direct"

    async def send(self, state: InputState) -> None:
        """Send one complete input state and commit it after transmission.

        Args:
            state: Complete input state to send.

        Raises:
            ClosedError: The gamepad is not connected.
            InvalidInputError: ``state`` is not an ``InputState``.
            UnsupportedInputError: The controller profile does not support part of
                the supplied state.
        """
        await self._runtime.send(state)

    @classmethod
    async def create_profile(
        cls,
        *,
        adapter: str,
        profile_path: str,
        local_address: str | None = None,
        pair_timeout: float | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> Self:
        """Create a new direct pairing profile and pair it.

        Args:
            adapter: Bumble adapter moniker. An explicit local address may prepare
                volatile adapter identity state.
            profile_path: New path for the swbt-owned profile JSON.
            local_address: Optional individual locally administered Bluetooth address.
                ``None`` uses the adapter's current default address without rewriting it.
            pair_timeout: Maximum seconds for link connection and protocol initialization.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Returns:
            A direct controller ready to accept normal input. The caller owns
            its lifetime.

        Raises:
            ValueError: ``local_address`` is invalid.
            FileExistsError: ``profile_path`` already exists.
            Exception: Profile preparation or pairing failed. The created profile remains
                available for a later retry.
        """
        return await cls._create_pairing_profile(
            profile_path=profile_path,
            local_address=local_address,
            pair_timeout=pair_timeout,
            construct=lambda: cls(
                adapter=adapter,  # ty: ignore[unknown-argument]
                profile_path=profile_path,  # ty: ignore[unknown-argument]
                controller_colors=controller_colors,  # ty: ignore[unknown-argument]
                diagnostics=diagnostics,  # ty: ignore[unknown-argument]
            ),
        )
