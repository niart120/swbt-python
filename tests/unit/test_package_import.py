"""Package import smoke tests."""

import pytest

import swbt

REARCHITECTURE_TARGET_XFAIL_REASON = (
    "target boundary fixed before implementation; unit_040 makes this green"
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
        "JoyCon",
        "Stick",
        "SwbtError",
        "SwitchGamepad",
        "SwitchGamepadConfig",
        "TransportOpenError",
        "UnsupportedInputError",
        "list_adapters",
    )


@pytest.mark.xfail(reason=REARCHITECTURE_TARGET_XFAIL_REASON, strict=True)
def test_rearchitecture_target_root_exports_controller_api() -> None:
    public_exports = set(swbt.__all__)

    assert {
        "JoyConL",
        "JoyConR",
        "ProController",
        "SwitchGamepad",
    }.issubset(public_exports)
    assert {
        "HidDeviceTransport",
        "JoyCon",
        "SwitchGamepadConfig",
    }.isdisjoint(public_exports)
