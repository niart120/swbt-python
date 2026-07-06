"""Public API docstring contract tests."""

import inspect

from swbt import (
    AdapterDiscoveryError,
    AdapterInfo,
    BondedPeer,
    ControllerColors,
    DiagnosticsConfig,
    DisconnectRequestResult,
    GamepadStatus,
    HidDeviceTransport,
    IMUFrame,
    InputState,
    JoyConL,
    JoyConR,
    ProController,
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
        (DisconnectRequestResult, ("status", "channels", "reason", "error_type", "message")),
        (BondedPeer, ("address",)),
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
        (
            SwitchGamepadConfig,
            ("adapter", "key_store_path", "report_period_us", "device_name", "controller_colors"),
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
        "transport",
        "Raises:",
        "InvalidInputError",
    )
    pro_constructor_doc = inspect.getdoc(ProController.__init__)
    assert pro_constructor_doc is not None
    assert "device_name" not in pro_constructor_doc

    for controller_cls in (JoyConL, JoyConR):
        _assert_doc_contains(
            controller_cls.__init__,
            "Args:",
            "adapter",
            "key_store_path",
            "report_period_us",
            "controller_colors",
            "diagnostics",
            "transport",
            "Raises:",
            "InvalidInputError",
        )
        constructor_doc = inspect.getdoc(controller_cls.__init__)
        assert constructor_doc is not None
        assert "device_name" not in constructor_doc

    for factory in (ProController.from_config, JoyConL.from_config, JoyConR.from_config):
        _assert_doc_contains(
            factory,
            "Args:",
            "config",
            "diagnostics",
            "transport",
            "Returns:",
            "Raises:",
            "InvalidInputError",
        )

    pro_from_config_doc = inspect.getdoc(ProController.from_config)
    assert pro_from_config_doc is not None
    assert "_RuntimeBackedGamepad" not in pro_from_config_doc


def test_transport_extension_docstrings_describe_public_arguments() -> None:
    expected_method_tokens: tuple[tuple[object, tuple[str, ...]], ...] = (
        (HidDeviceTransport.open, ("Open", "Raises:")),
        (HidDeviceTransport.start_advertising, ("host-discoverable", "Raises:")),
        (HidDeviceTransport.close, ("Close", "transport resources")),
        (HidDeviceTransport.request_disconnect, ("Returns:", "DisconnectRequestResult")),
        (HidDeviceTransport.local_bluetooth_address, ("Returns:", "bytes | None")),
        (
            HidDeviceTransport.list_bonded_peers,
            ("Returns:", "BondedPeer", "Raises:", "InvalidKeyStoreError"),
        ),
        (
            HidDeviceTransport.connect_bonded_peer,
            ("Args:", "peer_address", "connect_timeout", "Raises:"),
        ),
        (HidDeviceTransport.send_interrupt, ("Args:", "payload", "Raises:")),
        (HidDeviceTransport.send_control, ("Args:", "payload", "Raises:")),
        (HidDeviceTransport.on_interrupt_data, ("Args:", "callback")),
        (HidDeviceTransport.on_control_data, ("Args:", "callback")),
        (HidDeviceTransport.on_connected, ("Args:", "callback")),
        (HidDeviceTransport.on_disconnected, ("Args:", "callback")),
    )

    for method, tokens in expected_method_tokens:
        _assert_doc_contains(method, *tokens)
