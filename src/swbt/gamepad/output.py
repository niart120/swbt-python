"""Output report dispatch for SwitchGamepad."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from swbt.diagnostics import DiagnosticsRecorder
from swbt.input import InputState
from swbt.protocol.output_report import OutputReportParser
from swbt.protocol.session import SwitchHidSession
from swbt.protocol.subcommand import (
    SESSION_STATE_SUBCOMMANDS,
    SubcommandResponder,
    UnsupportedSubcommandError,
)
from swbt.state_store import InputStateStore

ReplyBuilder = Callable[[], bytes | Awaitable[bytes]]
ReplySender = Callable[[ReplyBuilder], Awaitable[bytes]]
ReplySenderRequirement = Callable[[], None]
ProtocolStateUpdated = Callable[[], None]
SubcommandReceived = Callable[[int], None]


def _ignore_protocol_state_update() -> None:
    pass


def _ignore_subcommand_received(_subcommand_id: int) -> None:
    pass


@dataclass
class OutputReportDispatcher:
    """Parse host output reports, record diagnostics, and enqueue replies."""

    diagnostics: DiagnosticsRecorder
    require_reply_sender: ReplySenderRequirement
    send_subcommand_reply: ReplySender
    session: SwitchHidSession
    state_store: InputStateStore
    protocol_state_updated: ProtocolStateUpdated = _ignore_protocol_state_update
    subcommand_received: SubcommandReceived = _ignore_subcommand_received
    output_report_parser: OutputReportParser = field(default_factory=OutputReportParser)
    subcommand_responder: SubcommandResponder = field(default_factory=SubcommandResponder)

    async def dispatch(self, payload: bytes) -> None:
        """Handle one host-to-device output report payload."""
        output_report = self.output_report_parser.parse(payload)
        subcommand_id = _format_subcommand_id(output_report.subcommand_id)
        if output_report.rumble is not None:
            self.diagnostics.record_raw_rumble(output_report.rumble)
        self.diagnostics.record_event(
            "output_report_rx",
            length=len(payload),
            packet_id=output_report.packet_id,
            report_id=_format_report_id(output_report.report_id),
            subcommand_id=subcommand_id,
        )
        if output_report.subcommand_id is None:
            return
        self.subcommand_received(output_report.subcommand_id)
        self.diagnostics.record_subcommand_rx(
            packet_id=output_report.packet_id,
            subcommand_id=output_report.subcommand_id,
        )
        self.session.observe_subcommand(output_report.subcommand_id)
        self.require_reply_sender()
        state_before_reply = self.session.state
        try:

            async def build_reply() -> bytes:
                state = (
                    await self.state_store.snapshot()
                    if self.session.state.protocol_ready
                    else InputState.neutral()
                )
                return self.subcommand_responder.respond(
                    output_report,
                    state=state,
                    session=self.session,
                )

            reply = await self.send_subcommand_reply(build_reply)
        except UnsupportedSubcommandError:
            self.session.restore_state(state_before_reply)
            self.diagnostics.record_event(
                "unsupported_subcommand",
                packet_id=output_report.packet_id,
                payload=output_report.subcommand_payload.hex(),
                subcommand_id=subcommand_id,
            )
            raise
        except BaseException:
            self.session.restore_state(state_before_reply)
            raise
        if output_report.subcommand_id in SESSION_STATE_SUBCOMMANDS:
            session_state = self.session.state
            self.diagnostics.record_event(
                "subcommand_session_state",
                imu_enabled=session_state.imu_enabled,
                imu_encoding_format=session_state.imu_encoding_format,
                imu_mode=_format_optional_byte(session_state.imu_mode),
                packet_id=output_report.packet_id,
                report_mode=_format_optional_byte(session_state.report_mode),
                report_mode_supported=session_state.report_mode_supported,
                player_lights=_format_optional_byte(session_state.player_lights),
                protocol_ready=session_state.protocol_ready,
                subcommand_id=subcommand_id,
                unsupported_report_mode=_format_optional_byte(
                    session_state.unsupported_report_mode
                ),
                vibration_enabled=session_state.vibration_enabled,
            )
        self.diagnostics.record_event(
            "subcommand_reply_tx",
            packet_id=output_report.packet_id,
            report_id=_format_report_id(reply[0]),
            subcommand_id=subcommand_id,
        )
        self.protocol_state_updated()


def _format_report_id(report_id: int) -> str:
    return f"0x{report_id:02x}"


def _format_subcommand_id(subcommand_id: int | None) -> str | None:
    if subcommand_id is None:
        return None
    return f"0x{subcommand_id:02x}"


def _format_optional_byte(value: int | None) -> str | None:
    if value is None:
        return None
    return f"0x{value:02x}"
