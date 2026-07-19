"""Read a CSR adapter identity without advertising or writing PSKEY values."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from swbt.transport._csr_bd_addr_harness import (
    probe_csr_identity as _probe,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Open one Bumble adapter, issue standard HCI identity reads and one "
            "CSR PSKEY_BDADDR GETREQ, then close it. No advertising or writes."
        )
    )
    parser.add_argument("--adapter", required=True, help="approved Bumble adapter, e.g. usb:0")
    parser.add_argument(
        "--output",
        type=Path,
        help="optional JSON artifact path",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=2.0,
        help="seconds to wait for each HCI response",
    )
    parser.add_argument(
        "--hci-reset",
        action="store_true",
        help="send an approved transient HCI Reset before the identity reads",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the approved read-only probe and emit its JSON result."""
    args = _parser().parse_args(argv)
    if args.timeout <= 0:
        _parser().error("--timeout must be greater than zero")
    result = asyncio.run(
        _probe(
            args.adapter,
            response_timeout=args.timeout,
            hci_reset=args.hci_reset,
        )
    )
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(output)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
