"""Configuration models for gamepad construction and runtime setup."""

from dataclasses import dataclass, field

from swbt.errors import InvalidInputError
from swbt.protocol.profiles.base import ControllerColors, ControllerProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile


@dataclass(frozen=True)
class _SwitchGamepadConfig:
    """Configuration used to construct a concrete gamepad.

    Attributes:
        adapter: Bumble adapter moniker, such as ``"usb:0"``.
        key_store_path: Path used by the default transport to persist pairing keys.
        profile: Fixed controller identity and protocol profile.
        report_period_us: Periodic input report interval in microseconds.
        device_name: HID device name advertised to the host.
        controller_colors: Fixed controller body, button, and grip colors for SPI profile data.
    """

    adapter: str | None = None
    key_store_path: str | None = None
    profile: ControllerProfile = field(default_factory=default_controller_profile)
    report_period_us: int | None = None
    device_name: str | None = None
    controller_colors: ControllerColors | None = None

    def __post_init__(self) -> None:
        """Validate resource configuration."""
        if not isinstance(self.profile, ControllerProfile):
            msg = "profile must be a ControllerProfile"
            raise InvalidInputError(msg)
        if self.report_period_us is None:
            object.__setattr__(
                self,
                "report_period_us",
                self.profile.default_report_period_us,
            )
        elif self.report_period_us <= 0:
            msg = "report_period_us must be positive"
            raise InvalidInputError(msg)
        if self.device_name is None:
            object.__setattr__(self, "device_name", self.profile.device_name)
        if self.controller_colors is not None and not isinstance(
            self.controller_colors, ControllerColors
        ):
            msg = "controller_colors must be a ControllerColors"
            raise InvalidInputError(msg)


@dataclass(frozen=True)
class _ControllerSpec:
    """Internal controller identity selected by a concrete controller class."""

    profile: ControllerProfile

    def build_config(
        self,
        *,
        adapter: str | None,
        key_store_path: str | None,
        report_period_us: int | None,
        controller_colors: ControllerColors | None,
    ) -> _SwitchGamepadConfig:
        """Create internal construction config from public constructor options."""
        return _SwitchGamepadConfig(
            adapter=adapter,
            key_store_path=key_store_path,
            profile=self.profile,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
        )


@dataclass(frozen=True)
class _RuntimeConfig:
    """Normalized internal configuration for ControllerRuntime."""

    adapter: str | None
    key_store_path: str | None
    profile: ControllerProfile
    report_period_us: int
    device_name: str
    controller_colors: ControllerColors | None

    @classmethod
    def from_public_config(cls, config: _SwitchGamepadConfig) -> "_RuntimeConfig":
        """Create normalized runtime configuration from public construction config."""
        if config.report_period_us is None or config.device_name is None:
            msg = "_SwitchGamepadConfig was not normalized"
            raise InvalidInputError(msg)
        return cls(
            adapter=config.adapter,
            key_store_path=config.key_store_path,
            profile=config.profile,
            report_period_us=config.report_period_us,
            device_name=config.device_name,
            controller_colors=config.controller_colors,
        )
