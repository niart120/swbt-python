"""Minimal diagnostics state for gamepad lifecycle and callback errors."""

import json
import platform
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class DiagnosticsConfig:
    """Diagnostics configuration accepted by SwitchGamepad.

    Attributes:
        trace_writer: Text stream that receives one JSON Lines diagnostics event per line.
    """

    trace_writer: TextIO | None = None


@dataclass(frozen=True)
class DiagnosticsEvent:
    """One diagnostics event recorded by the gamepad.

    Attributes:
        event: Stable event name.
        error_type: Exception type name for error events.
        message: Human-readable error message for error events.
        recoverable: Whether the error can be treated as recoverable.
        fields: Event-specific structured fields.
    """

    event: str
    error_type: str | None = None
    message: str | None = None
    recoverable: bool | None = None
    fields: dict[str, object] | None = None


@dataclass(frozen=True)
class GamepadStatus:
    """Snapshot of gamepad status exposed by SwitchGamepad.status().

    Attributes:
        connection_state: Current lifecycle state name.
        report_counters: Sent report counts keyed by numeric report ID.
        last_subcommand_id: Last observed subcommand ID, if any.
        raw_rumble: Last raw rumble payload received from the host.
        last_error: Latest diagnostics error event, if any.
    """

    connection_state: str
    report_counters: dict[int, int]
    last_subcommand_id: int | None
    raw_rumble: bytes | None
    last_error: DiagnosticsEvent | None


class DiagnosticsRecorder:
    """Record a small in-memory diagnostics event history."""

    def __init__(self, trace_writer: TextIO | None = None) -> None:
        """Create an empty recorder."""
        self._events: list[DiagnosticsEvent] = []
        self._report_counters: dict[int, int] = {}
        self._last_subcommand_id: int | None = None
        self._raw_rumble: bytes | None = None
        self._trace_writer = trace_writer

    @property
    def events(self) -> tuple[DiagnosticsEvent, ...]:
        """Return recorded events in order."""
        return tuple(self._events)

    @property
    def report_counters(self) -> dict[int, int]:
        """Return sent report counters keyed by report ID."""
        return dict(self._report_counters)

    @property
    def last_subcommand_id(self) -> int | None:
        """Return the last observed subcommand ID."""
        return self._last_subcommand_id

    @property
    def raw_rumble(self) -> bytes | None:
        """Return the last observed raw rumble payload."""
        return self._raw_rumble

    @property
    def last_error(self) -> DiagnosticsEvent | None:
        """Return the latest error event."""
        for event in reversed(self._events):
            if event.event == "error":
                return event
        return None

    def record_event(self, event: str, **fields: object) -> DiagnosticsEvent:
        """Record a diagnostics event with schema fields."""
        diagnostics_event = DiagnosticsEvent(event=event, fields=dict(fields))
        self._append(diagnostics_event)
        return diagnostics_event

    def record_report_tx(self, *, report_id: int, reason: str) -> DiagnosticsEvent:
        """Record one sent report and increment its counter."""
        counter = self._report_counters.get(report_id, 0) + 1
        self._report_counters[report_id] = counter
        return self.record_event(
            "report_tx",
            counter=counter,
            reason=reason,
            report_id=f"0x{report_id:02x}",
        )

    def record_subcommand_rx(self, *, packet_id: int | None, subcommand_id: int) -> None:
        """Record the latest observed subcommand ID."""
        self._last_subcommand_id = subcommand_id
        self.record_event(
            "subcommand_rx",
            packet_id=packet_id,
            subcommand_id=f"0x{subcommand_id:02x}",
        )

    def record_raw_rumble(self, raw_rumble: bytes) -> None:
        """Record the latest raw rumble bytes."""
        self._raw_rumble = bytes(raw_rumble)

    def record_run_metadata(
        self,
        *,
        adapter: str,
        key_store_path: str | None = None,
    ) -> DiagnosticsEvent:
        """Record environment metadata for one diagnostics run."""
        fields: dict[str, object] = {
            "adapter": adapter,
            "os": platform.system(),
            "package_version": self._package_version(),
            "python_version": platform.python_version(),
        }
        if key_store_path is not None:
            key_store_file = Path(key_store_path)
            fields["key_store_path"] = key_store_path
            fields["key_store_exists"] = key_store_file.exists()
            fields["key_store_previous_exists"] = _key_store_previous_exists(key_store_file)
        return self.record_event(
            "run_metadata",
            **fields,
        )

    def record_state_transition(
        self,
        *,
        previous: str,
        next_state: str,
        reason: str,
    ) -> DiagnosticsEvent:
        """Record one lifecycle state transition."""
        return self.record_event(
            "state_transition",
            previous=previous,
            next=next_state,
            reason=reason,
        )

    def record_error(self, error: BaseException, *, recoverable: bool) -> DiagnosticsEvent:
        """Record an exception as an error event."""
        event = DiagnosticsEvent(
            event="error",
            error_type=type(error).__name__,
            message=str(error),
            recoverable=recoverable,
        )
        self._append(event)
        return event

    def _append(self, event: DiagnosticsEvent) -> None:
        self._events.append(event)
        if self._trace_writer is None:
            return
        payload: dict[str, object] = {"event": event.event}
        if event.fields is not None:
            payload.update(event.fields)
        if event.error_type is not None:
            payload["error_type"] = event.error_type
        if event.message is not None:
            payload["message"] = event.message
        if event.recoverable is not None:
            payload["recoverable"] = event.recoverable
        self._trace_writer.write(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        self._trace_writer.write("\n")
        self._trace_writer.flush()

    @staticmethod
    def _package_version() -> str:
        try:
            return version("swbt-python")
        except PackageNotFoundError:
            return "unknown"


def _key_store_previous_exists(key_store_path: Path) -> bool:
    if not key_store_path.exists():
        return False
    try:
        key_store_data = json.loads(key_store_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(key_store_data, dict):
        return False
    return any(str(namespace).startswith("swbt.previous::") for namespace in key_store_data)
