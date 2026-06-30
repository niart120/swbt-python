import asyncio
import json
import platform
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest

from swbt.diagnostics import DiagnosticsRecorder
from swbt.transport.bumble import BumbleHidTransport


@pytest.mark.bumble
def test_bumble_adapter_open_close_records_diagnostics(
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    trace_path = swbt_hardware_artifact_dir / "bumble-adapter-open-close.jsonl"

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            diagnostics = DiagnosticsRecorder(trace_writer=trace)
            diagnostics.record_run_metadata(adapter=swbt_bumble_adapter)
            diagnostics.record_event(
                "bumble_runtime",
                bumble_version=version("bumble"),
                os_detail=platform.platform(),
            )
            transport = BumbleHidTransport(
                adapter=swbt_bumble_adapter,
                diagnostics=diagnostics,
            )
            try:
                await transport.open()
            finally:
                await transport.close()

    asyncio.run(run())

    events = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()]
    assert _contains_event(events, "run_metadata", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "bumble_runtime")
    assert _contains_event(events, "transport_open_start", adapter=swbt_bumble_adapter)
    assert _contains_event(events, "transport_open_complete", adapter=swbt_bumble_adapter)
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
