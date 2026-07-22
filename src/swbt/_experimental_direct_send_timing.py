"""Temporary DEBUG-only timing probe for direct input sends.

This module is intentionally private and experimental.  It is not a diagnostics
API and may be removed after the Issue #93 investigation.
"""

from __future__ import annotations

import json
import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from itertools import count
from time import perf_counter_ns
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

_LOGGER = logging.getLogger("swbt.experimental.direct_send_timing")
_OPERATION_IDS = count(1)


@dataclass
class DirectSendTimingProbe:
    """Collect one direct-send timing record while DEBUG logging is enabled."""

    operation_id: int
    started_ns: int
    fields: dict[str, int | str | None] = field(default_factory=dict)

    def now_ns(self) -> int:
        """Return the experimental duration clock value."""
        return perf_counter_ns()

    def record_elapsed(self, field_name: str, started_ns: int) -> None:
        """Record the non-negative duration since ``started_ns``."""
        self.fields[field_name] = max(0, perf_counter_ns() - started_ns)

    def record(self, field_name: str, value: int | str | None) -> None:
        """Record one experimental field."""
        self.fields[field_name] = value


_ACTIVE_PROBE: ContextVar[DirectSendTimingProbe | None] = ContextVar(
    "swbt_direct_send_timing_probe",
    default=None,
)


def active_direct_send_timing_probe() -> DirectSendTimingProbe | None:
    """Return the task-local probe for the current direct send, if enabled."""
    return _ACTIVE_PROBE.get()


@contextmanager
def direct_send_timing_probe() -> Iterator[DirectSendTimingProbe | None]:
    """Emit one JSON DEBUG record for the enclosed direct ``send()`` call."""
    if not _LOGGER.isEnabledFor(logging.DEBUG):
        yield None
        return

    probe = DirectSendTimingProbe(
        operation_id=next(_OPERATION_IDS),
        started_ns=perf_counter_ns(),
    )
    token = _ACTIVE_PROBE.set(probe)
    try:
        yield probe
    except BaseException:
        probe.record("outcome", "error")
        raise
    else:
        probe.record("outcome", "success")
    finally:
        probe.record_elapsed("total_duration_ns", probe.started_ns)
        _LOGGER.debug(
            "%s",
            json.dumps(
                {
                    "event": "direct_send_timing",
                    "operation": "send",
                    "operation_id": probe.operation_id,
                    "hid_enqueue_duration_ns": None,
                    "acl_drain_duration_ns": None,
                    "acl_pending_total_before_enqueue": None,
                    "acl_pending_total_after_enqueue": None,
                    "acl_pending_total_after_drain": None,
                    **probe.fields,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
        )
        _ACTIVE_PROBE.reset(token)
