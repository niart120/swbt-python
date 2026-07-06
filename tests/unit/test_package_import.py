"""Package import smoke tests."""

import pytest

import swbt

REARCHITECTURE_TARGET_XFAIL_REASON = (
    "target boundary fixed before implementation; unit_042 makes this green"
)


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


@pytest.mark.xfail(reason=REARCHITECTURE_TARGET_XFAIL_REASON, strict=True)
def test_rearchitecture_target_root_hides_internal_transport_type() -> None:
    public_exports = set(swbt.__all__)

    assert "HidDeviceTransport" not in public_exports


def test_rearchitecture_target_root_hides_internal_config_type() -> None:
    public_exports = set(swbt.__all__)

    assert "SwitchGamepadConfig" not in public_exports
