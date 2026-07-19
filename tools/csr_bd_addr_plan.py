"""Print a CSR BD_ADDR rewrite plan without opening a Bluetooth adapter."""

import argparse
import json
import sys

from swbt.transport._csr_bd_addr import CsrBdAddrStore, build_csr_bd_addr_rewrite_plan

_HARDWARE_OBSERVED_VOLATILE_ADDRESSES = frozenset(
    {
        "02:1B:DC:F9:9F:7D",
        "00:11:22:33:44:55",
    }
)


def main(argv: list[str] | None = None) -> int:
    """Print raw command bytes for source review and return without I/O."""
    parser = argparse.ArgumentParser(
        description="Build CSR BD_ADDR vendor command bytes without opening an adapter."
    )
    parser.add_argument("address", help="requested address in XX:XX:XX:XX:XX:XX notation")
    parser.add_argument(
        "--store",
        choices=tuple(CsrBdAddrStore),
        default=CsrBdAddrStore.VOLATILE,
        type=CsrBdAddrStore,
        help="volatile is the safe exploratory default; this command never sends either plan",
    )
    args = parser.parse_args(argv)
    plan = build_csr_bd_addr_rewrite_plan(args.address, store=args.store)
    verified_on_dongle = (
        plan.store is CsrBdAddrStore.VOLATILE
        and plan.address in _HARDWARE_OBSERVED_VOLATILE_ADDRESSES
    )
    output = {
        "adapter_opened": False,
        "address": plan.address,
        "store": plan.store,
        "source": "BlueZ tools/bdaddr.c CSR path",
        "verified_on_dongle": verified_on_dongle,
        "verification_scope": (
            "target_csr8510_a10_hardware_observation" if verified_on_dongle else "not_run"
        ),
        "write": {
            "opcode": f"0x{plan.write_command.opcode:04x}",
            "expected_event_code": f"0x{plan.write_command.expected_event_code:02x}",
            "parameters_hex": plan.write_command.parameters.hex(),
            "hci_packet_hex": plan.write_command.hci_packet.hex(),
        },
        "reset": {
            "opcode": f"0x{plan.reset_command.opcode:04x}",
            "expected_event_code": f"0x{plan.reset_command.expected_event_code:02x}",
            "parameters_hex": plan.reset_command.parameters.hex(),
            "hci_packet_hex": plan.reset_command.hci_packet.hex(),
        },
    }
    sys.stdout.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
