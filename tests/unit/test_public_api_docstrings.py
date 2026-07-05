"""Public API docstring contract tests."""

import inspect

from swbt import (
    AdapterDiscoveryError,
    AdapterInfo,
    DiagnosticsConfig,
    GamepadStatus,
    IMUFrame,
    InputState,
    Stick,
    SwitchGamepad,
    SwitchGamepadConfig,
    list_adapters,
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
        (
            AdapterInfo,
            (
                "name",
                "aliases",
                "vendor_id",
                "product_id",
                "manufacturer",
                "product",
                "serial_number",
            ),
        ),
        (
            AdapterDiscoveryError,
            ("platform", "backend", "libusb_available", "bumble_version"),
        ),
        (SwitchGamepadConfig, ("adapter", "key_store_path", "report_period_us", "device_name")),
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
        list_adapters,
        Stick.center,
        Stick.raw,
        Stick.normalized,
        Stick.tilt,
        Stick.up,
        Stick.down,
        Stick.left,
        Stick.right,
        IMUFrame.neutral,
        IMUFrame.raw,
        IMUFrame.gyro,
        IMUFrame.accel,
        IMUFrame.with_gyro,
        IMUFrame.with_accel,
        InputState.neutral,
        InputState.with_imu,
        InputState.with_gyro,
        InputState.with_accel,
    ):
        _assert_doc_contains(factory, "Returns:")

    _assert_doc_contains(list_adapters, "Raises:", "AdapterDiscoveryError")


def test_switch_gamepad_docstrings_describe_public_arguments_results_and_errors() -> None:
    _assert_doc_contains(
        SwitchGamepad.__init__,
        "Args:",
        "adapter",
        "key_store_path",
        "report_period_us",
        "device_name",
        "diagnostics",
        "transport",
    )

    expected_method_tokens: tuple[tuple[object, tuple[str, ...]], ...] = (
        (SwitchGamepad.__aenter__, ("Returns:", "SwitchGamepad")),
        (SwitchGamepad.open, ("Raises:", "TransportOpenError")),
        (SwitchGamepad.from_config, ("Args:", "config", "Returns:", "SwitchGamepad")),
        (
            SwitchGamepad.pair,
            ("Args:", "timeout", "Raises:", "ConnectionTimeoutError"),
        ),
        (SwitchGamepad.reconnect, ("Args:", "timeout", "Raises:", "ConnectionFailedError")),
        (SwitchGamepad.try_reconnect, ("Args:", "timeout", "Returns:", "ConnectionResult")),
        (
            SwitchGamepad.connect,
            ("Args:", "timeout", "allow_pairing", "Raises:", "ConnectionFailedError"),
        ),
        (
            SwitchGamepad.try_connect,
            ("Args:", "timeout", "allow_pairing", "Returns:", "ConnectionResult"),
        ),
        (SwitchGamepad.close, ("Args:", "neutral")),
        (SwitchGamepad.press, ("Args:", "buttons", "does not send")),
        (SwitchGamepad.apply, ("Args:", "state", "does not send")),
        (SwitchGamepad.sticks, ("Args:", "left", "right", "does not send")),
        (SwitchGamepad.lstick, ("Args:", "stick", "left stick", "does not send")),
        (SwitchGamepad.rstick, ("Args:", "stick", "right stick", "does not send")),
        (SwitchGamepad.imu, ("Args:", "frames", "IMU", "does not send")),
        (SwitchGamepad.release, ("Args:", "buttons", "does not send")),
        (SwitchGamepad.neutral, ("InputState.neutral()", "without immediate transmission")),
        (
            SwitchGamepad.tap,
            ("Args:", "buttons", "duration", "Raises:", "ClosedError", "immediate", "preserving"),
        ),
        (SwitchGamepad.status, ("Returns:", "GamepadStatus")),
        (SwitchGamepad.snapshot, ("Returns:", "InputState")),
    )

    for method, tokens in expected_method_tokens:
        _assert_doc_contains(method, *tokens)
