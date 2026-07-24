"""Manual comparison gate for reply-to-automatic-input holdoff variants."""

import asyncio
import json
from pathlib import Path
from typing import Any, Literal

import pytest

import swbt.report_loop as report_loop_module
from swbt import Button, DiagnosticsConfig, DirectProController, ProController
from swbt.errors import ConnectionTimeoutError

_PROFILE_FILENAME = "pairing-profile-adapter-default-pro.json"
_OBSERVATION_SECONDS = 5.0
_RECONNECT_TIMEOUT_SECONDS = 15.0
_PAIRING_TIMEOUT_SECONDS = 20.0
type ControllerKind = Literal["periodic", "direct"]


@pytest.mark.hardware
@pytest.mark.parametrize(
    ("holdoff_seconds", "expect_ready"),
    [(0.3, True), (0.1, True), (0.0, False)],
)
def test_switch_reply_holdoff_variant_fresh_pairing_characterizes_readiness_and_a_input(
    holdoff_seconds: float,
    expect_ready: bool,
    monkeypatch: pytest.MonkeyPatch,
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Pair one holdoff variant, send A, and close with neutral state.

    The operator must prepare the Switch pairing screen and record whether the
    controller registers and Button A is reflected. A new artifact directory is
    required for each run because this test writes a pairing profile.
    """
    label = f"fresh-periodic-{holdoff_seconds:.3f}".replace(".", "_")
    profile_path = swbt_hardware_artifact_dir / f"reply-holdoff-{label}.json"
    trace_path = swbt_hardware_artifact_dir / f"reply-holdoff-{label}.jsonl"
    if profile_path.exists():
        pytest.fail("fresh pairing profile already exists; use a new artifact directory")
    monkeypatch.setattr(
        report_loop_module,
        "REPLY_PERIODIC_HOLDOFF_SECONDS",
        holdoff_seconds,
    )

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            try:
                pad = await ProController.create_profile(
                    adapter=swbt_bumble_adapter,
                    profile_path=str(profile_path),
                    pair_timeout=_PAIRING_TIMEOUT_SECONDS,
                    diagnostics=DiagnosticsConfig(trace_writer=trace),
                )
            except ConnectionTimeoutError:
                if expect_ready:
                    raise
                return
            try:
                if not expect_ready:
                    pytest.fail("expected fresh pairing to time out without holdoff")
                await pad.tap(Button.A)
                await asyncio.sleep(_OBSERVATION_SECONDS)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    if expect_ready:
        assert _contains_event(events, "classic_pairing")
        assert _contains_event(events, "key_store_update", status="succeeded")
        assert _contains_event(events, "protocol_ready")
        assert _contains_event(events, "report_tx", reason="input", report_id="0x30")
    else:
        assert not _contains_event(events, "protocol_ready")
    assert _contains_event(
        events,
        "transport_close_complete",
        adapter=swbt_bumble_adapter,
    )


@pytest.mark.hardware
@pytest.mark.parametrize(
    ("holdoff_seconds", "controller_kind", "expect_ready"),
    [
        (0.3, "periodic", True),
        (0.1, "periodic", True),
        (0.0, "periodic", False),
        (0.3, "direct", True),
        (0.1, "direct", True),
        (0.0, "direct", False),
    ],
)
def test_switch_reply_holdoff_variant_reconnect_characterizes_readiness_and_a_input(
    holdoff_seconds: float,
    controller_kind: ControllerKind,
    expect_ready: bool,
    monkeypatch: pytest.MonkeyPatch,
    swbt_bumble_adapter: str,
    swbt_hardware_artifact_dir: Path,
) -> None:
    """Compare one holdoff variant through reconnect, input, and neutral close.

    A pass proves protocol readiness, the A send, and local cleanup. Switch UI input
    reflection must be observed by the operator and recorded in the hardware log.
    """
    profile_path = swbt_hardware_artifact_dir / _PROFILE_FILENAME
    if not profile_path.exists():
        pytest.skip(
            "adapter-default Pro pairing profile is missing; copy it into the artifact "
            "directory before the approved comparison run"
        )
    original_profile = profile_path.read_bytes()
    label = f"{controller_kind}-{holdoff_seconds:.3f}".replace(".", "_")
    trace_path = swbt_hardware_artifact_dir / f"reply-holdoff-{label}.jsonl"
    monkeypatch.setattr(
        report_loop_module,
        "REPLY_PERIODIC_HOLDOFF_SECONDS",
        holdoff_seconds,
    )
    controller_cls = ProController if controller_kind == "periodic" else DirectProController

    async def run() -> None:
        with trace_path.open("w", encoding="utf-8") as trace:
            pad = controller_cls(
                adapter=swbt_bumble_adapter,
                profile_path=str(profile_path),
                diagnostics=DiagnosticsConfig(trace_writer=trace),
            )
            try:
                result = await pad.try_reconnect(timeout=_RECONNECT_TIMEOUT_SECONDS)
                if expect_ready:
                    assert result.status == "connected"
                else:
                    assert result.status == "timeout"
                    return
                await pad.tap(Button.A)
                await asyncio.sleep(_OBSERVATION_SECONDS)
            finally:
                await pad.close(neutral=True)

    asyncio.run(run())

    events = _read_jsonl(trace_path)
    assert profile_path.read_bytes() == original_profile
    if expect_ready:
        assert _contains_event(events, "protocol_ready")
        assert _contains_event(
            events,
            "report_tx",
            reason="direct",
            report_id="0x30",
        ) or _contains_event(
            events,
            "report_tx",
            reason="input",
            report_id="0x30",
        )
        assert _contains_event(
            events,
            "active_reconnect_result",
            route="active_reconnect",
            status="connected",
        )
    else:
        assert not _contains_event(events, "protocol_ready")
        assert _contains_event(
            events,
            "active_reconnect_result",
            route="active_reconnect",
            status="timeout",
        )
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
    **expected: object,
) -> bool:
    return any(
        event.get("event") == event_name
        and all(event.get(key) == value for key, value in expected.items())
        for event in events
    )
