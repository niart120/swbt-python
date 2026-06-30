import asyncio
import json
from io import StringIO

from swbt.diagnostics import DiagnosticsRecorder
from swbt.transport.bumble import BumbleHidTransport


class FakeBumbleHandle:
    """Fake handle returned by the injected Bumble opener."""

    def __init__(self) -> None:
        """Create a fake open handle."""
        self.close_count = 0

    async def close(self) -> None:
        """Record close calls."""
        self.close_count += 1


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
