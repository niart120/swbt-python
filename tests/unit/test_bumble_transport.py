import asyncio
import json
from collections.abc import Callable
from io import StringIO
from typing import cast

import pytest

from swbt.diagnostics import DiagnosticsRecorder
from swbt.errors import ClosedError, TransportOpenError
from swbt.transport import bumble as bumble_module
from swbt.transport.bumble import BumbleHidTransport


class FakeBumbleHandle:
    """Fake handle returned by the injected Bumble opener."""

    def __init__(self) -> None:
        """Create a fake open handle."""
        self.close_count = 0
        self.source = object()
        self.sink = object()

    async def close(self) -> None:
        """Record close calls."""
        self.close_count += 1


class FakeBumbleDevice:
    """Fake Bumble device runtime."""

    EVENT_CONNECTION = "connection"
    EVENT_CONNECTION_FAILURE = "connection_failure"

    def __init__(self) -> None:
        """Create a fake device with power state."""
        self.powered_on = False
        self.power_on_count = 0
        self.power_off_count = 0
        self.connectable_calls: list[bool] = []
        self.discoverable_calls: list[bool] = []
        self.handlers: dict[str, list[Callable[..., None]]] = {}
        self.connection_requests: list[tuple[object, int, int]] = []

    async def power_on(self) -> None:
        """Record power-on calls."""
        self.power_on_count += 1
        self.powered_on = True

    async def power_off(self) -> None:
        """Record power-off calls."""
        self.power_off_count += 1
        self.powered_on = False

    async def set_connectable(self, connectable: bool = True) -> None:
        """Record connectable transitions."""
        self.connectable_calls.append(connectable)

    async def set_discoverable(self, discoverable: bool = True) -> None:
        """Record discoverable transitions."""
        self.discoverable_calls.append(discoverable)

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register one fake device event callback."""
        self.handlers.setdefault(event, []).append(callback)

    def emit(self, event: str, *args: object) -> None:
        """Emit one fake device event."""
        for callback in self.handlers[event]:
            callback(*args)

    def on_connection_request(
        self,
        bd_addr: object,
        class_of_device: int,
        link_type: int,
    ) -> None:
        """Record one fake incoming connection request."""
        self.connection_requests.append((bd_addr, class_of_device, link_type))


class FakeHidDevice:
    """Fake Bumble HID helper."""

    EVENT_INTERRUPT_DATA = "interrupt_data"
    EVENT_CONTROL_DATA = "control_data"

    def __init__(self) -> None:
        """Create a fake HID helper."""
        self.l2cap_intr_channel: object | None = None
        self.l2cap_ctrl_channel: object | None = None
        self.handlers: dict[str, Callable[[bytes], None]] = {}
        self.interrupt_payloads: list[bytes] = []
        self.control_payloads: list[tuple[int, bytes]] = []
        self.set_report_callback: Callable[[int, int, int, bytes], object] | None = None

    def on(self, event: str, callback: Callable[[bytes], None]) -> None:
        """Register one fake event callback."""
        self.handlers[event] = callback

    def emit(self, event: str, payload: bytes) -> None:
        """Emit one fake event."""
        callback = self.handlers[event]
        callback(payload)

    def send_data(self, data: bytes) -> None:
        """Record interrupt data."""
        self.interrupt_payloads.append(data)

    def send_control_data(self, report_type: int, data: bytes) -> None:
        """Record control data."""
        self.control_payloads.append((report_type, data))

    def register_set_report_cb(self, callback: Callable[[int, int, int, bytes], object]) -> None:
        """Register a fake SET_REPORT callback."""
        self.set_report_callback = callback

    def emit_set_report(self, report_id: int, report_type: int, report_data: bytes) -> object:
        """Emit one fake SET_REPORT call."""
        assert self.set_report_callback is not None
        report_size = len(report_data) + 1
        return self.set_report_callback(report_id, report_type, report_size, report_data)

    def on_l2cap_channel_open(self, l2cap_channel: object) -> None:
        """Record one fake L2CAP channel as open."""
        psm = getattr(l2cap_channel, "psm", None)
        if psm == 0x0011:
            self.l2cap_ctrl_channel = l2cap_channel
        elif psm == 0x0013:
            self.l2cap_intr_channel = l2cap_channel

    def on_l2cap_channel_close(self, l2cap_channel: object) -> None:
        """Record one fake L2CAP channel as closed."""
        psm = getattr(l2cap_channel, "psm", None)
        if psm == 0x0011:
            self.l2cap_ctrl_channel = None
        elif psm == 0x0013:
            self.l2cap_intr_channel = None


class FakeL2capChannel:
    """Fake L2CAP channel with only the PSM used by Bumble HID."""

    def __init__(self, psm: int) -> None:
        """Create a fake L2CAP channel."""
        self.psm = psm


class FakeConnection:
    """Fake Bumble connection event source."""

    EVENT_DISCONNECTION = "disconnection"
    EVENT_CLASSIC_PAIRING = "classic_pairing"
    EVENT_CLASSIC_PAIRING_FAILURE = "classic_pairing_failure"
    EVENT_PAIRING_START = "pairing_start"
    EVENT_PAIRING = "pairing"
    EVENT_PAIRING_FAILURE = "pairing_failure"

    def __init__(self) -> None:
        """Create a fake connection."""
        self.handle = 0x000B
        self.peer_address = "01:02:03:04:05:06"
        self.handlers: dict[str, list[Callable[..., None]]] = {}

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register one fake connection event callback."""
        self.handlers.setdefault(event, []).append(callback)

    def emit(self, event: str, *args: object) -> None:
        """Emit one fake connection event."""
        for callback in self.handlers[event]:
            callback(*args)


class FakeOpenError(Exception):
    """Fake exception raised by an injected opener."""


def _fake_runtime(
    *,
    device: FakeBumbleDevice | None = None,
    hid_device: FakeHidDevice | None = None,
) -> bumble_module._BumbleRuntime:
    return bumble_module._BumbleRuntime(
        device=cast("bumble_module._BumbleDeviceRuntime", device or FakeBumbleDevice()),
        hid_device=cast("bumble_module._BumbleHidRuntime", hid_device or FakeHidDevice()),
        service_record_count=1,
        hid_descriptor_size=203,
    )


def test_bumble_transport_records_adapter_string_in_diagnostics() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            assert adapter == "usb:0"
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime()

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        await transport.open()

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {"event": "transport_open_start", "adapter": "usb:0"} in events
        assert {
            "event": "bumble_device_initialized",
            "adapter": "usb:0",
            "classic_enabled": True,
            "device_name": "Pro Controller",
            "class_of_device": "0x002508",
        } in events
        assert {
            "event": "sdp_record_registered",
            "adapter": "usb:0",
            "hid_descriptor_size": 203,
            "service_record_count": 1,
        } in events
        assert {"event": "hid_device_initialized", "adapter": "usb:0"} in events
        assert {"event": "transport_open_complete", "adapter": "usb:0"} in events

        await transport.close()

    asyncio.run(run())


def test_bumble_transport_records_custom_device_name_in_diagnostics() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime()

        transport = BumbleHidTransport(
            adapter="usb:0",
            device_name="Reference Pad",
            diagnostics=diagnostics,
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        await transport.open()

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {
            "event": "bumble_device_initialized",
            "adapter": "usb:0",
            "classic_enabled": True,
            "device_name": "Reference Pad",
            "class_of_device": "0x002508",
        } in events

        await transport.close()

    asyncio.run(run())


def test_bumble_hid_service_record_matches_reference_sdp_policy() -> None:
    service_records = bumble_module._build_hid_service_records(b"\x00")
    attributes = {attribute.id: attribute.value for attribute in service_records[0x00010001]}

    assert attributes[0x0203].value == 0x21
    assert attributes[0x020A].value is True
    assert attributes[0x020C].value == 0x0C80
    assert attributes[0x020F].value == 0xFFFF
    assert attributes[0x0210].value == 0xFFFF


def test_bumble_open_failure_is_mapped_to_transport_open_error() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            raise FakeOpenError

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
        )

        with pytest.raises(TransportOpenError):
            await transport.open()

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {"event": "transport_open_start", "adapter": "usb:0"} in events
        assert {
            "event": "error",
            "error_type": "FakeOpenError",
            "message": "",
            "recoverable": False,
        } in events

    asyncio.run(run())


def test_bumble_open_failure_after_handle_open_closes_handle() -> None:
    async def run() -> None:
        handle = FakeBumbleHandle()

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return handle

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert opened_handle is handle
            raise FakeOpenError

        transport = BumbleHidTransport(
            adapter="usb:0",
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        with pytest.raises(TransportOpenError):
            await transport.open()

        assert handle.close_count == 1

    asyncio.run(run())


def test_bumble_close_is_idempotent() -> None:
    async def run() -> None:
        handle = FakeBumbleHandle()
        device = FakeBumbleDevice()

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return handle

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert opened_handle is handle
            return _fake_runtime(device=device)

        transport = BumbleHidTransport(
            adapter="usb:0",
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        await transport.open()
        await transport.start_advertising()
        await transport.close()
        await transport.close()

        assert handle.close_count == 1
        assert device.power_off_count == 1

    asyncio.run(run())


def test_bumble_start_advertising_powers_on_initialized_runtime() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)
        device = FakeBumbleDevice()

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(device=device)

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        await transport.open()
        await transport.start_advertising()
        await transport.start_advertising()

        assert device.power_on_count == 1
        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {"event": "advertising_start", "adapter": "usb:0"} in events

        await transport.close()

    asyncio.run(run())


def test_bumble_hid_data_callbacks_are_forwarded() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()
        interrupt_payloads: list[bytes] = []
        control_payloads: list[bytes] = []

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(hid_device=hid_device)

        transport = BumbleHidTransport(
            adapter="usb:0",
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )
        transport.on_interrupt_data(lambda payload: _append_payload(interrupt_payloads, payload))
        transport.on_control_data(lambda payload: _append_payload(control_payloads, payload))

        await transport.open()
        hid_device.emit(hid_device.EVENT_INTERRUPT_DATA, b"\xa2\x30")
        hid_device.emit(hid_device.EVENT_CONTROL_DATA, b"\xa2\x01")
        await asyncio.sleep(0)

        assert interrupt_payloads == [b"\x30"]
        assert control_payloads == [b"\x01"]

        await transport.close()

    asyncio.run(run())


def test_bumble_hid_data_callbacks_strip_hidp_output_data_header() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()
        interrupt_payloads: list[bytes] = []
        control_payloads: list[bytes] = []

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(hid_device=hid_device)

        transport = BumbleHidTransport(
            adapter="usb:0",
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )
        transport.on_interrupt_data(lambda payload: _append_payload(interrupt_payloads, payload))
        transport.on_control_data(lambda payload: _append_payload(control_payloads, payload))

        await transport.open()
        hid_device.emit(hid_device.EVENT_INTERRUPT_DATA, bytes.fromhex("a2 01 00"))
        hid_device.emit(hid_device.EVENT_CONTROL_DATA, bytes.fromhex("a2 10 2a"))
        await asyncio.sleep(0)

        assert interrupt_payloads == [bytes.fromhex("01 00")]
        assert control_payloads == [bytes.fromhex("10 2a")]

        await transport.close()

    asyncio.run(run())


def test_bumble_set_report_callback_forwards_output_report() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()
        control_payloads: list[bytes] = []

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(hid_device=hid_device)

        transport = BumbleHidTransport(
            adapter="usb:0",
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )
        transport.on_control_data(lambda payload: _append_payload(control_payloads, payload))

        await transport.open()

        result = hid_device.emit_set_report(
            report_id=0x01,
            report_type=0x02,
            report_data=bytes.fromhex("00 00"),
        )
        await asyncio.sleep(0)

        assert control_payloads == [bytes.fromhex("01 00 00")]
        assert getattr(result, "status") == 0xFF

        await transport.close()

    asyncio.run(run())


def test_bumble_send_fails_until_l2cap_channels_are_connected() -> None:
    async def run() -> None:
        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime()

        transport = BumbleHidTransport(
            adapter="usb:0",
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        await transport.open()
        with pytest.raises(ClosedError):
            await transport.send_interrupt(b"\x30")
        with pytest.raises(ClosedError):
            await transport.send_control(b"\x01")

        await transport.close()

    asyncio.run(run())


def test_bumble_l2cap_channel_open_records_diagnostics_and_connects_after_both_channels() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)
        hid_device = FakeHidDevice()
        connected_count = 0

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(hid_device=hid_device)

        async def on_connected() -> None:
            nonlocal connected_count
            connected_count += 1

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )
        transport.on_connected(on_connected)

        await transport.open()
        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0011))
        await asyncio.sleep(0)

        assert connected_count == 0

        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0013))
        await asyncio.sleep(0)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {
            "event": "l2cap_channel_open",
            "adapter": "usb:0",
            "channel": "control",
            "psm": "0x0011",
        } in events
        assert {
            "event": "l2cap_channel_open",
            "adapter": "usb:0",
            "channel": "interrupt",
            "psm": "0x0013",
        } in events
        assert {"event": "connected", "adapter": "usb:0"} in events
        assert connected_count == 1

        await transport.close()

    asyncio.run(run())


def test_bumble_connection_request_is_recorded_before_connection_complete() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)
        device = FakeBumbleDevice()

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(device=device)

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )

        await transport.open()
        device.on_connection_request("01:02:03:04:05:06", 0x2508, 1)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {
            "event": "connection_request",
            "adapter": "usb:0",
            "class_of_device": "0x002508",
            "link_type": 1,
            "peer_address": "01:02:03:04:05:06",
        } in events
        assert device.connection_requests == [("01:02:03:04:05:06", 0x2508, 1)]

        await transport.close()

    asyncio.run(run())


def test_bumble_device_disconnection_records_reason_and_notifies_callback() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)
        device = FakeBumbleDevice()
        disconnected_reasons: list[int | None] = []

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            _ = adapter
            return FakeBumbleHandle()

        async def initialize_device(opened_handle: object) -> bumble_module._BumbleRuntime:
            assert isinstance(opened_handle, FakeBumbleHandle)
            return _fake_runtime(device=device)

        async def on_disconnected(reason: int | None) -> None:
            disconnected_reasons.append(reason)

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
            _initialize_device=initialize_device,
        )
        transport.on_disconnected(on_disconnected)

        await transport.open()
        connection = FakeConnection()
        device.emit(device.EVENT_CONNECTION, connection)
        connection.emit(connection.EVENT_CLASSIC_PAIRING)
        connection.emit(connection.EVENT_PAIRING_START)
        connection.emit(connection.EVENT_PAIRING)
        connection.emit(connection.EVENT_DISCONNECTION, 0x13)
        await asyncio.sleep(0)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {
            "event": "host_connection",
            "adapter": "usb:0",
            "connection_handle": 0x000B,
            "peer_address": "01:02:03:04:05:06",
        } in events
        assert {"event": "classic_pairing", "adapter": "usb:0"} in events
        assert {"event": "pairing_start", "adapter": "usb:0"} in events
        assert {"event": "pairing_complete", "adapter": "usb:0"} in events
        assert {"event": "disconnected", "adapter": "usb:0", "reason": 0x13} in events
        assert disconnected_reasons == [0x13]

        await transport.close()

    asyncio.run(run())


async def _append_payload(payloads: list[bytes], payload: bytes) -> None:
    payloads.append(payload)
