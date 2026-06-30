"""Bumble-backed HID transport."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
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


class _BumbleHandle(Protocol):
    source: object
    sink: object

    async def close(self) -> None:
        """Close the opened Bumble resource."""


_OpenTransport = Callable[[str], Awaitable[_BumbleHandle]]


class _BumbleDeviceRuntime(Protocol):
    powered_on: bool

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
        diagnostics: DiagnosticsRecorder | None = None,
        _open_transport: _OpenTransport | None = None,
        _initialize_device: _InitializeDevice | None = None,
        _start_advertising: _StartAdvertising | None = None,
        _close_runtime: _CloseRuntime | None = None,
    ) -> None:
        """Create a Bumble transport for an adapter string."""
        self._adapter = adapter
        self._diagnostics = diagnostics
        self._open_transport = _open_transport or _default_open_transport
        self._initialize_device = _initialize_device or _default_initialize_device
        self._start_advertising = _start_advertising or _default_start_advertising
        self._close_runtime = _close_runtime or _default_close_runtime
        self._handle: _BumbleHandle | None = None
        self._runtime: _BumbleRuntime | None = None
        self._interrupt_callback: InterruptDataCallback | None = None
        self._control_callback: ControlDataCallback | None = None
        self._connected_callback: ConnectedCallback | None = None
        self._disconnected_callback: DisconnectedCallback | None = None

    async def open(self) -> None:
        """Open the configured Bumble adapter."""
        if self._handle is not None:
            return
        self._record_event("transport_open_start", adapter=self._adapter)
        try:
            self._handle = await self._open_transport(self._adapter)
            self._runtime = await self._initialize_device(self._handle)
            self._register_hid_callbacks(self._runtime.hid_device)
        except Exception as error:
            await self._cleanup_open_failure()
            self._record_error(error)
            msg = f"failed to open Bumble adapter: {self._adapter}"
            raise TransportOpenError(msg) from error
        self._record_event(
            "bumble_device_initialized",
            adapter=self._adapter,
            classic_enabled=True,
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

    def _dispatch_interrupt_data(self, payload: bytes) -> None:
        if self._interrupt_callback is None:
            return
        self._dispatch_callback(self._interrupt_callback, payload)

    def _dispatch_control_data(self, payload: bytes) -> None:
        if self._control_callback is None:
            return
        self._dispatch_callback(self._control_callback, payload)

    def _dispatch_callback(
        self,
        callback: Callable[[bytes], Awaitable[None]],
        payload: bytes,
    ) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError as error:
            self._record_error(error)
            return
        task = asyncio.ensure_future(callback(payload), loop=loop)
        task.add_done_callback(self._record_callback_error)

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
        if runtime is not None:
            await self._close_runtime(runtime)
        if handle is not None:
            await handle.close()


async def _default_open_transport(adapter: str) -> _BumbleHandle:
    from bumble.transport import open_transport  # noqa: PLC0415

    return cast("_BumbleHandle", await open_transport(adapter))


async def _default_initialize_device(handle: _BumbleHandle) -> _BumbleRuntime:
    from bumble import core  # noqa: PLC0415
    from bumble.device import Device, DeviceConfiguration  # noqa: PLC0415
    from bumble.hid import Device as HidDevice  # noqa: PLC0415

    profile = ProControllerProfile()
    config = DeviceConfiguration(
        name="swbt-python",
        class_of_device=_pack_class_of_device(
            service_classes=0,
            major_device_class=core.ClassOfDevice.MajorDeviceClass.PERIPHERAL,
            minor_device_class=core.ClassOfDevice.PeripheralMinorDeviceClass.GAMEPAD,
        ),
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


def _pack_class_of_device(
    *,
    service_classes: int,
    major_device_class: int,
    minor_device_class: int,
) -> int:
    return service_classes << 13 | major_device_class << 8 | minor_device_class << 2


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

    control_psm = 0x0011
    interrupt_psm = 0x0013
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
                                DataElement.unsigned_integer_16(control_psm),
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
                                        DataElement.unsigned_integer_16(interrupt_psm),
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
