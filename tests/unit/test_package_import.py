"""Package import smoke tests."""

import swbt


def test_package_exports_public_gamepad_surface() -> None:
    assert swbt.__all__ == (
        "Button",
        "DiagnosticsConfig",
        "GamepadStatus",
        "IMUFrame",
        "InputState",
        "Stick",
        "SwitchGamepad",
        "SwitchGamepadConfig",
    )
