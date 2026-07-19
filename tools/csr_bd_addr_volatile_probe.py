"""Round-trip one CSR PSRAM BD_ADDR value without warm reset or RF activity."""

import argparse
import asyncio
import json
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from bumble import hci
from bumble.host import Host
from bumble.transport import open_transport
from bumble.transport.common import Transport

from swbt.transport._csr_bd_addr import (
    CsrBdAddrRewritePlan,
    CsrBdAddrStore,
    CsrVendorCommand,
    build_csr_bd_addr_read_command,
    build_csr_bd_addr_rewrite_plan,
    build_csr_bd_addr_volatile_experiment_plan,
    matches_csr_vendor_response,
    parse_csr_bccmd_response,
    parse_csr_bd_addr_read_response,
)

_CSR_PSRAM_STORE = 0x0008


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Plan or execute a CSR PSRAM-only SETREQ/GETREQ/restore roundtrip. "
            "No warm reset, advertising, pairing, or persistent write is performed."
        )
    )
    parser.add_argument("--adapter", default="usb:0")
    parser.add_argument("--expected-original", required=True)
    parser.add_argument("--requested-address", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=float, default=2.0)
    return parser


def _command_payload(command: CsrVendorCommand) -> dict[str, object]:
    return {
        "opcode": f"0x{command.opcode:04x}",
        "expected_event_code": f"0x{command.expected_event_code:02x}",
        "parameters_hex": command.parameters.hex(),
        "hci_packet_hex": command.hci_packet.hex(),
    }


def _write_payload(plan: CsrBdAddrRewritePlan) -> dict[str, object]:
    return {
        "address": plan.address,
        "store": plan.store,
        "write": _command_payload(plan.write_command),
    }


async def _send_csr_vendor_command(
    host: Host,
    command: CsrVendorCommand,
    *,
    response_timeout: float,
) -> bytes:
    await host.command_semaphore.acquire()
    response: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

    def on_vendor_event(event: hci.HCI_Vendor_Event) -> None:
        data = bytes(event.data)
        if matches_csr_vendor_response(command, data) and not response.done():
            response.set_result(data)

    host.on("vendor_event", on_vendor_event)
    try:
        host.send_hci_packet(hci.HCI_Command(command.parameters, op_code=command.opcode))
        return await asyncio.wait_for(response, timeout=response_timeout)
    finally:
        host.remove_listener("vendor_event", on_vendor_event)
        if host.command_semaphore.locked():
            host.command_semaphore.release()


async def _initialize_host(
    transport: Transport,
    *,
    response_timeout: float,
) -> tuple[Host, int]:
    host = Host(transport.source, transport.sink)
    await host.send_sync_command(
        hci.HCI_Reset_Command(),
        response_timeout=response_timeout,
    )
    host.ready = True
    await host.send_sync_command(
        hci.HCI_Read_Local_Supported_Commands_Command(),
        response_timeout=response_timeout,
    )
    local_version = await host.send_sync_command(
        hci.HCI_Read_Local_Version_Information_Command(),
        response_timeout=response_timeout,
    )
    return host, local_version.company_identifier


async def _read_standard_address(host: Host, *, response_timeout: float) -> str:
    response = await host.send_sync_command(
        hci.HCI_Read_BD_ADDR_Command(),
        response_timeout=response_timeout,
    )
    return response.bd_addr.to_string(with_type_qualifier=False)


async def _read_csr_address(
    host: Host,
    *,
    store: int,
    sequence_number: int,
    response_timeout: float,
) -> tuple[str, str]:
    command = build_csr_bd_addr_read_command(
        store=store,
        sequence_number=sequence_number,
    )
    event = await _send_csr_vendor_command(
        host,
        command,
        response_timeout=response_timeout,
    )
    response = parse_csr_bd_addr_read_response(event)
    return response.address, event.hex()


async def _send_write(
    host: Host,
    plan: CsrBdAddrRewritePlan,
    *,
    response_timeout: float,
) -> dict[str, str | int]:
    event = await _send_csr_vendor_command(
        host,
        plan.write_command,
        response_timeout=response_timeout,
    )
    response = parse_csr_bccmd_response(event)
    if not response.succeeded:
        msg = f"CSR write failed with status 0x{response.status:04x}"
        raise RuntimeError(msg)
    return {"vendor_event_hex": event.hex(), "status": response.status}


def _require_equal(*, actual: str, expected: str, source: str) -> None:
    if actual != expected:
        msg = f"expected {source} {expected}, got {actual}"
        raise RuntimeError(msg)


def _require_csr_company_identifier(company_identifier: int) -> None:
    if company_identifier != 10:
        msg = f"expected CSR company identifier 10, got {company_identifier}"
        raise RuntimeError(msg)


async def _execute(
    *,
    adapter: str,
    original_address: str,
    requested_address: str,
    response_timeout: float,
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
        "warm_reset": False,
        "advertising": False,
        "switch_facing": False,
        "status": "started",
        "stage": "open_adapter",
        "cleanup": "not_started",
        "restoration": "not_required",
    }
    transport: Transport | None = None
    host: Host | None = None
    restore_required = False
    try:
        transport = await open_transport(adapter)
        host, company_identifier = await _initialize_host(
            transport,
            response_timeout=response_timeout,
        )
        _require_csr_company_identifier(company_identifier)

        result["stage"] = "verify_baseline"
        standard_before = await _read_standard_address(
            host,
            response_timeout=response_timeout,
        )
        csr_before, baseline_event = await _read_csr_address(
            host,
            store=0x0000,
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
            "company_identifier": company_identifier,
        }

        result["stage"] = "apply_psram_write"
        restore_required = True
        result["restoration"] = "required"
        result["apply_write"] = await _send_write(
            host,
            experiment.apply,
            response_timeout=response_timeout,
        )

        result["stage"] = "verify_psram_requested"
        psram_changed, changed_event = await _read_csr_address(
            host,
            store=_CSR_PSRAM_STORE,
            sequence_number=0x4712,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=psram_changed,
            expected=experiment.requested_address,
            source="CSR PSRAM address",
        )
        standard_during = await _read_standard_address(
            host,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=standard_during,
            expected=experiment.original_address,
            source="active standard HCI address before warm reset",
        )
        result["changed"] = {
            "psram_address": psram_changed,
            "standard_address": standard_during,
            "csr_vendor_event_hex": changed_event,
        }

        result["stage"] = "restore_psram_write"
        result["restore_write"] = await _send_write(
            host,
            experiment.restore,
            response_timeout=response_timeout,
        )

        result["stage"] = "verify_psram_restored"
        psram_restored, restored_event = await _read_csr_address(
            host,
            store=_CSR_PSRAM_STORE,
            sequence_number=0x4714,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=psram_restored,
            expected=experiment.original_address,
            source="restored CSR PSRAM address",
        )
        standard_after = await _read_standard_address(
            host,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=standard_after,
            expected=experiment.original_address,
            source="active standard HCI address after restore",
        )
        result["restored"] = {
            "psram_address": psram_restored,
            "standard_address": standard_after,
            "csr_vendor_event_hex": restored_event,
        }
        restore_required = False
        result["status"] = "passed"
        result["stage"] = "complete"
        result["restoration"] = "original_psram_value_restored"
    except Exception as error:  # noqa: BLE001
        result.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
    finally:
        if restore_required and host is not None:
            result["restoration"] = await _best_effort_restore(
                host,
                original_address=experiment.original_address,
                response_timeout=response_timeout,
            )
        if transport is None:
            result["cleanup"] = "adapter_not_opened"
        else:
            try:
                await transport.close()
                result["cleanup"] = "adapter_closed"
            except Exception as error:  # noqa: BLE001
                result["cleanup"] = {
                    "status": "adapter_close_failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
                result["status"] = "failed"
    return result


async def _best_effort_restore(
    host: Host,
    *,
    original_address: str,
    response_timeout: float,
) -> dict[str, object]:
    plan = build_csr_bd_addr_rewrite_plan(
        original_address,
        store=CsrBdAddrStore.VOLATILE,
        sequence_number=0x4715,
    )
    try:
        write = await _send_write(
            host,
            plan,
            response_timeout=response_timeout,
        )
        address, event = await _read_csr_address(
            host,
            store=_CSR_PSRAM_STORE,
            sequence_number=0x4716,
            response_timeout=response_timeout,
        )
        _require_equal(
            actual=address,
            expected=original_address,
            source="best-effort restored CSR PSRAM address",
        )
    except Exception as error:  # noqa: BLE001
        return {
            "status": "restore_failed_power_cycle_required",
            "error_type": type(error).__name__,
            "error": str(error),
        }
    return {
        "status": "original_psram_value_restored",
        "write": write,
        "csr_address": address,
        "csr_vendor_event_hex": event,
    }


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
        "warm_reset": False,
        "apply": _write_payload(experiment.apply),
        "restore": _write_payload(experiment.restore),
        "sequence": [
            "verify_original",
            "apply_psram_write",
            "read_psram_requested",
            "verify_active_address_unchanged",
            "restore_original_psram",
            "read_psram_restored",
            "close_adapter",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """Print a dry-run plan or run an approved PSRAM-only roundtrip."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be greater than zero")
    if args.execute:
        result = asyncio.run(
            _execute(
                adapter=args.adapter,
                original_address=args.expected_original,
                requested_address=args.requested_address,
                response_timeout=args.timeout,
            )
        )
    else:
        result = _dry_run_payload(args)
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(output)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
    return 0 if not args.execute or result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
