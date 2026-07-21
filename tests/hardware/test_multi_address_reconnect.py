"""Hardware gate for two locally addressed profiles reconnecting in both directions."""

import asyncio
import json
from pathlib import Path

import pytest

from swbt import DiagnosticsConfig, ProController


def _events(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _has(events: list[dict[str, object]], name: str, **fields: object) -> bool:
    return any(
        event.get("event") == name
        and all(
            event.get(key) in value if isinstance(value, tuple) else event.get(key) == value
            for key, value in fields.items()
        )
        for event in events
    )


@pytest.mark.hardware
def test_switch_two_profiles_round_trip_without_repairing(
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_secondary_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Pair A and B, then reconnect A, B, A, B without pairing fallback."""
    addresses = (swbt_local_address.upper(), swbt_secondary_local_address.upper())
    if addresses[0] == addresses[1]:
        pytest.fail("A and B addresses must differ")
    profiles = tuple(
        swbt_hardware_artifact_dir / f"multi-address-{label}.json" for label in ("a", "b")
    )
    if any(path.exists() for path in profiles):
        pytest.fail("profiles already exist; use a new hardware artifact directory")

    async def pair(address: str, profile: Path, trace_path: Path) -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = await ProController.create_profile(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile),
                local_address=address,
                pair_timeout=60.0,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            await pad.close(neutral=True)

    async def reconnect(address: str, profile: Path, trace_path: Path) -> None:
        original = profile.read_bytes()  # noqa: ASYNC240
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
            finally:
                await pad.close(neutral=True)
        events = _events(trace_path)
        assert profile.read_bytes() == original  # noqa: ASYNC240
        assert _has(
            events,
            "adapter_identity_prepared",
            status=("already_active", "rewritten"),
            target_address=address,
        )
        assert _has(events, "active_reconnect_result", route="active_reconnect", status="connected")
        assert not _has(events, "advertising_start")
        assert not _has(events, "classic_pairing")
        assert not _has(events, "key_store_update")
        assert _has(events, "transport_close_complete", adapter=swbt_bumble_adapter)

    async def run() -> None:
        await pair(
            addresses[0], profiles[0], swbt_hardware_artifact_dir / "multi-address-a-pair.jsonl"
        )
        await pair(
            addresses[1], profiles[1], swbt_hardware_artifact_dir / "multi-address-b-pair.jsonl"
        )
        for index, label in ((0, "a-1"), (1, "b-1"), (0, "a-2"), (1, "b-2")):
            await reconnect(
                addresses[index],
                profiles[index],
                swbt_hardware_artifact_dir / f"multi-address-{label}.jsonl",
            )

    asyncio.run(run())


@pytest.mark.hardware
def test_switch_two_profiles_observation_window_after_reconnect(
    swbt_bumble_adapter: str,
    swbt_local_address: str,
    swbt_secondary_local_address: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect A and B once each, hold the link for five seconds, then close."""
    addresses = (swbt_local_address.upper(), swbt_secondary_local_address.upper())
    profiles = tuple(
        swbt_hardware_artifact_dir / f"multi-address-{label}.json" for label in ("a", "b")
    )
    if any(not path.exists() for path in profiles):
        pytest.skip("run the round-trip pairing test first with the same artifact directory")

    async def reconnect_one(index: int) -> None:
        profile = profiles[index]
        trace_path = swbt_hardware_artifact_dir / f"multi-address-{('a', 'b')[index]}-observe.jsonl"
        original = profile.read_bytes()
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(5.0)
            finally:
                await pad.close(neutral=True)
        events = _events(trace_path)
        assert profile.read_bytes() == original
        assert _has(
            events,
            "adapter_identity_prepared",
            status=("already_active", "rewritten"),
            target_address=addresses[index],
        )
        assert _has(events, "active_reconnect_result", route="active_reconnect", status="connected")
        assert not _has(events, "advertising_start")
        assert not _has(events, "classic_pairing")
        assert not _has(events, "key_store_update")
        assert _has(events, "transport_close_complete", adapter=swbt_bumble_adapter)

    async def run() -> None:
        await reconnect_one(0)
        await reconnect_one(1)

    asyncio.run(run())
