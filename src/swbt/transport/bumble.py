"""Bumble-backed HID transport."""

from __future__ import annotations

import asyncio
import platform
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any, Protocol, cast

from swbt.errors import ClosedError, TransportOpenError
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.transport._bumble_acl import drain_bumble_acl_queue
from swbt.transport._bumble_hidp import (
    HID_GET_SET_SUCCESS,
    HID_GET_SET_UNSUPPORTED_REQUEST,
    HID_OUTPUT_REPORT_TYPE,
    decode_hidp_output_report,
    format_psm,
    hid_channel_name,
)
from swbt.transport._bumble_key_store import _CurrentPreviousJsonKeyStore, _DiagnosticKeyStore
from swbt.transport._bumble_lifecycle import (
    register_connection_diagnostics,
    register_connection_request_bridge,
    register_l2cap_lifecycle_bridge,
)
from swbt.transport._bumble_sdp import build_hid_service_records
from swbt.transport.base import BondedPeer, DisconnectRequestResult

if TYPE_CHECKING:
    from bumble.transport.common import TransportSink, TransportSource

    from swbt.diagnostics import DiagnosticsRecorder
    from swbt.protocol.profiles.base import ControllerProfile
    from swbt.transport.base import (
        ConnectedCallback,
        ControlDataCallback,
        DisconnectedCallback,
        InterruptDataCallback,
    )

_REFERENCE_LINK_POLICY_ENABLE_ROLE_SWITCH = 0x0001
_REFERENCE_LINK_POLICY_ENABLE_SNIFF_MODE = 0x0004
_DEFAULT_DEVICE_NAME = "Pro Controller"
_REFERENCE_CLASS_OF_DEVICE = 0x002508


@dataclass(frozen=True)
class _BumbleGetSetStatus:
    data: bytes = b""
    status: int = 0


_REFERENCE_DEFAULT_LINK_POLICY_SETTINGS = (
    _REFERENCE_LINK_POLICY_ENABLE_ROLE_SWITCH | _REFERENCE_LINK_POLICY_ENABLE_SNIFF_MODE
)


class _BumbleHandle(Protocol):
    source: object
    sink: object

    async def close(self) -> None:
        """Close the opened Bumble resource."""


_OpenTransport = Callable[[str], Awaitable[_BumbleHandle]]


class _BumbleConnectionRuntime(Protocol):
    async def authenticate(self) -> None:
        """Authenticate a Classic connection using stored link keys."""

    async def encrypt(self, enable: bool = True) -> None:
        """Enable or disable Classic connection encryption."""


class _BumbleDeviceRuntime(Protocol):
    EVENT_CONNECTION: str
    EVENT_CONNECTION_FAILURE: str
    keystore: _BumbleKeyStoreRuntime | None
    on_connection_request: Callable[[object, int, int], None]
    powered_on: bool

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register a Bumble device event callback."""

    async def power_on(self) -> None:
        """Power on the Bumble device."""

    async def power_off(self) -> None:
        """Power off the Bumble device."""

    async def set_connectable(self, connectable: bool = True) -> None:
        """Set Classic connectable state."""

    async def set_discoverable(self, discoverable: bool = True) -> None:
        """Set Classic discoverable state."""

    async def connect(
        self,
        peer_address: str,
        *,
        transport: object,
        timeout: float | None = None,  # noqa: ASYNC109
    ) -> _BumbleConnectionRuntime:
        """Connect to a Bluetooth peer."""


class _BumbleKeyStoreRuntime(Protocol):
    async def get_all(self) -> list[tuple[str, object]]:
        """Return all key entries keyed by peer address."""


class _BumbleHidRuntime(Protocol):
    EVENT_INTERRUPT_DATA: str
    EVENT_CONTROL_DATA: str
    l2cap_intr_channel: object | None
    l2cap_ctrl_channel: object | None
    on_l2cap_channel_open: Callable[[object], None]
    on_l2cap_channel_close: Callable[[object], None]

    def on(self, event: str, callback: Callable[[bytes], None]) -> None:
        """Register a HID helper event callback."""

    def send_data(self, data: bytes) -> None:
        """Send an interrupt-channel HID data message."""

    def send_control_data(self, report_type: int, data: bytes) -> None:
        """Send a control-channel HID data message."""

    async def connect_control_channel(self) -> None:
        """Request control-channel L2CAP connection."""

    async def connect_interrupt_channel(self) -> None:
        """Request interrupt-channel L2CAP connection."""

    async def disconnect_interrupt_channel(self) -> None:
        """Request interrupt-channel disconnection."""

    async def disconnect_control_channel(self) -> None:
        """Request control-channel disconnection."""


@dataclass
class _BumbleRuntime:
    device: _BumbleDeviceRuntime
    hid_device: _BumbleHidRuntime
    service_record_count: int
    hid_descriptor_size: int
    local_bluetooth_address: bytes | None = None
    classic_link_policy_settings: int | None = None
    advertising_started: bool = False


_InitializeDevice = Callable[[_BumbleHandle], Awaitable[_BumbleRuntime]]
_StartAdvertising = Callable[[_BumbleRuntime], Awaitable[None]]
_CloseRuntime = Callable[[_BumbleRuntime], Awaitable[None]]


class BumbleHidTransport:
    """HID transport boundary that keeps Bumble imports local to this module."""

    def __init__(
        self,
        *,
        adapter: str,
        device_name: str = _DEFAULT_DEVICE_NAME,
        profile: ControllerProfile | None = None,
        key_store_path: str | None = None,
        diagnostics: DiagnosticsRecorder | None = None,
        _open_transport: _OpenTransport | None = None,
        _initialize_device: _InitializeDevice | None = None,
        _start_advertising: _StartAdvertising | None = None,
        _close_runtime: _CloseRuntime | None = None,
    ) -> None:
        """Create a Bumble transport for an adapter string."""
        self._adapter = adapter
        self._device_name = device_name
        self._profile = profile or default_controller_profile()
        self._key_store_path = key_store_path
        self._diagnostics = diagnostics
        self._open_transport = _open_transport or _default_open_transport
        if _initialize_device is None:

            async def initialize_device(handle: _BumbleHandle) -> _BumbleRuntime:
                return await _default_initialize_device(
                    handle,
                    device_name=self._device_name,
                    profile=self._profile,
                    key_store_path=self._key_store_path,
                )

            self._initialize_device = initialize_device
        else:
            self._initialize_device = _initialize_device
        self._start_advertising = _start_advertising or _default_start_advertising
        self._close_runtime = _close_runtime or _default_close_runtime
        self._handle: _BumbleHandle | None = None
        self._runtime: _BumbleRuntime | None = None
        self._interrupt_callback: InterruptDataCallback | None = None
        self._control_callback: ControlDataCallback | None = None
        self._connected_callback: ConnectedCallback | None = None
        self._disconnected_callback: DisconnectedCallback | None = None
        self._l2cap_connected_emitted = False
        self._disconnected_callback_emitted = False
        self._close_lock = asyncio.Lock()

    async def open(self) -> None:
        """Open the configured Bumble adapter."""
        if self._handle is not None:
            return
        self._record_event(
            "bumble_runtime",
            bumble_version=_package_version("bumble"),
            os_detail=platform.platform(),
        )
        self._record_event("transport_open_start", adapter=self._adapter)
        try:
            self._handle = await self._open_transport(self._adapter)
            self._runtime = await self._initialize_device(self._handle)
            self._runtime.local_bluetooth_address = (
                self._runtime.local_bluetooth_address
                or _device_info_bluetooth_address_from_bumble_address(
                    getattr(self._runtime.device, "public_address", None)
                )
            )
            self._register_device_callbacks(self._runtime.device)
            self._register_hid_callbacks(self._runtime.hid_device)
            self._register_l2cap_lifecycle_bridge(self._runtime.hid_device)
        except Exception as error:
            await self._cleanup_open_failure()
            self._record_error(error)
            msg = f"failed to open Bumble adapter: {self._adapter}"
            raise TransportOpenError(msg) from error
        initialized_event: dict[str, object] = {
            "adapter": self._adapter,
            "classic_enabled": True,
            "device_name": self._device_name,
            "class_of_device": f"0x{_REFERENCE_CLASS_OF_DEVICE:06x}",
        }
        if self._runtime.local_bluetooth_address is not None:
            initialized_event["local_bluetooth_address"] = (
                self._runtime.local_bluetooth_address.hex()
            )
        self._record_event("bumble_device_initialized", **initialized_event)
        self._record_event(
            "sdp_record_registered",
            adapter=self._adapter,
            service_record_count=self._runtime.service_record_count,
            hid_descriptor_size=self._runtime.hid_descriptor_size,
        )
        self._record_event("hid_device_initialized", adapter=self._adapter)
        self._record_event("transport_open_complete", adapter=self._adapter)

    async def start_advertising(self) -> None:
        """Enter Bluetooth Classic discoverable/connectable state."""
        self._require_open()
        if self._runtime is None:
            msg = "Bumble runtime is not initialized"
            raise ClosedError(msg)
        if self._runtime.advertising_started:
            return
        await self._start_advertising(self._runtime)
        self._refresh_local_bluetooth_address(self._runtime)
        self._install_key_store_diagnostics(self._runtime)
        self._runtime.advertising_started = True
        if self._runtime.classic_link_policy_settings is not None:
            self._record_event(
                "classic_link_policy_configured",
                adapter=self._adapter,
                settings=f"0x{self._runtime.classic_link_policy_settings:04x}",
            )
        self._record_event("advertising_start", adapter=self._adapter)

    async def close(self) -> None:
        """Close the Bumble adapter if it is open."""
        async with self._close_lock:
            if self._handle is None:
                return
            handle = self._handle
            runtime = self._runtime
            self._handle = None
            self._runtime = None
            self._l2cap_connected_emitted = False
            self._disconnected_callback_emitted = False
            if runtime is not None:
                await self._close_runtime(runtime)
            await handle.close()
            self._record_event("transport_close_complete", adapter=self._adapter)

    async def request_disconnect(self) -> DisconnectRequestResult:
        """Request HID channel disconnection through Bumble when channels exist."""
        self._require_open()
        if self._runtime is None:
            return DisconnectRequestResult(
                status="unavailable",
                reason="runtime_not_initialized",
            )
        hid_device = self._runtime.hid_device
        disconnect_steps: list[tuple[str, Callable[[], Awaitable[None]]]] = []
        if hid_device.l2cap_intr_channel is not None:
            disconnect_steps.append(("interrupt", hid_device.disconnect_interrupt_channel))
        if hid_device.l2cap_ctrl_channel is not None:
            disconnect_steps.append(("control", hid_device.disconnect_control_channel))
        if not disconnect_steps:
            return DisconnectRequestResult(
                status="unavailable",
                reason="channels_not_connected",
            )
        requested_channels: list[str] = []
        for channel_name, disconnect_channel in disconnect_steps:
            try:
                await disconnect_channel()
            except Exception as error:  # noqa: BLE001
                return DisconnectRequestResult(
                    status="failed",
                    channels=tuple(requested_channels),
                    error_type=type(error).__name__,
                    message=str(error),
                )
            requested_channels.append(channel_name)
        return DisconnectRequestResult(
            status="requested",
            channels=tuple(requested_channels),
        )

    def local_bluetooth_address(self) -> bytes | None:
        """Return the local Classic controller address for Device Info."""
        if self._runtime is None:
            return None
        return self._runtime.local_bluetooth_address

    async def list_bonded_peers(self) -> tuple[BondedPeer, ...]:
        """Return bonded peer addresses from the Bumble key store."""
        self._require_open()
        if self._runtime is None:
            return ()
        await self._ensure_classic_runtime_ready(self._runtime)
        key_store = self._runtime.device.keystore
        if key_store is None:
            return ()
        entries = await key_store.get_all()
        return tuple(BondedPeer(address=address) for address, _keys in entries)

    async def connect_bonded_peer(
        self,
        peer_address: str,
        *,
        connect_timeout: float | None,
    ) -> None:
        """Start an active BR/EDR reconnect attempt with Bumble."""
        self._require_open()
        if self._runtime is None:
            msg = "Bumble runtime is not initialized"
            raise ClosedError(msg)
        await self._ensure_classic_runtime_ready(self._runtime)
        from bumble.core import PhysicalTransport  # noqa: PLC0415

        connection = await self._runtime.device.connect(
            peer_address,
            transport=PhysicalTransport.BR_EDR,
            timeout=connect_timeout,
        )
        await connection.authenticate()
        await connection.encrypt(True)
        await self._runtime.hid_device.connect_control_channel()
        if self._runtime.hid_device.l2cap_ctrl_channel is not None:
            self._record_l2cap_channel_event(
                "l2cap_channel_open",
                self._runtime.hid_device.l2cap_ctrl_channel,
            )
        await self._runtime.hid_device.connect_interrupt_channel()
        if self._runtime.hid_device.l2cap_intr_channel is not None:
            self._record_l2cap_channel_event(
                "l2cap_channel_open",
                self._runtime.hid_device.l2cap_intr_channel,
            )
        self._notify_connected_if_ready()

    async def send_interrupt(self, payload: bytes) -> None:
        """Send one interrupt report."""
        self._require_open()
        if self._runtime is None or self._runtime.hid_device.l2cap_intr_channel is None:
            msg = "Bumble interrupt channel is not connected"
            raise ClosedError(msg)
        self._runtime.hid_device.send_data(payload)
        await drain_bumble_acl_queue(self._runtime.hid_device.l2cap_intr_channel)

    async def send_control(self, payload: bytes) -> None:
        """Send one control report."""
        self._require_open()
        if self._runtime is None or self._runtime.hid_device.l2cap_ctrl_channel is None:
            msg = "Bumble control channel is not connected"
            raise ClosedError(msg)
        self._runtime.hid_device.send_control_data(HID_OUTPUT_REPORT_TYPE, payload)

    def on_interrupt_data(self, callback: InterruptDataCallback) -> None:
        """Register an interrupt data callback."""
        self._interrupt_callback = callback

    def on_control_data(self, callback: ControlDataCallback) -> None:
        """Register a control data callback."""
        self._control_callback = callback

    def on_connected(self, callback: ConnectedCallback) -> None:
        """Register a connection callback."""
        self._connected_callback = callback

    def on_disconnected(self, callback: DisconnectedCallback) -> None:
        """Register a disconnection callback."""
        self._disconnected_callback = callback

    def _register_hid_callbacks(self, hid_device: _BumbleHidRuntime) -> None:
        hid_device.on(
            hid_device.EVENT_INTERRUPT_DATA,
            self._dispatch_interrupt_data,
        )
        hid_device.on(
            hid_device.EVENT_CONTROL_DATA,
            self._dispatch_control_data,
        )
        self._register_set_report_callback(hid_device)

    def _register_set_report_callback(self, hid_device: _BumbleHidRuntime) -> None:
        register_set_report = getattr(hid_device, "register_set_report_cb", None)
        if not callable(register_set_report):
            return

        def on_set_report(
            report_id: int,
            report_type: int,
            report_size: int,
            report_data: bytes,
        ) -> _BumbleGetSetStatus:
            _ = report_size
            if report_type != HID_OUTPUT_REPORT_TYPE:
                return _BumbleGetSetStatus(status=HID_GET_SET_UNSUPPORTED_REQUEST)
            if not 0 <= report_id <= 0xFF:
                return _BumbleGetSetStatus(status=HID_GET_SET_UNSUPPORTED_REQUEST)
            report = bytes((report_id,)) + bytes(report_data)
            if not self._dispatch_control_report(report):
                return _BumbleGetSetStatus(status=HID_GET_SET_UNSUPPORTED_REQUEST)
            return _BumbleGetSetStatus(status=HID_GET_SET_SUCCESS)

        register_set_report(on_set_report)

    def _register_device_callbacks(self, device: _BumbleDeviceRuntime) -> None:
        device.on(device.EVENT_CONNECTION, self._handle_device_connection)
        device.on(device.EVENT_CONNECTION_FAILURE, self._handle_connection_failure)
        register_connection_request_bridge(
            adapter=self._adapter,
            device=device,
            record_event=self._record_event,
        )

    def _register_l2cap_lifecycle_bridge(self, hid_device: _BumbleHidRuntime) -> None:
        register_l2cap_lifecycle_bridge(
            hid_device=hid_device,
            notify_connected_if_ready=self._notify_connected_if_ready,
            notify_disconnected_if_channels_closed=self._notify_disconnected_if_channels_closed,
            record_l2cap_channel_event=self._record_l2cap_channel_event,
            set_l2cap_connected_emitted=self._set_l2cap_connected_emitted,
        )

    def _handle_device_connection(self, connection: object) -> None:
        self._l2cap_connected_emitted = False
        self._disconnected_callback_emitted = False
        fields: dict[str, object] = {"adapter": self._adapter}
        connection_handle = getattr(connection, "handle", None)
        peer_address = getattr(connection, "peer_address", None)
        if connection_handle is not None:
            fields["connection_handle"] = connection_handle
        if peer_address is not None:
            fields["peer_address"] = str(peer_address)
        self._record_event("host_connection", **fields)
        register_connection_diagnostics(
            adapter=self._adapter,
            connection=connection,
            handle_disconnection=self._handle_device_disconnection,
            record_event=self._record_event,
        )

    def _handle_connection_failure(self, error: object) -> None:
        self._record_event(
            "connection_failure",
            adapter=self._adapter,
            error_type=type(error).__name__,
            message=str(error),
        )

    def _handle_device_disconnection(self, reason: int | None = None) -> None:
        self._l2cap_connected_emitted = False
        self._record_event("disconnected", adapter=self._adapter, reason=reason)
        self._notify_disconnected_once(reason)

    def _dispatch_interrupt_data(self, payload: bytes) -> None:
        report = decode_hidp_output_report(payload)
        if report is None:
            return
        self._dispatch_interrupt_report(report)

    def _dispatch_control_data(self, payload: bytes) -> None:
        report = decode_hidp_output_report(payload)
        if report is None:
            return
        self._dispatch_control_report(report)

    def _dispatch_interrupt_report(self, payload: bytes) -> bool:
        if self._interrupt_callback is None:
            return False
        self._dispatch_callback(self._interrupt_callback, payload)
        return True

    def _dispatch_control_report(self, payload: bytes) -> bool:
        if self._control_callback is None:
            return False
        self._dispatch_callback(self._control_callback, payload)
        return True

    def _dispatch_callback(
        self,
        callback: Callable[[bytes], Awaitable[None]],
        payload: bytes,
    ) -> None:
        self._dispatch_awaitable(callback(payload))

    def _dispatch_connected_callback(self) -> None:
        if self._connected_callback is not None:
            self._dispatch_awaitable(self._connected_callback())

    def _dispatch_disconnected_callback(self, reason: int | None) -> None:
        if self._disconnected_callback is not None:
            self._dispatch_awaitable(self._disconnected_callback(reason))

    def _dispatch_awaitable(self, awaitable: Awaitable[None]) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as error:
            self._record_error(error)
            return
        task = asyncio.ensure_future(awaitable, loop=loop)
        task.add_done_callback(self._record_callback_error)

    def _notify_connected_if_ready(self) -> None:
        if self._runtime is None or self._l2cap_connected_emitted:
            return
        hid_device = self._runtime.hid_device
        if hid_device.l2cap_ctrl_channel is None or hid_device.l2cap_intr_channel is None:
            return
        self._l2cap_connected_emitted = True
        self._record_event("connected", adapter=self._adapter)
        self._dispatch_connected_callback()

    def _notify_disconnected_if_channels_closed(self) -> None:
        if self._runtime is None:
            return
        hid_device = self._runtime.hid_device
        if hid_device.l2cap_ctrl_channel is not None or hid_device.l2cap_intr_channel is not None:
            return
        self._notify_disconnected_once(None)

    def _notify_disconnected_once(self, reason: int | None) -> None:
        if self._disconnected_callback_emitted:
            return
        self._disconnected_callback_emitted = True
        if self._disconnected_callback is not None:
            self._dispatch_disconnected_callback(reason)

    def _set_l2cap_connected_emitted(self, emitted: bool) -> None:
        self._l2cap_connected_emitted = emitted

    def _record_l2cap_channel_event(self, event: str, l2cap_channel: object) -> None:
        psm = getattr(l2cap_channel, "psm", None)
        self._record_event(
            event,
            adapter=self._adapter,
            channel=hid_channel_name(psm),
            psm=format_psm(psm),
        )

    def _record_callback_error(self, task: asyncio.Future[None]) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if isinstance(error, Exception):
            self._record_error(error)

    def _require_open(self) -> None:
        if self._handle is None:
            msg = "Bumble transport is not open"
            raise ClosedError(msg)

    def _record_event(self, event: str, **fields: object) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record_event(event, **fields)

    def _record_error(self, error: Exception) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record_error(error, recoverable=False)

    def _install_key_store_diagnostics(self, runtime: _BumbleRuntime) -> None:
        if self._diagnostics is None:
            return
        key_store = runtime.device.keystore
        if key_store is None or isinstance(key_store, _DiagnosticKeyStore):
            return
        runtime.device.keystore = _DiagnosticKeyStore(key_store, self._diagnostics)

    async def _ensure_classic_runtime_ready(self, runtime: _BumbleRuntime) -> None:
        if not runtime.device.powered_on:
            await runtime.device.power_on()
        self._refresh_local_bluetooth_address(runtime)
        if runtime.classic_link_policy_settings is None:
            link_policy_settings = await _configure_reference_classic_link_policy(runtime.device)
            if link_policy_settings is not None:
                runtime.classic_link_policy_settings = link_policy_settings
                self._record_event(
                    "classic_link_policy_configured",
                    adapter=self._adapter,
                    settings=f"0x{link_policy_settings:04x}",
                )
        self._install_key_store_diagnostics(runtime)

    def _refresh_local_bluetooth_address(self, runtime: _BumbleRuntime) -> None:
        address = _device_info_bluetooth_address_from_bumble_address(
            getattr(runtime.device, "public_address", None)
        )
        if address is None or address == runtime.local_bluetooth_address:
            return
        runtime.local_bluetooth_address = address
        self._record_event(
            "local_bluetooth_address_configured",
            adapter=self._adapter,
            address=address.hex(),
        )

    async def _cleanup_open_failure(self) -> None:
        handle = self._handle
        runtime = self._runtime
        self._handle = None
        self._runtime = None
        self._l2cap_connected_emitted = False
        if runtime is not None:
            await self._close_runtime(runtime)
        if handle is not None:
            await handle.close()


async def _default_open_transport(adapter: str) -> _BumbleHandle:
    from bumble.transport import open_transport  # noqa: PLC0415

    return cast("_BumbleHandle", await open_transport(adapter))


async def _default_initialize_device(
    handle: _BumbleHandle,
    *,
    device_name: str,
    profile: ControllerProfile,
    key_store_path: str | None = None,
) -> _BumbleRuntime:
    from bumble.device import Device, DeviceConfiguration  # noqa: PLC0415
    from bumble.hid import Device as HidDevice  # noqa: PLC0415

    config = DeviceConfiguration(
        name=device_name,
        class_of_device=_REFERENCE_CLASS_OF_DEVICE,
        le_enabled=False,
        classic_enabled=True,
        keystore=None,
        # Bumble applies these flags during power_on; keep them off until after
        # the Classic link policy command is sent.
        connectable=False,
        discoverable=False,
    )
    device = Device.from_config_with_hci(
        config,
        cast("TransportSource", handle.source),
        cast("TransportSink", handle.sink),
    )
    if key_store_path is not None:
        cast("Any", device).keystore = _CurrentPreviousJsonKeyStore.from_device(
            device,
            filename=key_store_path,
        )
    service_records = build_hid_service_records(
        profile.hid_report_descriptor,
        device_name=device_name,
        sdp_policy=profile.hid_sdp_policy,
    )
    device.sdp_service_records = service_records
    hid_device = HidDevice(device)
    return _BumbleRuntime(
        device=cast("_BumbleDeviceRuntime", device),
        hid_device=cast("_BumbleHidRuntime", hid_device),
        service_record_count=len(service_records),
        hid_descriptor_size=len(profile.hid_report_descriptor),
        local_bluetooth_address=_device_info_bluetooth_address_from_bumble_address(
            getattr(device, "public_address", None)
        ),
    )


async def _default_start_advertising(runtime: _BumbleRuntime) -> None:
    if not runtime.device.powered_on:
        await runtime.device.power_on()
    link_policy_settings = await _configure_reference_classic_link_policy(runtime.device)
    if link_policy_settings is not None:
        runtime.classic_link_policy_settings = link_policy_settings
    await runtime.device.set_connectable(True)
    await runtime.device.set_discoverable(True)


async def _default_close_runtime(runtime: _BumbleRuntime) -> None:
    if runtime.device.powered_on:
        await runtime.device.set_discoverable(False)
        await runtime.device.set_connectable(False)
        await runtime.device.power_off()


async def _configure_reference_classic_link_policy(device: object) -> int | None:
    """Set the reference Classic default link policy when Bumble exposes HCI access."""
    from bumble import hci  # noqa: PLC0415

    send_sync_command = getattr(device, "send_sync_command", None)
    if not callable(send_sync_command):
        return None
    host = getattr(device, "host", None)
    supports_command = getattr(host, "supports_command", None)
    if callable(supports_command) and not supports_command(
        hci.HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND
    ):
        return None
    await send_sync_command(
        hci.HCI_Write_Default_Link_Policy_Settings_Command(
            default_link_policy_settings=_REFERENCE_DEFAULT_LINK_POLICY_SETTINGS
        )
    )
    return _REFERENCE_DEFAULT_LINK_POLICY_SETTINGS


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def _device_info_bluetooth_address_from_bumble_address(address: object) -> bytes | None:
    """Return Device Info address bytes from a Bumble address object."""
    if address is None:
        return None
    to_string = getattr(address, "to_string", None)
    address_text = str(to_string(False)) if callable(to_string) else str(address)
    address_text = address_text.split("/", 1)[0]
    parts = address_text.split(":")
    if len(parts) != 6 or any(len(part) != 2 for part in parts):
        return None
    try:
        address_bytes = bytes.fromhex("".join(parts))
    except ValueError:
        return None
    if address_bytes == b"\x00\x00\x00\x00\x00\x00":
        return None
    return address_bytes
