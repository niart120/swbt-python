"""Create one Pro Controller profile after explicit hardware approval."""

import argparse
import asyncio
from collections.abc import Sequence
from pathlib import Path

from swbt import DiagnosticsConfig, ProController


async def run(
    *,
    adapter: str,
    profile_path: str,
    exp_local_address: str,
    trace_path: Path,
    pair_timeout: float,
) -> None:
    """Create a profile and run its first approved pairing.

    Args:
        adapter: Bumble adapter moniker, such as ``"usb:0"``.
        profile_path: New swbt profile path. It must not already exist.
        exp_local_address: Individual locally administered Bluetooth address.
        trace_path: JSON Lines diagnostics trace output path.
        pair_timeout: Seconds to wait for a host connection.
    """
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as trace_writer:
        pad = await ProController.create_profile(
            adapter=adapter,
            profile_path=profile_path,
            exp_local_address=exp_local_address,
            pair_timeout=pair_timeout,
            diagnostics=DiagnosticsConfig(trace_writer=trace_writer),
        )
        await pad.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the example argument parser."""
    parser = argparse.ArgumentParser(
        description="Create a profile and pair after explicit approval with cleanup.",
    )
    parser.add_argument("--adapter", default="usb:0", help="Bumble adapter moniker")
    parser.add_argument("--profile", required=True, help="new swbt profile path")
    parser.add_argument(
        "--exp-local-address",
        required=True,
        help="individual locally administered Bluetooth address",
    )
    parser.add_argument("--trace", required=True, type=Path, help="JSON Lines trace output path")
    parser.add_argument("--timeout", default=30.0, type=float, help="pairing timeout seconds")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the example."""
    args = build_parser().parse_args(argv)
    asyncio.run(
        run(
            adapter=args.adapter,
            profile_path=args.profile,
            exp_local_address=args.exp_local_address,
            trace_path=args.trace,
            pair_timeout=args.timeout,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
