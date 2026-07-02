import asyncio
import json
from collections.abc import Callable
from io import StringIO
from typing import Any, cast

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


class FakeBumbleHost:
    """Fake Bumble host for command-support checks."""

    def __init__(self) -> None:
        """Create a fake host that records command support probes."""
        self.supported_commands: list[int] = []

    def supports_command(self, command: int) -> bool:
        """Record one supported-command probe."""
        self.supported_commands.append(command)
        return True


class FakeBumbleDeviceWithLinkPolicy(FakeBumbleDevice):
    """Fake Bumble device that accepts raw HCI commands."""

    def __init__(self) -> None:
        """Create a fake device with an HCI host boundary."""
        super().__init__()
        self.host = FakeBumbleHost()
        self.sent_commands: list[object] = []
        self.operations: list[str] = []

    async def power_on(self) -> None:
        """Record the power-on operation."""
        self.operations.append("power_on")
        await super().power_on()

    async def set_connectable(self, connectable: bool = True) -> None:
        """Record connectable transitions."""
        self.operations.append("set_connectable")
        await super().set_connectable(connectable)

    async def set_discoverable(self, discoverable: bool = True) -> None:
        """Record discoverable transitions."""
        self.operations.append("set_discoverable")
        await super().set_discoverable(discoverable)

    async def send_sync_command(self, command: object) -> object:
        """Record one HCI command."""
        self.operations.append("link_policy")
        self.sent_commands.append(command)
        return object()


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
        self.disconnect_calls: list[str] = []
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

    async def disconnect_interrupt_channel(self) -> None:
        """Record a fake interrupt channel disconnect request."""
        self.disconnect_calls.append("interrupt")
        self.l2cap_intr_channel = None

    async def disconnect_control_channel(self) -> None:
        """Record a fake control channel disconnect request."""
        self.disconnect_calls.append("control")
        self.l2cap_ctrl_channel = None

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

    def __init__(self, psm: int, connection: object | None = None) -> None:
        """Create a fake L2CAP channel."""
        self.psm = psm
        self.connection = connection


class FakeAclPacketQueue:
    """Fake Bumble ACL packet queue."""

    def __init__(self, *, clears_pending: bool = True) -> None:
        """Create an empty drain record."""
        self.drained_handles: list[int] = []
        self.pending = 1
        self.clears_pending = clears_pending

    async def drain(self, connection_handle: int) -> None:
        """Record one drain wait."""
        self.drained_handles.append(connection_handle)
        if self.clears_pending:
            self.pending = 0


class FakeAclPacketQueueHost:
    """Fake Bumble host exposing per-connection ACL queues."""

    def __init__(self, acl_packet_queue: FakeAclPacketQueue) -> None:
        """Create a fake host with one queue."""
        self.acl_packet_queue = acl_packet_queue
        self.requested_handles: list[int] = []

    def get_data_packet_queue(self, connection_handle: int) -> FakeAclPacketQueue:
        """Return the queue for a fake connection handle."""
        self.requested_handles.append(connection_handle)
        return self.acl_packet_queue


class FakeDeviceWithAclPacketQueueHost:
    """Fake Bumble device exposing an ACL queue host."""

    def __init__(self, host: FakeAclPacketQueueHost) -> None:
        """Create a fake device with a host."""
        self.host = host


class FakeL2capConnection:
    """Fake L2CAP connection with an ACL packet queue."""

    def __init__(self, *, handle: int, acl_packet_queue: FakeAclPacketQueue) -> None:
        """Create a fake connection."""
        self.handle = handle
        self.acl_packet_queue = acl_packet_queue


class FakeL2capConnectionWithHostQueue:
    """Fake L2CAP connection that reaches ACL queues via device.host."""

    def __init__(self, *, handle: int, host: FakeAclPacketQueueHost) -> None:
        """Create a fake connection with host-backed queue lookup."""
        self.handle = handle
        self.device = FakeDeviceWithAclPacketQueueHost(host)


class FakeConnection:
    """Fake Bumble connection event source."""

    EVENT_DISCONNECTION = "disconnection"
    EVENT_CLASSIC_PAIRING = "classic_pairing"
    EVENT_CLASSIC_PAIRING_FAILURE = "classic_pairing_failure"
    EVENT_PAIRING_START = "pairing_start"
    EVENT_PAIRING = "pairing"
    EVENT_PAIRING_FAILURE = "pairing_failure"
    EVENT_CONNECTION_AUTHENTICATION = "connection_authentication"
    EVENT_CONNECTION_AUTHENTICATION_FAILURE = "connection_authentication_failure"
    EVENT_CONNECTION_ENCRYPTION_CHANGE = "connection_encryption_change"
    EVENT_CONNECTION_ENCRYPTION_FAILURE = "connection_encryption_failure"
    EVENT_CONNECTION_ENCRYPTION_KEY_REFRESH = "connection_encryption_key_refresh"
    EVENT_LINK_KEY = "link_key"
    EVENT_MODE_CHANGE = "mode_change"
    EVENT_MODE_CHANGE_FAILURE = "mode_change_failure"

    def __init__(self) -> None:
        """Create a fake connection."""
        self.handle = 0x000B
        self.peer_address = "01:02:03:04:05:06"
        self.authenticated = False
        self.encryption = 0
        self.encryption_key_size = 0
        self.sc = False
        self.classic_mode = 0
        self.classic_interval = 0
        self.handlers: dict[str, list[Callable[..., None]]] = {}

    def on(self, event: str, callback: Callable[..., None]) -> None:
        """Register one fake connection event callback."""
        self.handlers.setdefault(event, []).append(callback)

    def emit(self, event: str, *args: object) -> None:
        """Emit one fake connection event."""
        for callback in self.handlers[event]:
            callback(*args)


class FakePairingKeys:
    """Fake Bumble pairing keys that do not expose real key material."""

    def __init__(self, *, link_key: object | None) -> None:
        """Create fake pairing keys with or without a link key marker."""
        self.link_key = link_key


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
    attributes: dict[int, Any] = {}
    for attribute in service_records[0x00010001]:
        typed_attribute = cast("Any", attribute)
        attributes[typed_attribute.id] = typed_attribute.value

    language_base = attributes[0x0006]
    hid_language_base_sequence = attributes[0x0207].value
    hid_language_base = hid_language_base_sequence[0]

    assert attributes[0x0100].value == b"Pro Controller"
    assert [element.value for element in language_base.value] == [0x656E, 0x006A, 0x0100]
    assert [element.value for element in hid_language_base.value] == [0x0409, 0x0100]
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


def test_bumble_start_advertising_configures_reference_classic_link_policy() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)
        device = FakeBumbleDeviceWithLinkPolicy()

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

        assert device.power_on_count == 1
        assert device.connectable_calls == [True]
        assert device.discoverable_calls == [True]
        assert device.operations == [
            "power_on",
            "link_policy",
            "set_connectable",
            "set_discoverable",
        ]
        assert len(device.sent_commands) == 1
        command = cast("Any", device.sent_commands[0])
        assert (
            command.default_link_policy_settings
            == bumble_module._REFERENCE_DEFAULT_LINK_POLICY_SETTINGS
        )

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {
            "event": "classic_link_policy_configured",
            "adapter": "usb:0",
            "settings": "0x0005",
        } in events
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
        assert cast("Any", result).status == 0xFF

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


def test_bumble_send_interrupt_waits_for_acl_queue_drain() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()
        acl_packet_queue = FakeAclPacketQueue()
        connection = FakeL2capConnection(
            handle=0x0048,
            acl_packet_queue=acl_packet_queue,
        )

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

        await transport.open()
        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0013, connection=connection))

        await transport.send_interrupt(b"\x30")

        assert hid_device.interrupt_payloads == [b"\x30"]
        assert acl_packet_queue.drained_handles == [0x0048]

        await transport.close()

    asyncio.run(run())


def test_bumble_send_interrupt_falls_back_to_host_acl_queue_drain() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()
        acl_packet_queue = FakeAclPacketQueue()
        host = FakeAclPacketQueueHost(acl_packet_queue)
        connection = FakeL2capConnectionWithHostQueue(
            handle=0x0049,
            host=host,
        )

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

        await transport.open()
        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0013, connection=connection))

        await transport.send_interrupt(b"\x30")

        assert hid_device.interrupt_payloads == [b"\x30"]
        assert host.requested_handles == [0x0049]
        assert acl_packet_queue.drained_handles == [0x0049]

        await transport.close()

    asyncio.run(run())


def test_bumble_send_interrupt_drain_stops_when_acl_queue_makes_no_progress() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()
        acl_packet_queue = FakeAclPacketQueue(clears_pending=False)
        connection = FakeL2capConnection(
            handle=0x004A,
            acl_packet_queue=acl_packet_queue,
        )

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

        await transport.open()
        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0013, connection=connection))

        await asyncio.wait_for(transport.send_interrupt(b"\x30"), timeout=1.0)

        assert hid_device.interrupt_payloads == [b"\x30"]
        assert acl_packet_queue.drained_handles == [0x004A]

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


def test_bumble_request_disconnect_calls_interrupt_then_control_helpers() -> None:
    async def run() -> None:
        hid_device = FakeHidDevice()

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

        await transport.open()
        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0011))
        hid_device.on_l2cap_channel_open(FakeL2capChannel(0x0013))

        result = await transport.request_disconnect()

        assert result.status == "requested"
        assert result.channels == ("interrupt", "control")
        assert hid_device.disconnect_calls == ["interrupt", "control"]

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
        connection.authenticated = True
        connection.encryption = 1
        connection.encryption_key_size = 16
        connection.sc = True
        connection.emit(connection.EVENT_PAIRING, FakePairingKeys(link_key=object()))
        connection.emit(connection.EVENT_CONNECTION_AUTHENTICATION)
        connection.emit(connection.EVENT_CONNECTION_ENCRYPTION_CHANGE)
        connection.emit(connection.EVENT_CONNECTION_ENCRYPTION_KEY_REFRESH)
        connection.emit(connection.EVENT_LINK_KEY)
        connection.classic_mode = 2
        connection.classic_interval = 24
        connection.emit(connection.EVENT_MODE_CHANGE)
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
        assert {
            "event": "pairing_complete",
            "adapter": "usb:0",
            "authenticated": True,
            "encryption": 1,
            "encryption_key_size": 16,
            "secure_connections": True,
            "has_link_key": True,
        } in events
        assert {
            "event": "connection_authentication",
            "adapter": "usb:0",
            "authenticated": True,
        } in events
        assert {
            "event": "connection_encryption_change",
            "adapter": "usb:0",
            "authenticated": True,
            "encryption": 1,
            "encryption_key_size": 16,
            "secure_connections": True,
        } in events
        assert {
            "event": "connection_encryption_key_refresh",
            "adapter": "usb:0",
            "authenticated": True,
            "encryption": 1,
            "encryption_key_size": 16,
            "secure_connections": True,
        } in events
        assert {"event": "link_key_available", "adapter": "usb:0"} in events
        assert {
            "event": "classic_mode_change",
            "adapter": "usb:0",
            "mode": 2,
            "interval": 24,
        } in events
        assert {"event": "disconnected", "adapter": "usb:0", "reason": 0x13} in events
        assert disconnected_reasons == [0x13]

        await transport.close()

    asyncio.run(run())


async def _append_payload(payloads: list[bytes], payload: bytes) -> None:
    payloads.append(payload)
