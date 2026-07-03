"""Public API docstring contract tests."""

import inspect

from swbt import (
    DiagnosticsConfig,
    GamepadStatus,
    IMUFrame,
    InputState,
    Stick,
    SwitchGamepad,
    SwitchGamepadConfig,
)
from swbt.gamepad import ConnectionResult


def _assert_doc_contains(obj: object, *tokens: str) -> None:
    doc = inspect.getdoc(obj)

    assert doc is not None
    missing = [token for token in tokens if token not in doc]
    assert not missing, f"{obj!r} docstring is missing: {missing}"


def test_public_value_object_docstrings_describe_attributes_and_factory_returns() -> None:
    for cls, attributes in (
        (ConnectionResult, ("route", "status", "peer_address", "peer_count")),
        (SwitchGamepadConfig, ("adapter", "report_period_us", "device_name", "key_store_path")),
        (DiagnosticsConfig, ("trace_writer",)),
        (
            GamepadStatus,
            (
                "connection_state",
                "report_counters",
                "last_subcommand_id",
                "raw_rumble",
                "last_error",
            ),
        ),
        (Stick, ("x", "y")),
        (IMUFrame, ("accel_x", "accel_y", "accel_z", "gyro_x", "gyro_y", "gyro_z")),
        (InputState, ("buttons", "left_stick", "right_stick", "imu_frames")),
    ):
        _assert_doc_contains(cls, "Attributes:", *attributes)

    for factory in (
        Stick.center,
        Stick.raw,
        Stick.normalized,
        IMUFrame.neutral,
        InputState.neutral,
    ):
        _assert_doc_contains(factory, "Returns:")


def test_switch_gamepad_docstrings_describe_public_arguments_results_and_errors() -> None:
    _assert_doc_contains(
        SwitchGamepad.__init__,
        "Args:",
        "adapter",
        "report_period_us",
        "device_name",
        "key_store_path",
        "diagnostics",
        "transport",
    )

    expected_method_tokens: tuple[tuple[object, tuple[str, ...]], ...] = (
        (SwitchGamepad.__aenter__, ("Returns:", "SwitchGamepad")),
        (SwitchGamepad.open, ("Raises:", "TransportOpenError")),
        (SwitchGamepad.pair, ("Args:", "timeout", "Raises:", "ConnectionTimeoutError")),
        (SwitchGamepad.reconnect, ("Args:", "timeout", "Returns:", "ConnectionResult")),
        (
            SwitchGamepad.connect,
            ("Args:", "timeout", "allow_pairing", "Returns:", "ConnectionResult"),
        ),
        (SwitchGamepad.close, ("Args:", "neutral")),
        (SwitchGamepad.press, ("Args:", "buttons")),
        (SwitchGamepad.set_input, ("Args:", "state")),
        (SwitchGamepad.release, ("Args:", "buttons")),
        (SwitchGamepad.neutral, ("InputState.neutral()",)),
        (SwitchGamepad.tap, ("Args:", "buttons", "duration", "Raises:", "ClosedError")),
        (SwitchGamepad.status, ("Returns:", "GamepadStatus")),
        (SwitchGamepad.snapshot, ("Returns:", "InputState")),
    )

    for method, tokens in expected_method_tokens:
        _assert_doc_contains(method, *tokens)
