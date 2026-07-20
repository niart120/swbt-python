"""Command line probes for swbt hardware setup."""

import argparse
import asyncio
import json
import platform
import sys
from collections.abc import Sequence
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from swbt import AdapterDiscoveryError, AdapterInfo, DiagnosticsConfig, ProController, list_adapters


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
        "--profile",
        dest="profile_path",
        required=True,
        help="swbt profile path for the approved pairing run",
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
    try:
        adapters = list_adapters()
    except AdapterDiscoveryError as error:
        payload = {
            "adapters": [],
            "bumble_version": error.bumble_version,
            "error": _adapter_discovery_error_payload(error),
            "opens_adapter": False,
            "platform": error.platform,
            "python_version": platform.python_version(),
            "status": "discovery_error",
        }
        if args.json:
            sys.stdout.write(f"{json.dumps(payload, sort_keys=True)}\n")
        else:
            sys.stdout.write("Adapter discovery failed without opening a Bluetooth adapter.\n")
            sys.stdout.write(f"Error: {error}\n")
        return 1

    payload = {
        "adapters": [_adapter_info_payload(adapter) for adapter in adapters],
        "bumble_version": _package_version("bumble"),
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
        if adapters:
            sys.stdout.write("Candidate adapters:\n")
            for adapter in adapters:
                _write_adapter_text(adapter)
        else:
            sys.stdout.write("Candidate adapters: none\n")
        sys.stdout.write("Opening an adapter requires an explicit hardware approval scope.\n")
    return 0


def _run_pair(_args: argparse.Namespace) -> int:
    asyncio.run(
        _run_pair_probe(
            adapter=_args.adapter,
            profile_path=_args.profile_path,
            pair_timeout=_args.timeout,
            trace_path=_args.trace,
        )
    )
    return 0


async def _run_pair_probe(
    *,
    adapter: str,
    profile_path: str,
    pair_timeout: float,
    trace_path: Path,
) -> None:
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("w", encoding="utf-8") as trace_writer:
        diagnostics = DiagnosticsConfig(trace_writer=trace_writer)
        async with ProController(
            adapter=adapter,
            profile_path=profile_path,
            diagnostics=diagnostics,
        ) as pad:
            await pad.pair(timeout=pair_timeout)


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"


def _adapter_info_payload(adapter: AdapterInfo) -> dict[str, object]:
    return {
        "aliases": list(adapter.aliases),
        "bus_number": adapter.bus_number,
        "device_address": adapter.device_address,
        "is_bluetooth_hci": adapter.is_bluetooth_hci,
        "manufacturer": adapter.manufacturer,
        "name": adapter.name,
        "port_numbers": list(adapter.port_numbers),
        "product": adapter.product,
        "product_id": adapter.product_id,
        "product_id_hex": _usb_id_hex(adapter.product_id),
        "serial_number": adapter.serial_number,
        "vendor_id": adapter.vendor_id,
        "vendor_id_hex": _usb_id_hex(adapter.vendor_id),
    }


def _usb_id_hex(value: int | None) -> str | None:
    if value is None:
        return None
    return f"{value:04X}"


def _adapter_discovery_error_payload(error: AdapterDiscoveryError) -> dict[str, object]:
    return {
        "backend": error.backend,
        "bumble_version": error.bumble_version,
        "libusb_available": error.libusb_available,
        "message": str(error),
        "platform": error.platform,
        "type": type(error).__name__,
    }


def _write_adapter_text(adapter: AdapterInfo) -> None:
    sys.stdout.write(f"- {adapter.name}\n")
    if adapter.vendor_id is not None and adapter.product_id is not None:
        sys.stdout.write(
            f"  VID/PID: {_usb_id_hex(adapter.vendor_id)}:{_usb_id_hex(adapter.product_id)}\n"
        )
    if adapter.aliases:
        sys.stdout.write(f"  Aliases: {', '.join(adapter.aliases)}\n")
    if adapter.manufacturer:
        sys.stdout.write(f"  Manufacturer: {adapter.manufacturer}\n")
    if adapter.product:
        sys.stdout.write(f"  Product: {adapter.product}\n")
    if adapter.serial_number:
        sys.stdout.write(f"  Serial: {adapter.serial_number}\n")


if __name__ == "__main__":
    raise SystemExit(main())
