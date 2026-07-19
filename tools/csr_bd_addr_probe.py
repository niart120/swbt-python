"""Read a CSR adapter identity without advertising or writing PSKEY values."""

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

from swbt.transport._csr_bd_addr import (
    CsrVendorCommand,
    build_csr_bd_addr_read_command,
    parse_csr_bd_addr_read_response,
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


async def _send_csr_vendor_command(
    host: Host,
    command: CsrVendorCommand,
    *,
    response_timeout: float,
) -> bytes:
    """Send one command while correlating its CSR Vendor Event by sequence number."""
    await host.command_semaphore.acquire()
    response: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()
    expected_sequence = command.parameters[5:7]

    def on_vendor_event(event: hci.HCI_Vendor_Event) -> None:
        data = bytes(event.data)
        if (
            len(data) >= 7
            and data[0] == 0xC2
            and data[5:7] == expected_sequence
            and not response.done()
        ):
            response.set_result(data)

    host.on("vendor_event", on_vendor_event)
    try:
        host.send_hci_packet(hci.HCI_Command(command.parameters, op_code=command.opcode))
        return await asyncio.wait_for(response, timeout=response_timeout)
    finally:
        host.remove_listener("vendor_event", on_vendor_event)
        if host.command_semaphore.locked():
            host.command_semaphore.release()


async def _probe(
    adapter: str,
    *,
    response_timeout: float,
    hci_reset: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "adapter": adapter,
        "os": platform.platform(),
        "python": platform.python_version(),
        "bumble": version("bumble"),
        "scope": {
            "adapter_open": True,
            "standard_hci_identity_reads": True,
            "csr_pskey_getreq": True,
            "hci_reset": hci_reset,
            "pskey_write": False,
            "advertising": False,
            "switch_facing": False,
        },
        "status": "started",
        "stage": "opening_adapter",
        "cleanup": "not_started",
    }
    transport = None
    try:
        transport = await open_transport(adapter)
        host = Host(transport.source, transport.sink)
        if hci_reset:
            result["stage"] = "hci_reset"
            await host.send_sync_command(
                hci.HCI_Reset_Command(),
                response_timeout=response_timeout,
            )
        host.ready = True
        result["stage"] = "read_local_supported_commands"
        supported_commands = await host.send_sync_command(
            hci.HCI_Read_Local_Supported_Commands_Command(),
            response_timeout=response_timeout,
        )
        result["stage"] = "read_local_version"
        local_version = await host.send_sync_command(
            hci.HCI_Read_Local_Version_Information_Command(),
            response_timeout=response_timeout,
        )
        result["stage"] = "read_standard_bd_addr"
        local_address = await host.send_sync_command(
            hci.HCI_Read_BD_ADDR_Command(),
            response_timeout=response_timeout,
        )
        csr_command = build_csr_bd_addr_read_command(store=0x0000)
        result["stage"] = "read_csr_pskey_bdaddr"
        vendor_event = await _send_csr_vendor_command(
            host,
            csr_command,
            response_timeout=response_timeout,
        )
        csr_address = parse_csr_bd_addr_read_response(vendor_event)
        standard_address = local_address.bd_addr.to_string(with_type_qualifier=False)
        result.update(
            {
                "status": "passed",
                "stage": "complete",
                "standard_hci": {
                    "address": standard_address,
                    "supported_commands_hex": supported_commands.supported_commands.hex(),
                    "hci_version": int(local_version.hci_version),
                    "hci_subversion": local_version.hci_subversion,
                    "lmp_version": int(local_version.lmp_version),
                    "company_identifier": local_version.company_identifier,
                    "lmp_subversion": local_version.lmp_subversion,
                },
                "csr": {
                    "opcode": f"0x{csr_command.opcode:04x}",
                    "request_parameters_hex": csr_command.parameters.hex(),
                    "vendor_event_hex": vendor_event.hex(),
                    "address": csr_address.address,
                    "raw_value_hex": csr_address.raw_value.hex(),
                    "status": csr_address.status,
                    "matches_standard_hci": csr_address.address == standard_address,
                },
            }
        )
    except Exception as error:  # noqa: BLE001
        result.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
            }
        )
    finally:
        if transport is None:
            result["cleanup"] = "adapter_not_opened"
        else:
            try:
                await transport.close()
                result["cleanup"] = "adapter_closed"
            except Exception as error:  # noqa: BLE001
                result["cleanup"] = {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
    return result


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
