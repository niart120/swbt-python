import asyncio
import json
import platform
from collections.abc import Callable
from importlib import metadata
from io import StringIO
from pathlib import Path
from typing import Literal, cast

import pytest

import swbt.gamepad as gamepad_module
import swbt.gamepad.runtime as gamepad_runtime_module
from swbt import (
    Button,
    ControllerColors,
    DiagnosticsConfig,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    IMUFrame,
    InputState,
    JoyConL,
    JoyConR,
    ProController,
    Stick,
    SwitchGamepad,
)
from swbt._testing.gamepad import (
    make_direct_joycon_l,
    make_direct_pro_controller,
    make_joycon_l,
    make_joycon_r,
    make_pro_controller,
)
from swbt.errors import (
    ClosedError,
    ConnectionFailedError,
    ConnectionTimeoutError,
    InvalidInputError,
    InvalidKeyStoreError,
    UnsupportedInputError,
)
from swbt.gamepad._config import _SwitchGamepadConfig
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import ProControllerProfile
from swbt.transport.fake import FakeHidTransport

_OUTPUT_REPORT_PREFIX = bytes.fromhex("01 00 00 00 00 00 00 00 00 00")


def _joycon_class(side: Literal["left", "right"]) -> Callable[..., JoyConL | JoyConR]:
    if side == "left":
        return make_joycon_l
    return make_joycon_r


async def _complete_protocol_handshake(transport: FakeHidTransport) -> None:
    await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("03 30"))
    await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("30 01"))


async def _connect_protocol_ready(transport: FakeHidTransport) -> None:
    await transport.connect()
    await _complete_protocol_handshake(transport)
    transport.clear_sent_interrupt_reports()


async def _wait_for_transport_event(
    transport: FakeHidTransport,
    event: str,
) -> None:
    async with asyncio.timeout(0.1):
        while event not in transport.events:  # noqa: ASYNC110
            await asyncio.sleep(0)


def _imu_frame_bytes(frame: IMUFrame) -> bytes:
    return b"".join(
        int(value).to_bytes(2, "little", signed=True)
        for value in (
            frame.accel_x,
            frame.accel_y,
            frame.accel_z,
            frame.gyro_x,
            frame.gyro_y,
            frame.gyro_z,
        )
    )


def test_async_context_opens_and_closes_fake_transport() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        assert transport.is_open is False

        async with make_pro_controller(transport=transport):
            assert transport.is_open is True
            assert transport.open_count == 1
            assert transport.close_count == 0

        assert transport.is_open is False
        assert transport.open_count == 1
        assert transport.close_count == 1
        assert transport.events == (
            "open",
            "request_disconnect_unavailable",
            "close",
        )

    asyncio.run(run())


def test_pair_starts_advertising_and_waits_for_fake_connection() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            pairing = asyncio.create_task(pad.pair(timeout=1.0))
            await asyncio.sleep(0)

            assert pairing.done() is False
            assert transport.events == ("open", "start_advertising")

            await transport.connect()
            await asyncio.sleep(0)

            assert pairing.done() is False
            assert pad.status().connection_state == "initializing"

            await _complete_protocol_handshake(transport)
            await asyncio.wait_for(pairing, timeout=0.1)

        assert transport.events == (
            "open",
            "start_advertising",
            "connected",
            "interrupt_rx",
            "interrupt_rx",
            "request_disconnect",
            "disconnect_request_closed",
            "close",
        )

    asyncio.run(run())


def test_pair_waits_until_ready_subcommand_reply_is_transport_accepted() -> None:
    async def run() -> None:
        send_interrupt_wait = asyncio.Event()
        send_interrupt_wait.set()
        transport = FakeHidTransport(send_interrupt_wait=send_interrupt_wait)

        async with make_direct_pro_controller(transport=transport) as pad:
            pairing = asyncio.create_task(pad.pair(timeout=1.0))
            await asyncio.sleep(0)
            await transport.connect()
            await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("03 30"))

            send_interrupt_wait.clear()
            player_lights = asyncio.create_task(
                transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("30 01"))
            )
            await asyncio.sleep(0)

            assert player_lights.done() is False
            assert pairing.done() is False
            assert pad.status().connection_state == "initializing"

            send_interrupt_wait.set()
            await player_lights
            await asyncio.wait_for(pairing, timeout=0.1)

    asyncio.run(run())


def test_pair_fails_and_cleans_up_when_ready_reply_send_fails() -> None:
    class PlayerLightsReplyError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("player lights reply failed")

    class FailPlayerLightsReplyFakeHidTransport(FakeHidTransport):
        async def send_interrupt(self, payload: bytes) -> None:
            if payload[0] == 0x21 and payload[14] == 0x30:
                raise PlayerLightsReplyError
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = FailPlayerLightsReplyFakeHidTransport()
        pad = make_direct_pro_controller(transport=transport)

        pairing = asyncio.create_task(pad.pair(timeout=1.0))
        await _wait_for_transport_event(transport, "start_advertising")
        await transport.connect()
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("03 30"))
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("30 01"))

        with pytest.raises(ConnectionFailedError):
            await asyncio.wait_for(pairing, timeout=0.1)

        assert pad.status().connection_state == "closed"
        assert transport.is_open is False

    asyncio.run(run())


def test_pair_fails_immediately_when_link_disconnects_before_protocol_ready() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport)

        pairing = asyncio.create_task(pad.pair(timeout=1.0))
        await _wait_for_transport_event(transport, "start_advertising")
        await transport.connect()
        await transport.disconnect(reason=0x13)

        with pytest.raises(ConnectionFailedError):
            await asyncio.wait_for(pairing, timeout=0.1)

        assert pad.status().connection_state == "closed"
        assert transport.is_open is False

    asyncio.run(run())


def test_pair_fails_immediately_for_unsupported_subcommand_before_ready() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport)

        pairing = asyncio.create_task(pad.pair(timeout=1.0))
        await _wait_for_transport_event(transport, "start_advertising")
        await transport.connect()
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("ff"))

        with pytest.raises(ConnectionFailedError):
            await asyncio.wait_for(pairing, timeout=0.1)

        assert pad.status().connection_state == "closed"
        assert transport.is_open is False

    asyncio.run(run())


def test_try_connect_returns_failed_for_disconnect_before_protocol_ready() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport)

        connecting = asyncio.create_task(pad.try_connect(timeout=1.0, allow_pairing=True))
        await _wait_for_transport_event(transport, "start_advertising")
        await transport.connect()
        await transport.disconnect(reason=0x13)

        result = await asyncio.wait_for(connecting, timeout=0.1)

        assert result.route == "pairing"
        assert result.status == "failed"
        assert pad.status().connection_state == "closed"

    asyncio.run(run())


@pytest.mark.parametrize(
    ("controller_class", "profile"),
    [
        (ProController, ProControllerProfile()),
        (JoyConL, JoyConLeftProfile()),
        (JoyConR, JoyConRightProfile()),
        (DirectProController, ProControllerProfile()),
        (DirectJoyConL, JoyConLeftProfile()),
        (DirectJoyConR, JoyConRightProfile()),
    ],
)
def test_all_concrete_controllers_share_protocol_ready_connection_boundary(
    controller_class: type[
        ProController | JoyConL | JoyConR | DirectProController | DirectJoyConL | DirectJoyConR
    ],
    profile: ProControllerProfile | JoyConLeftProfile | JoyConRightProfile,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = controller_class._from_config(
            _SwitchGamepadConfig(profile=profile),
            transport=transport,
        )

        pairing = asyncio.create_task(pad.pair(timeout=1.0))
        await _wait_for_transport_event(transport, "start_advertising")
        await transport.connect()
        await asyncio.sleep(0)

        assert pairing.done() is False
        assert pad.status().connection_state == "initializing"

        await _complete_protocol_handshake(transport)
        await asyncio.wait_for(pairing, timeout=0.1)

        assert pad.status().connection_state == "connected"
        await pad.close(neutral=False)

    asyncio.run(run())


def test_periodic_bootstrap_stops_after_first_subcommand_then_starts_when_ready() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport, report_period_us=1000)
        await pad.open()
        await pad.press(Button.A)
        await transport.connect()

        bootstrap_report = await transport.wait_for_interrupt_report_id(0x30)

        assert pad.status().connection_state == "initializing"
        assert bootstrap_report[3:6] == bytes.fromhex("00 00 00")

        transport.clear_sent_interrupt_reports()
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("02"))
        await asyncio.sleep(0.02)

        assert [report[0] for report in transport.sent_interrupt_reports] == [0x21]
        assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("00 00 00")

        transport.clear_sent_interrupt_reports()
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("03 30"))
        initializing_report = await transport.wait_for_interrupt_report_id(0x30)

        assert pad.status().connection_state == "initializing"
        assert initializing_report[3:6] == bytes.fromhex("00 00 00")

        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("30 01"))
        transport.clear_sent_interrupt_reports()
        await transport.wait_for_interrupt_report_id(0x30)

        input_report = next(
            report for report in transport.sent_interrupt_reports if report[0] == 0x30
        )
        assert input_report[3:6] == bytes.fromhex("08 00 00")

        await pad.close(neutral=False)

    asyncio.run(run())


def test_handshake_bootstrap_retries_until_first_subcommand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        monkeypatch.setattr(
            gamepad_runtime_module,
            "HANDSHAKE_BOOTSTRAP_RETRY_SECONDS",
            0.001,
        )
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport)
        await pad.open()
        await transport.connect()

        await transport.wait_for_interrupt_report_count(2)
        assert [report[0] for report in transport.sent_interrupt_reports] == [0x30, 0x30]

        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("02"))
        reports_after_reply = len(transport.sent_interrupt_reports)
        await asyncio.sleep(0.01)

        assert len(transport.sent_interrupt_reports) == reports_after_reply
        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_input_is_rejected_until_protocol_ready() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_direct_pro_controller(transport=transport)
        await pad.open()
        await transport.connect()

        with pytest.raises(ClosedError):
            await pad.press(Button.A)

        await _complete_protocol_handshake(transport)
        transport.clear_sent_interrupt_reports()
        await pad.press(Button.A)

        assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("08 00 00")
        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_bootstrap_stops_after_first_subcommand_and_remains_nonperiodic() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_direct_pro_controller(transport=transport)
        await pad.open()
        await transport.connect()

        bootstrap_report = await transport.wait_for_interrupt_report_id(0x30)

        assert pad.status().connection_state == "initializing"
        assert bootstrap_report[3:6] == bytes.fromhex("00 00 00")

        transport.clear_sent_interrupt_reports()
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("02"))
        await asyncio.sleep(0.02)

        assert [report[0] for report in transport.sent_interrupt_reports] == [0x21]
        transport.clear_sent_interrupt_reports()
        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("03 30"))
        initializing_report = await transport.wait_for_interrupt_report_id(0x30)

        assert pad.status().connection_state == "initializing"
        assert initializing_report[3:6] == bytes.fromhex("00 00 00")

        await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("30 01"))
        transport.clear_sent_interrupt_reports()
        await asyncio.sleep(0.03)

        assert pad.status().connection_state == "connected"
        assert transport.sent_interrupt_reports == ()
        await pad.close(neutral=False)

    asyncio.run(run())


def test_protocol_ready_trace_occurs_once_after_the_completing_reply() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ):
            await transport.connect()
            await _complete_protocol_handshake(transport)
            await transport.inject_interrupt_data(_OUTPUT_REPORT_PREFIX + bytes.fromhex("30 01"))

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        event_names = [event["event"] for event in events]
        ready_index = event_names.index("protocol_ready")

        assert event_names.count("protocol_ready") == 1
        assert event_names[ready_index - 1] == "subcommand_reply_tx"
        assert events[ready_index]["observed_subcommands"] == ["0x03", "0x30"]
        assert events[ready_index]["profile_kind"] == "pro_controller"
        assert events[ready_index]["route"] == "active_reconnect"

    asyncio.run(run())


def test_incoming_connection_trace_does_not_use_active_reconnect_events() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport(bonded_peer_addresses=("01:02:03:04:05:06",))

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            pairing = asyncio.create_task(pad.pair(timeout=1.0))
            await asyncio.sleep(0)
            await _connect_protocol_ready(transport)
            await asyncio.wait_for(pairing, timeout=0.1)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        event_names = [event["event"] for event in events]

        assert {
            "event": "incoming_connection",
            "previous_state": "advertising",
            "route": "incoming",
        } in events
        assert "active_reconnect_attempt" not in event_names
        assert "active_reconnect_result" not in event_names
        assert "active_reconnect" not in transport.events

    asyncio.run(run())


def test_open_only_does_not_start_advertising() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport)

        await pad.open()

        assert transport.is_open is True
        assert pad.status().connection_state == "opened"
        assert transport.events == ("open",)

        await pad.close(neutral=True)

    asyncio.run(run())


def test_profile_path_is_recorded_in_run_metadata(tmp_path: Path) -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        profile_path = tmp_path / "profile.json"
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            profile_path=str(profile_path),
            transport=transport,
        )

        result = await pad.try_reconnect()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        assert result.status == "no_bond"
        assert {
            "event": "run_metadata",
            "adapter": "custom",
            "profile_path": str(profile_path),
            "os": platform.system(),
            "package_version": metadata.version("swbt-python"),
            "python_version": platform.python_version(),
        } in events

    asyncio.run(run())


def test_try_reconnect_with_injected_transport_skips_default_key_store_warning() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        )

        result = await pad.try_reconnect(timeout=0.1)
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert result.status == "no_bond"
        assert not any(event["event"] == "reconnect_profile_unavailable" for event in events)

    asyncio.run(run())


def test_injected_transport_is_not_reconfigured_by_switch_gamepad() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(
            profile_path="configured-for-metadata.json",
            transport=transport,
        ) as pad:
            result = await pad.try_reconnect()

            assert result.status == "no_bond"
            assert not hasattr(transport, "configure_profile_path")

    asyncio.run(run())


def test_async_context_exception_requests_disconnect_and_reraises() -> None:
    class ExpectedError(Exception):
        """Exception raised inside the gamepad context."""

    async def raise_inside_context(transport: FakeHidTransport) -> None:
        async with make_pro_controller(transport=transport):
            await transport.connect()
            raise ExpectedError

    async def run() -> None:
        transport = FakeHidTransport()

        with pytest.raises(ExpectedError):
            await raise_inside_context(transport)

        assert transport.close_count == 1
        assert transport.events == (
            "open",
            "connected",
            "request_disconnect",
            "disconnect_request_closed",
            "close",
        )

    asyncio.run(run())


def test_press_buttons_are_reflected_in_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.press(Button.L, Button.R)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[0] == 0x30
            assert report[3:6] == bytes.fromhex("40 00 40")

    asyncio.run(run())


def test_release_buttons_clears_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)

            await pad.press(Button.L, Button.R)
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("40 00 40")

            await pad.release(Button.L, Button.R)
            released_count = len(transport.sent_interrupt_reports)
            released_reports = await transport.wait_for_interrupt_report_count(released_count + 1)
            assert released_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_release_only_clears_requested_buttons_in_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)

            await pad.press(Button.A, Button.L, Button.R)
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("48 00 40")

            await pad.release(Button.L)
            released_count = len(transport.sent_interrupt_reports)
            released_reports = await transport.wait_for_interrupt_report_count(released_count + 1)
            assert released_reports[-1][3:6] == bytes.fromhex("48 00 00")

    asyncio.run(run())


def test_apply_updates_snapshot_and_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        state = InputState.neutral().with_buttons([Button.X])

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(state)

            assert pad.snapshot() == state

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            assert reports[-1][3:6] == bytes.fromhex("02 00 00")

    asyncio.run(run())


def test_direct_send_waits_for_transport_and_commits_exactly_one_report() -> None:
    class BlockingFakeHidTransport(FakeHidTransport):
        def __init__(self) -> None:
            super().__init__()
            self.send_started = asyncio.Event()
            self.release_send = asyncio.Event()

        async def send_interrupt(self, payload: bytes) -> None:
            self.send_started.set()
            await self.release_send.wait()
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = BlockingFakeHidTransport()
        state = InputState.neutral().with_buttons([Button.X])
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(report_period_us=60_000_000),
            transport=transport,
        )

        async with pad:
            transport.release_send.set()
            await _connect_protocol_ready(transport)
            transport.send_started.clear()
            transport.release_send.clear()
            ready_report_count = len(transport.sent_interrupt_reports)
            send_task = asyncio.create_task(pad.send(state))
            try:
                await asyncio.wait_for(transport.send_started.wait(), timeout=0.1)

                assert send_task.done() is False
                assert len(transport.sent_interrupt_reports) == ready_report_count
                assert pad.snapshot() == InputState.neutral()

                transport.release_send.set()
                await asyncio.wait_for(send_task, timeout=0.1)

                assert pad.snapshot() == state
                assert len(transport.sent_interrupt_reports) == ready_report_count + 1
                assert transport.sent_interrupt_reports[-1][0] == 0x30
                assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("02 00 00")
            finally:
                transport.release_send.set()
                if not send_task.done():
                    send_task.cancel()
                await asyncio.gather(send_task, return_exceptions=True)

    asyncio.run(run())


def test_direct_connection_is_non_periodic_and_still_replies_to_subcommands() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")
        pad = make_direct_pro_controller(transport=transport)

        await pad.open()
        await _connect_protocol_ready(transport)
        ready_report_count = len(transport.sent_interrupt_reports)
        await asyncio.sleep(0.03)

        assert len(transport.sent_interrupt_reports) == ready_report_count

        await transport.inject_interrupt_data(request_device_info)
        reply = await transport.wait_for_interrupt_report_id(0x21)
        await asyncio.sleep(0.03)

        assert reply[14] == 0x02
        assert [report[0] for report in transport.sent_interrupt_reports[ready_report_count:]] == [
            0x21
        ]

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_send_failures_do_not_change_last_successfully_sent_state() -> None:
    class ExpectedSendError(RuntimeError):
        pass

    class ToggleFailFakeHidTransport(FakeHidTransport):
        def __init__(self) -> None:
            super().__init__()
            self.fail_send = False

        async def send_interrupt(self, payload: bytes) -> None:
            if self.fail_send:
                raise ExpectedSendError
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = ToggleFailFakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        sent = InputState.neutral().with_buttons([Button.A])
        rejected = InputState.neutral().with_buttons([Button.X])

        with pytest.raises(ClosedError):
            await pad.send(sent)
        assert pad.snapshot() == InputState.neutral()
        assert transport.sent_interrupt_reports == ()

        await pad.open()
        await _connect_protocol_ready(transport)
        await pad.send(sent)

        with pytest.raises(InvalidInputError):
            await pad.send(cast("InputState", object()))
        assert pad.snapshot() == sent

        transport.fail_send = True

        with pytest.raises(ExpectedSendError):
            await pad.send(rejected)
        with pytest.raises(ExpectedSendError):
            await pad.press(Button.X)

        assert pad.snapshot() == sent
        assert len(transport.sent_interrupt_reports) == 1

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_send_rejects_unsupported_profile_state_without_sending() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_direct_joycon_l(transport=transport)
        unsupported = InputState.neutral().with_buttons([Button.A])

        await pad.open()
        await _connect_protocol_ready(transport)

        with pytest.raises(UnsupportedInputError):
            await pad.send(unsupported)

        assert pad.snapshot() == InputState.neutral()
        assert transport.sent_interrupt_reports == ()

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_semantic_operations_send_once_and_commit_after_success() -> None:
    async def run() -> None:
        unopened = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=FakeHidTransport(),
        )
        with pytest.raises(ClosedError):
            await unopened.press(Button.A)
        assert unopened.snapshot() == InputState.neutral()

        transport = FakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        left = Stick.up()
        right = Stick.right()
        frame = IMUFrame.gyro(100, -100, 50)

        await pad.open()
        await _connect_protocol_ready(transport)

        await pad.press(Button.A)
        assert pad.snapshot() == InputState.neutral().with_buttons([Button.A])

        await pad.sticks(left=left, right=right)
        assert pad.snapshot() == InputState.neutral().with_buttons([Button.A]).with_sticks(
            left_stick=left,
            right_stick=right,
        )

        await pad.lstick(Stick.left())
        await pad.rstick(Stick.down())
        await pad.imu(frame)
        assert pad.snapshot().imu_frames == (frame, frame, frame)

        await pad.release(Button.A)
        assert pad.snapshot().buttons == frozenset()

        await pad.neutral()
        assert pad.snapshot() == InputState.neutral()

        reports = transport.sent_interrupt_reports
        assert len(reports) == 7
        assert all(report[0] == 0x30 for report in reports)
        assert reports[0][3:6] == bytes.fromhex("08 00 00")
        assert reports[-1][3:6] == bytes.fromhex("00 00 00")

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_concurrent_operations_are_serialized_without_lost_state() -> None:
    class SequencedFakeHidTransport(FakeHidTransport):
        def __init__(self) -> None:
            super().__init__()
            self.send_started = (asyncio.Event(), asyncio.Event())
            self.release_send = (asyncio.Event(), asyncio.Event())
            self.send_count = 0

        async def send_interrupt(self, payload: bytes) -> None:
            if payload[0] != 0x30:
                await super().send_interrupt(payload)
                return
            index = self.send_count
            self.send_count += 1
            self.send_started[index].set()
            await self.release_send[index].wait()
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = SequencedFakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        await pad.open()
        await _connect_protocol_ready(transport)

        press_a = asyncio.create_task(pad.press(Button.A))
        await asyncio.wait_for(transport.send_started[0].wait(), timeout=0.1)

        press_b = asyncio.create_task(pad.press(Button.B))
        await asyncio.sleep(0)
        assert transport.send_started[1].is_set() is False

        transport.release_send[0].set()
        await asyncio.wait_for(transport.send_started[1].wait(), timeout=0.1)
        transport.release_send[1].set()
        await asyncio.gather(press_a, press_b)

        reports = transport.sent_interrupt_reports
        assert reports[0][3:6] == bytes.fromhex("08 00 00")
        assert reports[1][3:6] == bytes.fromhex("0c 00 00")
        assert pad.snapshot().buttons == frozenset({Button.A, Button.B})

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_tap_sends_press_and_release_once_while_preserving_held_input() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        held = InputState.neutral().with_buttons([Button.ZL])

        await pad.open()
        await _connect_protocol_ready(transport)
        await pad.send(held)
        start_count = len(transport.sent_interrupt_reports)

        await pad.tap(Button.A, duration=0)

        reports = transport.sent_interrupt_reports[start_count:]
        assert len(reports) == 2
        assert reports[0][3:6] == bytes.fromhex("08 00 80")
        assert reports[1][3:6] == bytes.fromhex("00 00 80")
        assert pad.snapshot() == held

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_tap_keeps_pressed_state_when_release_send_fails() -> None:
    class ExpectedReleaseError(RuntimeError):
        pass

    class FailSecondSendFakeHidTransport(FakeHidTransport):
        def __init__(self) -> None:
            super().__init__()
            self.send_count = 0
            self.fail_second_send = True

        async def send_interrupt(self, payload: bytes) -> None:
            if payload[0] != 0x30:
                await super().send_interrupt(payload)
                return
            self.send_count += 1
            if self.fail_second_send and self.send_count == 2:
                raise ExpectedReleaseError
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = FailSecondSendFakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        pressed = InputState.neutral().with_buttons([Button.A])

        await pad.open()
        await _connect_protocol_ready(transport)

        with pytest.raises(ExpectedReleaseError):
            await pad.tap(Button.A, duration=0)

        assert pad.snapshot() == pressed
        assert len(transport.sent_interrupt_reports) == 1
        assert transport.sent_interrupt_reports[0][3:6] == bytes.fromhex("08 00 00")

        transport.fail_second_send = False
        await pad.release(Button.A)
        assert pad.snapshot() == InputState.neutral()
        assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("00 00 00")

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_tap_serializes_concurrent_input_until_release() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        await pad.open()
        await _connect_protocol_ready(transport)

        tap = asyncio.create_task(pad.tap(Button.A, duration=0.02))
        await transport.wait_for_interrupt_report_count(1)
        press_b = asyncio.create_task(pad.press(Button.B))
        await asyncio.sleep(0)

        assert len(transport.sent_interrupt_reports) == 1

        await asyncio.gather(tap, press_b)
        reports = transport.sent_interrupt_reports
        assert [report[3:6] for report in reports] == [
            bytes.fromhex("08 00 00"),
            bytes.fromhex("00 00 00"),
            bytes.fromhex("04 00 00"),
        ]
        assert pad.snapshot().buttons == frozenset({Button.B})

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_subcommand_reply_uses_state_committed_by_prior_serialized_input() -> None:
    class BlockFirstSendFakeHidTransport(FakeHidTransport):
        def __init__(self) -> None:
            super().__init__()
            self.first_send_started = asyncio.Event()
            self.release_first_send = asyncio.Event()
            self.send_count = 0

        async def send_interrupt(self, payload: bytes) -> None:
            if payload[0] != 0x30:
                await super().send_interrupt(payload)
                return
            self.send_count += 1
            if self.send_count == 1:
                self.first_send_started.set()
                await self.release_first_send.wait()
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = BlockFirstSendFakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        state = InputState.neutral().with_buttons([Button.A])
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        await pad.open()
        await _connect_protocol_ready(transport)

        input_send = asyncio.create_task(pad.send(state))
        await asyncio.wait_for(transport.first_send_started.wait(), timeout=0.1)
        reply_send = asyncio.create_task(transport.inject_interrupt_data(request_device_info))
        await asyncio.sleep(0)

        transport.release_first_send.set()
        await asyncio.gather(input_send, reply_send)

        reports = transport.sent_interrupt_reports
        assert [report[0] for report in reports] == [0x30, 0x21]
        assert reports[1][1] == (reports[0][1] + 1) & 0xFF
        assert reports[1][3:6] == bytes.fromhex("08 00 00")

        await pad.close(neutral=False)

    asyncio.run(run())


def test_direct_close_controls_trailing_neutral_report() -> None:
    async def close_with(neutral: bool) -> tuple[FakeHidTransport, int]:
        transport = FakeHidTransport()
        pad = DirectProController._from_config(
            _SwitchGamepadConfig(),
            transport=transport,
        )
        held = InputState.neutral().with_buttons([Button.A])

        await pad.open()
        await _connect_protocol_ready(transport)
        await pad.send(held)
        before_close = len(transport.sent_interrupt_reports)
        await pad.close(neutral=neutral)

        assert pad.snapshot() == InputState.neutral()
        return transport, before_close

    async def run() -> None:
        neutral_transport, neutral_before = await close_with(True)
        assert len(neutral_transport.sent_interrupt_reports) == neutral_before + 1
        assert neutral_transport.sent_interrupt_reports[-1][0] == 0x30
        assert neutral_transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("00 00 00")
        assert neutral_transport.disconnect_request_sent_interrupt_count == neutral_before + 1

        unchanged_transport, unchanged_before = await close_with(False)
        assert len(unchanged_transport.sent_interrupt_reports) == unchanged_before
        assert unchanged_transport.disconnect_request_sent_interrupt_count == unchanged_before

    asyncio.run(run())


@pytest.mark.parametrize(
    ("controller_cls", "profile", "supported", "unsupported"),
    [
        (DirectProController, ProControllerProfile(), Button.A, Button.SL),
        (DirectJoyConL, JoyConLeftProfile(), Button.L, Button.A),
        (DirectJoyConR, JoyConRightProfile(), Button.R, Button.DPAD_LEFT),
    ],
)
def test_direct_controller_profiles_share_send_and_validation_contract(
    controller_cls: type[DirectProController | DirectJoyConL | DirectJoyConR],
    profile: ProControllerProfile | JoyConLeftProfile | JoyConRightProfile,
    supported: Button,
    unsupported: Button,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = controller_cls._from_config(
            _SwitchGamepadConfig(profile=profile),
            transport=transport,
        )
        await pad.open()
        await _connect_protocol_ready(transport)

        await pad.press(supported)
        before = pad.snapshot()

        with pytest.raises(UnsupportedInputError):
            await pad.press(unsupported)

        assert pad.snapshot() == before
        assert len(transport.sent_interrupt_reports) == 1

        await pad.close(neutral=False)

    asyncio.run(run())


def test_set_input_is_not_public_method() -> None:
    assert not hasattr(SwitchGamepad, "set_input")


def test_apply_reflects_left_and_right_sticks_in_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        state = InputState.neutral().with_sticks(
            left_stick=Stick.normalized(x=1.0, y=-1.0),
            right_stick=Stick.normalized(x=-1.0, y=1.0),
        )

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(state)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[6:9] == bytes.fromhex("ff 0f 00")
            assert report[9:12] == bytes.fromhex("00 f0 ff")

    asyncio.run(run())


def test_sticks_left_updates_only_left_stick_and_preserves_buttons_and_right_stick() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        right_stick = Stick.normalized(x=-1.0, y=1.0)
        initial = InputState.neutral().with_buttons([Button.A]).with_sticks(right_stick=right_stick)
        left_stick = Stick.normalized(x=1.0, y=-1.0)

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(initial)

            await pad.sticks(left=left_stick)

            assert pad.snapshot() == initial.with_sticks(left_stick=left_stick)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[3:6] == bytes.fromhex("08 00 00")
            assert report[6:9] == bytes.fromhex("ff 0f 00")
            assert report[9:12] == bytes.fromhex("00 f0 ff")

    asyncio.run(run())


def test_sticks_right_updates_only_right_stick_and_preserves_buttons_and_left_stick() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        left_stick = Stick.normalized(x=1.0, y=-1.0)
        initial = InputState.neutral().with_buttons([Button.B]).with_sticks(left_stick=left_stick)
        right_stick = Stick.normalized(x=-1.0, y=1.0)

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(initial)

            await pad.sticks(right=right_stick)

            assert pad.snapshot() == initial.with_sticks(right_stick=right_stick)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[3:6] == bytes.fromhex("04 00 00")
            assert report[6:9] == bytes.fromhex("ff 0f 00")
            assert report[9:12] == bytes.fromhex("00 f0 ff")

    asyncio.run(run())


def test_sticks_updates_left_and_right_in_same_committed_state() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        left_stick = Stick.normalized(x=1.0, y=-1.0)
        right_stick = Stick.normalized(x=-1.0, y=1.0)

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)

            await pad.sticks(left=left_stick, right=right_stick)

            assert pad.snapshot() == InputState.neutral().with_sticks(
                left_stick=left_stick,
                right_stick=right_stick,
            )

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[6:9] == bytes.fromhex("ff 0f 00")
            assert report[9:12] == bytes.fromhex("00 f0 ff")

    asyncio.run(run())


def test_lstick_updates_only_left_stick_and_preserves_buttons_and_right_stick() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        right_stick = Stick.right()
        initial = InputState.neutral().with_buttons([Button.A]).with_sticks(right_stick=right_stick)
        left_stick = Stick.up()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(initial)

            await pad.lstick(left_stick)

            assert pad.snapshot() == initial.with_sticks(left_stick=left_stick)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[3:6] == bytes.fromhex("08 00 00")
            assert report[6:9] == bytes.fromhex("00 f8 ff")
            assert report[9:12] == bytes.fromhex("ff 0f 80")

    asyncio.run(run())


def test_rstick_updates_only_right_stick_and_preserves_buttons_and_left_stick() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        left_stick = Stick.left()
        initial = InputState.neutral().with_buttons([Button.B]).with_sticks(left_stick=left_stick)
        right_stick = Stick.down()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(initial)

            await pad.rstick(right_stick)

            assert pad.snapshot() == initial.with_sticks(right_stick=right_stick)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[3:6] == bytes.fromhex("04 00 00")
            assert report[6:9] == bytes.fromhex("00 00 80")
            assert report[9:12] == bytes.fromhex("00 08 00")

    asyncio.run(run())


def test_sticks_rejects_tuple_inputs() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(InvalidInputError):
                await pad.sticks(left=cast("Stick", (0.0, 1.0)))

            with pytest.raises(InvalidInputError):
                await pad.sticks(right=cast("Stick", (0, 4095)))

    asyncio.run(run())


def test_lstick_and_rstick_reject_tuple_inputs() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(InvalidInputError):
                await pad.lstick(cast("Stick", (0.0, 1.0)))

            with pytest.raises(InvalidInputError):
                await pad.rstick(cast("Stick", (0, 4095)))

    asyncio.run(run())


def test_imu_updates_repeat_frame_and_preserves_buttons_and_sticks() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        left_stick = Stick.up()
        right_stick = Stick.right()
        initial = (
            InputState.neutral()
            .with_buttons([Button.A])
            .with_sticks(
                left_stick=left_stick,
                right_stick=right_stick,
            )
        )
        frame = IMUFrame.raw(accel=(1, -2, 4096), gyro=(100, -100, 0))
        enable_standard_imu = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 01")

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await transport.inject_interrupt_data(enable_standard_imu)
            await transport.wait_for_interrupt_report_id(0x21)
            await pad.apply(initial)

            await pad.imu(frame)

            assert pad.snapshot() == initial.with_imu(frame)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            report = reports[-1]

            assert report[3:6] == bytes.fromhex("08 00 00")
            assert report[6:9] == bytes.fromhex("00 f8 ff")
            assert report[9:12] == bytes.fromhex("ff 0f 80")
            assert report[13:49] == _imu_frame_bytes(frame) * 3

    asyncio.run(run())


def test_imu_updates_three_frames_in_order() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        frames = (
            IMUFrame.gyro(100, 0, 0),
            IMUFrame.gyro(120, 0, 0),
            IMUFrame.gyro(140, 0, 0),
        )
        enable_standard_imu = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 01")

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await transport.inject_interrupt_data(enable_standard_imu)
            await transport.wait_for_interrupt_report_id(0x21)

            await pad.imu(*frames)

            assert pad.snapshot() == InputState.neutral().with_imu(*frames)

            start_count = len(transport.sent_interrupt_reports)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)
            assert reports[-1][13:49] == b"".join(_imu_frame_bytes(frame) for frame in frames)

    asyncio.run(run())


def test_imu_rejects_invalid_frame_counts_and_types() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(InvalidInputError):
                await pad.imu()

            with pytest.raises(InvalidInputError):
                await pad.imu(IMUFrame.neutral(), IMUFrame.neutral())

            with pytest.raises(InvalidInputError):
                await pad.imu(*(IMUFrame.neutral(),) * 4)

            with pytest.raises(InvalidInputError):
                await pad.imu(cast("IMUFrame", Stick.center()))

    asyncio.run(run())


def test_state_update_apis_do_not_require_connection() -> None:
    async def run() -> None:
        pad = make_pro_controller(transport=FakeHidTransport())
        left_stick = Stick.normalized(x=0.0, y=1.0)
        right_stick = Stick.normalized(x=1.0, y=0.0)
        state = InputState.neutral().with_buttons([Button.X])

        await pad.press(Button.A)
        await pad.release(Button.A)
        await pad.sticks(left=left_stick)
        await pad.lstick(left_stick)
        await pad.rstick(right_stick)
        await pad.imu(IMUFrame.gyro(100, 0, 0))
        await pad.apply(state)
        await pad.neutral()

        assert pad.snapshot() == InputState.neutral()

    asyncio.run(run())


def test_joycon_left_press_rejects_unsupported_button_before_commit() -> None:
    async def run() -> None:
        pad = make_joycon_l(transport=FakeHidTransport())
        await pad.press(Button.L)
        before = pad.snapshot()

        with pytest.raises(UnsupportedInputError):
            await pad.press(Button.A)

        assert pad.snapshot() == before

    asyncio.run(run())


def test_joycon_right_press_rejects_unsupported_button_before_commit() -> None:
    async def run() -> None:
        pad = make_joycon_r(transport=FakeHidTransport())
        await pad.press(Button.R)
        before = pad.snapshot()

        with pytest.raises(UnsupportedInputError):
            await pad.press(Button.DPAD_LEFT)

        assert pad.snapshot() == before

    asyncio.run(run())


def test_joycon_left_rejects_right_stick_update_before_commit() -> None:
    async def run() -> None:
        pad = make_joycon_l(transport=FakeHidTransport())
        await pad.lstick(Stick.up())
        before = pad.snapshot()

        with pytest.raises(UnsupportedInputError):
            await pad.rstick(Stick.right())

        assert pad.snapshot() == before

    asyncio.run(run())


def test_joycon_right_rejects_left_stick_update_before_commit() -> None:
    async def run() -> None:
        pad = make_joycon_r(transport=FakeHidTransport())
        await pad.rstick(Stick.right())
        before = pad.snapshot()

        with pytest.raises(UnsupportedInputError):
            await pad.lstick(Stick.left())

        assert pad.snapshot() == before

    asyncio.run(run())


def test_joycon_apply_rejects_unsupported_state_before_commit() -> None:
    async def run() -> None:
        pad = make_joycon_l(transport=FakeHidTransport())
        await pad.apply(InputState.neutral().with_buttons([Button.L]))
        before = pad.snapshot()
        unsupported = InputState.neutral().with_buttons([Button.A])

        with pytest.raises(UnsupportedInputError):
            await pad.apply(unsupported)

        assert pad.snapshot() == before

    asyncio.run(run())


def test_state_update_apis_do_not_send_immediate_interrupt_reports() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport, report_period_us=60_000_000) as pad:
            await transport.connect()
            report_count = len(transport.sent_interrupt_reports)

            await pad.press(Button.A)
            await pad.release(Button.A)
            await pad.sticks(left=Stick.normalized(x=0.0, y=1.0))
            await pad.lstick(Stick.up())
            await pad.rstick(Stick.right())
            await pad.imu(IMUFrame.gyro(100, 0, 0))
            await pad.apply(InputState.neutral().with_buttons([Button.X]))
            await pad.neutral()

            assert len(transport.sent_interrupt_reports) == report_count

    asyncio.run(run())


def test_neutral_updates_snapshot_and_clears_next_periodic_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pressed = InputState.neutral().with_buttons([Button.A])

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.apply(pressed)
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("08 00 00")

            await pad.neutral()
            assert pad.snapshot() == InputState.neutral()

            neutral_count = len(transport.sent_interrupt_reports)
            neutral_reports = await transport.wait_for_interrupt_report_count(neutral_count + 1)
            assert neutral_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_output_report_injection_sends_subcommand_reply() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(transport=transport, report_period_us=1000):
            await transport.connect()

            await transport.inject_interrupt_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02

    asyncio.run(run())


def test_imu_mode_02_output_switches_periodic_input_to_quaternion_motion() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        enable_quaternion_imu = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 02")

        async with make_pro_controller(
            transport=transport,
            report_period_us=10_000_000,
        ) as pad:
            await _connect_protocol_ready(transport)
            await transport.inject_interrupt_data(enable_quaternion_imu)
            await transport.wait_for_interrupt_report_id(0x21)

            start_count = len(transport.sent_interrupt_reports)
            await pad.tap(Button.ZL, duration=0)
            reports = transport.sent_interrupt_reports[start_count:]

            assert reports[0][0] == 0x30
            assert reports[0][19] & 0x0F == 0x0E

    asyncio.run(run())


def test_imu_mode_01_ack_switches_next_input_to_standard_raw() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        enable_standard_imu = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 01")
        frames = (
            IMUFrame.raw(accel=(1, -2, 3), gyro=(-4, 5, -6)),
            IMUFrame.raw(accel=(7, -8, 9), gyro=(-10, 11, -12)),
            IMUFrame.raw(accel=(13, -14, 15), gyro=(-16, 17, -18)),
        )

        async with make_pro_controller(
            transport=transport,
            report_period_us=10_000_000,
        ) as pad:
            await _connect_protocol_ready(transport)
            await pad.imu(*frames)
            await transport.inject_interrupt_data(enable_standard_imu)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            start_count = len(transport.sent_interrupt_reports)
            await pad.tap(Button.ZL, duration=0)
            reports = transport.sent_interrupt_reports[start_count:]

            assert reply[14] == 0x40
            assert reports[0][0] == 0x30
            assert reports[0][13:49] == b"".join(_imu_frame_bytes(frame) for frame in frames)

    asyncio.run(run())


@pytest.mark.parametrize("imu_mode", [0x02, 0x03, 0x04, 0x05])
@pytest.mark.parametrize("controller_kind", ["pro", "left", "right"])
def test_quaternion_imu_modes_switch_all_profiles_to_mode_2_input(
    controller_kind: Literal["pro", "left", "right"],
    imu_mode: int,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        enable_quaternion_imu = bytes.fromhex(f"01 00 00 00 00 00 00 00 00 00 40 {imu_mode:02x}")
        if controller_kind == "pro":
            pad = make_pro_controller(transport=transport, report_period_us=10_000_000)
            trigger = Button.ZL
        elif controller_kind == "left":
            pad = make_joycon_l(transport=transport, report_period_us=10_000_000)
            trigger = Button.ZL
        else:
            pad = make_joycon_r(transport=transport, report_period_us=10_000_000)
            trigger = Button.ZR

        async with pad:
            await _connect_protocol_ready(transport)
            await pad.imu(IMUFrame.accel(0, 0, 4096))
            await transport.inject_interrupt_data(enable_quaternion_imu)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            start_count = len(transport.sent_interrupt_reports)
            await pad.tap(trigger, duration=0)
            reports = transport.sent_interrupt_reports[start_count:]

            assert reply[14] == 0x40
            assert reports[0][0] == 0x30
            assert reports[0][19] & 0x0F == 0x0E
            assert reports[0][48] >> 2 == 3

    asyncio.run(run())


def test_output_report_injection_uses_transport_bluetooth_address_for_device_info() -> None:
    async def run() -> None:
        transport = FakeHidTransport(local_bluetooth_address=bytes.fromhex("00 1b dc f9 9f 7d"))
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(transport=transport, report_period_us=1000):
            await transport.connect()

            await transport.inject_interrupt_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02
            assert reply[15:27] == bytes.fromhex("04 00 03 02 00 1b dc f9 9f 7d 03 02")

    asyncio.run(run())


def test_pair_refreshes_transport_bluetooth_address_after_advertising_for_device_info() -> None:
    class AdvertisingAddressTransport(FakeHidTransport):
        async def start_advertising(self) -> None:
            await super().start_advertising()
            self._local_bluetooth_address = bytes.fromhex("00 1b dc f9 9f 7d")

    async def run() -> None:
        transport = AdvertisingAddressTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            pairing = asyncio.create_task(pad.pair(timeout=1.0))
            await asyncio.sleep(0)

            assert transport.events == ("open", "start_advertising")

            await _connect_protocol_ready(transport)
            await asyncio.wait_for(pairing, timeout=0.1)

            await transport.inject_interrupt_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02
            assert reply[15:27] == bytes.fromhex("04 00 03 02 00 1b dc f9 9f 7d 03 02")

    asyncio.run(run())


def test_output_report_injection_uses_configured_controller_colors() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_controller_colors = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 10 50 60 00 00 0c")

        async with make_pro_controller(
            controller_colors=ControllerColors(
                body=0x112233,
                buttons=0x445566,
                left_grip=0x778899,
                right_grip=0xAABBCC,
            ),
            transport=transport,
            report_period_us=1000,
        ):
            await transport.connect()

            await transport.inject_interrupt_data(request_controller_colors)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x10
            assert reply[15:32] == bytes.fromhex(
                "50 60 00 00 0c 11 22 33 44 55 66 77 88 99 aa bb cc"
            )

    asyncio.run(run())


def test_output_report_injection_uses_default_controller_colors_when_none() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_controller_colors = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 10 50 60 00 00 0c")

        async with make_pro_controller(
            controller_colors=None,
            transport=transport,
            report_period_us=1000,
        ):
            await transport.connect()

            await transport.inject_interrupt_data(request_controller_colors)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x10
            assert reply[15:32] == bytes.fromhex(
                "50 60 00 00 0c 32 32 32 ff ff ff 00 b2 ff ff 3b 30"
            )

    asyncio.run(run())


def test_from_config_output_report_injection_uses_configured_controller_colors() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        config = _SwitchGamepadConfig(
            controller_colors=ControllerColors(
                body=0x102030,
                buttons=0x405060,
                left_grip=0x708090,
                right_grip=0xA0B0C0,
            ),
            report_period_us=1000,
        )
        request_controller_colors = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 10 50 60 00 00 0c")

        async with ProController._from_config(config, transport=transport):
            await transport.connect()

            await transport.inject_interrupt_data(request_controller_colors)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x10
            assert reply[15:32] == bytes.fromhex(
                "50 60 00 00 0c 10 20 30 40 50 60 70 80 90 a0 b0 c0"
            )

    asyncio.run(run())


def test_from_config_uses_profile_controller_colors_when_colors_are_unspecified() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        config = _SwitchGamepadConfig(
            profile=ProControllerProfile(
                controller_colors=ControllerColors(
                    body=0x010203,
                    buttons=0x040506,
                    left_grip=0x070809,
                    right_grip=0x0A0B0C,
                )
            ),
            controller_colors=None,
            report_period_us=1000,
        )
        request_controller_colors = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 10 50 60 00 00 0c")

        async with ProController._from_config(config, transport=transport):
            await transport.connect()

            await transport.inject_interrupt_data(request_controller_colors)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x10
            assert reply[15:32] == bytes.fromhex(
                "50 60 00 00 0c 01 02 03 04 05 06 07 08 09 0a 0b 0c"
            )

    asyncio.run(run())


@pytest.mark.parametrize(
    ("side", "expected_colors"),
    [
        ("left", "00 b2 ff 32 32 32 00 b2 ff 00 b2 ff"),
        ("right", "ff 3b 30 32 32 32 ff 3b 30 ff 3b 30"),
    ],
)
def test_joycon_uses_side_default_controller_colors_when_colors_are_unspecified(
    side: Literal["left", "right"],
    expected_colors: str,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_controller_colors = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 10 50 60 00 00 0c")

        async with _joycon_class(side)(
            controller_colors=None,
            transport=transport,
            report_period_us=1000,
        ):
            await transport.connect()

            await transport.inject_interrupt_data(request_controller_colors)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x10
            assert reply[15:32] == bytes.fromhex("50 60 00 00 0c " + expected_colors)

    asyncio.run(run())


def test_from_config_profile_reaches_periodic_input_report_builder() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        config = _SwitchGamepadConfig(
            profile=ProControllerProfile(battery_connection=0x92),
            report_period_us=1000,
        )

        async with ProController._from_config(config, transport=transport):
            await _connect_protocol_ready(transport)

            report = await transport.wait_for_interrupt_report_id(0x30)

            assert report[0] == 0x30
            assert report[2] == 0x92

    asyncio.run(run())


def test_from_config_joycon_profile_reaches_device_info_reply() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        config = _SwitchGamepadConfig(
            profile=JoyConLeftProfile(),
            report_period_us=1000,
        )
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with JoyConL._from_config(config, transport=transport):
            await transport.connect()

            await transport.inject_interrupt_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02
            assert reply[15:27] == bytes.fromhex("04 00 01 02 00 00 00 00 00 00 01 01")

    asyncio.run(run())


@pytest.mark.parametrize(
    ("side", "device_info"),
    [
        ("left", "04 00 01 02 00 00 00 00 00 00 01 01"),
        ("right", "04 00 02 02 00 00 00 00 00 00 01 01"),
    ],
)
def test_joycon_wrapper_reaches_device_info_reply(
    side: Literal["left", "right"],
    device_info: str,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with _joycon_class(side)(transport=transport, report_period_us=1000):
            await transport.connect()

            await transport.inject_interrupt_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02
            assert reply[15:27] == bytes.fromhex(device_info)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("side", "button_bytes"),
    [
        ("left", "00 00 30"),
        ("right", "30 00 00"),
    ],
)
def test_joycon_wrapper_sends_sr_sl_order_button_input(
    side: Literal["left", "right"],
    button_bytes: str,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with _joycon_class(side)(transport=transport, report_period_us=10_000_000) as pad:
            await _connect_protocol_ready(transport)

            start_count = len(transport.sent_interrupt_reports)
            await pad.tap(Button.SR, Button.SL, duration=0)
            reports = await transport.wait_for_interrupt_report_count(start_count + 2)

            press_report = reports[start_count]
            release_report = reports[start_count + 1]

            assert press_report[0] == 0x30
            assert press_report[3:6] == bytes.fromhex(button_bytes)
            assert release_report[0] == 0x30
            assert release_report[3:6] == b"\x00\x00\x00"
            assert pad.snapshot() == InputState.neutral()

    asyncio.run(run())


@pytest.mark.parametrize(
    ("side", "button_bytes"),
    [
        ("left", "00 00 30"),
        ("right", "30 00 00"),
    ],
)
def test_joycon_wrapper_holds_sr_sl_in_periodic_input(
    side: Literal["left", "right"],
    button_bytes: str,
) -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with _joycon_class(side)(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)

            start_count = len(transport.sent_interrupt_reports)
            await pad.press(Button.SR, Button.SL)
            reports = await transport.wait_for_interrupt_report_count(start_count + 1)

            hold_report = reports[start_count]
            assert hold_report[0] == 0x30
            assert hold_report[3:6] == bytes.fromhex(button_bytes)

            await pad.release(Button.SR, Button.SL)
            reports = await transport.wait_for_interrupt_report_count(start_count + 2)

            neutral_report = reports[start_count + 1]
            assert neutral_report[0] == 0x30
            assert neutral_report[3:6] == b"\x00\x00\x00"
            assert pad.snapshot() == InputState.neutral()

    asyncio.run(run())


def test_joycon_concrete_classes_have_no_invalid_side_path() -> None:
    for controller_cls in (JoyConL, JoyConR):
        assert "side" not in controller_cls.__init__.__annotations__


def test_control_output_report_injection_sends_subcommand_reply() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(transport=transport, report_period_us=1000):
            await transport.connect()

            await transport.inject_control_data(request_device_info)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[0] == 0x21
            assert reply[14] == 0x02

    asyncio.run(run())


def test_subcommand_reply_queue_takes_priority_over_periodic_input() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(transport=transport, report_period_us=100_000):
            await _connect_protocol_ready(transport)

            start_count = len(transport.sent_interrupt_reports)
            await transport.inject_interrupt_data(request_device_info)
            reports = await transport.wait_for_interrupt_report_count(start_count + 2)

            assert reports[start_count][0] == 0x21
            assert reports[start_count + 1][0] == 0x30

    asyncio.run(run())


def test_imu_mode_ack_precedes_first_periodic_input_in_the_new_format() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        enable_quaternion_imu = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 02")

        async with make_pro_controller(transport=transport, report_period_us=100_000) as pad:
            await _connect_protocol_ready(transport)
            await pad.imu(IMUFrame.accel(0, 0, 4096))

            start_count = len(transport.sent_interrupt_reports)
            await transport.inject_interrupt_data(enable_quaternion_imu)
            reports = await transport.wait_for_interrupt_report_count(start_count + 2)

            ack = reports[start_count]
            first_new_input = reports[start_count + 1]
            assert ack[0] == 0x21
            assert ack[14] == 0x40
            assert first_new_input[0] == 0x30
            assert first_new_input[19] & 0x0F == 0x0E

    asyncio.run(run())


def test_reopened_connection_does_not_inherit_host_requested_session_state() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=10_000_000,
        )
        set_report_mode = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 03 30")
        enable_quaternion_imu = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 02")
        enable_vibration = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 48 01")
        disable_vibration = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 48 00")

        await pad.open()
        await _connect_protocol_ready(transport)
        await transport.inject_interrupt_data(set_report_mode)
        await transport.inject_interrupt_data(enable_quaternion_imu)
        await transport.inject_interrupt_data(enable_vibration)
        await pad.close(neutral=True)

        await pad.open()
        await _connect_protocol_ready(transport)
        try:
            start_count = len(transport.sent_interrupt_reports)
            await pad.tap(Button.ZL, duration=0)
            first_new_input = transport.sent_interrupt_reports[start_count]

            assert first_new_input[0] == 0x30
            assert first_new_input[13:49] == bytes(36)

            await transport.inject_interrupt_data(disable_vibration)
            events = [json.loads(line) for line in trace.getvalue().splitlines()]
            session_events = [
                event for event in events if event["event"] == "subcommand_session_state"
            ]
            assert session_events[-1]["report_mode"] == "0x30"
            assert session_events[-1]["player_lights"] == "0x01"
            assert session_events[-1]["protocol_ready"] is True
            assert session_events[-1]["imu_mode"] == "0x00"
            assert session_events[-1]["imu_enabled"] is False
            assert session_events[-1]["vibration_enabled"] is False
        finally:
            await pad.close(neutral=True)

    asyncio.run(run())


def test_disconnect_neutralizes_input_without_changing_profile_spi_data() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport, report_period_us=10_000_000)
        read_factory_calibration = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 10 20 60 00 00 18")

        await pad.open()
        await transport.connect()
        await transport.inject_interrupt_data(read_factory_calibration)
        first_reply = transport.sent_interrupt_reports[-1]

        await pad.apply(
            InputState.neutral()
            .with_buttons([Button.A])
            .with_imu(IMUFrame.accel(0, 0, 4096).with_gyro(100, 200, 300))
        )
        await transport.disconnect(reason=0x13)

        assert pad.snapshot() == InputState.neutral()
        assert transport.is_open is False

        await pad.open()
        await transport.connect()
        try:
            await transport.inject_interrupt_data(read_factory_calibration)
            second_reply = transport.sent_interrupt_reports[-1]

            assert first_reply[15:44] == second_reply[15:44]
        finally:
            await pad.close(neutral=True)

    asyncio.run(run())


def test_report_tx_counter_distinguishes_0x21_and_0x30() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=1000,
        ) as pad:
            await _connect_protocol_ready(transport)
            await pad.press(Button.A)
            await transport.wait_for_interrupt_report_id(0x30)

            await transport.inject_interrupt_data(request_device_info)
            await transport.wait_for_interrupt_report_id(0x21)

        report_events = [
            json.loads(line)
            for line in trace.getvalue().splitlines()
            if json.loads(line)["event"] == "report_tx"
        ]

        assert {
            "event": "report_tx",
            "counter": 1,
            "reason": "periodic",
            "report_id": "0x30",
        } in report_events
        assert {
            "event": "report_tx",
            "counter": 1,
            "reason": "subcommand_reply",
            "report_id": "0x21",
        } in report_events

    asyncio.run(run())


def test_output_report_rx_and_subcommand_rx_share_packet_id() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 12 00 00 00 00 00 00 00 00 02")

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=1000,
        ):
            await transport.connect()
            await transport.inject_interrupt_data(request_device_info)
            await transport.wait_for_interrupt_report_id(0x21)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "output_report_rx",
            "length": 11,
            "packet_id": 0x12,
            "report_id": "0x01",
            "subcommand_id": "0x02",
        } in events
        assert {
            "event": "subcommand_rx",
            "packet_id": 0x12,
            "subcommand_id": "0x02",
        } in events
        assert {
            "event": "subcommand_reply_tx",
            "packet_id": 0x12,
            "report_id": "0x21",
            "subcommand_id": "0x02",
        } in events

    asyncio.run(run())


def test_output_report_injection_records_subcommand_session_state() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        request_report_mode = bytes.fromhex("01 21 00 01 40 40 00 01 40 40 03 3f")

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=1000,
        ):
            await _connect_protocol_ready(transport)
            await transport.inject_interrupt_data(request_report_mode)
            reply = await transport.wait_for_interrupt_report_id(0x21)

            assert reply[13] == 0x80
            assert reply[14] == 0x03

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "subcommand_session_state",
            "imu_enabled": False,
            "imu_encoding_format": "disabled",
            "imu_mode": "0x00",
            "packet_id": 0x21,
            "player_lights": "0x01",
            "protocol_ready": False,
            "report_mode": "0x3f",
            "report_mode_supported": False,
            "subcommand_id": "0x03",
            "unsupported_report_mode": "0x3f",
            "vibration_enabled": False,
        } in events

    asyncio.run(run())


def test_imu_mode_diagnostics_record_accepted_mode_and_encoding_format() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=10_000_000,
        )

        await pad.open()
        await transport.connect()
        await transport.inject_interrupt_data(bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 02"))
        await transport.inject_interrupt_data(bytes.fromhex("01 00 00 00 00 00 00 00 00 00 40 01"))
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        imu_events = [
            event
            for event in events
            if event["event"] == "subcommand_session_state" and event["subcommand_id"] == "0x40"
        ]

        assert [(event["imu_mode"], event["imu_encoding_format"]) for event in imu_events] == [
            ("0x02", "quaternion"),
            ("0x01", "standard"),
        ]
        assert all(not any("reset" in key for key in event) for event in imu_events)

    asyncio.run(run())


def test_status_returns_report_counters_last_subcommand_and_raw_rumble() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        request_device_info = bytes.fromhex("01 2a 10 11 12 13 14 15 16 17 02")

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.tap(Button.A, duration=0)

            await transport.inject_interrupt_data(request_device_info)
            await transport.wait_for_interrupt_report_id(0x21)

            status = pad.status()

            assert status.report_counters == {0x30: 2, 0x21: 3}
            assert status.last_subcommand_id == 0x02
            assert status.raw_rumble == bytes.fromhex("10 11 12 13 14 15 16 17")

    asyncio.run(run())


def test_close_with_neutral_records_trailing_neutral_report() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport, report_period_us=100_000)

        await pad.open()
        await _connect_protocol_ready(transport)
        await pad.press(Button.A)
        await pad.close(neutral=True)

        assert transport.is_open is False
        assert transport.sent_interrupt_reports[-1][0] == 0x30
        assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_connected_close_requests_disconnect_after_trailing_neutral() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        pad = make_pro_controller(transport=transport, report_period_us=100_000)

        await pad.open()
        await _connect_protocol_ready(transport)
        await pad.press(Button.A)

        await pad.close(neutral=True)

        assert transport.events == (
            "open",
            "connected",
            "interrupt_rx",
            "interrupt_rx",
            "request_disconnect",
            "disconnect_request_closed",
            "close",
        )
        assert transport.disconnect_request_sent_interrupt_count == 1
        assert transport.sent_interrupt_reports[-1][0] == 0x30
        assert transport.sent_interrupt_reports[-1][3:6] == bytes.fromhex("00 00 00")
        assert transport.close_count == 1

    asyncio.run(run())


def test_close_waits_for_disconnect_request_closed_event_once() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport(disconnect_request_auto_complete=False)
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=100_000,
        )

        await pad.open()
        await transport.connect()

        close_task = asyncio.create_task(pad.close(neutral=True))
        await transport.wait_for_disconnect_request()
        await asyncio.sleep(0)

        assert close_task.done() is False

        await transport.complete_disconnect_request(reason=0x13)
        await transport.complete_disconnect_request(reason=0x13)
        await asyncio.wait_for(close_task, timeout=0.1)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "disconnect_request",
            "status": "requested",
            "channels": ["control", "interrupt"],
        } in events
        assert {"event": "disconnect_request_terminal", "status": "closed"} in events
        assert transport.close_count == 1
        assert transport.events == (
            "open",
            "connected",
            "request_disconnect",
            "disconnect_request_closed",
            "close",
        )

    asyncio.run(run())


def test_close_request_disconnected_callback_leaves_final_close_to_user_close() -> None:
    async def run() -> None:
        close_wait = asyncio.Event()
        transport = FakeHidTransport(
            disconnect_request_auto_complete=False,
            close_wait=close_wait,
        )
        pad = make_pro_controller(transport=transport, report_period_us=100_000)

        await pad.open()
        await transport.connect()

        close_task = asyncio.create_task(pad.close(neutral=True))
        await transport.wait_for_disconnect_request()

        callback_task = asyncio.create_task(transport.complete_disconnect_request(reason=0x13))
        await asyncio.wait_for(callback_task, timeout=0.1)
        await transport.wait_for_close_start()

        assert close_task.done() is False
        assert transport.is_open is True
        assert transport.close_count == 0
        assert transport.events == (
            "open",
            "connected",
            "request_disconnect",
            "disconnect_request_closed",
        )

        close_wait.set()
        await asyncio.wait_for(close_task, timeout=0.1)

        assert transport.is_open is False
        assert transport.close_count == 1
        assert transport.events == (
            "open",
            "connected",
            "request_disconnect",
            "disconnect_request_closed",
            "close",
        )

    asyncio.run(run())


def test_close_request_timeout_records_terminal_state_and_closes_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport(disconnect_request_auto_complete=False)
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=100_000,
        )
        monkeypatch.setattr(gamepad_module, "DISCONNECT_REQUEST_TIMEOUT_SECONDS", 0.001)

        await pad.open()
        await transport.connect()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "disconnect_request",
            "status": "requested",
            "channels": ["control", "interrupt"],
        } in events
        assert {
            "event": "disconnect_request_terminal",
            "status": "timeout",
            "timeout": 0.001,
        } in events
        assert pad.status().connection_state == "closed"
        assert transport.close_count == 1
        assert transport.events == (
            "open",
            "connected",
            "request_disconnect",
            "close",
        )

    asyncio.run(run())


def test_close_without_connection_records_disconnect_unavailable() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        )

        await pad.open()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "disconnect_request",
            "status": "unavailable",
            "reason": "channels_not_connected",
        } in events
        assert transport.close_count == 1
        assert pad.status().connection_state == "closed"

    asyncio.run(run())


def test_close_when_transport_already_closed_records_disconnect_unavailable() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        )

        await pad.open()
        await transport.close()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "disconnect_request",
            "status": "unavailable",
            "reason": "transport_closed",
            "error_type": "ClosedError",
            "message": "fake transport is not open",
        } in events
        assert transport.close_count == 1
        assert pad.status().connection_state == "closed"

    asyncio.run(run())


def test_close_request_failure_records_failure_and_closes_transport() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport(disconnect_request_error=RuntimeError("request failed"))
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        )

        await pad.open()
        await transport.connect()
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "disconnect_request",
            "status": "failed",
            "error_type": "RuntimeError",
            "message": "request failed",
        } in events
        assert not any(event.get("event") == "disconnect_request_terminal" for event in events)
        assert transport.close_count == 1
        assert pad.status().connection_state == "closed"

    asyncio.run(run())


def test_close_treats_trailing_neutral_send_failure_as_best_effort() -> None:
    class NeutralSendError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("neutral failed")

    class FailInputFakeHidTransport(FakeHidTransport):
        async def send_interrupt(self, payload: bytes) -> None:
            if payload[0] == 0x30:
                raise NeutralSendError
            await super().send_interrupt(payload)

    async def run() -> None:
        trace = StringIO()
        transport = FailInputFakeHidTransport()
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=100_000,
        )

        await pad.open()
        await _connect_protocol_ready(transport)
        await pad.press(Button.A)
        await pad.close(neutral=True)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert pad.snapshot() == InputState.neutral()
        assert pad.status().connection_state == "closed"
        assert transport.close_count == 1
        assert {
            "event": "error",
            "error_type": "NeutralSendError",
            "message": "neutral failed",
            "recoverable": True,
        } in events

    asyncio.run(run())


def test_host_disconnect_racing_user_close_closes_once_and_neutralizes_state() -> None:
    async def run() -> None:
        transport = FakeHidTransport(disconnect_request_auto_complete=False)
        pad = make_pro_controller(transport=transport, report_period_us=100_000)

        await pad.open()
        await transport.connect()
        await pad.press(Button.A)

        close_task = asyncio.create_task(pad.close(neutral=True))
        await transport.wait_for_disconnect_request()
        await transport.disconnect(reason=0x13)
        await asyncio.wait_for(close_task, timeout=0.1)

        assert pad.snapshot() == InputState.neutral()
        assert pad.status().connection_state == "closed"
        assert transport.close_count == 1
        assert transport.events == (
            "open",
            "connected",
            "request_disconnect",
            "disconnected",
            "close",
        )

    asyncio.run(run())


def test_fake_l2cap_channels_must_both_open_before_connection_is_complete() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            await transport.open_l2cap_channel("control")
            await asyncio.sleep(0)

            assert pad.status().connection_state == "opened"

            await transport.open_l2cap_channel("interrupt")

            assert pad.status().connection_state == "initializing"

            await _complete_protocol_handshake(transport)

            assert pad.status().connection_state == "connected"
            assert transport.events[:4] == (
                "open",
                "l2cap_control_open",
                "l2cap_interrupt_open",
                "connected",
            )

    asyncio.run(run())


def test_disconnect_callback_neutralizes_state_and_stops_report_loop() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)
            await pad.press(Button.A)
            await transport.wait_for_interrupt_report_id(0x30)

            await transport.disconnect(reason=0x13)

            report_count = len(transport.sent_interrupt_reports)
            await asyncio.sleep(0.01)

            assert pad.snapshot() == InputState.neutral()
            assert pad.status().connection_state == "closed"
            assert transport.is_open is False
            assert transport.close_count == 1
            assert len(transport.sent_interrupt_reports) == report_count

    asyncio.run(run())


def test_disconnect_with_reconnect_disabled_records_closed_terminal_state() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport(bonded_peer_addresses=("01:02:03:04:05:06",))

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
            report_period_us=1000,
        ) as pad:
            await transport.connect()
            await transport.disconnect(reason=0x13)

            assert pad.status().connection_state == "closed"

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "reconnect_disabled",
            "next_state": "closed",
            "reason": 0x13,
        } in events
        assert "active_reconnect" not in transport.events
        assert "start_advertising" not in transport.events

    asyncio.run(run())


def test_pair_timeout_records_advertising_failure_position_in_trace() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            with pytest.raises(ConnectionTimeoutError):
                await pad.pair(timeout=0.001)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "connection_timeout",
            "observed_subcommands": [],
            "player_lights": None,
            "report_mode": None,
            "stage": "protocol_initialization",
            "state": "advertising",
            "timeout": 0.001,
        } in events
        assert transport.events == (
            "open",
            "start_advertising",
            "request_disconnect_unavailable",
            "close",
        )

    asyncio.run(run())


def test_pair_timeout_budget_includes_start_advertising() -> None:
    class BlockingAdvertisingFakeHidTransport(FakeHidTransport):
        async def start_advertising(self) -> None:
            await asyncio.Event().wait()

    async def run() -> None:
        transport = BlockingAdvertisingFakeHidTransport()
        pad = make_pro_controller(transport=transport)

        with pytest.raises(ConnectionTimeoutError):
            await pad.pair(timeout=0.001)

        assert transport.is_open is False
        assert pad.status().connection_state == "closed"

    asyncio.run(run())


@pytest.mark.parametrize(
    ("peer_addresses", "status", "selection"),
    [
        ((), "no_bond", "none"),
        (("01:02:03:04:05:06",), "connected", "selected"),
    ],
)
def test_reconnect_records_bonded_peer_selection_without_advertising(
    peer_addresses: tuple[str, ...],
    status: str,
    selection: str,
) -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport(
            bonded_peer_addresses=peer_addresses,
            active_reconnect_auto_connect=False,
        )

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            reconnect = asyncio.create_task(pad.try_reconnect(timeout=0.1))
            if peer_addresses:
                await _wait_for_transport_event(transport, "active_reconnect")
                await _connect_protocol_ready(transport)
            result = await reconnect

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert result.status == status
        assert {
            "event": "bonded_peers_discovered",
            "peer_count": len(peer_addresses),
            "selection": selection,
        } in events
        assert "start_advertising" not in transport.events

        if peer_addresses:
            assert result.peer_address == peer_addresses[0]
            assert {
                "event": "active_reconnect_attempt",
                "peer_address": peer_addresses[0],
                "route": "active_reconnect",
            } in events
            assert {
                "event": "active_reconnect_result",
                "peer_address": peer_addresses[0],
                "route": "active_reconnect",
                "status": "connected",
            } in events
            assert "active_reconnect" in transport.events

    asyncio.run(run())


def test_try_reconnect_raises_invalid_key_store_for_multiple_current_peers() -> None:
    async def run() -> None:
        transport = FakeHidTransport(
            bonded_peer_addresses=("01:02:03:04:05:06", "0a:0b:0c:0d:0e:0f"),
        )

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(InvalidKeyStoreError):
                await pad.try_reconnect(timeout=0.1)

        assert "active_reconnect" not in transport.events

    asyncio.run(run())


def test_connect_prefers_active_reconnect_when_one_bond_exists() -> None:
    async def run() -> None:
        trace = StringIO()
        peer_address = "01:02:03:04:05:06"
        transport = FakeHidTransport(
            bonded_peer_addresses=(peer_address,),
            active_reconnect_auto_connect=False,
        )

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            connecting = asyncio.create_task(pad.connect(timeout=0.1))
            await _wait_for_transport_event(transport, "active_reconnect")
            await _connect_protocol_ready(transport)
            await connecting

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert {
            "event": "active_reconnect_result",
            "peer_address": peer_address,
            "route": "active_reconnect",
            "status": "connected",
        } in events
        assert "active_reconnect" in transport.events
        assert "start_advertising" not in transport.events

    asyncio.run(run())


def test_try_connect_returns_pairing_result_when_no_bond_and_allowed() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            connect_task = asyncio.create_task(
                pad.try_connect(
                    timeout=1.0,
                    allow_pairing=True,
                )
            )
            await asyncio.sleep(0)

            assert transport.events == ("open", "start_advertising")

            await _connect_protocol_ready(transport)
            result = await asyncio.wait_for(connect_task, timeout=0.1)

        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert result.route == "pairing"
        assert result.status == "connected"
        assert {
            "event": "connect_pairing_fallback",
            "reason": "no_bond",
            "route": "pairing",
        } in events

    asyncio.run(run())


def test_connect_raises_when_no_bond_and_pairing_not_allowed() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(ConnectionFailedError):
                await pad.connect(timeout=0.1)

        assert "start_advertising" not in transport.events

    asyncio.run(run())


@pytest.mark.parametrize(
    "peer_addresses",
    [
        (),
    ],
)
def test_reconnect_raises_when_reconnect_does_not_connect(
    peer_addresses: tuple[str, ...],
) -> None:
    async def run() -> None:
        transport = FakeHidTransport(bonded_peer_addresses=peer_addresses)

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(ConnectionFailedError):
                await pad.reconnect(timeout=0.1)

    asyncio.run(run())


@pytest.mark.parametrize(
    (
        "active_reconnect_auto_connect",
        "active_reconnect_error",
        "status",
        "failure_reason",
        "extra_fields",
    ),
    [
        (
            True,
            asyncio.CancelledError("abort: disconnection event occurred."),
            "failed",
            "transport_error",
            {
                "error_type": "CancelledError",
                "message": "abort: disconnection event occurred.",
            },
        ),
        (
            True,
            RuntimeError("connection refused"),
            "failed",
            "transport_error",
            {"error_type": "RuntimeError", "message": "connection refused"},
        ),
        (
            False,
            None,
            "timeout",
            "connection_timeout",
            {},
        ),
    ],
)
def test_active_reconnect_failure_records_reason_without_advertising(
    active_reconnect_auto_connect: bool,
    active_reconnect_error: BaseException | None,
    status: str,
    failure_reason: str,
    extra_fields: dict[str, object],
) -> None:
    async def run() -> None:
        trace = StringIO()
        peer_address = "01:02:03:04:05:06"
        transport = FakeHidTransport(
            bonded_peer_addresses=(peer_address,),
            active_reconnect_auto_connect=active_reconnect_auto_connect,
            active_reconnect_error=active_reconnect_error,
        )

        async with make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        ) as pad:
            result = await pad.try_reconnect(timeout=0.001)
            assert pad.status().connection_state == "closed"

        events = [json.loads(line) for line in trace.getvalue().splitlines()]
        expected_event = {
            "event": "active_reconnect_result",
            "failure_reason": failure_reason,
            "peer_address": peer_address,
            "route": "active_reconnect",
            "status": status,
        }
        expected_event.update(extra_fields)

        assert result.status == status
        assert expected_event in events
        assert "active_reconnect" in transport.events
        assert "start_advertising" not in transport.events

    asyncio.run(run())


def test_active_reconnect_task_cancellation_propagates() -> None:
    async def run() -> None:
        peer_address = "01:02:03:04:05:06"
        transport = FakeHidTransport(
            bonded_peer_addresses=(peer_address,),
            active_reconnect_auto_connect=False,
        )

        async with make_pro_controller(transport=transport) as pad:
            reconnect_task = asyncio.create_task(pad.try_reconnect(timeout=None))
            for _ in range(5):
                if "active_reconnect" in transport.events:
                    break
                await asyncio.sleep(0)
            assert "active_reconnect" in transport.events

            reconnect_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await reconnect_task

    asyncio.run(run())


def test_concurrent_press_and_release_preserve_button_state() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport, report_period_us=1000) as pad:
            await _connect_protocol_ready(transport)

            await asyncio.gather(
                pad.press(Button.L),
                pad.press(Button.R),
                pad.press(Button.L, Button.R),
            )
            pressed_count = len(transport.sent_interrupt_reports)
            pressed_reports = await transport.wait_for_interrupt_report_count(pressed_count + 1)
            assert pressed_reports[-1][3:6] == bytes.fromhex("40 00 40")

            await asyncio.gather(
                pad.release(Button.L),
                pad.release(Button.R),
                pad.release(Button.L, Button.R),
            )
            released_count = len(transport.sent_interrupt_reports)
            released_reports = await transport.wait_for_interrupt_report_count(released_count + 1)
            assert released_reports[-1][3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_concurrent_press_waiting_on_state_lock_uses_latest_state() -> None:
    async def run() -> None:
        pad = make_pro_controller(transport=FakeHidTransport())
        state_lock = pad._state_store._lock

        await state_lock.acquire()
        try:
            press_left = asyncio.create_task(pad.press(Button.L))
            press_right = asyncio.create_task(pad.press(Button.R))
            await asyncio.sleep(0)

            assert press_left.done() is False
            assert press_right.done() is False
        finally:
            state_lock.release()

        await asyncio.gather(press_left, press_right)

        assert pad.snapshot() == InputState.neutral().with_buttons([Button.L, Button.R])

    asyncio.run(run())


def test_callback_exception_is_recorded_and_close_cleans_up() -> None:
    async def run() -> None:
        transport = FakeHidTransport()
        unsupported_subcommand = bytes.fromhex("01 00 00 00 00 00 00 00 00 00 ff")
        pad = make_pro_controller(transport=transport)

        await pad.open()
        await transport.connect()

        await transport.inject_interrupt_data(unsupported_subcommand)
        status = pad.status()

        assert status.connection_state == "failed"
        assert status.last_error is not None
        assert status.last_error.event == "error"
        assert status.last_error.error_type == "UnsupportedSubcommandError"

        await pad.close()
        assert transport.is_open is False

    asyncio.run(run())


def test_callback_exception_is_recorded_in_trace_and_status() -> None:
    async def run() -> None:
        trace = StringIO()
        transport = FakeHidTransport()
        unsupported_subcommand = bytes.fromhex("01 2a 00 00 00 00 00 00 00 00 ff 01 02")
        pad = make_pro_controller(
            diagnostics=DiagnosticsConfig(trace_writer=trace),
            transport=transport,
        )

        await pad.open()
        await transport.connect()

        await transport.inject_interrupt_data(unsupported_subcommand)

        status = pad.status()
        events = [json.loads(line) for line in trace.getvalue().splitlines()]

        assert status.connection_state == "failed"
        assert status.last_error is not None
        assert status.last_error.error_type == "UnsupportedSubcommandError"
        assert {
            "event": "unsupported_subcommand",
            "packet_id": 0x2A,
            "payload": "0102",
            "subcommand_id": "0xff",
        } in events
        assert {
            "event": "error",
            "error_type": "UnsupportedSubcommandError",
            "message": "unsupported subcommand: 0xff",
            "recoverable": False,
        } in events

        await pad.close()

    asyncio.run(run())


def test_tap_button_a_records_press_and_release_reports() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            await _connect_protocol_ready(transport)

            await pad.tap(Button.A, duration=0)

            assert len(transport.sent_interrupt_reports) == 2
            pressed, released = transport.sent_interrupt_reports
            assert pressed[0] == 0x30
            assert pressed[3:6] == bytes.fromhex("08 00 00")
            assert released[0] == 0x30
            assert released[3:6] == bytes.fromhex("00 00 00")

    asyncio.run(run())


def test_tap_releases_only_tapped_button_and_preserves_held_buttons() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            await _connect_protocol_ready(transport)
            await pad.press(Button.ZL)

            await pad.tap(Button.A, duration=0)

            assert pad.snapshot() == InputState.neutral().with_buttons([Button.ZL])
            assert len(transport.sent_interrupt_reports) == 2
            pressed, released = transport.sent_interrupt_reports
            assert pressed[3:6] == bytes.fromhex("08 00 80")
            assert released[3:6] == bytes.fromhex("00 00 80")

    asyncio.run(run())


def test_tap_before_connection_does_not_leave_pressed_state() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            with pytest.raises(ClosedError):
                await pad.tap(Button.A, duration=0)

            assert pad.snapshot() == InputState.neutral()

    asyncio.run(run())


def test_tap_send_failure_releases_pressed_state() -> None:
    class InputSendError(RuntimeError):
        def __init__(self) -> None:
            super().__init__("send failed")

    class FailInputFakeHidTransport(FakeHidTransport):
        async def send_interrupt(self, payload: bytes) -> None:
            if payload[0] == 0x30:
                raise InputSendError
            await super().send_interrupt(payload)

    async def run() -> None:
        transport = FailInputFakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            await _connect_protocol_ready(transport)

            with pytest.raises(RuntimeError, match="send failed"):
                await pad.tap(Button.A, duration=0)

            assert pad.snapshot() == InputState.neutral()

    asyncio.run(run())


def test_fake_connected_callback_sets_connected_status() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with make_pro_controller(transport=transport) as pad:
            await transport.connect()

            assert pad.status().connection_state == "initializing"

            await _complete_protocol_handshake(transport)

            assert pad.status().connection_state == "connected"
            assert transport.events == (
                "open",
                "connected",
                "interrupt_rx",
                "interrupt_rx",
            )

    asyncio.run(run())
