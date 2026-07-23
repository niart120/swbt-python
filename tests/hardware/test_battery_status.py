import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from swbt import DiagnosticsConfig, ProController

_PROFILE_FILENAME = "battery-status-profile.json"


@pytest.mark.hardware
def test_switch_reports_default_battery_status_for_manual_ui_confirmation(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Reconnect, send neutral reports for five seconds, and close cleanly."""
    profile_path = swbt_hardware_artifact_dir / _PROFILE_FILENAME
    trace_path = swbt_hardware_artifact_dir / "battery-status.jsonl"
    if not profile_path.exists():
        pytest.skip(
            "paired profile is missing; copy an existing adapter-default Pro Controller "
            f"profile to {profile_path}"
        )
    original_profile = profile_path.read_bytes()

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=60.0)
                assert result.status == "connected"
                await asyncio.sleep(5.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    assert profile_path.read_bytes() == original_profile
    assert _contains_event(
        events,
        "active_reconnect_result",
        route="active_reconnect",
        status="connected",
    )
    assert _contains_event(events, "report_tx", report_id="0x30")
    assert not _contains_event(events, "advertising_start")
    assert not _contains_event(events, "classic_pairing")
    assert not _contains_event(events, "key_store_update")
    assert not _contains_event(events, "error")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _contains_event(
    events: list[dict[str, Any]],
    event_name: str,
    **expected_fields: object,
) -> bool:
    return any(
        event.get("event") == event_name
        and all(event.get(key) == value for key, value in expected_fields.items())
        for event in events
    )
