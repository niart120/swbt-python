"""Characterize Bumble ACL credit flow while sending gyro input.

This is an explicit hardware probe. It opens the configured Bluetooth adapter,
actively reconnects with an existing Pro Controller profile, sends positive yaw
through the Direct or Periodic route, and closes with a neutral report.
"""

import argparse
import asyncio
import json
import platform
import sys
import time
from collections import deque
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal, Protocol

import bumble
from bumble import hci
from bumble.host import DataPacketQueue
from bumble.transport.usb import UsbPacketSink

from swbt import DiagnosticsConfig, DirectProController, IMUFrame, InputState, ProController

_DEFAULT_PERIODS_MS = (8.0, 16.0, 8.0)
_DEFAULT_PHASE_SECONDS = 8.0
_DEFAULT_MAX_EVENTS = 100_000
type Route = Literal["direct", "periodic"]


class UsbTransfer(Protocol):
    """Subset of usb1 transfer methods used by the diagnostic callback."""

    def getStatus(self) -> int:  # noqa: N802 - mirrors usb1 API
        """Return the libusb transfer status."""
        ...

    def getActualLength(self) -> int:  # noqa: N802 - mirrors usb1 API
        """Return the completed transfer length."""
        ...

    def getBuffer(self) -> bytes | bytearray | memoryview:  # noqa: N802 - mirrors usb1 API
        """Return the transfer buffer."""
        ...


class ReconnectError(RuntimeError):
    """Raised when the approved active reconnect does not reach connected."""

    def __init__(self, result: object) -> None:
        """Describe the unsuccessful reconnect result."""
        super().__init__(f"active reconnect failed: {result}")


class CreditRecorder:
    """Record Bumble queue transitions without file I/O in the send path."""

    def __init__(self, *, max_events: int) -> None:
        """Create a bounded recorder."""
        self._events: deque[dict[str, object]] = deque(maxlen=max_events)
        self._total_events = 0
        self._original_init = DataPacketQueue.__init__
        self._original_enqueue = DataPacketQueue.enqueue
        self._original_completed = DataPacketQueue.on_packets_completed
        self._original_usb_init = UsbPacketSink.__init__
        self._original_usb_on_packet = UsbPacketSink.on_packet
        self._original_usb_transfer_callback = UsbPacketSink.transfer_callback

    def record(self, event: str, **fields: object) -> None:
        """Append one timestamped event to the bounded in-memory buffer."""
        self._total_events += 1
        self._events.append(
            {
                "sequence": self._total_events,
                "perf_counter_ns": time.perf_counter_ns(),
                "event": event,
                **fields,
            }
        )

    @staticmethod
    def _queue_fields(queue: DataPacketQueue) -> dict[str, int]:
        return {
            "max_in_flight": queue.max_in_flight,
            "in_flight": queue._in_flight,
            "waiting": len(queue._packets),
            "queued_total": queue.queued,
            "completed_total": queue.completed,
            "pending": queue.pending,
        }

    def install(self) -> None:
        """Install temporary queue instrumentation for this process."""
        recorder = self
        original_init = self._original_init
        original_enqueue = self._original_enqueue
        original_completed = self._original_completed
        original_usb_init = self._original_usb_init
        original_usb_on_packet = self._original_usb_on_packet
        original_usb_transfer_callback = self._original_usb_transfer_callback

        def instrumented_init(
            queue: DataPacketQueue,
            max_packet_size: int,
            max_in_flight: int,
            send: Callable[[hci.HCI_Packet], None],
        ) -> None:
            original_init(queue, max_packet_size, max_in_flight, send)
            original_send = queue._send
            queue_id = id(queue)

            def instrumented_send(packet: hci.HCI_Packet) -> None:
                packet_fields: dict[str, object] = {
                    "queue_id": queue_id,
                    **recorder._queue_fields(queue),
                }
                if isinstance(packet, hci.HCI_AclDataPacket):
                    packet_fields.update(
                        {
                            "connection_handle": packet.connection_handle,
                            "pb_flag": packet.pb_flag,
                            "bc_flag": packet.bc_flag,
                            "data_total_length": packet.data_total_length,
                            "data_prefix_hex": packet.data[:16].hex(),
                            "data_hex": packet.data.hex(),
                        }
                    )
                recorder.record("acl_dispatch", **packet_fields)
                original_send(packet)

            queue._send = instrumented_send
            recorder.record(
                "queue_created",
                queue_id=queue_id,
                max_packet_size=max_packet_size,
                max_in_flight=max_in_flight,
            )

        def instrumented_enqueue(
            queue: DataPacketQueue,
            packet: hci.HCI_Packet,
            connection_handle: int,
        ) -> None:
            recorder.record(
                "acl_enqueue_before",
                queue_id=id(queue),
                connection_handle=connection_handle,
                **recorder._queue_fields(queue),
            )
            original_enqueue(queue, packet, connection_handle)
            recorder.record(
                "acl_enqueue_after",
                queue_id=id(queue),
                connection_handle=connection_handle,
                **recorder._queue_fields(queue),
            )

        def instrumented_completed(
            queue: DataPacketQueue,
            packet_count: int,
            connection_handle: int,
        ) -> None:
            recorder.record(
                "credit_return_before",
                queue_id=id(queue),
                connection_handle=connection_handle,
                packet_count=packet_count,
                **recorder._queue_fields(queue),
            )
            original_completed(queue, packet_count, connection_handle)
            recorder.record(
                "credit_return_after",
                queue_id=id(queue),
                connection_handle=connection_handle,
                packet_count=packet_count,
                **recorder._queue_fields(queue),
            )

        class RecordingSemaphore:
            def __init__(
                self,
                semaphore: asyncio.Semaphore,
                sink: UsbPacketSink,
            ) -> None:
                self._semaphore = semaphore
                self._sink = sink

            async def acquire(self) -> bool:
                acquired = await self._semaphore.acquire()
                recorder.record(
                    "usb_out_slot_acquired",
                    sink_id=id(self._sink),
                    usb_waiting=self._sink.packets.qsize(),
                )
                return acquired

            def release(self) -> None:
                recorder.record(
                    "usb_out_slot_released",
                    sink_id=id(self._sink),
                    usb_waiting=self._sink.packets.qsize(),
                )
                self._semaphore.release()

        def instrumented_usb_init(
            sink: UsbPacketSink,
            device: object,
            bulk_out: object,
            isochronous_out: object,
        ) -> None:
            original_usb_init(sink, device, bulk_out, isochronous_out)
            object.__setattr__(
                sink,
                "out_transfer_ready",
                RecordingSemaphore(sink.out_transfer_ready, sink),
            )
            recorder.record("usb_sink_created", sink_id=id(sink))

        def instrumented_usb_on_packet(
            sink: UsbPacketSink,
            packet: bytes,
        ) -> None:
            recorder.record(
                "usb_sink_enqueue",
                sink_id=id(sink),
                usb_waiting_before=sink.packets.qsize(),
                packet_type=packet[0] if packet else None,
                packet_prefix_hex=packet[:21].hex(),
            )
            original_usb_on_packet(sink, packet)

        def instrumented_usb_transfer_callback(
            sink: UsbPacketSink,
            transfer: UsbTransfer,
        ) -> None:
            actual_length = transfer.getActualLength()
            recorder.record(
                "usb_out_transfer_callback",
                sink_id=id(sink),
                usb_waiting=sink.packets.qsize(),
                status=transfer.getStatus(),
                actual_length=actual_length,
                buffer_prefix_hex=bytes(transfer.getBuffer()[:actual_length])[:20].hex(),
            )
            original_usb_transfer_callback(sink, transfer)

        type.__setattr__(DataPacketQueue, "__init__", instrumented_init)
        type.__setattr__(DataPacketQueue, "enqueue", instrumented_enqueue)
        type.__setattr__(DataPacketQueue, "on_packets_completed", instrumented_completed)
        type.__setattr__(UsbPacketSink, "__init__", instrumented_usb_init)
        type.__setattr__(UsbPacketSink, "on_packet", instrumented_usb_on_packet)
        type.__setattr__(
            UsbPacketSink,
            "transfer_callback",
            instrumented_usb_transfer_callback,
        )

    def uninstall(self) -> None:
        """Restore the Bumble class methods replaced by :meth:`install`."""
        type.__setattr__(DataPacketQueue, "__init__", self._original_init)
        type.__setattr__(DataPacketQueue, "enqueue", self._original_enqueue)
        type.__setattr__(
            DataPacketQueue,
            "on_packets_completed",
            self._original_completed,
        )
        type.__setattr__(UsbPacketSink, "__init__", self._original_usb_init)
        type.__setattr__(UsbPacketSink, "on_packet", self._original_usb_on_packet)
        type.__setattr__(
            UsbPacketSink,
            "transfer_callback",
            self._original_usb_transfer_callback,
        )

    def write(self, path: Path, *, metadata: dict[str, object]) -> None:
        """Write metadata and retained events after adapter cleanup."""
        path.parent.mkdir(parents=True, exist_ok=True)
        retained_events = list(self._events)
        payload = {
            "metadata": {
                **metadata,
                "total_events": self._total_events,
                "retained_events": len(retained_events),
                "dropped_events": self._total_events - len(retained_events),
            },
            "events": retained_events,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def _send_phase(
    pad: DirectProController,
    recorder: CreditRecorder,
    *,
    phase_index: int,
    period_ms: float,
    duration_seconds: float,
    state: InputState,
) -> None:
    """Send one fixed-deadline phase without catch-up bursts."""
    period_seconds = period_ms / 1000.0
    deadline = time.perf_counter()
    phase_end = deadline + duration_seconds
    send_index = 0
    recorder.record(
        "phase_start",
        phase_index=phase_index,
        period_ms=period_ms,
        duration_seconds=duration_seconds,
    )

    while deadline < phase_end:
        delay = deadline - time.perf_counter()
        if delay > 0:
            await asyncio.sleep(delay)

        started_ns = time.perf_counter_ns()
        await pad.send(state)
        completed_ns = time.perf_counter_ns()
        recorder.record(
            "direct_send_complete",
            phase_index=phase_index,
            send_index=send_index,
            period_ms=period_ms,
            call_started_ns=started_ns,
            call_completed_ns=completed_ns,
            call_duration_ns=completed_ns - started_ns,
        )
        send_index += 1
        deadline += period_seconds

        now = time.perf_counter()
        if deadline <= now:
            skipped = int((now - deadline) // period_seconds) + 1
            recorder.record(
                "deadline_skipped",
                phase_index=phase_index,
                skipped=skipped,
            )
            deadline += skipped * period_seconds

    recorder.record(
        "phase_end",
        phase_index=phase_index,
        period_ms=period_ms,
        sends=send_index,
    )


async def _observe_periodic_phase(
    pad: ProController,
    recorder: CreditRecorder,
    *,
    period_ms: float,
    duration_seconds: float,
    state: InputState,
) -> None:
    """Apply one state and observe the Periodic route for one fixed period."""
    recorder.record(
        "phase_start",
        phase_index=0,
        period_ms=period_ms,
        duration_seconds=duration_seconds,
    )
    await pad.apply(state)
    await asyncio.sleep(duration_seconds)
    await pad.apply(InputState.neutral())
    recorder.record(
        "phase_end",
        phase_index=0,
        period_ms=period_ms,
        sends=None,
    )


async def run(
    *,
    route: Route,
    adapter: str,
    profile_path: Path,
    trace_path: Path,
    output_path: Path,
    periods_ms: Sequence[float],
    phase_seconds: float,
    settle_seconds: float,
    max_events: int,
    high_resolution_loop_clock: bool,
) -> None:
    """Reconnect, send A-B-A positive-yaw input, neutralize, and close."""
    loop = asyncio.get_running_loop()
    monotonic_info = time.get_clock_info("monotonic")
    perf_counter_info = time.get_clock_info("perf_counter")
    if high_resolution_loop_clock:
        object.__setattr__(loop, "time", time.perf_counter)
        object.__setattr__(
            loop,
            "_clock_resolution",
            perf_counter_info.resolution,
        )
    loop_resolution = getattr(loop, "_clock_resolution", None)

    original_profile = await asyncio.to_thread(profile_path.read_bytes)
    recorder = CreditRecorder(max_events=max_events)
    recorder.install()
    trace_path.parent.mkdir(parents=True, exist_ok=True)

    metadata: dict[str, object] = {
        "route": route,
        "adapter": adapter,
        "profile_path": str(profile_path),
        "trace_path": str(trace_path),
        "periods_ms": list(periods_ms),
        "phase_seconds": phase_seconds,
        "settle_seconds": settle_seconds,
        "gyro_rate_rad_s": {"x": 0.0, "y": 0.0, "z": 1.0},
        "acceleration_g": {"x": 0.0, "y": 0.0, "z": 1.0},
        "platform": platform.platform(),
        "python_version": sys.version,
        "bumble_version": bumble.__version__,
        "clocks": {
            "monotonic": {
                "implementation": monotonic_info.implementation,
                "resolution_seconds": monotonic_info.resolution,
            },
            "perf_counter": {
                "implementation": perf_counter_info.implementation,
                "resolution_seconds": perf_counter_info.resolution,
            },
            "event_loop": {
                "high_resolution_override": high_resolution_loop_clock,
                "resolution_seconds": loop_resolution,
            },
        },
    }

    try:
        with trace_path.open("w", encoding="utf-8") as trace_writer:
            diagnostics = DiagnosticsConfig(trace_writer=trace_writer)
            pad: DirectProController | ProController
            if route == "direct":
                pad = DirectProController(
                    adapter=adapter,
                    profile_path=str(profile_path),
                    diagnostics=diagnostics,
                )
            else:
                pad = ProController(
                    adapter=adapter,
                    profile_path=str(profile_path),
                    report_period_us=round(periods_ms[0] * 1000),
                    diagnostics=diagnostics,
                )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                if result.status != "connected":
                    raise ReconnectError(result)
                recorder.record("reconnect_complete", status=result.status)
                if settle_seconds:
                    await asyncio.sleep(settle_seconds)

                imu = IMUFrame.gyro_rate(z_rad_s=1.0).with_accel_g(z_g=1.0)
                gyro_state = InputState.neutral().with_imu(imu)
                if isinstance(pad, DirectProController):
                    for phase_index, period_ms in enumerate(periods_ms):
                        await _send_phase(
                            pad,
                            recorder,
                            phase_index=phase_index,
                            period_ms=period_ms,
                            duration_seconds=phase_seconds,
                            state=gyro_state,
                        )
                else:
                    await _observe_periodic_phase(
                        pad,
                        recorder,
                        period_ms=periods_ms[0],
                        duration_seconds=phase_seconds,
                        state=gyro_state,
                    )
            finally:
                recorder.record("cleanup_start")
                await pad.close(neutral=True)
                recorder.record(
                    "cleanup_complete",
                    connection_state=pad.status().connection_state,
                )
    finally:
        recorder.uninstall()
        current_profile = await asyncio.to_thread(profile_path.read_bytes)
        metadata["profile_unchanged"] = current_profile == original_profile
        recorder.write(output_path, metadata=metadata)


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit hardware probe command line."""
    parser = argparse.ArgumentParser(
        description=(
            "Reconnect a Pro Controller and record Bumble ACL credit flow during "
            "positive-yaw Direct or Periodic input. Requires explicit hardware approval."
        )
    )
    parser.add_argument("--route", choices=("direct", "periodic"), default="direct")
    parser.add_argument("--adapter", default="usb:0")
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--period-ms",
        dest="periods_ms",
        nargs="+",
        type=float,
        default=list(_DEFAULT_PERIODS_MS),
    )
    parser.add_argument("--phase-seconds", type=float, default=_DEFAULT_PHASE_SECONDS)
    parser.add_argument("--settle-seconds", type=float, default=2.0)
    parser.add_argument("--max-events", type=int, default=_DEFAULT_MAX_EVENTS)
    parser.add_argument(
        "--high-resolution-loop-clock",
        action="store_true",
        help=(
            "diagnostic override: use perf_counter for the running asyncio loop "
            "instead of the Python default clock"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the hardware probe."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.profile.is_file():
        parser.error(f"profile does not exist: {args.profile}")
    if any(period_ms <= 0 for period_ms in args.periods_ms):
        parser.error("--period-ms values must be positive")
    if args.route == "periodic" and len(args.periods_ms) != 1:
        parser.error("Periodic route requires exactly one --period-ms value")
    if args.phase_seconds <= 0:
        parser.error("--phase-seconds must be positive")
    if args.settle_seconds < 0:
        parser.error("--settle-seconds must not be negative")
    if args.max_events <= 0:
        parser.error("--max-events must be positive")

    asyncio.run(
        run(
            route=args.route,
            adapter=args.adapter,
            profile_path=args.profile,
            trace_path=args.trace,
            output_path=args.output,
            periods_ms=args.periods_ms,
            phase_seconds=args.phase_seconds,
            settle_seconds=args.settle_seconds,
            max_events=args.max_events,
            high_resolution_loop_clock=args.high_resolution_loop_clock,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
