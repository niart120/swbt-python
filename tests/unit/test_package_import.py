"""Package import smoke tests."""

import swbt


def test_package_exports_public_gamepad_surface() -> None:
    assert swbt.__all__ == (
        "AdapterDiscoveryError",
        "AdapterIdentityRecoveryRequired",
        "AdapterInfo",
        "Button",
        "ClosedError",
        "ConnectionFailedError",
        "ConnectionResult",
        "ConnectionTimeoutError",
        "ControllerColors",
        "DiagnosticsConfig",
        "DirectJoyConL",
        "DirectJoyConR",
        "DirectProController",
        "DirectSwitchGamepad",
        "GamepadStatus",
        "IMUFrame",
        "InputState",
        "InvalidInputError",
        "InvalidKeyStoreError",
        "InvalidProfileError",
        "JoyConL",
        "JoyConR",
        "PeriodicSwitchGamepad",
        "ProController",
        "ProfileControllerMismatchError",
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
        "DirectJoyConL",
        "DirectJoyConR",
        "DirectProController",
        "DirectSwitchGamepad",
        "JoyConL",
        "JoyConR",
        "ProController",
        "PeriodicSwitchGamepad",
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
