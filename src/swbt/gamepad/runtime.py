"""Stateful runtime for gamepad lifecycle and input behavior."""

import asyncio
from dataclasses import replace
from types import TracebackType

import swbt.gamepad as gamepad_module
from swbt.diagnostics import DiagnosticsConfig, DiagnosticsRecorder, GamepadStatus
from swbt.errors import (
    ClosedError,
    ConnectionTimeoutError,
    InvalidInputError,
    SwbtError,
)
from swbt.gamepad._config import _RuntimeConfig, _SwitchGamepadConfig
from swbt.gamepad.connection import (
    ConnectionResult,
    ConnectionWorkflow,
    raise_if_connection_failed,
)
from swbt.gamepad.output import OutputReportDispatcher
from swbt.gamepad.transport_factory import (
    _BumbleTransportFactory,
    _StaticTransportFactory,
)
from swbt.input import Button, IMUFrame, InputState, Stick
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.profiles.base import ControllerColors
from swbt.protocol.session import SwitchHidSession
from swbt.protocol.subcommand import SubcommandResponder
from swbt.report_loop import ReportLoop
from swbt.state_store import InputStateStore
from swbt.transport.base import DisconnectRequestResult, HidDeviceTransport


class ControllerRuntime:
    """Stateful NX-compatible virtual gamepad runtime.

    The runtime owns the input state, report loop, diagnostics recorder, and HID
    transport lifetime.
    """

    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        report_period_us: int | None = None,
        device_name: str | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> None:
        """Create a gamepad object.

        Args:
            adapter: Bumble adapter moniker used when the default transport is created.
                Required unless a custom transport is supplied.
            key_store_path: Optional path used by the default transport to persist keys.
            report_period_us: Optional periodic input report interval in microseconds.
            device_name: Optional HID device name passed to the default transport.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.
            transport: Optional HID transport instance. When supplied, no Bumble
                transport is created by the constructor.

        Raises:
            InvalidInputError: ``adapter`` is omitted for the default transport or
                ``report_period_us`` is not positive.
        """
        config = _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            device_name=device_name,
            controller_colors=controller_colors,
        )
        self._init_from_config(config, diagnostics=diagnostics, transport=transport)

    def _init_from_config(
        self,
        config: _SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None,
        transport: HidDeviceTransport | None,
    ) -> None:
        runtime_config = _RuntimeConfig.from_public_config(config)
        if transport is None and runtime_config.adapter is None:
            msg = "adapter is required when no custom transport is supplied"
            raise InvalidInputError(msg)
        self._config = runtime_config
        self._transport = transport
        self._transport_was_injected = transport is not None
        if transport is None:
            self._transport_factory = _BumbleTransportFactory()
        else:
            self._transport_factory = _StaticTransportFactory(transport)
        self._state_store = InputStateStore()
        self._diagnostics = DiagnosticsRecorder(
            trace_writer=diagnostics.trace_writer if diagnostics is not None else None
        )
        self._controller_profile = replace(
            self._config.profile,
            controller_colors=self._config.controller_colors
            or self._config.profile.controller_colors,
        )
        self._protocol_session = SwitchHidSession(self._controller_profile)
        self._output_report_dispatcher = OutputReportDispatcher(
            diagnostics=self._diagnostics,
            require_reply_sender=self._require_subcommand_reply_sender,
            send_subcommand_reply=self._send_subcommand_reply,
            state_store=self._state_store,
            subcommand_responder=SubcommandResponder(
                profile=self._controller_profile,
                session=self._protocol_session,
            ),
        )
        self._report_loop: ReportLoop | None = None
        self._lifecycle_lock = asyncio.Lock()
        self._connected_event = asyncio.Event()
        self._disconnect_event = asyncio.Event()
        self._connection_state = "closed"
        self._is_open = False
        self._close_in_progress = False
        self._configured_device_info_bluetooth_address: bytes | None = None
        self._connection_workflow = ConnectionWorkflow(
            clear_connected=self._connected_event.clear,
            close_neutral=self._close_neutral_for_connection_workflow,
            diagnostics=self._diagnostics,
            ensure_open=self.open,
            get_transport=self._connection_transport,
            key_store_path=self._config.key_store_path,
            pair=self._pair_for_connection_workflow,
            set_connection_state=self._set_connection_state,
            transport_was_injected=self._transport_was_injected,
            wait_for_connected=self._wait_for_reconnect_connected_for_workflow,
        )

    @classmethod
    def from_config(
        cls,
        config: _SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> "ControllerRuntime":
        """Create a runtime from an explicit resource configuration.

        Args:
            config: Resource configuration for the runtime.
            diagnostics: Optional diagnostics configuration for trace output.
            transport: Optional HID transport instance.

        Returns:
            ControllerRuntime: A runtime configured from ``config``.
        """
        runtime = cls.__new__(cls)
        runtime._init_from_config(
            config,
            diagnostics=diagnostics,
            transport=transport,
        )
        return runtime

    async def __aenter__(self) -> "ControllerRuntime":
        """Open the runtime for an async context manager.

        Returns:
            ControllerRuntime: This runtime after resources have been opened.
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

        Opening prepares transport callbacks, diagnostics metadata, and the report
        loop. It does not start HID advertising, pairing, or active reconnect.

        Raises:
            TransportOpenError: Raised by the transport when the adapter cannot be opened.
            Exception: Propagates unexpected transport open failures after cleanup.
        """
        async with self._lifecycle_lock:
            if self._is_open:
                return
            transport = self._ensure_transport()
            self._record_run_metadata()
            self._connection_state = "opening"
            self._reset_protocol_session()
            self._register_transport_callbacks()
            self._connected_event.clear()
            try:
                await transport.open()
                self._configure_device_info_bluetooth_address(transport)
                self._report_loop = ReportLoop(
                    transport=transport,
                    state_store=self._state_store,
                    report_period_us=self._config.report_period_us,
                    input_report_builder=InputReportBuilder(
                        self._controller_profile,
                    ),
                    session=self._protocol_session,
                    diagnostics=self._diagnostics,
                )
                self._connection_state = "opened"
                self._is_open = True
            except Exception:
                self._connection_state = "failed"
                await transport.close()
                self._report_loop = None
                self._is_open = False
                raise

    def _reset_protocol_session(self) -> None:
        """Create fresh host-requested state for the next HID connection generation."""
        self._protocol_session = SwitchHidSession(self._controller_profile)
        self._output_report_dispatcher.subcommand_responder = SubcommandResponder(
            profile=self._controller_profile,
            session=self._protocol_session,
        )
        self._configured_device_info_bluetooth_address = None

    async def pair(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Start pairing advertising and wait for a host connection.

        Args:
            timeout: Maximum seconds to wait for a connection. ``None`` waits until
                the host connects.

        Raises:
            ConnectionTimeoutError: The timeout elapsed before a connection completed.
            ClosedError: The transport was unavailable after opening.
        """
        if not self._is_open:
            await self.open()
        if self._transport is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        self._connection_state = "advertising"
        await self._transport.start_advertising()
        self._configure_device_info_bluetooth_address(self._transport)
        if timeout is None:
            await self._connected_event.wait()
            return
        try:
            async with asyncio.timeout(timeout):
                await self._connected_event.wait()
        except TimeoutError as error:
            msg = "connection timed out"
            connection_error = ConnectionTimeoutError(msg)
            self._diagnostics.record_event(
                "connection_timeout",
                state=self._connection_state,
                timeout=timeout,
            )
            self._diagnostics.record_error(connection_error, recoverable=True)
            raise connection_error from error

    async def reconnect(self, timeout: float | None = None) -> None:  # noqa: ASYNC109
        """Reconnect with exactly one bonded peer and raise on failure.

        Args:
            timeout: Maximum seconds for the active reconnect attempt. ``None`` uses
                the transport default.

        Raises:
            ConnectionFailedError: No single bonded peer was available or reconnect failed.
            ConnectionTimeoutError: The active reconnect attempt timed out.
        """
        result = await self.try_reconnect(timeout=timeout)
        raise_if_connection_failed(result)

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
        return await self._connection_workflow.try_reconnect(timeout=timeout)

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
        result = await self.try_connect(
            timeout=timeout,
            allow_pairing=allow_pairing,
        )
        raise_if_connection_failed(result)

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
        return await self._connection_workflow.try_connect(
            timeout=timeout,
            allow_pairing=allow_pairing,
        )

    async def close(self, *, neutral: bool = True) -> None:
        """Close the transport and leave the gamepad in a closed state.

        Args:
            neutral: If ``True``, send a trailing neutral report before disconnect
                when a connection is active.
        """
        async with self._lifecycle_lock:
            if not self._is_open or self._transport is None:
                return
            self._close_in_progress = True
            try:
                self._connection_state = "disconnecting"
                if neutral:
                    try:
                        await self._send_trailing_neutral_if_connected()
                    except Exception as error:  # noqa: BLE001
                        self._diagnostics.record_error(error, recoverable=True)
                if self._report_loop is not None:
                    await self._report_loop.stop()
                self._disconnect_event.clear()
                try:
                    disconnect_result = await self._transport.request_disconnect()
                except ClosedError as error:
                    disconnect_result = DisconnectRequestResult(
                        status="unavailable",
                        reason="transport_closed",
                        error_type=type(error).__name__,
                        message=str(error),
                    )
                self._record_disconnect_request_result(disconnect_result)
                if disconnect_result.status == "requested":
                    disconnect_closed = await self._wait_for_disconnect_request_closed()
                    if disconnect_closed:
                        self._diagnostics.record_event(
                            "disconnect_request_terminal",
                            status="closed",
                        )
                    else:
                        self._diagnostics.record_event(
                            "disconnect_request_terminal",
                            status="timeout",
                            timeout=gamepad_module.DISCONNECT_REQUEST_TIMEOUT_SECONDS,
                        )
                await self._transport.close()
                self._report_loop = None
                self._is_open = False
                self._connection_state = "closed"
            finally:
                self._close_in_progress = False

    async def press(self, *buttons: Button) -> None:
        """Add buttons to the current input state.

        Args:
            buttons: Buttons to add to the current button set.

        This updates local state only and does not send an immediate input report.
        """
        await self._state_store.update(
            lambda current: current.with_buttons((*current.buttons, *buttons)),
            validate=self._controller_profile.validate_input_state,
        )

    async def apply(self, state: InputState) -> None:
        """Replace the current input state without immediate transmission.

        Args:
            state: Complete input state to commit.

        This updates local state only and does not send an immediate input report.
        """
        self._controller_profile.validate_input_state(state)
        await self._state_store.apply(state)

    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> None:
        """Replace one or both stick positions without immediate transmission.

        Args:
            left: Optional replacement for the left stick.
            right: Optional replacement for the right stick.

        Raises:
            InvalidInputError: ``left`` or ``right`` is not a ``Stick``.

        This updates local state only and does not send an immediate input report.
        """
        self._validate_stick("left", left)
        self._validate_stick("right", right)
        self._controller_profile.validate_requested_sticks(
            left=left is not None,
            right=right is not None,
        )
        await self._state_store.update(
            lambda current: current.with_sticks(left_stick=left, right_stick=right),
            validate=self._controller_profile.validate_input_state,
        )

    async def lstick(self, stick: Stick) -> None:
        """Replace the left stick position without immediate transmission.

        Args:
            stick: Replacement for the left stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.

        This updates local state only and does not send an immediate input report.
        """
        await self.sticks(left=stick)

    async def rstick(self, stick: Stick) -> None:
        """Replace the right stick position without immediate transmission.

        Args:
            stick: Replacement for the right stick.

        Raises:
            InvalidInputError: ``stick`` is not a ``Stick``.

        This updates local state only and does not send an immediate input report.
        """
        await self.sticks(right=stick)

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
        await self._state_store.imu(*frames)

    async def release(self, *buttons: Button) -> None:
        """Remove buttons from the current input state.

        Args:
            buttons: Buttons to remove from the current button set.

        This updates local state only and does not send an immediate input report.
        """
        self._controller_profile.validate_buttons(buttons)
        await self._state_store.update(
            lambda current: current.with_buttons(current.buttons.difference(buttons)),
            validate=self._controller_profile.validate_input_state,
        )

    async def neutral(self) -> None:
        """Return local input state to ``InputState.neutral()`` without immediate transmission."""
        await self._state_store.neutral()

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
        self._require_connected_for_input()
        await self.press(*buttons)
        primary_error: BaseException | None = None
        try:
            await self._send_current_input()
            if duration > 0:
                await asyncio.sleep(duration)
        except BaseException as error:
            primary_error = error
            raise
        finally:
            await self.release(*buttons)
            try:
                await self._send_current_input()
            except Exception as error:
                self._diagnostics.record_error(error, recoverable=True)
                if primary_error is None:
                    raise

    def status(self) -> GamepadStatus:
        """Return the current gamepad status.

        Returns:
            GamepadStatus: Connection state, report counters, rumble bytes, and last error.
        """
        return GamepadStatus(
            connection_state=self._connection_state,
            report_counters=self._diagnostics.report_counters,
            last_subcommand_id=self._diagnostics.last_subcommand_id,
            raw_rumble=self._diagnostics.raw_rumble,
            last_error=self._diagnostics.last_error,
        )

    def snapshot(self) -> InputState:
        """Return the latest committed input state.

        Returns:
            InputState: Immutable snapshot of the current input state.
        """
        return self._state_store.current

    def _register_transport_callbacks(self) -> None:
        if self._transport is None:
            return
        self._transport.on_interrupt_data(self._handle_interrupt_data)
        self._transport.on_control_data(self._handle_control_data)
        self._transport.on_connected(self._handle_connected)
        self._transport.on_disconnected(self._handle_disconnected)

    def _configure_device_info_bluetooth_address(self, transport: HidDeviceTransport) -> None:
        get_address = getattr(transport, "local_bluetooth_address", None)
        if not callable(get_address):
            return
        address = get_address()
        if address is None:
            return
        if len(address) != 6:
            msg = "local_bluetooth_address must return 6 bytes"
            raise InvalidInputError(msg)
        if address == self._configured_device_info_bluetooth_address:
            return
        self._output_report_dispatcher.subcommand_responder.set_device_info_bluetooth_address(
            address
        )
        self._configured_device_info_bluetooth_address = address
        self._diagnostics.record_event(
            "device_info_bluetooth_address_configured",
            address=address.hex(),
        )

    async def _send_trailing_neutral_if_connected(self) -> None:
        await self._state_store.neutral()
        if self._report_loop is None or not self._connected_event.is_set():
            return
        await self._report_loop.send_current_input()

    async def _send_current_input(self) -> None:
        if self._report_loop is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        await self._report_loop.send_current_input()

    def _require_subcommand_reply_sender(self) -> None:
        _ = self._subcommand_reply_sender()

    async def _send_subcommand_reply(self, reply: bytes) -> None:
        await self._subcommand_reply_sender().send_subcommand_reply(reply)

    def _subcommand_reply_sender(self) -> ReportLoop:
        if self._report_loop is None:
            msg = "gamepad is not open"
            raise ClosedError(msg)
        return self._report_loop

    def _require_connected_for_input(self) -> None:
        if self._report_loop is None or not self._connected_event.is_set():
            msg = "gamepad is not connected"
            raise ClosedError(msg)

    @staticmethod
    def _validate_stick(name: str, value: Stick | None) -> None:
        if value is not None and not isinstance(value, Stick):
            msg = f"{name} must be a Stick"
            raise InvalidInputError(msg)

    def _record_run_metadata(self) -> None:
        key_store_exists: bool | None = None
        key_store_previous_exists: bool | None = None
        if self._config.key_store_path is not None:
            from swbt.transport._bumble_key_store import (  # noqa: PLC0415
                read_key_store_metadata,
            )

            key_store_metadata = read_key_store_metadata(self._config.key_store_path)
            key_store_exists = key_store_metadata.exists
            key_store_previous_exists = key_store_metadata.previous_exists
        self._diagnostics.record_run_metadata(
            adapter=self._metadata_adapter(),
            key_store_exists=key_store_exists,
            key_store_path=self._config.key_store_path,
            key_store_previous_exists=key_store_previous_exists,
        )

    def _metadata_adapter(self) -> str:
        if self._config.adapter is not None:
            return self._config.adapter
        return "custom"

    def _connection_transport(self) -> HidDeviceTransport | None:
        return self._transport

    async def _close_neutral_for_connection_workflow(self) -> None:
        await self.close(neutral=True)

    async def _pair_for_connection_workflow(self, timeout: float | None) -> None:  # noqa: ASYNC109
        await self.pair(timeout=timeout)

    def _set_connection_state(self, state: str) -> None:
        self._connection_state = state

    async def _wait_for_reconnect_connected_for_workflow(
        self,
        timeout: float | None,  # noqa: ASYNC109
    ) -> None:
        await self._wait_for_reconnect_connected(max_wait=timeout)

    async def _wait_for_disconnect_request_closed(self) -> bool:
        try:
            async with asyncio.timeout(gamepad_module.DISCONNECT_REQUEST_TIMEOUT_SECONDS):
                await self._disconnect_event.wait()
                return True
        except TimeoutError:
            return False

    async def _wait_for_reconnect_connected(self, *, max_wait: float | None) -> None:
        if max_wait is None:
            await self._connected_event.wait()
            return
        try:
            async with asyncio.timeout(max_wait):
                await self._connected_event.wait()
        except TimeoutError as error:
            self._diagnostics.record_event(
                "connection_timeout",
                route="active_reconnect",
                state=self._connection_state,
                timeout=max_wait,
            )
            raise TimeoutError from error

    def _record_disconnect_request_result(self, result: DisconnectRequestResult) -> None:
        fields: dict[str, object] = {"status": result.status}
        if result.channels:
            fields["channels"] = list(result.channels)
        if result.reason is not None:
            fields["reason"] = result.reason
        if result.error_type is not None:
            fields["error_type"] = result.error_type
        if result.message is not None:
            fields["message"] = result.message
        self._diagnostics.record_event("disconnect_request", **fields)

    async def _handle_interrupt_data(self, payload: bytes) -> None:
        await self._handle_output_report_data(payload)

    async def _handle_control_data(self, payload: bytes) -> None:
        await self._handle_output_report_data(payload)

    async def _handle_output_report_data(self, payload: bytes) -> None:
        try:
            await self._output_report_dispatcher.dispatch(payload)
        except SwbtError as error:
            self._connection_state = "failed"
            self._diagnostics.record_error(error, recoverable=False)

    async def _handle_connected(self) -> None:
        previous_state = self._connection_state
        if self._transport is not None:
            self._configure_device_info_bluetooth_address(self._transport)
        if previous_state == "advertising":
            self._diagnostics.record_event(
                "incoming_connection",
                previous_state=previous_state,
                route="incoming",
            )
        self._connection_state = "connected"
        self._connected_event.set()
        if self._report_loop is not None:
            self._report_loop.start()

    async def _handle_disconnected(self, reason: int | None) -> None:
        self._diagnostics.record_event("disconnected", reason=reason)
        self._connected_event.clear()
        try:
            await self._state_store.neutral()
            if self._report_loop is not None:
                await self._report_loop.stop()
                self._report_loop = None
            if self._close_in_progress:
                return
            if self._transport is not None and self._is_open:
                await self._transport.close()
            self._is_open = False
            self._connection_state = "closed"
            self._diagnostics.record_event(
                "reconnect_disabled",
                next_state=self._connection_state,
                reason=reason,
            )
        finally:
            self._disconnect_event.set()

    def _ensure_transport(self) -> HidDeviceTransport:
        if self._transport is None:
            if self._config.adapter is None:
                msg = "adapter is required when no custom transport is supplied"
                raise InvalidInputError(msg)
            adapter = self._config.adapter
            if adapter is None:
                msg = "adapter is required when no custom transport is supplied"
                raise InvalidInputError(msg)
            self._transport = self._transport_factory.create(
                adapter=adapter,
                device_name=self._config.device_name,
                profile=self._controller_profile,
                diagnostics=self._diagnostics,
                key_store_path=self._config.key_store_path,
            )
        return self._transport
