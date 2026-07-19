"""Pair with a Switch only when a CSR adapter exposes the expected BD_ADDR."""

import argparse
import asyncio
import json
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from csr_bd_addr_probe import _probe

from swbt import DiagnosticsConfig, ProController
from swbt.diagnostics import DiagnosticsRecorder
from swbt.gamepad._config import _SwitchGamepadConfig
from swbt.transport.bumble import BumbleHidTransport


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Dry-run or execute one explicitly approved Switch pairing probe. "
            "Execution performs a read-only CSR identity preflight, checks the "
            "address again after Bumble power_on and before visibility, then starts "
            "HID advertising. Cleanup closes the controller and adapter."
        )
    )
    parser.add_argument("--adapter", default="usb:0")
    parser.add_argument("--expected-address", required=True)
    parser.add_argument("--key-store", required=True, type=Path)
    parser.add_argument("--reuse-key-store", action="store_true")
    parser.add_argument("--trace", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--preflight-timeout", type=float, default=2.0)
    parser.add_argument("--pair-timeout", type=float, default=60.0)
    parser.add_argument("--observation-seconds", type=float, default=5.0)
    parser.add_argument("--post-close-address-read", action="store_true")
    return parser


def _parse_address(address: str) -> bytes:
    parts = address.split(":")
    if len(parts) != 6 or any(len(part) != 2 for part in parts):
        msg = "BD_ADDR must use XX:XX:XX:XX:XX:XX notation"
        raise ValueError(msg)
    try:
        parsed = bytes.fromhex("".join(parts))
    except ValueError as error:
        msg = "BD_ADDR must use XX:XX:XX:XX:XX:XX notation"
        raise ValueError(msg) from error
    return parsed


def _display_address(address: bytes) -> str:
    return address.hex(":").upper()


def _dry_run_payload(args: argparse.Namespace, expected_address: bytes) -> dict[str, object]:
    key_store_mode = "reuse" if args.reuse_key_store else "fresh"
    sequence = [
        ("require_existing_key_store" if args.reuse_key_store else "reject_existing_key_store"),
        "read_standard_and_csr_address_without_hci_reset",
        "require_both_addresses_to_match_expected",
        "bumble_power_on",
        "require_powered_on_address_to_match_expected_before_visibility",
        "enable_connectable_and_discoverable",
        "wait_for_switch_pairing",
        "hold_connected_for_observation",
        "close_controller_and_adapter",
    ]
    if args.post_close_address_read:
        sequence.append("read_standard_and_csr_address_after_close_without_hci_reset")
    sequence.extend(
        [
            "physical_power_cycle",
            "run_read_only_recovery_check",
        ]
    )
    return {
        "adapter_opened": False,
        "execute": False,
        "adapter": args.adapter,
        "expected_address": _display_address(expected_address),
        "key_store": str(args.key_store),
        "key_store_mode": key_store_mode,
        "key_store_must_be_fresh": not args.reuse_key_store,
        "trace": str(args.trace),
        "output": str(args.output),
        "persistent_write": False,
        "advertising": False,
        "switch_facing": False,
        "periodic_input": "neutral_only_after_connection",
        "observation_seconds": args.observation_seconds,
        "post_close_address_read": args.post_close_address_read,
        "sequence": sequence,
    }


def _identity_read_completed(identity_read: dict[str, object]) -> bool:
    standard = identity_read.get("standard_hci")
    csr = identity_read.get("csr")
    if not isinstance(standard, dict) or not isinstance(csr, dict):
        return False
    return (
        identity_read.get("status") == "passed"
        and isinstance(standard.get("address"), str)
        and isinstance(csr.get("address"), str)
        and csr.get("matches_standard_hci") is True
        and identity_read.get("cleanup") == "adapter_closed"
    )


def _preflight_matches_expected(preflight: dict[str, object], expected: str) -> bool:
    standard = preflight.get("standard_hci")
    csr = preflight.get("csr")
    if not isinstance(standard, dict) or not isinstance(csr, dict):
        return False
    return (
        _identity_read_completed(preflight)
        and standard.get("address") == expected
        and csr.get("address") == expected
    )


async def _execute(
    *,
    adapter: str,
    expected_address: bytes,
    key_store_path: Path,
    trace_path: Path,
    preflight_timeout: float,
    pair_timeout: float,
    observation_seconds: float,
    reuse_key_store: bool,
    post_close_address_read: bool,
) -> dict[str, object]:
    expected_text = _display_address(expected_address)
    result: dict[str, object] = {
        "timestamp": datetime.now(UTC).isoformat(),
        "adapter": adapter,
        "os": platform.platform(),
        "python": platform.python_version(),
        "bumble": version("bumble"),
        "expected_address": expected_text,
        "key_store": str(key_store_path),
        "key_store_mode": "reuse" if reuse_key_store else "fresh",
        "trace": str(trace_path),
        "persistent_write": False,
        "advertising": False,
        "switch_facing": False,
        "periodic_input": "neutral_only_after_connection",
        "observation_seconds": observation_seconds,
        "post_close_address_read": post_close_address_read,
        "status": "started",
        "stage": "reject_existing_key_store",
        "cleanup": "adapter_not_opened",
    }
    result["stage"] = "read_only_identity_preflight"
    preflight = await _probe(
        adapter,
        response_timeout=preflight_timeout,
        hci_reset=False,
    )
    result["preflight"] = preflight
    if not _preflight_matches_expected(preflight, expected_text):
        result.update(
            {
                "status": "failed",
                "stage": "identity_preflight_rejected",
                "error_type": "RuntimeError",
                "error": f"active CSR identity did not match {expected_text}",
                "cleanup": preflight.get("cleanup", "unknown"),
            }
        )
        return result

    result["stage"] = "open_guarded_controller"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    key_store_path.parent.mkdir(parents=True, exist_ok=True)
    transport_diagnostics: DiagnosticsRecorder | None = None
    try:
        with trace_path.open("w", encoding="utf-8") as trace_writer:
            transport_diagnostics = DiagnosticsRecorder(trace_writer=trace_writer)
            transport = BumbleHidTransport(
                adapter=adapter,
                key_store_path=str(key_store_path),
                diagnostics=transport_diagnostics,
                expected_local_bluetooth_address=expected_address,
            )
            config = _SwitchGamepadConfig(
                adapter=adapter,
                key_store_path=str(key_store_path),
            )
            pad = ProController._from_config(
                config,
                diagnostics=DiagnosticsConfig(trace_writer=trace_writer),
                transport=transport,
            )
            async with pad:
                result.update(
                    {
                        "stage": "pairing",
                        "cleanup": "controller_context_active",
                    }
                )
                await pad.pair(timeout=pair_timeout)
                result["stage"] = "observation"
                await asyncio.sleep(observation_seconds)
        result.update(
            {
                "status": "paired",
                "stage": "complete",
                "cleanup": "controller_and_adapter_closed",
                "key_store_created": await asyncio.to_thread(key_store_path.exists),
            }
        )
        if post_close_address_read:
            result["stage"] = "post_close_identity_read"
            post_close_read = await _probe(
                adapter,
                response_timeout=preflight_timeout,
                hci_reset=False,
            )
            result["post_close_read"] = post_close_read
            if not _identity_read_completed(post_close_read):
                result.update(
                    {
                        "status": "failed",
                        "stage": "post_close_identity_read_failed",
                        "error_type": "RuntimeError",
                        "error": "post-close CSR identity read did not complete",
                        "cleanup": (
                            "controller_closed_post_close_cleanup_"
                            f"{post_close_read.get('cleanup', 'unknown')}"
                        ),
                    }
                )
            else:
                retained = _preflight_matches_expected(
                    post_close_read,
                    expected_text,
                )
                result.update(
                    {
                        "stage": "complete",
                        "cleanup": "controller_and_post_close_adapter_closed",
                        "post_close_matches_expected": retained,
                        "post_close_status": (
                            "expected_address_retained" if retained else "address_changed"
                        ),
                    }
                )
    except Exception as error:  # noqa: BLE001
        cleanup = (
            "controller_closed_post_close_probe_exit_attempted"
            if result.get("stage") == "post_close_identity_read"
            else "controller_context_exit_attempted"
        )
        result.update(
            {
                "status": "failed",
                "error_type": type(error).__name__,
                "error": str(error),
                "cleanup": cleanup,
                "key_store_created": await asyncio.to_thread(key_store_path.exists),
            }
        )
    finally:
        advertising_started = transport_diagnostics is not None and any(
            event.event == "advertising_start" for event in transport_diagnostics.events
        )
        result["advertising"] = advertising_started
        result["switch_facing"] = advertising_started
    return result


def main(argv: list[str] | None = None) -> int:
    """Print a dry-run plan or execute an explicitly approved pairing probe."""
    parser = _parser()
    args = parser.parse_args(argv)
    if args.preflight_timeout <= 0:
        parser.error("--preflight-timeout must be greater than zero")
    if args.pair_timeout <= 0:
        parser.error("--pair-timeout must be greater than zero")
    if args.observation_seconds <= 0:
        parser.error("--observation-seconds must be greater than zero")
    try:
        expected_address = _parse_address(args.expected_address)
    except ValueError as error:
        parser.error(str(error))

    key_store_exists = args.key_store.exists()
    invalid_key_store_state = args.execute and (
        (args.reuse_key_store and not key_store_exists)
        or (not args.reuse_key_store and key_store_exists)
    )
    if invalid_key_store_state:
        error = (
            f"existing key store required: {args.key_store}"
            if args.reuse_key_store
            else f"fresh key store required: {args.key_store}"
        )
        result = {
            "timestamp": datetime.now(UTC).isoformat(),
            "adapter": args.adapter,
            "expected_address": _display_address(expected_address),
            "key_store": str(args.key_store),
            "key_store_mode": "reuse" if args.reuse_key_store else "fresh",
            "trace": str(args.trace),
            "persistent_write": False,
            "advertising": False,
            "switch_facing": False,
            "observation_seconds": args.observation_seconds,
            "post_close_address_read": args.post_close_address_read,
            "status": "failed",
            "stage": (
                "require_existing_key_store"
                if args.reuse_key_store
                else "reject_existing_key_store"
            ),
            "cleanup": "adapter_not_opened",
            "error_type": "FileNotFoundError" if args.reuse_key_store else "FileExistsError",
            "error": error,
        }
    elif args.execute:
        result = asyncio.run(
            _execute(
                adapter=args.adapter,
                expected_address=expected_address,
                key_store_path=args.key_store,
                trace_path=args.trace,
                preflight_timeout=args.preflight_timeout,
                pair_timeout=args.pair_timeout,
                observation_seconds=args.observation_seconds,
                reuse_key_store=args.reuse_key_store,
                post_close_address_read=args.post_close_address_read,
            )
        )
    else:
        result = _dry_run_payload(args, expected_address)

    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    return 0 if not args.execute or result["status"] == "paired" else 1


if __name__ == "__main__":
    raise SystemExit(main())
