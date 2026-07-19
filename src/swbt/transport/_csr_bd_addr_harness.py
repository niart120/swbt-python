"""Bumble-backed CSR BD_ADDR helpers for the exploratory hardware tools."""

import asyncio
import platform
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import version

from bumble import hci
from bumble.host import Host
from bumble.transport import open_transport
from bumble.transport.common import Transport

from swbt.transport._csr_bd_addr import (
    CsrBdAddrRewritePlan,
    CsrVendorCommand,
    build_csr_bd_addr_read_command,
    matches_csr_vendor_response,
    parse_csr_bccmd_response,
    parse_csr_bd_addr_read_response,
)


@dataclass(frozen=True)
class CsrHostMetadata:
    """Primitive controller metadata captured while initializing a CSR host."""

    supported_commands: bytes
    hci_version: int
    hci_subversion: int
    lmp_version: int
    company_identifier: int
    lmp_subversion: int


class CsrAdapterSession:
    """One raw Bumble adapter session used by the CSR experiment commands."""

    def __init__(self, transport: Transport, host: Host) -> None:
        self._transport = transport
        self._host = host

    @classmethod
    async def open(cls, adapter: str) -> "CsrAdapterSession":
        """Open one adapter without enabling advertising or Switch-facing behavior."""
        transport = await open_transport(adapter)
        return cls(transport, Host(transport.source, transport.sink))

    async def initialize(
        self,
        *,
        response_timeout: float,
        hci_reset: bool,
        on_stage: Callable[[str], None] | None = None,
    ) -> CsrHostMetadata:
        """Optionally reset the controller and collect its standard metadata."""

        def set_stage(stage: str) -> None:
            if on_stage is not None:
                on_stage(stage)

        if hci_reset:
            set_stage("hci_reset")
            await self._host.send_sync_command(
                hci.HCI_Reset_Command(),
                response_timeout=response_timeout,
            )
        self._host.ready = True
        set_stage("read_local_supported_commands")
        supported_commands = await self._host.send_sync_command(
            hci.HCI_Read_Local_Supported_Commands_Command(),
            response_timeout=response_timeout,
        )
        set_stage("read_local_version")
        local_version = await self._host.send_sync_command(
            hci.HCI_Read_Local_Version_Information_Command(),
            response_timeout=response_timeout,
        )
        return CsrHostMetadata(
            supported_commands=supported_commands.supported_commands,
            hci_version=int(local_version.hci_version),
            hci_subversion=local_version.hci_subversion,
            lmp_version=int(local_version.lmp_version),
            company_identifier=local_version.company_identifier,
            lmp_subversion=local_version.lmp_subversion,
        )

    async def read_standard_address(self, *, response_timeout: float) -> str:
        """Read the controller address through the standard HCI command."""
        response = await self._host.send_sync_command(
            hci.HCI_Read_BD_ADDR_Command(),
            response_timeout=response_timeout,
        )
        return response.bd_addr.to_string(with_type_qualifier=False)

    async def read_csr_address(
        self,
        *,
        store: int,
        sequence_number: int,
        response_timeout: float,
    ) -> tuple[str, str]:
        """Read PSKEY_BDADDR and return its display value and raw Vendor Event."""
        command = build_csr_bd_addr_read_command(
            store=store,
            sequence_number=sequence_number,
        )
        event = await self._send_vendor_command(
            command,
            response_timeout=response_timeout,
        )
        response = parse_csr_bd_addr_read_response(event)
        return response.address, event.hex()

    async def send_write(
        self,
        plan: CsrBdAddrRewritePlan,
        *,
        response_timeout: float,
    ) -> dict[str, str | int]:
        """Send one CSR BD_ADDR write and require a successful status."""
        event = await self._send_vendor_command(
            plan.write_command,
            response_timeout=response_timeout,
        )
        response = parse_csr_bccmd_response(event)
        if not response.succeeded:
            msg = f"CSR write failed with status 0x{response.status:04x}"
            raise RuntimeError(msg)
        return {"vendor_event_hex": event.hex(), "status": response.status}

    def enqueue_warm_reset(self, command: CsrVendorCommand) -> None:
        """Enqueue a CSR warm reset without waiting for USB re-enumeration."""
        self._host.send_hci_packet(hci.HCI_Command(command.parameters, op_code=command.opcode))

    async def close(self) -> None:
        """Close the underlying Bumble transport."""
        await self._transport.close()

    async def _send_vendor_command(
        self,
        command: CsrVendorCommand,
        *,
        response_timeout: float,
    ) -> bytes:
        await self._host.command_semaphore.acquire()
        response: asyncio.Future[bytes] = asyncio.get_running_loop().create_future()

        def on_vendor_event(event: hci.HCI_Vendor_Event) -> None:
            data = bytes(event.data)
            if matches_csr_vendor_response(command, data) and not response.done():
                response.set_result(data)

        self._host.on("vendor_event", on_vendor_event)
        try:
            self._host.send_hci_packet(hci.HCI_Command(command.parameters, op_code=command.opcode))
            return await asyncio.wait_for(response, timeout=response_timeout)
        finally:
            self._host.remove_listener("vendor_event", on_vendor_event)
            if self._host.command_semaphore.locked():
                self._host.command_semaphore.release()


def command_payload(command: CsrVendorCommand) -> dict[str, object]:
    """Render one command without sending it."""
    return {
        "opcode": f"0x{command.opcode:04x}",
        "expected_event_code": f"0x{command.expected_event_code:02x}",
        "parameters_hex": command.parameters.hex(),
        "hci_packet_hex": command.hci_packet.hex(),
    }


def require_equal(*, actual: str, expected: str, source: str) -> None:
    """Reject an unexpected address before a later experiment stage."""
    if actual != expected:
        msg = f"expected {source} {expected}, got {actual}"
        raise RuntimeError(msg)


def require_csr_company_identifier(company_identifier: int) -> None:
    """Reject a controller that does not report the CSR company identifier."""
    if company_identifier != 10:
        msg = f"expected CSR company identifier 10, got {company_identifier}"
        raise RuntimeError(msg)


async def probe_csr_identity(
    adapter: str,
    *,
    response_timeout: float,
    hci_reset: bool,
) -> dict[str, object]:
    """Read standard and CSR identity values without advertising or PSKEY writes."""
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
    session: CsrAdapterSession | None = None
    try:
        session = await CsrAdapterSession.open(adapter)
        metadata = await session.initialize(
            response_timeout=response_timeout,
            hci_reset=hci_reset,
            on_stage=lambda stage: result.__setitem__("stage", stage),
        )
        result["stage"] = "read_standard_bd_addr"
        standard_address = await session.read_standard_address(response_timeout=response_timeout)
        result["stage"] = "read_csr_pskey_bdaddr"
        csr_address, vendor_event_hex = await session.read_csr_address(
            store=0x0000,
            sequence_number=0x4711,
            response_timeout=response_timeout,
        )
        csr_command = build_csr_bd_addr_read_command(store=0x0000)
        result.update(
            {
                "status": "passed",
                "stage": "complete",
                "standard_hci": {
                    "address": standard_address,
                    "supported_commands_hex": metadata.supported_commands.hex(),
                    "hci_version": metadata.hci_version,
                    "hci_subversion": metadata.hci_subversion,
                    "lmp_version": metadata.lmp_version,
                    "company_identifier": metadata.company_identifier,
                    "lmp_subversion": metadata.lmp_subversion,
                },
                "csr": {
                    "opcode": f"0x{csr_command.opcode:04x}",
                    "request_parameters_hex": csr_command.parameters.hex(),
                    "vendor_event_hex": vendor_event_hex,
                    "address": csr_address,
                    "raw_value_hex": parse_csr_bd_addr_read_response(
                        bytes.fromhex(vendor_event_hex)
                    ).raw_value.hex(),
                    "status": 0,
                    "matches_standard_hci": csr_address == standard_address,
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
        if session is None:
            result["cleanup"] = "adapter_not_opened"
        else:
            try:
                await session.close()
                result["cleanup"] = "adapter_closed"
            except Exception as error:  # noqa: BLE001
                result["cleanup"] = {
                    "status": "failed",
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
    return result
