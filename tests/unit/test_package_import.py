"""Package import smoke tests."""

import swbt


def test_package_exports_public_gamepad_surface() -> None:
    assert swbt.__all__ == (
        "AdapterDiscoveryError",
        "AdapterInfo",
        "Button",
        "ClosedError",
        "ConnectionFailedError",
        "ConnectionResult",
        "ConnectionTimeoutError",
        "ControllerColors",
        "DiagnosticsConfig",
        "GamepadStatus",
        "IMUFrame",
        "InputState",
        "InvalidInputError",
        "InvalidKeyStoreError",
        "JoyConL",
        "JoyConR",
        "ProController",
        "Stick",
        "SwbtError",
        "SwitchGamepad",
        "TransportOpenError",
        "UnsupportedInputError",
        "list_adapters",
    )


def test_rearchitecture_target_root_exports_controller_api() -> None:
    public_exports = set(swbt.__all__)

    assert {
        "JoyConL",
        "JoyConR",
        "ProController",
        "SwitchGamepad",
    }.issubset(public_exports)
    assert "JoyCon" not in public_exports


def test_rearchitecture_target_root_hides_internal_transport_type() -> None:
    public_exports = set(swbt.__all__)

    assert "HidDeviceTransport" not in public_exports
    assert "DisconnectRequestResult" not in public_exports
    assert "BondedPeer" not in public_exports


def test_rearchitecture_target_root_hides_internal_config_type() -> None:
    public_exports = set(swbt.__all__)

    assert "SwitchGamepadConfig" not in public_exports
