"""Internal gamepad constructors for tests that inject fake transports."""

from swbt import (
    ControllerColors,
    DiagnosticsConfig,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    JoyConL,
    JoyConR,
    ProController,
)
from swbt.gamepad._config import _SwitchGamepadConfig
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.transport.base import HidDeviceTransport


def make_pro_controller(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    key_store_path: str | None = None,
    report_period_us: int | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
) -> ProController:
    """Create a Pro Controller with an injected internal transport for tests."""
    return ProController._from_config(
        _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        ),
        diagnostics=diagnostics,
        transport=transport,
    )


def make_joycon_l(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    key_store_path: str | None = None,
    report_period_us: int | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
) -> JoyConL:
    """Create a Joy-Con L with an injected internal transport for tests."""
    return JoyConL._from_config(
        _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            profile=JoyConLeftProfile(),
        ),
        diagnostics=diagnostics,
        transport=transport,
    )


def make_joycon_r(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    key_store_path: str | None = None,
    report_period_us: int | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
) -> JoyConR:
    """Create a Joy-Con R with an injected internal transport for tests."""
    return JoyConR._from_config(
        _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            profile=JoyConRightProfile(),
        ),
        diagnostics=diagnostics,
        transport=transport,
    )


def make_direct_pro_controller(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    key_store_path: str | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
) -> DirectProController:
    """Create a Direct Pro Controller with an injected transport for tests."""
    return DirectProController._from_config(
        _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            controller_colors=controller_colors,
        ),
        diagnostics=diagnostics,
        transport=transport,
    )


def make_direct_joycon_l(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    key_store_path: str | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
) -> DirectJoyConL:
    """Create a Direct Joy-Con L with an injected transport for tests."""
    return DirectJoyConL._from_config(
        _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            controller_colors=controller_colors,
            profile=JoyConLeftProfile(),
        ),
        diagnostics=diagnostics,
        transport=transport,
    )


def make_direct_joycon_r(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    key_store_path: str | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
) -> DirectJoyConR:
    """Create a Direct Joy-Con R with an injected transport for tests."""
    return DirectJoyConR._from_config(
        _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            controller_colors=controller_colors,
            profile=JoyConRightProfile(),
        ),
        diagnostics=diagnostics,
        transport=transport,
    )
