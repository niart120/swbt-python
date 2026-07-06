"""Integration tests for public examples."""

import asyncio
import importlib.util
import subprocess
import sys
from collections.abc import Awaitable
from pathlib import Path
from typing import Protocol, cast

from swbt import Button, InputState, ProController, SwitchGamepad
from swbt.transport.fake import FakeHidTransport

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


class TapAOnce(Protocol):
    """Callable shape exported by examples/tap_a.py."""

    def __call__(self, pad: SwitchGamepad, *, duration: float = 0.08) -> Awaitable[None]:
        """Tap Button A on a connected gamepad."""


def _load_tap_a_once() -> TapAOnce:
    example_path = EXAMPLES_DIR / "tap_a.py"
    spec = importlib.util.spec_from_file_location("swbt_example_tap_a", example_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast("TapAOnce", module.tap_a_once)


def test_tap_a_example_can_run_with_fake_transport() -> None:
    tap_a_once = _load_tap_a_once()

    async def run() -> None:
        transport = FakeHidTransport()

        async with ProController(transport=transport) as pad:
            await transport.connect()

            await tap_a_once(pad, duration=0)

            pressed, released = transport.sent_interrupt_reports
            assert pressed[0] == 0x30
            assert pressed[3:6] == bytes.fromhex("08 00 00")
            assert released[0] == 0x30
            assert released[3:6] == bytes.fromhex("00 00 00")
            assert pad.snapshot() == InputState.neutral()

    assert Button.A.name == "A"
    asyncio.run(run())


def test_hardware_examples_help_describes_approval_boundary() -> None:
    for example_name in ("pairing_probe.py", "hardware_bringup.py"):
        result = subprocess.run(  # noqa: S603
            [sys.executable, str(EXAMPLES_DIR / example_name), "--help"],
            capture_output=True,
            check=False,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        help_text = " ".join(result.stdout.split())
        assert "--adapter" in result.stdout
        assert "--trace" in result.stdout
        assert "--timeout" in result.stdout
        assert "explicit approval" in help_text
        assert "cleanup" in help_text
