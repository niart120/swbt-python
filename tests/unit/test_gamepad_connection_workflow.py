import asyncio
import json
from io import StringIO

from swbt._gamepad_connection import ConnectionWorkflow
from swbt.diagnostics import DiagnosticsRecorder
from swbt.transport.fake import FakeHidTransport


def test_connection_workflow_records_no_bond_result() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()

        async def ensure_open() -> None:
            await transport.open()

        async def close_neutral() -> None:
            await transport.close()

        async def pair(timeout: float | None) -> None:  # noqa: ASYNC109
            _ = timeout

        async def wait_for_connected(timeout: float | None) -> None:  # noqa: ASYNC109
            _ = timeout

        def set_connection_state(state: str) -> None:
            _ = state

        def clear_connected() -> None:
            return

        workflow = ConnectionWorkflow(
            clear_connected=clear_connected,
            close_neutral=close_neutral,
            diagnostics=DiagnosticsRecorder(trace_writer=trace),
            ensure_open=ensure_open,
            get_transport=lambda: transport,
            key_store_path=None,
            pair=pair,
            set_connection_state=set_connection_state,
            transport_was_injected=False,
            wait_for_connected=wait_for_connected,
        )

        result = await workflow.try_reconnect(timeout=0.1)
        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert result.status == "no_bond"
        assert {
            "event": "reconnect_key_store_unavailable",
            "reason": "key_store_path_none",
            "route": "active_reconnect",
        } in events
        assert {
            "event": "active_reconnect_result",
            "peer_count": 0,
            "route": "active_reconnect",
            "status": "no_bond",
        } in events

    asyncio.run(run())
