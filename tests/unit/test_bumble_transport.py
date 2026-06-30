import asyncio
import json
from io import StringIO

import pytest

from swbt.diagnostics import DiagnosticsRecorder
from swbt.errors import TransportOpenError
from swbt.transport.bumble import BumbleHidTransport


class FakeBumbleHandle:
    """Fake handle returned by the injected Bumble opener."""

    def __init__(self) -> None:
        """Create a fake open handle."""
        self.close_count = 0

    async def close(self) -> None:
        """Record close calls."""
        self.close_count += 1


class FakeOpenError(Exception):
    """Fake exception raised by an injected opener."""


def test_bumble_transport_records_adapter_string_in_diagnostics() -> None:
    async def run() -> None:
        trace = StringIO()
        diagnostics = DiagnosticsRecorder(trace_writer=trace)

        async def open_transport(adapter: str) -> FakeBumbleHandle:
            assert adapter == "usb:0"
            return FakeBumbleHandle()

        transport = BumbleHidTransport(
            adapter="usb:0",
            diagnostics=diagnostics,
            _open_transport=open_transport,
        )

        await transport.open()

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert {"event": "transport_open_start", "adapter": "usb:0"} in events
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

        async def initialize_device(opened_handle: object) -> None:
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
