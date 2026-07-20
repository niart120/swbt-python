"""Public gamepad API."""

from typing import ClassVar, Literal, Self

from swbt.diagnostics import DiagnosticsConfig, GamepadStatus
from swbt.errors import InvalidInputError
from swbt.gamepad._config import _ControllerSpec, _SwitchGamepadConfig
from swbt.gamepad.connection import ConnectionResult
from swbt.gamepad.interface import (
    DirectSwitchGamepad,
    PeriodicSwitchGamepad,
)
from swbt.gamepad.output import OutputReportDispatcher
from swbt.gamepad.runtime import ControllerRuntime
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.profiles.base import ControllerColors
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.state_store import InputStateStore
from swbt.transport._exp_local_address import (
    ExpLocalAddress,
    ExpLocalControllerKind,
    ExpLocalProfile,
)
from swbt.transport.base import HidDeviceTransport


class _RuntimeBackedGamepad:
    """Runtime-backed concrete gamepad base.

    The object owns the public API surface and delegates stateful
    controller work to an internal runtime.
    """

    _controller_spec = _ControllerSpec(profile=default_controller_profile())
    _reporting_mode: ClassVar[Literal["periodic", "direct"]] = "periodic"

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
        config: _SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None,
        transport: HidDeviceTransport | None,
    ) -> None:
        self._runtime = ControllerRuntime.from_config(
            config,
            diagnostics=diagnostics,
            reporting_mode=self._reporting_mode,
            transport=transport,
        )

    @classmethod
    def _from_config(
        cls,
        config: _SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> Self:
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

        Opening prepares transport callbacks, diagnostics metadata, and the
        reporting-type resources. It does not start HID advertising, pairing,
        or active reconnect.

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

        A periodic controller commits local state. A direct controller sends one
        input report and commits only after transmission succeeds.
        """
        await self._runtime.press(*buttons)

    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> None:
        """Replace one or both stick positions according to the reporting type.

        Args:
            left: Optional replacement for the left stick.
            right: Optional replacement for the right stick.

        Raises:
            InvalidInputError: ``left`` or ``right`` is not a ``Stick``.

        A periodic controller commits local state. A direct controller sends one
        input report and commits only after transmission succeeds.
        """
        await self._runtime.sticks(left=left, right=right)

    async def lstick(self, stick: Stick) -> None:
        """Replace the left stick position according to the reporting type.

        Args:
            stick: Replacement for the left stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.

        A periodic controller commits local state. A direct controller sends one
        input report and commits only after transmission succeeds.
        """
        await self._runtime.lstick(stick)

    async def rstick(self, stick: Stick) -> None:
        """Replace the right stick position according to the reporting type.

        Args:
            stick: Replacement for the right stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.

        A periodic controller commits local state. A direct controller sends one
        input report and commits only after transmission succeeds.
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

        This updates local IMU state only and does not send an immediate input report.
        """
        await self._runtime.imu(*frames)

    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state.

        Args:
            buttons: Buttons to remove from the current button set.

        A periodic controller commits local state. A direct controller sends one
        input report and commits only after transmission succeeds.
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

        A periodic controller returns its latest local state. A direct
        controller returns the last state sent successfully.

        Returns:
            InputState: Immutable snapshot of the current input state.
        """
        return self._runtime.snapshot()


class _PeriodicRuntimeBackedGamepad(_RuntimeBackedGamepad, PeriodicSwitchGamepad):
    """Runtime-backed gamepad with library-owned periodic input transmission."""

    async def apply(self, state: InputState) -> None:
        """Replace the current input state without immediate transmission.

        Args:
            state: Complete input state to commit.

        This updates local state only and does not send an immediate input report.
        """
        await self._runtime.apply(state)

    @classmethod
    async def _create_exp_local_profile(
        cls,
        *,
        controller_kind: ExpLocalControllerKind,
        adapter: str,
        profile_path: str,
        exp_local_address: str,
        pair_timeout: float | None,
        report_period_us: int | None,
        controller_colors: ControllerColors | None,
        diagnostics: DiagnosticsConfig | None,
    ) -> Self:
        """Create, pair, and clean up a concrete periodic controller profile."""
        target = ExpLocalAddress.parse(exp_local_address)
        ExpLocalProfile.create_new(
            profile_path,
            target,
            controller_kind=controller_kind,
        )
        gamepad = cls(
            adapter=adapter,
            profile_path=profile_path,  # ty: ignore[unknown-argument]
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )
        try:
            await gamepad.pair(timeout=pair_timeout)
        except BaseException:
            await gamepad.close(neutral=False)
            raise
        return gamepad


class _DirectRuntimeBackedGamepad(_RuntimeBackedGamepad, DirectSwitchGamepad):
    """Runtime-backed gamepad with caller-owned input transmission."""

    _reporting_mode = "direct"

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a direct-reporting gamepad object.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            key_store_path: Optional path used by the Bluetooth backend to persist keys.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=None,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)

    async def send(self, state: InputState) -> None:
        """Send one complete input state and commit it after transmission.

        Args:
            state: Complete input state to send.
        """
        await self._runtime.send(state)


class ProController(_PeriodicRuntimeBackedGamepad):
    """Runtime-backed Pro Controller-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=default_controller_profile())

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a Pro Controller-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned exp local address profile path.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: adapter is omitted or report_period_us is not positive.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=None,
            profile_path=profile_path,
            exp_local_controller_kind="pro",
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)

    @classmethod
    async def create_profile(
        cls,
        *,
        adapter: str,
        profile_path: str,
        exp_local_address: str,
        pair_timeout: float | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> Self:
        """Create a new exp local address profile and pair it.

        Args:
            adapter: Bumble adapter moniker used for volatile identity preparation.
            profile_path: New path for the swbt-owned profile JSON.
            exp_local_address: Individual locally administered Bluetooth address.
            pair_timeout: Maximum seconds to wait for the initial pairing connection.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Returns:
            ProController: The paired controller. The caller owns its lifetime.

        Raises:
            ValueError: ``exp_local_address`` is invalid.
            FileExistsError: ``profile_path`` already exists.
            Exception: Profile preparation or pairing failed. The created profile remains
                available for a later retry.
        """
        return await cls._create_exp_local_profile(
            controller_kind="pro",
            adapter=adapter,
            profile_path=profile_path,
            exp_local_address=exp_local_address,
            pair_timeout=pair_timeout,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class JoyConL(_PeriodicRuntimeBackedGamepad):
    """Runtime-backed Joy-Con L-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=JoyConLeftProfile())

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a left Joy-Con-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            key_store_path: Optional path used with the adapter's native address.
            profile_path: Optional swbt-owned exp local address profile path.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=key_store_path,
            profile_path=profile_path,
            exp_local_controller_kind="joycon_l",
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)

    @classmethod
    async def create_profile(
        cls,
        *,
        adapter: str,
        profile_path: str,
        exp_local_address: str,
        pair_timeout: float | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> Self:
        """Create a new Joy-Con L exp local address profile and pair it.

        Args:
            adapter: Bumble adapter moniker used for volatile identity preparation.
            profile_path: New path for the swbt-owned profile JSON.
            exp_local_address: Individual locally administered Bluetooth address.
            pair_timeout: Maximum seconds to wait for the initial pairing connection.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Returns:
            JoyConL: The paired controller. The caller owns its lifetime.

        Raises:
            ValueError: ``exp_local_address`` is invalid.
            FileExistsError: ``profile_path`` already exists.
            Exception: Profile preparation or pairing failed. The created profile remains
                available for a later retry.
        """
        return await cls._create_exp_local_profile(
            controller_kind="joycon_l",
            adapter=adapter,
            profile_path=profile_path,
            exp_local_address=exp_local_address,
            pair_timeout=pair_timeout,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class JoyConR(_PeriodicRuntimeBackedGamepad):
    """Runtime-backed Joy-Con R-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=JoyConRightProfile())

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a right Joy-Con-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            key_store_path: Optional path used with the adapter's native address.
            profile_path: Optional swbt-owned exp local address profile path.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        config = self._controller_spec.build_config(
            adapter=adapter,
            key_store_path=key_store_path,
            profile_path=profile_path,
            exp_local_controller_kind="joycon_r",
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=None)

    @classmethod
    async def create_profile(
        cls,
        *,
        adapter: str,
        profile_path: str,
        exp_local_address: str,
        pair_timeout: float | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> Self:
        """Create a new Joy-Con R exp local address profile and pair it.

        Args:
            adapter: Bumble adapter moniker used for volatile identity preparation.
            profile_path: New path for the swbt-owned profile JSON.
            exp_local_address: Individual locally administered Bluetooth address.
            pair_timeout: Maximum seconds to wait for the initial pairing connection.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Returns:
            JoyConR: The paired controller. The caller owns its lifetime.

        Raises:
            ValueError: ``exp_local_address`` is invalid.
            FileExistsError: ``profile_path`` already exists.
            Exception: Profile preparation or pairing failed. The created profile remains
                available for a later retry.
        """
        return await cls._create_exp_local_profile(
            controller_kind="joycon_r",
            adapter=adapter,
            profile_path=profile_path,
            exp_local_address=exp_local_address,
            pair_timeout=pair_timeout,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class DirectProController(_DirectRuntimeBackedGamepad):
    """Direct-reporting Pro Controller-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=default_controller_profile())


class DirectJoyConL(_DirectRuntimeBackedGamepad):
    """Direct-reporting Joy-Con L-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=JoyConLeftProfile())


class DirectJoyConR(_DirectRuntimeBackedGamepad):
    """Direct-reporting Joy-Con R-compatible gamepad."""

    _controller_spec = _ControllerSpec(profile=JoyConRightProfile())
