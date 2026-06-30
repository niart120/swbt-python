import asyncio
import json
from collections.abc import Callable
from io import StringIO

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

    def __init__(self) -> None:
        """Create a fake device with power state."""
        self.powered_on = False
        self.power_on_count = 0
        self.power_off_count = 0
        self.connectable_calls: list[bool] = []
        self.discoverable_calls: list[bool] = []

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


class FakeOpenError(Exception):
    """Fake exception raised by an injected opener."""


def _fake_runtime(
    *,
    device: FakeBumbleDevice | None = None,
    hid_device: FakeHidDevice | None = None,
) -> bumble_module._BumbleRuntime:
    return bumble_module._BumbleRuntime(
        device=device or FakeBumbleDevice(),
        hid_device=hid_device or FakeHidDevice(),
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
        hid_device.emit(hid_device.EVENT_INTERRUPT_DATA, b"\x30")
        hid_device.emit(hid_device.EVENT_CONTROL_DATA, b"\x01")
        await asyncio.sleep(0)

        assert interrupt_payloads == [b"\x30"]
        assert control_payloads == [b"\x01"]

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


async def _append_payload(payloads: list[bytes], payload: bytes) -> None:
    payloads.append(payload)
