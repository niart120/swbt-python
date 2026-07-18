import asyncio
import json
from collections.abc import Awaitable, Callable
from io import StringIO

from swbt.diagnostics import DiagnosticsRecorder
from swbt.gamepad.output import OutputReportDispatcher
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.protocol.session import SwitchHidSession
from swbt.state_store import InputStateStore


def test_output_report_dispatcher_records_trace_and_sends_subcommand_reply() -> None:
    async def run() -> None:
        trace = StringIO()
        sent_replies: list[bytes] = []

        def require_reply_sender() -> None:
            return

        async def send_subcommand_reply(
            build_reply: Callable[[], bytes | Awaitable[bytes]],
        ) -> bytes:
            built_reply = build_reply()
            reply = built_reply if isinstance(built_reply, bytes) else await built_reply
            sent_replies.append(reply)
            return reply

        dispatcher = OutputReportDispatcher(
            diagnostics=DiagnosticsRecorder(trace_writer=trace),
            require_reply_sender=require_reply_sender,
            send_subcommand_reply=send_subcommand_reply,
            session=SwitchHidSession(default_controller_profile()),
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
