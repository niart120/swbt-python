import pytest

from swbt.transport._csr_bd_addr import (
    CSR_VENDOR_OPCODE,
    CsrBdAddrStore,
    build_csr_bd_addr_read_command,
    build_csr_bd_addr_rewrite_plan,
    parse_csr_bccmd_response,
    parse_csr_bd_addr_read_response,
)


def test_csr_bd_addr_plan_matches_bluez_persistent_command_layout() -> None:
    plan = build_csr_bd_addr_rewrite_plan(
        "01:23:45:67:89:AB",
        store=CsrBdAddrStore.PERSISTENT,
    )

    assert plan.address == "01:23:45:67:89:AB"
    assert plan.write_command.opcode == CSR_VENDOR_OPCODE
    assert plan.write_command.parameters.hex() == (
        "c202000c001147037000000100040000006700ab8945002301"
    )
    assert plan.write_command.hci_packet.hex() == (
        "0100fc19c202000c001147037000000100040000006700ab8945002301"
    )
    assert plan.reset_command.parameters.hex() == ("c2020009000000014000000000000000000000")


def test_csr_bd_addr_plan_marks_volatile_store_and_reset() -> None:
    plan = build_csr_bd_addr_rewrite_plan(
        "01:23:45:67:89:AB",
        store=CsrBdAddrStore.VOLATILE,
    )

    assert plan.write_command.parameters[15] == 0x08
    assert plan.reset_command.parameters[7] == 0x02


def test_csr_bd_addr_read_command_matches_bluez_getreq_layout() -> None:
    command = build_csr_bd_addr_read_command(store=0x0000, sequence_number=0x4711)

    assert command.opcode == CSR_VENDOR_OPCODE
    assert command.parameters.hex() == ("c200000c001147037000000100040000000000000000000000")
    assert command.hci_packet.hex() == "0100fc19" + command.parameters.hex()


def test_csr_bd_addr_read_response_decodes_pskey_value() -> None:
    response = parse_csr_bd_addr_read_response(
        bytes.fromhex("c201000c001147037000000100040000006700ab8945002301")
    )

    assert response.address == "01:23:45:67:89:AB"
    assert response.raw_value.hex() == "6700ab8945002301"
    assert response.status == 0


def test_csr_bd_addr_read_response_rejects_failed_or_short_getresp() -> None:
    with pytest.raises(ValueError, match="status 0x1234"):
        parse_csr_bd_addr_read_response(
            bytes.fromhex("c201000c00114703703412000100040000006700ab8945002301")
        )
    with pytest.raises(ValueError, match="at least 25 bytes"):
        parse_csr_bd_addr_read_response(bytes.fromhex("c201000c00114703700000"))


@pytest.mark.parametrize(
    "address",
    [
        "",
        "01:23:45:67:89",
        "01:23:45:67:89:GG",
        "01-23-45-67-89-AB",
    ],
)
def test_csr_bd_addr_plan_rejects_invalid_display_address(address: str) -> None:
    with pytest.raises(ValueError, match="XX:XX:XX:XX:XX:XX"):
        build_csr_bd_addr_rewrite_plan(address, store=CsrBdAddrStore.VOLATILE)


def test_csr_bccmd_response_exposes_vendor_status() -> None:
    success = parse_csr_bccmd_response(bytes.fromhex("c200000000000000000000"))
    failure = parse_csr_bccmd_response(bytes.fromhex("c200000000000000003412"))

    assert success.status == 0
    assert success.succeeded is True
    assert failure.status == 0x1234
    assert failure.succeeded is False


def test_csr_bccmd_response_rejects_non_csr_or_short_vendor_event() -> None:
    with pytest.raises(ValueError, match="CSR BCCMD"):
        parse_csr_bccmd_response(bytes.fromhex("c1" + "00" * 10))
    with pytest.raises(ValueError, match="at least 11 bytes"):
        parse_csr_bccmd_response(bytes.fromhex("c2"))
