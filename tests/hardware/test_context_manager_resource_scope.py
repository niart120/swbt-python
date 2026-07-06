import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from swbt import DiagnosticsConfig, ProController


@pytest.mark.bumble
def test_switch_gamepad_open_only_does_not_start_advertising_on_bumble(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    trace_path = swbt_hardware_artifact_dir / "resource-open-only.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = ProController(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.open()
                assert pad.status().connection_state == "opened"
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)

    assert _contains_event(events, "run_metadata", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "transport_open_complete", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "disconnect_request", status="unavailable")
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)
    assert not _contains_event(events, "advertising_start", adapter=swbt_bumble_adapter)
    assert not _contains_event(events, "host_connection", adapter=swbt_bumble_adapter)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
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
