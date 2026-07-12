"""Public API docstring contract tests."""

import inspect
from collections.abc import Callable
from dataclasses import fields, is_dataclass

import swbt
from swbt import (
    AdapterDiscoveryError,
    AdapterInfo,
    ControllerColors,
    DiagnosticsConfig,
    GamepadStatus,
    IMUFrame,
    InputState,
    JoyConL,
    JoyConR,
    ProController,
    Stick,
    SwitchGamepad,
    UnsupportedInputError,
    list_adapters,
)
from swbt.gamepad import ConnectionResult


def _explicit_parameters(callable_obj: Callable[..., object]) -> tuple[str, ...]:
    return tuple(
        parameter.name
        for parameter in inspect.signature(callable_obj).parameters.values()
        if parameter.name not in {"self", "cls"}
        and parameter.kind
        not in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }
    )


def _assert_doc_contains(obj: object, *tokens: str) -> None:
    doc = inspect.getdoc(obj)

    assert doc is not None
    missing = [token for token in tokens if token not in doc]
    assert not missing, f"{obj!r} docstring is missing: {missing}"


def test_root_public_api_docstrings_list_google_style_arguments() -> None:
    for public_name in swbt.__all__:
        public_obj = getattr(swbt, public_name)

        if is_dataclass(public_obj):
            _assert_doc_contains(
                public_obj,
                "Args:",
                *(field.name for field in fields(public_obj)),
            )
            continue

        if inspect.isfunction(public_obj):
            parameters = _explicit_parameters(public_obj)
            if parameters:
                _assert_doc_contains(public_obj, "Args:", *parameters)
            continue

        if inspect.isclass(public_obj):
            parameters = _explicit_parameters(public_obj.__init__)
            if parameters:
                _assert_doc_contains(public_obj.__init__, "Args:", *parameters)


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
        (ControllerColors, ("body", "buttons", "left_grip", "right_grip")),
    ):
        _assert_doc_contains(cls, "Args:", "Attributes:", *attributes)

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
        IMUFrame.gyro_rate,
        IMUFrame.accel,
        IMUFrame.accel_g,
        IMUFrame.with_gyro,
        IMUFrame.with_gyro_rate,
        IMUFrame.with_accel,
        IMUFrame.with_accel_g,
        IMUFrame.to_gyro_rate,
        IMUFrame.to_accel_g,
        InputState.neutral,
        InputState.with_imu,
        InputState.with_gyro,
        InputState.with_accel,
        ControllerColors.to_spi_bytes,
    ):
        _assert_doc_contains(factory, "Returns:")

    _assert_doc_contains(list_adapters, "Raises:", "AdapterDiscoveryError")


def test_imu_gyro_rate_docstrings_describe_units_scale_and_range_errors() -> None:
    for method in (IMUFrame.gyro_rate, IMUFrame.with_gyro_rate):
        _assert_doc_contains(
            method,
            "Args:",
            "x_rad_s",
            "y_rad_s",
            "z_rad_s",
            "radians per second",
            "0.070 dps/raw",
            "Raises:",
            "InvalidInputError",
        )

    _assert_doc_contains(
        IMUFrame.to_gyro_rate,
        "Returns:",
        "radians per second",
        "0.070 dps/raw",
    )


def test_imu_accel_g_docstrings_describe_units_scale_and_range_errors() -> None:
    for method in (IMUFrame.accel_g, IMUFrame.with_accel_g):
        _assert_doc_contains(
            method,
            "Args:",
            "x_g",
            "y_g",
            "z_g",
            "1/4096 G/raw",
            "Raises:",
            "InvalidInputError",
        )

    _assert_doc_contains(IMUFrame.to_accel_g, "Returns:", "1/4096 G/raw")


def test_public_error_docstrings_describe_constructor_arguments() -> None:
    _assert_doc_contains(
        AdapterDiscoveryError.__init__,
        "Args:",
        "message",
        "platform",
        "backend",
        "libusb_available",
        "bumble_version",
    )
    _assert_doc_contains(
        UnsupportedInputError.__init__,
        "Args:",
        "message",
        "profile_kind",
        "buttons",
        "sticks",
    )


def test_switch_gamepad_docstrings_describe_public_arguments_results_and_errors() -> None:
    _assert_doc_contains(SwitchGamepad, "abstract", "ProController", "JoyConL", "JoyConR")

    expected_method_tokens: tuple[tuple[object, tuple[str, ...]], ...] = (
        (SwitchGamepad.__aenter__, ("Returns:", "SwitchGamepad")),
        (SwitchGamepad.__aexit__, ("Args:", "exc_type", "exc", "traceback")),
        (SwitchGamepad.open, ("Open", "transport", "Raises:")),
        (
            SwitchGamepad.pair,
            ("pairing", "connection", "Args:", "timeout", "Raises:"),
        ),
        (SwitchGamepad.reconnect, ("Reconnect", "bonded peer", "Args:", "timeout", "Raises:")),
        (
            SwitchGamepad.try_reconnect,
            ("Try", "bonded peer", "Args:", "timeout", "Returns:", "ConnectionResult"),
        ),
        (
            SwitchGamepad.connect,
            ("Connect", "pairing fallback", "Args:", "timeout", "allow_pairing", "Raises:"),
        ),
        (
            SwitchGamepad.try_connect,
            (
                "Try",
                "pairing fallback",
                "Args:",
                "timeout",
                "allow_pairing",
                "Returns:",
                "ConnectionResult",
            ),
        ),
        (SwitchGamepad.close, ("Close", "transport", "Args:", "neutral")),
        (SwitchGamepad.press, ("buttons", "input state", "Args:", "buttons")),
        (SwitchGamepad.apply, ("input state", "Args:", "state")),
        (SwitchGamepad.sticks, ("stick positions", "Args:", "left", "right")),
        (SwitchGamepad.lstick, ("left stick", "Args:", "stick")),
        (SwitchGamepad.rstick, ("right stick", "Args:", "stick")),
        (SwitchGamepad.imu, ("IMU", "Args:", "frames")),
        (SwitchGamepad.release, ("buttons", "input state", "Args:", "buttons")),
        (SwitchGamepad.neutral, ("InputState.neutral()", "without immediate transmission")),
        (
            SwitchGamepad.tap,
            ("connected button action", "Args:", "buttons", "duration", "Raises:"),
        ),
        (SwitchGamepad.status, ("gamepad status", "Returns:", "GamepadStatus")),
        (SwitchGamepad.snapshot, ("input state", "Returns:", "InputState")),
    )

    for method, tokens in expected_method_tokens:
        _assert_doc_contains(method, *tokens)


def test_concrete_controller_docstrings_describe_constructor_arguments() -> None:
    _assert_doc_contains(
        ProController.__init__,
        "Args:",
        "adapter",
        "key_store_path",
        "report_period_us",
        "controller_colors",
        "diagnostics",
        "Raises:",
        "InvalidInputError",
    )
    pro_constructor_doc = inspect.getdoc(ProController.__init__)
    assert pro_constructor_doc is not None
    assert "device_name" not in pro_constructor_doc
    assert "transport:" not in pro_constructor_doc
    assert "Optional HID transport instance" not in pro_constructor_doc

    for controller_cls in (JoyConL, JoyConR):
        _assert_doc_contains(
            controller_cls.__init__,
            "Args:",
            "adapter",
            "key_store_path",
            "report_period_us",
            "controller_colors",
            "diagnostics",
            "Raises:",
            "InvalidInputError",
        )
        constructor_doc = inspect.getdoc(controller_cls.__init__)
        assert constructor_doc is not None
        assert "device_name" not in constructor_doc
        assert "transport:" not in constructor_doc
        assert "Optional HID transport instance" not in constructor_doc
