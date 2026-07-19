import json
import subprocess
import sys
from pathlib import Path

import pytest

from swbt.transport._csr_bd_addr import (
    CSR_VENDOR_OPCODE,
    CsrBdAddrStore,
    build_csr_bd_addr_read_command,
    build_csr_bd_addr_rewrite_plan,
    build_csr_bd_addr_volatile_experiment_plan,
    matches_csr_vendor_response,
    parse_csr_bccmd_response,
    parse_csr_bd_addr_read_response,
)

PLAN_TOOL = Path(__file__).resolve().parents[2] / "tools" / "csr_bd_addr_plan.py"


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


@pytest.mark.parametrize(
    ("address", "store", "verified_on_dongle"),
    [
        ("00:11:22:33:44:55", "volatile", True),
        ("02:1B:DC:F9:9F:7D", "volatile", True),
        ("01:23:45:67:89:AB", "volatile", False),
        ("00:11:22:33:44:55", "persistent", False),
    ],
)
def test_csr_bd_addr_plan_reports_target_dongle_verification(
    address: str,
    store: str,
    verified_on_dongle: bool,
) -> None:
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(PLAN_TOOL),
            address,
            "--store",
            store,
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["verified_on_dongle"] is verified_on_dongle
    assert payload["verification_scope"] == (
        "target_csr8510_a10_hardware_observation" if verified_on_dongle else "not_run"
    )


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


def test_volatile_experiment_plan_applies_and_restores_only_psram() -> None:
    plan = build_csr_bd_addr_volatile_experiment_plan(
        original_address="00:1B:DC:F9:9F:7D",
        requested_address="02:1B:DC:F9:9F:7D",
    )

    assert plan.original_address == "00:1B:DC:F9:9F:7D"
    assert plan.requested_address == "02:1B:DC:F9:9F:7D"
    assert plan.apply.store is CsrBdAddrStore.VOLATILE
    assert plan.restore.store is CsrBdAddrStore.VOLATILE
    assert plan.apply.address == plan.requested_address
    assert plan.restore.address == plan.original_address
    assert plan.apply.write_command.parameters[15] == 0x08
    assert plan.restore.write_command.parameters[15] == 0x08
    assert plan.apply.write_command.parameters[5:7] == bytes.fromhex("1147")
    assert plan.restore.write_command.parameters[5:7] == bytes.fromhex("1347")
    assert plan.apply.reset_command.parameters[7] == 0x02
    assert plan.restore.reset_command.parameters[7] == 0x02


def test_volatile_experiment_plan_rejects_noop_address() -> None:
    with pytest.raises(ValueError, match="must differ"):
        build_csr_bd_addr_volatile_experiment_plan(
            original_address="00:1B:DC:F9:9F:7D",
            requested_address="00:1b:dc:f9:9f:7d",
        )


def test_csr_response_match_accepts_getresp_for_getreq_and_setreq() -> None:
    get_command = build_csr_bd_addr_read_command(store=0x0008, sequence_number=0x4712)
    set_command = build_csr_bd_addr_rewrite_plan(
        "02:1B:DC:F9:9F:7D",
        store=CsrBdAddrStore.VOLATILE,
        sequence_number=0x4711,
    ).write_command
    get_response = bytes.fromhex("c201000c00124703700000010004000800f9007d9fdc001b02")
    set_response = bytes.fromhex("c201000c00114703700000010004000800f9007d9fdc001b02")

    assert matches_csr_vendor_response(get_command, get_response) is True
    assert matches_csr_vendor_response(set_command, set_response) is True


def test_csr_response_match_rejects_delayed_response_from_another_stage() -> None:
    get_command = build_csr_bd_addr_read_command(store=0x0008, sequence_number=0x4712)
    delayed_set_response = bytes.fromhex("c201000c00114703700000010004000800f9007d9fdc001b02")

    assert matches_csr_vendor_response(get_command, delayed_set_response) is False


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
