"""Apply a CSR PSRAM BD_ADDR and enqueue warm reset without RF activity."""

import argparse
import asyncio
import json
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from swbt.transport._csr_bd_addr import build_csr_bd_addr_volatile_experiment_plan
from swbt.transport._csr_bd_addr_harness import (
    CsrAdapterSession,
)
from swbt.transport._csr_bd_addr_harness import (
    command_payload as _command_payload,
)
from swbt.transport._csr_bd_addr_harness import (
    require_csr_company_identifier as _require_csr_company_identifier,
)
from swbt.transport._csr_bd_addr_harness import (
    require_equal as _require_equal,
)

_CSR_DEFAULT_STORE = 0x0000
_CSR_PSRAM_STORE = 0x0008


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Apply one CSR PSRAM BD_ADDR, verify it, enqueue CSR warm reset, "
            "then exit for a separate-process identity read. No advertising, "
            "pairing, persistent write, or automatic restore is performed."
        )
    )
    parser.add_argument("--adapter", default="usb:0")
    parser.add_argument("--expected-original", required=True)
    parser.add_argument("--requested-address", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--settle-seconds", type=float, default=0.5)
    return parser


async def _execute(
    *,
    adapter: str,
    original_address: str,
    requested_address: str,
    response_timeout: float,
    settle_seconds: float,
) -> dict[str, object]:
    experiment = build_csr_bd_addr_volatile_experiment_plan(
        original_address=original_address,
        requested_address=requested_address,
    )
    result: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "adapter": adapter,
        "os": platform.platform(),
        "python": platform.python_version(),
        "bumble": version("bumble"),
        "original_address": experiment.original_address,
        "requested_address": experiment.requested_address,
        "persistent_write": False,
        "warm_reset": True,
        "advertising": False,
        "switch_facing": False,
        "automatic_restore": False,
        "recovery": "physical_power_cycle_required",
        "status": "started",
        "stage": "open_adapter",
        "cleanup": "not_started",
    }
    session: CsrAdapterSession | None = None
    psram_changed = False
    warm_reset_enqueued = False
    try:
        session = await CsrAdapterSession.open(adapter)
        metadata = await session.initialize(
            response_timeout=response_timeout,
            hci_reset=True,
        )
        _require_csr_company_identifier(metadata.company_identifier)

        result["stage"] = "verify_baseline"
        standard_before = await session.read_standard_address(
            response_timeout=response_timeout,
        )
        csr_before, baseline_event = await session.read_csr_address(
            store=_CSR_DEFAULT_STORE,
            sequence_number=0x4710,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=standard_before,
            expected=experiment.original_address,
            source="standard HCI address",
        )
        _require_equal(
            actual=csr_before,
            expected=experiment.original_address,
            source="CSR default-store address",
        )
        result["baseline"] = {
            "standard_address": standard_before,
            "csr_address": csr_before,
            "csr_vendor_event_hex": baseline_event,
            "company_identifier": metadata.company_identifier,
        }

        result["stage"] = "apply_psram_write"
        result["apply_write"] = await session.send_write(
            experiment.apply,
            response_timeout=response_timeout,
        )

        result["stage"] = "verify_psram_requested"
        psram_address, changed_event = await session.read_csr_address(
            store=_CSR_PSRAM_STORE,
            sequence_number=0x4712,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=psram_address,
            expected=experiment.requested_address,
            source="CSR PSRAM address",
        )
        psram_changed = True
        standard_during = await session.read_standard_address(
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=standard_during,
            expected=experiment.original_address,
            source="active standard HCI address before warm reset",
        )
        result["changed"] = {
            "psram_address": psram_address,
            "standard_address": standard_during,
            "csr_vendor_event_hex": changed_event,
        }

        result["stage"] = "enqueue_csr_warm_reset"
        session.enqueue_warm_reset(experiment.apply.reset_command)
        warm_reset_enqueued = True
        result["warm_reset_command"] = _command_payload(experiment.apply.reset_command)
        result["warm_reset_enqueued"] = True
        await asyncio.sleep(settle_seconds)
        result["status"] = "warm_reset_enqueued"
        result["stage"] = "await_separate_process_identity_read"
    except Exception as error:  # noqa: BLE001
        result.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
                "psram_changed": psram_changed,
                "warm_reset_enqueued": warm_reset_enqueued,
            }
        )
    finally:
        if session is None:
            result["cleanup"] = "adapter_not_opened"
        else:
            try:
                await session.close()
                result["cleanup"] = "adapter_closed_or_reenumerated"
            except Exception as error:  # noqa: BLE001
                result["cleanup"] = {
                    "status": "close_failed_after_possible_reenumeration",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
    return result


def _dry_run_payload(args: argparse.Namespace) -> dict[str, object]:
    experiment = build_csr_bd_addr_volatile_experiment_plan(
        original_address=args.expected_original,
        requested_address=args.requested_address,
    )
    return {
        "adapter_opened": False,
        "execute": False,
        "adapter": args.adapter,
        "persistent_write": False,
        "warm_reset": True,
        "advertising": False,
        "switch_facing": False,
        "automatic_restore": False,
        "recovery": "physical_power_cycle_required",
        "apply_write": _command_payload(experiment.apply.write_command),
        "warm_reset_command": _command_payload(experiment.apply.reset_command),
        "sequence": [
            "verify_original",
            "apply_psram_write",
            "read_psram_requested",
            "verify_active_address_unchanged",
            "enqueue_csr_warm_reset",
            "close_or_observe_usb_reenumeration",
            "run_separate_process_read_without_hci_reset",
            "physical_power_cycle",
            "run_read_only_recovery_check",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """Print a dry-run plan or execute an approved staged warm-reset probe."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.settle_seconds <= 0:
        parser.error("--settle-seconds must be greater than zero")
    if args.execute:
        result = asyncio.run(
            _execute(
                adapter=args.adapter,
                original_address=args.expected_original,
                requested_address=args.requested_address,
                response_timeout=args.timeout,
                settle_seconds=args.settle_seconds,
            )
        )
    else:
        result = _dry_run_payload(args)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(output)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    return 0 if not args.execute or result["status"] == "warm_reset_enqueued" else 1


if __name__ == "__main__":
    raise SystemExit(main())
