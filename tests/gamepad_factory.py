"""Gamepad constructors that inject fake transports through the runtime boundary."""

from collections.abc import Callable
from contextlib import nullcontext
from functools import partial
from unittest.mock import patch

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
from swbt.gamepad import core as gamepad_core
from swbt.gamepad.runtime import ControllerRuntime
from swbt.protocol.profiles.base import ControllerProfile
from swbt.transport.base import HidDeviceTransport

type _PeriodicController = ProController | JoyConL | JoyConR
type _DirectController = DirectProController | DirectJoyConL | DirectJoyConR


def _construct_with_transport[ControllerT: _PeriodicController | _DirectController](
    controller_type: type[ControllerT],
    *,
    transport: HidDeviceTransport,
    profile: ControllerProfile | None,
    constructor: Callable[[], ControllerT],
) -> ControllerT:
    runtime_constructor = partial(ControllerRuntime, transport=transport)
    profile_patch = (
        nullcontext() if profile is None else patch.object(controller_type, "_profile", profile)
    )
    with (
        profile_patch,
        patch.object(gamepad_core, "ControllerRuntime", runtime_constructor),
    ):
        return constructor()


def make_pro_controller(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    profile_path: str | None = None,
    report_period_us: int | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
    profile: ControllerProfile | None = None,
) -> ProController:
    """Create a Pro Controller through its public constructor."""
    return _construct_with_transport(
        ProController,
        transport=transport,
        profile=profile,
        constructor=lambda: ProController(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        ),
    )


def make_joycon_l(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    profile_path: str | None = None,
    report_period_us: int | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
    profile: ControllerProfile | None = None,
) -> JoyConL:
    """Create a Joy-Con L through its public constructor."""
    return _construct_with_transport(
        JoyConL,
        transport=transport,
        profile=profile,
        constructor=lambda: JoyConL(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        ),
    )


def make_joycon_r(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    profile_path: str | None = None,
    report_period_us: int | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
    profile: ControllerProfile | None = None,
) -> JoyConR:
    """Create a Joy-Con R through its public constructor."""
    return _construct_with_transport(
        JoyConR,
        transport=transport,
        profile=profile,
        constructor=lambda: JoyConR(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        ),
    )


def make_direct_pro_controller(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    profile_path: str | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
    profile: ControllerProfile | None = None,
) -> DirectProController:
    """Create a direct Pro Controller through its public constructor."""
    return _construct_with_transport(
        DirectProController,
        transport=transport,
        profile=profile,
        constructor=lambda: DirectProController(
            adapter=adapter,
            profile_path=profile_path,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        ),
    )


def make_direct_joycon_l(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    profile_path: str | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
    profile: ControllerProfile | None = None,
) -> DirectJoyConL:
    """Create a direct Joy-Con L through its public constructor."""
    return _construct_with_transport(
        DirectJoyConL,
        transport=transport,
        profile=profile,
        constructor=lambda: DirectJoyConL(
            adapter=adapter,
            profile_path=profile_path,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        ),
    )


def make_direct_joycon_r(
    *,
    transport: HidDeviceTransport,
    adapter: str | None = None,
    profile_path: str | None = None,
    controller_colors: ControllerColors | None = None,
    diagnostics: DiagnosticsConfig | None = None,
    profile: ControllerProfile | None = None,
) -> DirectJoyConR:
    """Create a direct Joy-Con R through its public constructor."""
    return _construct_with_transport(
        DirectJoyConR,
        transport=transport,
        profile=profile,
        constructor=lambda: DirectJoyConR(
            adapter=adapter,
            profile_path=profile_path,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        ),
    )
