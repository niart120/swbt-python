"""Command line probes for swbt hardware setup."""

import argparse
import json
import sys
from collections.abc import Sequence


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
        "adapters": [],
        "opens_adapter": False,
        "status": "adapter probing is not implemented in this command yet",
    }
    if args.json:
        sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
    else:
        sys.stdout.write("This command does not open a Bluetooth adapter.\n")
        sys.stdout.write("Adapter probing will require an explicit hardware approval scope.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
