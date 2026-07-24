"""Behavioral checks for runtime configuration normalization."""

import asyncio
import importlib

import pytest

from swbt.gamepad import runtime as gamepad_runtime
from swbt.gamepad._config import _GamepadConfig
from swbt.protocol.profiles.pro_controller import ProControllerProfile
from swbt.transport.base import DisconnectRequestResult
from swbt.transport.fake import FakeHidTransport


def test_normalized_config_uses_profile_device_name_unless_user_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run(config: _GamepadConfig) -> str:
        bumble_module = importlib.import_module("swbt.transport.bumble")
        captured_config: dict[str, object] = {}

        class FakeBumbleTransport:
            def __init__(
                self,
                *,
                adapter: str,
                device_name: str,
                profile: ProControllerProfile,
                diagnostics: object,
                profile_path: str | None,
                expected_local_bluetooth_address: bytes | None,
            ) -> None:
                _ = (
                    adapter,
                    profile,
                    diagnostics,
                    profile_path,
                    expected_local_bluetooth_address,
                )
                captured_config["device_name"] = device_name

            async def open(self) -> None:
                return None

            async def start_advertising(self) -> None:
                return None

            async def close(self) -> None:
                return None

            async def request_disconnect(self) -> DisconnectRequestResult:
                return DisconnectRequestResult(status="unavailable")

            def local_bluetooth_address(self) -> bytes | None:
                return None

            async def bonded_peer_address(self) -> str | None:
                return None

            async def connect_bonded_peer(
                self,
                peer_address: str,
                *,
                connect_timeout: float | None,
            ) -> None:
                _ = (peer_address, connect_timeout)

            async def send_interrupt(self, payload: bytes) -> None:
                _ = payload

            def on_interrupt_data(self, callback: object) -> None:
                _ = callback

            def on_control_data(self, callback: object) -> None:
                _ = callback

            def on_connected(self, callback: object) -> None:
                _ = callback

            def on_disconnected(self, callback: object) -> None:
                _ = callback

        monkeypatch.setattr(bumble_module, "BumbleHidTransport", FakeBumbleTransport)

        runtime = gamepad_runtime.ControllerRuntime(config)
        await runtime.open()
        await runtime.close(neutral=True)

        return str(captured_config["device_name"])

    profile_default_name = asyncio.run(
        run(
            _GamepadConfig(
                adapter="usb:1",
                profile=ProControllerProfile(device_name="Profile Pad"),
            )
        )
    )
    explicit_name = asyncio.run(
        run(
            _GamepadConfig(
                adapter="usb:1",
                device_name="Override Pad",
                profile=ProControllerProfile(device_name="Profile Pad"),
            )
        )
    )

    assert profile_default_name == "Profile Pad"
    assert explicit_name == "Override Pad"


def test_normalized_config_uses_profile_report_period_unless_user_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_periods: list[int] = []

    class SpyReportLoop:
        def __init__(
            self,
            *,
            transport: object,
            state_store: object,
            report_period_us: int,
            input_report_builder: object | None = None,
            session: object | None = None,
            diagnostics: object | None = None,
            sender: object | None = None,
            is_user_input_enabled: object | None = None,
            stop_when_user_input_enabled: bool = False,
        ) -> None:
            _ = (
                transport,
                state_store,
                input_report_builder,
                session,
                diagnostics,
                sender,
                is_user_input_enabled,
                stop_when_user_input_enabled,
            )
            captured_periods.append(report_period_us)

        async def stop(self) -> None:
            return None

    monkeypatch.setattr(gamepad_runtime, "ReportLoop", SpyReportLoop)

    async def run(config: _GamepadConfig) -> int:
        runtime = gamepad_runtime.ControllerRuntime(
            config,
            transport=FakeHidTransport(),
        )
        await runtime.open()
        await runtime.close(neutral=False)
        return captured_periods[-1]

    profile_default_period = asyncio.run(
        run(
            _GamepadConfig(
                profile=ProControllerProfile(default_report_period_us=12_345),
            )
        )
    )
    explicit_period = asyncio.run(
        run(
            _GamepadConfig(
                profile=ProControllerProfile(default_report_period_us=12_345),
                report_period_us=8000,
            )
        )
    )

    assert profile_default_period == 12_345
    assert explicit_period == 8000
