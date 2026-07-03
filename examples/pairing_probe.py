"""Pairing probe example with diagnostics trace output.

Running this file opens the configured Bluetooth adapter, starts HID advertising,
and waits for a host connection. Use it only after explicit approval covers the
adapter, target screen, trace path, timeout, and cleanup plan.
"""

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from swbt import DiagnosticsConfig, SwitchGamepad


async def run(
    *,
    adapter: str,
    key_store_path: str | None,
    trace_path: Path,
    pair_timeout: float,
) -> None:
    """Run one approved pairing probe.

    Args:
        adapter: Bumble adapter moniker, such as ``"usb:0"``.
        key_store_path: Optional pairing key store path.
        trace_path: JSON Lines diagnostics trace output path.
        pair_timeout: Seconds to wait for a host connection.
    """
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as trace_writer:
        await _pair_with_trace(
            adapter=adapter,
            key_store_path=key_store_path,
            pair_timeout=pair_timeout,
            trace_writer=trace_writer,
        )


async def _pair_with_trace(
    *,
    adapter: str,
    key_store_path: str | None,
    pair_timeout: float,
    trace_writer: TextIO,
) -> None:
    diagnostics = DiagnosticsConfig(trace_writer=trace_writer)
    async with SwitchGamepad(
        adapter=adapter,
        diagnostics=diagnostics,
    ) as pad:
        await pad.pair(timeout=pair_timeout, key_store_path=key_store_path)


def build_parser() -> argparse.ArgumentParser:
    """Build the example argument parser.

    Returns:
        argparse.ArgumentParser: Parser for this example script.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Run a pairing probe after explicit approval. The approval scope must include cleanup."
        ),
    )
    parser.add_argument("--adapter", default="usb:0", help="Bumble adapter moniker")
    parser.add_argument("--key-store", dest="key_store_path", help="pairing key store path")
    parser.add_argument("--trace", required=True, type=Path, help="JSON Lines trace output path")
    parser.add_argument("--timeout", default=30.0, type=float, help="pairing timeout seconds")
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
            key_store_path=args.key_store_path,
            trace_path=args.trace,
            pair_timeout=args.timeout,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
