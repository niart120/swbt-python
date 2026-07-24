"""Bounded automatic reporting during Switch protocol handshake."""

import asyncio
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal

from swbt.diagnostics import DiagnosticsRecorder
from swbt.input import InputState
from swbt.protocol.session import SwitchHidSession
from swbt.report_loop import ReportSender

HANDSHAKE_BOOTSTRAP_RETRY_SECONDS = 1.0


@dataclass(frozen=True)
class HandshakeOutcome:
    """Terminal result of one protocol handshake."""

    state: Literal["ready", "failed"]
    error: Exception | None = None


class ProtocolHandshake:
    """Own automatic neutral reports from HID link connection through readiness."""

    def __init__(
        self,
        *,
        sender: ReportSender,
        session: SwitchHidSession,
        report_period_us: int,
        on_outcome: Callable[[HandshakeOutcome], None],
        diagnostics: DiagnosticsRecorder | None = None,
        bootstrap_retry_seconds: float = HANDSHAKE_BOOTSTRAP_RETRY_SECONDS,
    ) -> None:
        """Create a handshake that borrows the session and report sender."""
        self._sender = sender
        self._session = session
        self._report_period_seconds = report_period_us / 1_000_000
        self._on_outcome = on_outcome
        self._diagnostics = diagnostics
        self._bootstrap_retry_seconds = bootstrap_retry_seconds
        self._changed = asyncio.Event()
        self._subcommand_received = False
        self._stopped = False
        self._failure: Exception | None = None
        self._attempts = 0
        self._task: asyncio.Task[HandshakeOutcome | None] | None = None

    def start(self) -> None:
        """Start the one automatic-report task for this handshake."""
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="swbt-protocol-handshake")
        self._task.add_done_callback(self._task_finished)
        self._record("handshake_bootstrap_started", retry_seconds=self._bootstrap_retry_seconds)

    def subcommand_received(self, subcommand_id: int) -> None:
        """Stop bootstrap retries after the first parsed subcommand."""
        if self._subcommand_received:
            return
        self._subcommand_received = True
        self._changed.set()
        self._record(
            "handshake_bootstrap_stopped",
            attempts=self._attempts,
            reason="subcommand_received",
            subcommand_id=f"0x{subcommand_id:02x}",
        )

    def protocol_state_updated(self) -> None:
        """Wake automatic reporting after a reply changes the borrowed session."""
        self._changed.set()

    def fail(self, error: Exception) -> None:
        """Finish the handshake as failed after the automatic task is collected."""
        if self._failure is None:
            self._failure = error
        self._changed.set()

    async def stop(self) -> None:
        """Stop and collect the automatic-report task without an outcome callback."""
        await self._stop_task()

    async def complete_ready(self) -> None:
        """Collect the task, then publish a ready outcome exactly once."""
        await self._complete(HandshakeOutcome("ready"))

    async def complete_failure(self, error: Exception) -> None:
        """Collect the task, then publish a failed outcome exactly once."""
        await self._complete(HandshakeOutcome("failed", error))

    async def _complete(self, outcome: HandshakeOutcome) -> None:
        if self._stopped:
            return
        await self._stop_task()
        self._on_outcome(outcome)

    async def _stop_task(self) -> None:
        self._stopped = True
        self._changed.set()
        task = self._task
        if task is None:
            return
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task

    async def wait(self) -> HandshakeOutcome | None:
        """Wait for the automatic-report task to reach its terminal outcome."""
        task = self._task
        if task is None:
            return None
        return await task

    async def _run(self) -> HandshakeOutcome | None:
        try:
            while not self._stopped:
                self._changed.clear()
                if self._failure is not None:
                    return HandshakeOutcome("failed", self._failure)
                if self._session.state.protocol_ready:
                    return HandshakeOutcome("ready")
                if not self._subcommand_received:
                    self._attempts += 1
                    await self._sender.send_automatic_input(
                        InputState.neutral(),
                        reason="handshake_bootstrap",
                    )
                    await self._wait_for_change(self._bootstrap_retry_seconds)
                    continue
                if self._session.state.report_mode_supported:
                    await self._sender.send_automatic_input(
                        InputState.neutral(),
                        reason="handshake_report_mode",
                    )
                    await self._wait_for_change(self._report_period_seconds)
                    continue
                await self._wait_for_change(None)
        except asyncio.CancelledError:
            raise
        except Exception as error:  # noqa: BLE001
            return HandshakeOutcome("failed", error)
        return None

    async def _wait_for_change(self, wait_seconds: float | None) -> None:
        if wait_seconds is None:
            await self._changed.wait()
            return
        try:
            async with asyncio.timeout(wait_seconds):
                await self._changed.wait()
        except TimeoutError:
            pass

    def _task_finished(self, task: asyncio.Task[HandshakeOutcome | None]) -> None:
        if self._stopped or task.cancelled():
            return
        outcome = task.result()
        if outcome is not None:
            self._on_outcome(outcome)

    def _record(self, event: str, **fields: object) -> None:
        if self._diagnostics is not None:
            self._diagnostics.record_event(event, **fields)
