"""Public gamepad API."""

from swbt.diagnostics import DiagnosticsConfig, GamepadStatus
from swbt.errors import InvalidInputError
from swbt.gamepad._config import SwitchGamepadConfig, _ControllerSpec
from swbt.gamepad.connection import ConnectionResult
from swbt.gamepad.interface import SwitchGamepad
from swbt.gamepad.output import OutputReportDispatcher
from swbt.gamepad.runtime import ControllerRuntime
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.profiles.base import ControllerColors
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.state_store import InputStateStore
from swbt.transport.base import HidDeviceTransport


class _RuntimeBackedGamepad(SwitchGamepad):
    """Runtime-backed concrete gamepad base.

    The object owns the public API surface and delegates stateful
    controller work to an internal runtime.
    """

    _controller_spec = _ControllerSpec(profile=default_controller_profile())

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a gamepad object.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            key_store_path: Optional path used by the Bluetooth backend to persist keys.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)

    def _init_from_config(
        self,
        config: SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None,
        transport: HidDeviceTransport | None,
    ) -> None:
        self._runtime = ControllerRuntime.from_config(
            config,
            diagnostics=diagnostics,
            transport=transport,
        )

    @classmethod
    def _from_config(
        cls,
        config: SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> "_RuntimeBackedGamepad":
        """Create a concrete gamepad from an explicit resource configuration.

        Args:
            config: Resource configuration for the gamepad.
            diagnostics: Optional diagnostics configuration for trace output.
            transport: Optional HID transport instance.

        Returns:
            SwitchGamepad: A concrete gamepad configured from ``config``.

        Raises:
            InvalidInputError: ``config`` is invalid or omits ``adapter`` while no
                custom ``transport`` is supplied.
        """
        expected_kind = cls._controller_spec.profile.kind
        if config.profile.kind is not expected_kind:
            msg = f"{cls.__name__}._from_config requires a {expected_kind.value} profile"
            raise InvalidInputError(msg)
        gamepad = cls.__new__(cls)
        gamepad._init_from_config(
            config,
            diagnostics=diagnostics,
            transport=transport,
        )
        return gamepad

    @property
    def _state_store(self) -> InputStateStore:
        return self._runtime._state_store

    @property
    def _output_report_dispatcher(self) -> OutputReportDispatcher:
        return self._runtime._output_report_dispatcher

    async def open(self) -> None:
        """Open the configured transport.

        Opening prepares transport callbacks, diagnostics metadata, and the report
        loop. It does not start HID advertising, pairing, or active reconnect.

        Raises:
            TransportOpenError: Raised by the transport when the adapter cannot be opened.
            Exception: Propagates unexpected transport open failures after cleanup.
        """
        await self._runtime.open()

    async def pair(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Start pairing advertising and wait for a host connection.

        Args:
            timeout: Maximum seconds to wait for a connection. ``None`` waits until
                the host connects.

        Raises:
            ConnectionTimeoutError: The timeout elapsed before a connection completed.
            ClosedError: The transport was unavailable after opening.
        """
        await self._runtime.pair(timeout=timeout)

    async def reconnect(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Reconnect with exactly one bonded peer and raise on failure.

        Args:
            timeout: Maximum seconds for the active reconnect attempt. ``None`` uses
                the transport default.

        Raises:
            ConnectionFailedError: No single bonded peer was available or reconnect failed.
            ConnectionTimeoutError: The active reconnect attempt timed out.
        """
        await self._runtime.reconnect(timeout=timeout)

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
        """
        return await self._runtime.try_reconnect(timeout=timeout)

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
            ConnectionResult: Route and status chosen by reconnect or pairing fallback.
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

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.press(*buttons)

    async def apply(self, state: InputState) -> None:
        """Replace the current input state without immediate transmission.

        Args:
            state: Complete input state to commit.

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.apply(state)

    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> None:
        """Replace one or both stick positions without immediate transmission.

        Args:
            left: Optional replacement for the left stick.
            right: Optional replacement for the right stick.

        Raises:
            InvalidInputError: ``left`` or ``right`` is not a ``Stick``.

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.sticks(left=left, right=right)

    async def lstick(self, stick: Stick) -> None:
        """Replace the left stick position without immediate transmission.

        Args:
            stick: Replacement for the left stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.lstick(stick)

    async def rstick(self, stick: Stick) -> None:
        """Replace the right stick position without immediate transmission.

        Args:
            stick: Replacement for the right stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.rstick(stick)

    async def imu(self, *frames: IMUFrame) -> None:
        """Replace IMU frames without immediate transmission.

        Args:
            frames: One ``IMUFrame`` to repeat across all three IMU slots, or exactly
                three frames to store in order.

        Raises:
            InvalidInputError: The frame count is not one or three, or any value is
                not an ``IMUFrame``.

        This updates local IMU state only and does not send an immediate input report.
        """
        await self._runtime.imu(*frames)

    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state.

        Args:
            buttons: Buttons to remove from the current button set.

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.release(*buttons)

    async def neutral(self) -> None:
        """Return local input state to ``InputState.neutral()`` without immediate transmission."""
        await self._runtime.neutral()

    async def tap(self, *buttons: Button, duration: float = 0.08) -> None:
        """Send a short connected button action.

        Args:
            buttons: Buttons to press for the tap.
            duration: Seconds to keep the buttons pressed before release.

        Raises:
            ClosedError: The gamepad is not open and cannot send input reports.

        The tap sends immediate press and release input reports. The release step
        removes only the buttons supplied to this call, preserving other held buttons.
        """
        await self._runtime.tap(*buttons, duration=duration)

    def status(self) -> GamepadStatus:
        """Return the current gamepad status.

        Returns:
            GamepadStatus: Connection state, report counters, rumble bytes, and last error.
        """
        return self._runtime.status()

    def snapshot(self) -> InputState:
        """Return the latest committed input state.

        Returns:
            InputState: Immutable snapshot of the current input state.
        """
        return self._runtime.snapshot()


class ProController(_RuntimeBackedGamepad):
    """Runtime-backed Pro Controller-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=default_controller_profile())


class JoyConL(_RuntimeBackedGamepad):
    """Runtime-backed Joy-Con L-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=JoyConLeftProfile())

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a left Joy-Con-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            key_store_path: Optional path used by the Bluetooth backend to persist keys.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)


class JoyConR(_RuntimeBackedGamepad):
    """Runtime-backed Joy-Con R-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=JoyConRightProfile())

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a right Joy-Con-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            key_store_path: Optional path used by the Bluetooth backend to persist keys.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)
