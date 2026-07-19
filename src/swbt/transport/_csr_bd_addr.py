"""Pure CSR BD_ADDR command planning for the exploratory hardware path."""

import re
from dataclasses import dataclass
from enum import StrEnum

CSR_VENDOR_OPCODE = 0xFC00
CSR_VENDOR_EVENT_CODE = 0xFF
_CSR_BCCMD_CHANNEL = 0xC2
_CSR_BD_ADDR_VALUE_LENGTH = 8
_CSR_PSKEY_BDADDR = 0x0001
_CSR_VARID_PS = 0x7003
_BD_ADDR_PATTERN = re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}")


class CsrBdAddrStore(StrEnum):
    """CSR persistent-store target used by the BlueZ command layout."""

    VOLATILE = "volatile"
    PERSISTENT = "persistent"


@dataclass(frozen=True)
class CsrVendorCommand:
    """One raw CSR vendor command without any adapter I/O."""

    opcode: int
    parameters: bytes
    expected_event_code: int = CSR_VENDOR_EVENT_CODE

    @property
    def hci_packet(self) -> bytes:
        """Return the complete HCI command packet, including packet type."""
        return (
            b"\x01"
            + self.opcode.to_bytes(2, "little")
            + bytes((len(self.parameters),))
            + self.parameters
        )


@dataclass(frozen=True)
class CsrBdAddrRewritePlan:
    """Dry-run CSR commands corresponding to one requested address."""

    address: str
    store: CsrBdAddrStore
    write_command: CsrVendorCommand
    reset_command: CsrVendorCommand


@dataclass(frozen=True)
class CsrBdAddrVolatileExperimentPlan:
    """Apply and mandatory restoration plans for one volatile experiment."""

    original_address: str
    requested_address: str
    apply: CsrBdAddrRewritePlan
    restore: CsrBdAddrRewritePlan


@dataclass(frozen=True)
class CsrBccmdResponse:
    """Status extracted from a CSR BCCMD vendor event."""

    status: int

    @property
    def succeeded(self) -> bool:
        """Return whether the CSR status word reports success."""
        return self.status == 0


@dataclass(frozen=True)
class CsrBdAddrReadResponse:
    """BD_ADDR value returned by a CSR PSKEY GETREQ."""

    address: str
    raw_value: bytes
    status: int


def build_csr_bd_addr_read_command(
    *,
    store: int,
    sequence_number: int = 0x4711,
) -> CsrVendorCommand:
    """Build a BlueZ-compatible read-only GETREQ for ``PSKEY_BDADDR``."""
    store_bytes = _uint16_bytes(store, name="store")
    sequence_bytes = _uint16_bytes(sequence_number, name="sequence_number")
    value_words = _CSR_BD_ADDR_VALUE_LENGTH // 2
    payload_words = value_words + 8

    payload = bytearray(24)
    payload[0:2] = b"\x00\x00"  # GETREQ
    payload[2:4] = payload_words.to_bytes(2, "little")
    payload[4:6] = sequence_bytes
    payload[6:8] = _CSR_VARID_PS.to_bytes(2, "little")
    payload[10:12] = _CSR_PSKEY_BDADDR.to_bytes(2, "little")
    payload[12:14] = value_words.to_bytes(2, "little")
    payload[14:16] = store_bytes
    return _vendor_command(payload)


def build_csr_bd_addr_volatile_experiment_plan(
    *,
    original_address: str,
    requested_address: str,
) -> CsrBdAddrVolatileExperimentPlan:
    """Build an apply/restore pair that cannot select persistent storage."""
    apply = build_csr_bd_addr_rewrite_plan(
        requested_address,
        store=CsrBdAddrStore.VOLATILE,
        sequence_number=0x4711,
    )
    restore = build_csr_bd_addr_rewrite_plan(
        original_address,
        store=CsrBdAddrStore.VOLATILE,
        sequence_number=0x4713,
    )
    if apply.address == restore.address:
        msg = "requested_address must differ from original_address"
        raise ValueError(msg)
    return CsrBdAddrVolatileExperimentPlan(
        original_address=restore.address,
        requested_address=apply.address,
        apply=apply,
        restore=restore,
    )


def build_csr_bd_addr_rewrite_plan(
    address: str,
    *,
    store: CsrBdAddrStore,
    sequence_number: int = 0x4711,
) -> CsrBdAddrRewritePlan:
    """Build the BlueZ-compatible CSR write and reset command bytes.

    This function performs no USB or HCI I/O. The byte layout is a direct port
    of BlueZ ``tools/bdaddr.c`` and remains experimental until characterized on
    the dedicated CSR8510 A10 dongle.
    """
    display_bytes = _parse_display_address(address)
    bluez_bdaddr = display_bytes[::-1]
    sequence_bytes = _uint16_bytes(sequence_number, name="sequence_number")

    write_payload = bytearray(bytes.fromhex("02000c001147037000000100040000000000000000000000"))
    write_payload[4:6] = sequence_bytes
    if store is CsrBdAddrStore.VOLATILE:
        write_payload[14] = 0x08
    write_payload[16] = bluez_bdaddr[2]
    write_payload[17] = 0x00
    write_payload[18] = bluez_bdaddr[0]
    write_payload[19] = bluez_bdaddr[1]
    write_payload[20] = bluez_bdaddr[3]
    write_payload[21] = 0x00
    write_payload[22] = bluez_bdaddr[4]
    write_payload[23] = bluez_bdaddr[5]

    reset_payload = bytearray(bytes.fromhex("020009000000014000000000000000000000"))
    if store is CsrBdAddrStore.VOLATILE:
        reset_payload[6] = 0x02

    return CsrBdAddrRewritePlan(
        address=address.upper(),
        store=store,
        write_command=_vendor_command(write_payload),
        reset_command=_vendor_command(reset_payload),
    )


def parse_csr_bccmd_response(event_parameters: bytes) -> CsrBccmdResponse:
    """Parse the status word checked by BlueZ from a CSR vendor event."""
    if len(event_parameters) < 11:
        msg = "CSR BCCMD vendor event must contain at least 11 bytes"
        raise ValueError(msg)
    if event_parameters[0] != _CSR_BCCMD_CHANNEL:
        msg = "vendor event is not a CSR BCCMD response"
        raise ValueError(msg)
    return CsrBccmdResponse(status=int.from_bytes(event_parameters[9:11], "little"))


def matches_csr_vendor_response(
    command: CsrVendorCommand,
    event_parameters: bytes,
) -> bool:
    """Match a CSR response by channel, command type, sequence, and VARID."""
    if len(command.parameters) < 9 or len(event_parameters) < 9:
        return False
    request_type = int.from_bytes(command.parameters[1:3], "little")
    if request_type not in {0x0000, 0x0002}:
        return False
    return (
        event_parameters[0] == _CSR_BCCMD_CHANNEL
        and int.from_bytes(event_parameters[1:3], "little") == 0x0001
        and event_parameters[5:7] == command.parameters[5:7]
        and event_parameters[7:9] == command.parameters[7:9]
    )


def parse_csr_bd_addr_read_response(event_parameters: bytes) -> CsrBdAddrReadResponse:
    """Decode the PSKEY value returned by a CSR BD_ADDR GETREQ."""
    minimum_length = 17 + _CSR_BD_ADDR_VALUE_LENGTH
    if len(event_parameters) < minimum_length:
        msg = f"CSR BD_ADDR response must contain at least {minimum_length} bytes"
        raise ValueError(msg)
    response = parse_csr_bccmd_response(event_parameters)
    if not response.succeeded:
        msg = f"CSR BCCMD response failed with status 0x{response.status:04x}"
        raise ValueError(msg)

    raw_value = event_parameters[17:minimum_length]
    display_bytes = bytes(
        (
            raw_value[7],
            raw_value[6],
            raw_value[4],
            raw_value[0],
            raw_value[3],
            raw_value[2],
        )
    )
    return CsrBdAddrReadResponse(
        address=":".join(f"{octet:02X}" for octet in display_bytes),
        raw_value=raw_value,
        status=response.status,
    )


def _parse_display_address(address: str) -> bytes:
    if _BD_ADDR_PATTERN.fullmatch(address) is None:
        msg = "BD_ADDR must use XX:XX:XX:XX:XX:XX notation"
        raise ValueError(msg)
    return bytes(int(part, 16) for part in address.split(":"))


def _vendor_command(payload: bytes | bytearray) -> CsrVendorCommand:
    return CsrVendorCommand(
        opcode=CSR_VENDOR_OPCODE,
        parameters=bytes((_CSR_BCCMD_CHANNEL,)) + bytes(payload),
    )


def _uint16_bytes(value: int, *, name: str) -> bytes:
    if not 0 <= value <= 0xFFFF:
        msg = f"{name} must fit in an unsigned 16-bit word"
        raise ValueError(msg)
    return value.to_bytes(2, "little")
