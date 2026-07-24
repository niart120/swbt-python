"""Normalized configuration for gamepad construction and runtime setup."""

from dataclasses import dataclass

from swbt.errors import InvalidInputError
from swbt.protocol.profiles.base import ControllerColors, ControllerProfile


@dataclass(frozen=True, init=False)
class _GamepadConfig:
    """Normalized internal configuration shared by a controller and its runtime."""

    adapter: str | None
    profile_path: str | None
    profile: ControllerProfile
    report_period_us: int
    device_name: str
    controller_colors: ControllerColors | None

    def __init__(
        self,
        *,
        profile: ControllerProfile,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        device_name: str | None = None,
        controller_colors: ControllerColors | None = None,
    ) -> None:
        """Validate and normalize controller construction values."""
        if not isinstance(profile, ControllerProfile):
            msg = "profile must be a ControllerProfile"
            raise InvalidInputError(msg)
        normalized_report_period = (
            profile.default_report_period_us if report_period_us is None else report_period_us
        )
        if normalized_report_period <= 0:
            msg = "report_period_us must be positive"
            raise InvalidInputError(msg)
        if controller_colors is not None and not isinstance(controller_colors, ControllerColors):
            msg = "controller_colors must be a ControllerColors"
            raise InvalidInputError(msg)

        object.__setattr__(self, "adapter", adapter)
        object.__setattr__(self, "profile_path", profile_path)
        object.__setattr__(self, "profile", profile)
        object.__setattr__(self, "report_period_us", normalized_report_period)
        object.__setattr__(
            self,
            "device_name",
            profile.device_name if device_name is None else device_name,
        )
        object.__setattr__(self, "controller_colors", controller_colors)
