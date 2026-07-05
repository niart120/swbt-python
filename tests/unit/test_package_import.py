"""Package import smoke tests."""

import swbt


def test_package_exports_public_gamepad_surface() -> None:
    assert swbt.__all__ == (
        "AdapterDiscoveryError",
        "AdapterInfo",
        "BondedPeer",
        "Button",
        "ClosedError",
        "ConnectionFailedError",
        "ConnectionResult",
        "ConnectionTimeoutError",
        "ControllerColors",
        "DiagnosticsConfig",
        "DisconnectRequestResult",
        "GamepadStatus",
        "HidDeviceTransport",
        "IMUFrame",
        "InputState",
        "InvalidInputError",
        "InvalidKeyStoreError",
        "Stick",
        "SwbtError",
        "SwitchGamepad",
        "SwitchGamepadConfig",
        "TransportOpenError",
        "list_adapters",
    )
