"""Minimal diagnostics state for gamepad lifecycle and callback errors."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DiagnosticsEvent:
    """One diagnostics event recorded by the gamepad."""

    event: str
    error_type: str | None = None
    message: str | None = None
    recoverable: bool | None = None


@dataclass(frozen=True)
class GamepadStatus:
    """Snapshot of gamepad status exposed by SwitchGamepad.status()."""

    connection_state: str
    last_error: DiagnosticsEvent | None


class DiagnosticsRecorder:
    """Record a small in-memory diagnostics event history."""

    def __init__(self) -> None:
        """Create an empty recorder."""
        self._events: list[DiagnosticsEvent] = []

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

    def record_error(self, error: Exception, *, recoverable: bool) -> DiagnosticsEvent:
        """Record an exception as an error event."""
        event = DiagnosticsEvent(
            event="error",
            error_type=type(error).__name__,
            message=str(error),
            recoverable=recoverable,
        )
        self._events.append(event)
        return event
