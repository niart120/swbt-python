"""Connection-scoped Switch HID protocol state."""

from dataclasses import dataclass, field

from swbt.protocol.imu_report import ImuEncodingState, ImuMode


@dataclass(frozen=True)
class SwitchHidSessionState:
    """Immutable host-requested state for one HID connection generation."""

    report_mode: int | None = None
    report_mode_supported: bool = False
    unsupported_report_mode: int | None = None
    imu_mode: ImuMode = ImuMode.DISABLED
    imu_encoding_state: ImuEncodingState = field(default_factory=ImuEncodingState)
    vibration_enabled: bool = False

    @property
    def imu_enabled(self) -> bool:
        """Return whether the host selected an active IMU mode."""
        return self.imu_mode is not ImuMode.DISABLED
