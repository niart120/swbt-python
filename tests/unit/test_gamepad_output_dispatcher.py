import asyncio
import json
from io import StringIO

from swbt._gamepad_output import OutputReportDispatcher
from swbt.diagnostics import DiagnosticsRecorder
from swbt.state_store import InputStateStore


def test_output_report_dispatcher_records_trace_and_sends_subcommand_reply() -> None:
    async def run() -> None:
        trace = StringIO()
        sent_replies: list[bytes] = []

        def require_reply_sender() -> None:
            return

        async def send_subcommand_reply(reply: bytes) -> None:
            sent_replies.append(reply)

        dispatcher = OutputReportDispatcher(
            diagnostics=DiagnosticsRecorder(trace_writer=trace),
            require_reply_sender=require_reply_sender,
            send_subcommand_reply=send_subcommand_reply,
            state_store=InputStateStore(),
        )

        await dispatcher.dispatch(bytes.fromhex("01 12 00 00 00 00 00 00 00 00 02"))

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert sent_replies[0][0] == 0x21
        assert {
            "event": "output_report_rx",
            "length": 11,
            "packet_id": 0x12,
            "report_id": "0x01",
            "subcommand_id": "0x02",
        } in events
        assert {
            "event": "subcommand_reply_tx",
            "packet_id": 0x12,
            "report_id": "0x21",
            "subcommand_id": "0x02",
        } in events

    asyncio.run(run())
