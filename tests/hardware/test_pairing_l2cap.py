import asyncio
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest

from swbt import DiagnosticsConfig, SwitchGamepad


@pytest.mark.hardware
def test_switch_pairing_l2cap_records_diagnostics(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    trace_path = swbt_hardware_artifact_dir / "pairing-l2cap.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = SwitchGamepad(
                adapter=swbt_bumble_adapter,
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                await pad.open()
                await pad.wait_connected(timeout=60.0)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]

    assert _contains_event(events, "run_metadata", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "bumble_runtime", bumble_version=version("bumble"))
    assert _contains_event(events, "transport_open_start", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "bumble_device_initialized",
        adapter=swbt_bumble_adapter,
        device_name="Pro Controller",
        class_of_device="0x002508",
    )
    assert _contains_event(events, "advertising_start", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "host_connection", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "classic_pairing", adapter=swbt_bumble_adapter)
    assert _contains_event(
        events,
        "l2cap_channel_open",
        adapter=swbt_bumble_adapter,
        channel="control",
    )
    assert _contains_event(
        events,
        "l2cap_channel_open",
        adapter=swbt_bumble_adapter,
        channel="interrupt",
    )
    assert _contains_event(events, "connected", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "transport_close_complete", adapter=swbt_bumble_adapter)


def _contains_event(
    events: list[dict[str, Any]],
    event_name: str,
    **expected_fields: object,
) -> bool:
    for event in events:
        if event.get("event") != event_name:
            continue
        if all(event.get(key) == value for key, value in expected_fields.items()):
            return True
    return False
