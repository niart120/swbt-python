"""Command line probes for swbt hardware setup."""

import argparse
import asyncio
import json
import platform
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from swbt import DiagnosticsConfig, SwitchGamepad


def build_parser() -> argparse.ArgumentParser:
    """Build the swbt-probe argument parser.

    Returns:
        argparse.ArgumentParser: Parser for the ``swbt-probe`` command.
    """
    parser = argparse.ArgumentParser(
        prog="swbt-probe",
        description="Probe helper for swbt-python development and hardware setup.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    adapters_parser = subparsers.add_parser(
        "adapters",
        description=(
            "Show adapter discovery guidance. This command does not open a Bluetooth adapter."
        ),
        help="show adapter discovery guidance without opening hardware",
    )
    adapters_parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable adapter probe guidance",
    )
    adapters_parser.set_defaults(handler=_run_adapters)

    pair_parser = subparsers.add_parser(
        "pair",
        description=(
            "Pairing probe requires explicit approval before any Switch-facing Bluetooth action."
        ),
        help="show pairing probe options and approval requirements",
    )
    pair_parser.add_argument(
        "--adapter",
        default="usb:0",
        help="adapter moniker to use after approval, for example usb:0",
    )
    pair_parser.add_argument(
        "--key-store",
        dest="key_store_path",
        help="pairing key store path for the approved pairing run",
    )
    pair_parser.add_argument(
        "--trace",
        required=True,
        type=Path,
        metavar="PATH",
        help="JSON Lines trace output path for the approved pairing run",
    )
    pair_parser.add_argument(
        "--timeout",
        default=30.0,
        type=float,
        help="seconds to wait for pairing during an approved run",
    )
    pair_parser.set_defaults(handler=_run_pair)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the swbt-probe command.

    Args:
        argv: Optional argument vector. ``None`` reads arguments from ``sys.argv``.

    Returns:
        int: Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = args.handler
    return int(handler(args))


def _run_adapters(args: argparse.Namespace) -> int:
    payload = {
        "bumble_version": _package_version("bumble"),
        "candidate_adapters": ["usb:0"],
        "opens_adapter": False,
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "status": "adapter listing does not open hardware",
    }
    if args.json:
        sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
    else:
        sys.stdout.write("This command does not open a Bluetooth adapter.\n")
        sys.stdout.write(f"Platform: {payload['platform']}\n")
        sys.stdout.write(f"Python: {payload['python_version']}\n")
        sys.stdout.write(f"Bumble: {payload['bumble_version']}\n")
        sys.stdout.write("Candidate adapters: usb:0\n")
        sys.stdout.write("Opening an adapter requires an explicit hardware approval scope.\n")
    return 0


def _run_pair(_args: argparse.Namespace) -> int:
    asyncio.run(
        _run_pair_probe(
            adapter=_args.adapter,
            key_store_path=_args.key_store_path,
            pair_timeout=_args.timeout,
            trace_path=_args.trace,
        )
    )
    return 0


async def _run_pair_probe(
    *,
    adapter: str,
    key_store_path: str | None,
    pair_timeout: float,
    trace_path: Path,
) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as trace_writer:
        diagnostics = DiagnosticsConfig(trace_writer=trace_writer)
        async with SwitchGamepad(
            adapter=adapter,
            key_store_path=key_store_path,
            diagnostics=diagnostics,
        ) as pad:
            await pad.pair(timeout=pair_timeout)


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
