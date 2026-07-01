"""Bumble-backed HID transport."""

from __future__ import annotations

import asyncio
import platform
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Protocol, cast

from swbt.errors import ClosedError, TransportOpenError
from swbt.protocol.profile import ProControllerProfile

if TYPE_CHECKING:
    from bumble.transport.common import TransportSink, TransportSource

    from swbt.diagnostics import DiagnosticsRecorder
    from swbt.transport.base import (
        ConnectedCallback,
        ControlDataCallback,
        DisconnectedCallback,
        InterruptDataCallback,
    )

_HID_SERVICE_RECORD_HANDLE = 0x00010001
_HID_REPORT_DESCRIPTOR_TYPE = 0x22
_HID_OUTPUT_REPORT_TYPE = 0x02
_HIDP_DATA_MESSAGE_TYPE = 0x0A
_HID_GET_SET_SUCCESS = 0xFF
_HID_GET_SET_UNSUPPORTED_REQUEST = 0x02
_HID_CONTROL_PSM = 0x0011
_HID_INTERRUPT_PSM = 0x0013
_DEFAULT_DEVICE_NAME = "Pro Controller"
_REFERENCE_CLASS_OF_DEVICE = 0x002508

_SDP_HID_PARSER_VERSION_ATTRIBUTE_ID = 0x0201
_SDP_HID_DEVICE_SUBCLASS_ATTRIBUTE_ID = 0x0202
_SDP_HID_COUNTRY_CODE_ATTRIBUTE_ID = 0x0203
_SDP_HID_VIRTUAL_CABLE_ATTRIBUTE_ID = 0x0204
_SDP_HID_RECONNECT_INITIATE_ATTRIBUTE_ID = 0x0205
_SDP_HID_DESCRIPTOR_LIST_ATTRIBUTE_ID = 0x0206
_SDP_HID_LANG_ID_BASE_LIST_ATTRIBUTE_ID = 0x0207
_SDP_HID_PROFILE_VERSION_ATTRIBUTE_ID = 0x020B
_SDP_HID_NORMALLY_CONNECTABLE_ATTRIBUTE_ID = 0x020D
_SDP_HID_BOOT_DEVICE_ATTRIBUTE_ID = 0x020E

_LANGUAGE_BASE_EN_US = 0x0100
_LANGUAGE_ID_EN_US = 0x0409


@dataclass(frozen=True)
class _BumbleGetSetStatus:
    data: bytes = b""
    status: int = 0


class _BumbleHandle(Protocol):
    source: object
    sink: object

    async def close(self) -> None:
        """Close the opened Bumble resource."""


_OpenTransport = Callable[[str], Awaitable[_BumbleHandle]]


class _BumbleDeviceRuntime(Protocol):
    EVENT_CONNECTION: str
    EVENT_CONNECTION_FAILURE: str
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


@dataclass
class _BumbleRuntime:
    device: _BumbleDeviceRuntime
    hid_device: _BumbleHidRuntime
    service_record_count: int
    hid_descriptor_size: int
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
        diagnostics: DiagnosticsRecorder | None = None,
        _open_transport: _OpenTransport | None = None,
        _initialize_device: _InitializeDevice | None = None,
        _start_advertising: _StartAdvertising | None = None,
        _close_runtime: _CloseRuntime | None = None,
    ) -> None:
        """Create a Bumble transport for an adapter string."""
        self._adapter = adapter
        self._device_name = device_name
        self._diagnostics = diagnostics
        self._open_transport = _open_transport or _default_open_transport
        if _initialize_device is None:

            async def initialize_device(handle: _BumbleHandle) -> _BumbleRuntime:
                return await _default_initialize_device(handle, device_name=self._device_name)

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
            self._register_device_callbacks(self._runtime.device)
            self._register_hid_callbacks(self._runtime.hid_device)
            self._register_l2cap_lifecycle_bridge(self._runtime.hid_device)
        except Exception as error:
            await self._cleanup_open_failure()
            self._record_error(error)
            msg = f"failed to open Bumble adapter: {self._adapter}"
            raise TransportOpenError(msg) from error
        self._record_event(
            "bumble_device_initialized",
            adapter=self._adapter,
            classic_enabled=True,
            device_name=self._device_name,
            class_of_device=f"0x{_REFERENCE_CLASS_OF_DEVICE:06x}",
        )
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
        self._runtime.advertising_started = True
        self._record_event("advertising_start", adapter=self._adapter)

    async def close(self) -> None:
        """Close the Bumble adapter if it is open."""
        if self._handle is None:
            return
        handle = self._handle
        runtime = self._runtime
        self._handle = None
        self._runtime = None
        self._l2cap_connected_emitted = False
        if runtime is not None:
            await self._close_runtime(runtime)
        await handle.close()
        self._record_event("transport_close_complete", adapter=self._adapter)

    async def send_interrupt(self, payload: bytes) -> None:
        """Send one interrupt report."""
        self._require_open()
        if self._runtime is None or self._runtime.hid_device.l2cap_intr_channel is None:
            msg = "Bumble interrupt channel is not connected"
            raise ClosedError(msg)
        self._runtime.hid_device.send_data(payload)

    async def send_control(self, payload: bytes) -> None:
        """Send one control report."""
        self._require_open()
        if self._runtime is None or self._runtime.hid_device.l2cap_ctrl_channel is None:
            msg = "Bumble control channel is not connected"
            raise ClosedError(msg)
        self._runtime.hid_device.send_control_data(_HID_OUTPUT_REPORT_TYPE, payload)

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
            if report_type != _HID_OUTPUT_REPORT_TYPE:
                return _BumbleGetSetStatus(status=_HID_GET_SET_UNSUPPORTED_REQUEST)
            if not 0 <= report_id <= 0xFF:
                return _BumbleGetSetStatus(status=_HID_GET_SET_UNSUPPORTED_REQUEST)
            report = bytes((report_id,)) + bytes(report_data)
            if not self._dispatch_control_report(report):
                return _BumbleGetSetStatus(status=_HID_GET_SET_UNSUPPORTED_REQUEST)
            return _BumbleGetSetStatus(status=_HID_GET_SET_SUCCESS)

        register_set_report(on_set_report)

    def _register_device_callbacks(self, device: _BumbleDeviceRuntime) -> None:
        device.on(device.EVENT_CONNECTION, self._handle_device_connection)
        device.on(device.EVENT_CONNECTION_FAILURE, self._handle_connection_failure)
        self._register_connection_request_bridge(device)

    def _register_connection_request_bridge(self, device: _BumbleDeviceRuntime) -> None:
        original_connection_request = device.on_connection_request

        def on_connection_request(
            bd_addr: object,
            class_of_device: int,
            link_type: int,
        ) -> None:
            self._record_event(
                "connection_request",
                adapter=self._adapter,
                class_of_device=f"0x{class_of_device:06x}",
                link_type=link_type,
                peer_address=str(bd_addr),
            )
            original_connection_request(bd_addr, class_of_device, link_type)

        device.on_connection_request = on_connection_request

    def _register_l2cap_lifecycle_bridge(self, hid_device: _BumbleHidRuntime) -> None:
        original_open = hid_device.on_l2cap_channel_open
        original_close = hid_device.on_l2cap_channel_close

        def on_l2cap_channel_open(l2cap_channel: object) -> None:
            original_open(l2cap_channel)
            self._record_l2cap_channel_event("l2cap_channel_open", l2cap_channel)
            self._notify_connected_if_ready()

        def on_l2cap_channel_close(l2cap_channel: object) -> None:
            original_close(l2cap_channel)
            self._record_l2cap_channel_event("l2cap_channel_close", l2cap_channel)
            self._l2cap_connected_emitted = False

        hid_device.on_l2cap_channel_open = on_l2cap_channel_open
        hid_device.on_l2cap_channel_close = on_l2cap_channel_close

    def _handle_device_connection(self, connection: object) -> None:
        self._l2cap_connected_emitted = False
        fields: dict[str, object] = {"adapter": self._adapter}
        connection_handle = getattr(connection, "handle", None)
        peer_address = getattr(connection, "peer_address", None)
        if connection_handle is not None:
            fields["connection_handle"] = connection_handle
        if peer_address is not None:
            fields["peer_address"] = str(peer_address)
        self._record_event("host_connection", **fields)
        self._register_connection_callbacks(connection)

    def _register_connection_callbacks(self, connection: object) -> None:
        on_event = getattr(connection, "on", None)
        if not callable(on_event):
            return
        on_event(
            getattr(connection, "EVENT_DISCONNECTION", "disconnection"),
            self._handle_device_disconnection,
        )
        on_event(
            getattr(connection, "EVENT_CLASSIC_PAIRING", "classic_pairing"),
            lambda *_args: self._record_event("classic_pairing", adapter=self._adapter),
        )
        on_event(
            getattr(connection, "EVENT_CLASSIC_PAIRING_FAILURE", "classic_pairing_failure"),
            lambda reason=None, *_args: self._record_event(
                "classic_pairing_failure",
                adapter=self._adapter,
                reason=reason,
            ),
        )
        on_event(
            getattr(connection, "EVENT_PAIRING_START", "pairing_start"),
            lambda *_args: self._record_event("pairing_start", adapter=self._adapter),
        )
        on_event(
            getattr(connection, "EVENT_PAIRING", "pairing"),
            lambda *_args: self._record_event("pairing_complete", adapter=self._adapter),
        )
        on_event(
            getattr(connection, "EVENT_PAIRING_FAILURE", "pairing_failure"),
            lambda reason=None, *_args: self._record_event(
                "pairing_failure",
                adapter=self._adapter,
                reason=reason,
            ),
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
        if self._disconnected_callback is not None:
            self._dispatch_disconnected_callback(reason)

    def _dispatch_interrupt_data(self, payload: bytes) -> None:
        report = _decode_hidp_output_report(payload)
        if report is None:
            return
        self._dispatch_interrupt_report(report)

    def _dispatch_control_data(self, payload: bytes) -> None:
        report = _decode_hidp_output_report(payload)
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

    def _record_l2cap_channel_event(self, event: str, l2cap_channel: object) -> None:
        psm = getattr(l2cap_channel, "psm", None)
        self._record_event(
            event,
            adapter=self._adapter,
            channel=_hid_channel_name(psm),
            psm=_format_psm(psm),
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
) -> _BumbleRuntime:
    from bumble.device import Device, DeviceConfiguration  # noqa: PLC0415
    from bumble.hid import Device as HidDevice  # noqa: PLC0415

    profile = ProControllerProfile()
    config = DeviceConfiguration(
        name=device_name,
        class_of_device=_REFERENCE_CLASS_OF_DEVICE,
        le_enabled=False,
        classic_enabled=True,
        connectable=True,
        discoverable=True,
    )
    device = Device.from_config_with_hci(
        config,
        cast("TransportSource", handle.source),
        cast("TransportSink", handle.sink),
    )
    service_records = _build_hid_service_records(profile.hid_report_descriptor)
    device.sdp_service_records = service_records
    hid_device = HidDevice(device)
    return _BumbleRuntime(
        device=cast("_BumbleDeviceRuntime", device),
        hid_device=cast("_BumbleHidRuntime", hid_device),
        service_record_count=len(service_records),
        hid_descriptor_size=len(profile.hid_report_descriptor),
    )


async def _default_start_advertising(runtime: _BumbleRuntime) -> None:
    if runtime.device.powered_on:
        await runtime.device.set_connectable(True)
        await runtime.device.set_discoverable(True)
        return
    await runtime.device.power_on()


async def _default_close_runtime(runtime: _BumbleRuntime) -> None:
    if runtime.device.powered_on:
        await runtime.device.power_off()


def _hid_channel_name(psm: object) -> str:
    if psm == _HID_CONTROL_PSM:
        return "control"
    if psm == _HID_INTERRUPT_PSM:
        return "interrupt"
    return "unknown"


def _format_psm(psm: object) -> str:
    if isinstance(psm, int):
        return f"0x{psm:04x}"
    return "unknown"


def _decode_hidp_output_report(pdu: bytes) -> bytes | None:
    if not pdu:
        return None
    message_type = pdu[0] >> 4
    report_type = pdu[0] & 0x03
    if message_type != _HIDP_DATA_MESSAGE_TYPE:
        return None
    if report_type != _HID_OUTPUT_REPORT_TYPE:
        return None
    return pdu[1:]


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def _build_hid_service_records(hid_descriptor: bytes) -> dict[int, list[object]]:
    from bumble import core  # noqa: PLC0415
    from bumble.sdp import (  # noqa: PLC0415
        SDP_ADDITIONAL_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
        SDP_BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRIBUTE_ID,
        SDP_BROWSE_GROUP_LIST_ATTRIBUTE_ID,
        SDP_LANGUAGE_BASE_ATTRIBUTE_ID_LIST_ATTRIBUTE_ID,
        SDP_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
        SDP_PUBLIC_BROWSE_ROOT,
        SDP_SERVICE_CLASS_ID_LIST_ATTRIBUTE_ID,
        SDP_SERVICE_RECORD_HANDLE_ATTRIBUTE_ID,
        DataElement,
        ServiceAttribute,
    )

    return {
        _HID_SERVICE_RECORD_HANDLE: [
            ServiceAttribute(
                SDP_SERVICE_RECORD_HANDLE_ATTRIBUTE_ID,
                DataElement.unsigned_integer_32(_HID_SERVICE_RECORD_HANDLE),
            ),
            ServiceAttribute(
                SDP_SERVICE_CLASS_ID_LIST_ATTRIBUTE_ID,
                DataElement.sequence([DataElement.uuid(core.BT_HUMAN_INTERFACE_DEVICE_SERVICE)]),
            ),
            ServiceAttribute(
                SDP_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.uuid(core.BT_L2CAP_PROTOCOL_ID),
                                DataElement.unsigned_integer_16(_HID_CONTROL_PSM),
                            ]
                        ),
                        DataElement.sequence([DataElement.uuid(core.BT_HIDP_PROTOCOL_ID)]),
                    ]
                ),
            ),
            ServiceAttribute(
                SDP_BROWSE_GROUP_LIST_ATTRIBUTE_ID,
                DataElement.sequence([DataElement.uuid(SDP_PUBLIC_BROWSE_ROOT)]),
            ),
            ServiceAttribute(
                SDP_LANGUAGE_BASE_ATTRIBUTE_ID_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.unsigned_integer_16(_LANGUAGE_ID_EN_US),
                        DataElement.unsigned_integer_16(106),
                        DataElement.unsigned_integer_16(_LANGUAGE_BASE_EN_US),
                    ]
                ),
            ),
            ServiceAttribute(
                SDP_BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.uuid(core.BT_HUMAN_INTERFACE_DEVICE_SERVICE),
                                DataElement.unsigned_integer_16(0x0101),
                            ]
                        )
                    ]
                ),
            ),
            ServiceAttribute(
                SDP_ADDITIONAL_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.sequence(
                                    [
                                        DataElement.uuid(core.BT_L2CAP_PROTOCOL_ID),
                                        DataElement.unsigned_integer_16(_HID_INTERRUPT_PSM),
                                    ]
                                ),
                                DataElement.sequence([DataElement.uuid(core.BT_HIDP_PROTOCOL_ID)]),
                            ]
                        )
                    ]
                ),
            ),
            ServiceAttribute(
                _SDP_HID_PARSER_VERSION_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(0x0111),
            ),
            ServiceAttribute(
                _SDP_HID_DEVICE_SUBCLASS_ATTRIBUTE_ID,
                DataElement.unsigned_integer_8(0x08),
            ),
            ServiceAttribute(
                _SDP_HID_COUNTRY_CODE_ATTRIBUTE_ID,
                DataElement.unsigned_integer_8(0x00),
            ),
            ServiceAttribute(
                _SDP_HID_VIRTUAL_CABLE_ATTRIBUTE_ID,
                DataElement.boolean(True),
            ),
            ServiceAttribute(
                _SDP_HID_RECONNECT_INITIATE_ATTRIBUTE_ID,
                DataElement.boolean(True),
            ),
            ServiceAttribute(
                _SDP_HID_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.unsigned_integer_8(_HID_REPORT_DESCRIPTOR_TYPE),
                                DataElement.text_string(hid_descriptor),
                            ]
                        )
                    ]
                ),
            ),
            ServiceAttribute(
                _SDP_HID_LANG_ID_BASE_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.unsigned_integer_16(_LANGUAGE_ID_EN_US),
                                DataElement.unsigned_integer_16(_LANGUAGE_BASE_EN_US),
                            ]
                        )
                    ]
                ),
            ),
            ServiceAttribute(
                _SDP_HID_PROFILE_VERSION_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(0x0101),
            ),
            ServiceAttribute(
                _SDP_HID_NORMALLY_CONNECTABLE_ATTRIBUTE_ID,
                DataElement.boolean(True),
            ),
            ServiceAttribute(
                _SDP_HID_BOOT_DEVICE_ATTRIBUTE_ID,
                DataElement.boolean(False),
            ),
        ]
    }
