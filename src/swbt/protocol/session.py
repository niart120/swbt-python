"""Connection-scoped Switch HID protocol state."""

from dataclasses import dataclass, field, replace

from swbt.errors import ProtocolError
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


def apply_imu_mode_request(
    state: SwitchHidSessionState,
    *,
    requested_mode: int,
    accepted_modes: tuple[int, ...],
) -> SwitchHidSessionState:
    """Return the session state for a newly accepted IMU encoding epoch."""
    if requested_mode not in accepted_modes:
        msg = f"unsupported enable IMU value: 0x{requested_mode:02x}"
        raise ProtocolError(msg)
    try:
        mode = ImuMode(requested_mode)
    except ValueError as error:
        msg = f"unknown enable IMU value: 0x{requested_mode:02x}"
        raise ProtocolError(msg) from error
    return replace(
        state,
        imu_mode=mode,
        imu_encoding_state=ImuEncodingState(),
    )
