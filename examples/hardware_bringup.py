"""Hardware bring-up example for a connect, tap, neutral, and close path.

Running this file opens the configured Bluetooth adapter and sends input reports.
Use it only after explicit approval covers the adapter, target screen, trace
path, timeout, input action, and cleanup plan.
"""

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from swbt import Button, DiagnosticsConfig, ProController


async def run(
    *,
    adapter: str,
    profile_path: str,
    trace_path: Path,
    connect_timeout: float,
    tap_duration: float,
) -> None:
    """Run one approved hardware bring-up path.

    Args:
        adapter: Bumble adapter moniker, such as ``"usb:0"``.
        profile_path: Existing swbt profile path.
        trace_path: JSON Lines diagnostics trace output path.
        connect_timeout: Seconds to wait for reconnect or pairing.
        tap_duration: Seconds to keep Button A pressed.
    """
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as trace_writer:
        await _bring_up_with_trace(
            adapter=adapter,
            profile_path=profile_path,
            connect_timeout=connect_timeout,
            tap_duration=tap_duration,
            trace_writer=trace_writer,
        )


async def _bring_up_with_trace(
    *,
    adapter: str,
    profile_path: str,
    connect_timeout: float,
    tap_duration: float,
    trace_writer: TextIO,
) -> None:
    diagnostics = DiagnosticsConfig(trace_writer=trace_writer)
    async with ProController(
        adapter=adapter,
        profile_path=profile_path,
        diagnostics=diagnostics,
    ) as pad:
        await pad.connect(
            timeout=connect_timeout,
            allow_pairing=True,
        )
        await pad.tap(Button.A, duration=tap_duration)
        await pad.neutral()


def build_parser() -> argparse.ArgumentParser:
    """Build the example argument parser.

    Returns:
        argparse.ArgumentParser: Parser for this example script.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run hardware bring-up after explicit approval. The approval scope must "
            "include cleanup."
        ),
    )
    parser.add_argument("--adapter", default="usb:0", help="Bumble adapter moniker")
    parser.add_argument(
        "--profile", dest="profile_path", required=True, help="existing swbt profile path"
    )
    parser.add_argument("--trace", required=True, type=Path, help="JSON Lines trace output path")
    parser.add_argument("--timeout", default=30.0, type=float, help="connection timeout seconds")
    parser.add_argument(
        "--tap-duration",
        default=0.08,
        type=float,
        help="Button A press duration seconds",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the example.

    Args:
        argv: Optional argument vector. ``None`` reads arguments from ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    args = build_parser().parse_args(argv)
    asyncio.run(
        run(
            adapter=args.adapter,
            profile_path=args.profile_path,
            trace_path=args.trace,
            connect_timeout=args.timeout,
            tap_duration=args.tap_duration,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
