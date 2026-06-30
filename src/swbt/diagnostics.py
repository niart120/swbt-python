"""Minimal diagnostics state for gamepad lifecycle and callback errors."""

import json
import platform
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import TextIO


@dataclass(frozen=True)
class DiagnosticsConfig:
    """Diagnostics configuration accepted by SwitchGamepad."""

    trace_writer: TextIO | None = None


@dataclass(frozen=True)
class DiagnosticsEvent:
    """One diagnostics event recorded by the gamepad."""

    event: str
    error_type: str | None = None
    message: str | None = None
    recoverable: bool | None = None
    fields: dict[str, object] | None = None


@dataclass(frozen=True)
class GamepadStatus:
    """Snapshot of gamepad status exposed by SwitchGamepad.status()."""

    connection_state: str
    last_error: DiagnosticsEvent | None


class DiagnosticsRecorder:
    """Record a small in-memory diagnostics event history."""

    def __init__(self, trace_writer: TextIO | None = None) -> None:
        """Create an empty recorder."""
        self._events: list[DiagnosticsEvent] = []
        self._trace_writer = trace_writer

    @property
    def events(self) -> tuple[DiagnosticsEvent, ...]:
        """Return recorded events in order."""
        return tuple(self._events)

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

    def record_run_metadata(self, *, adapter: str) -> DiagnosticsEvent:
        """Record environment metadata for one diagnostics run."""
        return self.record_event(
            "run_metadata",
            adapter=adapter,
            os=platform.system(),
            package_version=self._package_version(),
            python_version=platform.python_version(),
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

    def record_error(self, error: Exception, *, recoverable: bool) -> DiagnosticsEvent:
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
