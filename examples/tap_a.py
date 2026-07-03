"""Minimal Button A tap example.

Running this file against real hardware opens the configured Bluetooth adapter
and starts a Switch-facing connection attempt. Use it only after the adapter,
command, trace handling, and cleanup scope have been approved.
"""

import argparse
import asyncio
from collections.abc import Sequence

from swbt import Button, SwitchGamepad


async def tap_a_once(pad: SwitchGamepad, *, duration: float = 0.08) -> None:
    """Tap Button A on an already connected gamepad.

    Args:
        pad: Open and connected gamepad.
        duration: Seconds to keep Button A pressed.

    Raises:
        swbt.errors.ClosedError: The gamepad is not open or cannot send reports.
    """
    await pad.tap(Button.A, duration=duration)
    await pad.neutral()


async def run(
    *,
    adapter: str,
    key_store_path: str | None,
    connect_timeout: float,
    duration: float,
    allow_pairing: bool,
) -> None:
    """Connect to a host and tap Button A once.

    Args:
        adapter: Bumble adapter moniker, such as ``"usb:0"``.
        key_store_path: Optional pairing key store path.
        connect_timeout: Seconds to wait for each connection attempt.
        duration: Seconds to keep Button A pressed.
        allow_pairing: If ``True``, allow first-time pairing when no bond exists.
    """
    async with SwitchGamepad(adapter=adapter, key_store_path=key_store_path) as pad:
        await pad.connect(
            timeout=connect_timeout,
            allow_pairing=allow_pairing,
        )
        await tap_a_once(pad, duration=duration)


def build_parser() -> argparse.ArgumentParser:
    """Build the example argument parser.

    Returns:
        argparse.ArgumentParser: Parser for this example script.
    """
    parser = argparse.ArgumentParser(
        description="Tap Button A once through swbt-python.",
    )
    parser.add_argument("--adapter", default="usb:0", help="Bumble adapter moniker")
    parser.add_argument("--key-store", dest="key_store_path", help="pairing key store path")
    parser.add_argument("--timeout", default=30.0, type=float, help="connection timeout seconds")
    parser.add_argument(
        "--duration",
        default=0.08,
        type=float,
        help="Button A press duration seconds",
    )
    parser.add_argument(
        "--allow-pairing",
        action="store_true",
        help="allow first-time pairing when no bonded peer is available",
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
            key_store_path=args.key_store_path,
            connect_timeout=args.timeout,
            duration=args.duration,
            allow_pairing=args.allow_pairing,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
