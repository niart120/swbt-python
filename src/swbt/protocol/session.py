"""Connection-scoped Switch HID protocol state."""

from dataclasses import dataclass, field, replace

from swbt.errors import ProtocolError
from swbt.input import IMUFrame
from swbt.protocol.imu_report import (
    ImuEncodingState,
    ImuMode,
    encode_imu_block,
)
from swbt.protocol.profiles.base import ControllerProfile


@dataclass(frozen=True)
class SwitchHidSessionState:
    """Immutable host-requested state for one HID connection."""

    report_mode: int | None = None
    report_mode_supported: bool = False
    unsupported_report_mode: int | None = None
    player_lights: int | None = None
    imu_mode: ImuMode = ImuMode.DISABLED
    imu_encoding_state: ImuEncodingState = field(default_factory=ImuEncodingState)
    vibration_enabled: bool = False
    observed_subcommands: frozenset[int] = frozenset()

    @property
    def imu_enabled(self) -> bool:
        """Return whether the host selected an active IMU mode."""
        return self.imu_mode is not ImuMode.DISABLED

    @property
    def protocol_ready(self) -> bool:
        """Return whether the host selected usable reports and assigned player lights."""
        return (
            self.report_mode_supported
            and self.player_lights is not None
            and self.player_lights != 0x00
        )

    @property
    def imu_encoding_format(self) -> str:
        """Return the diagnostic wire-format name derived from the IMU mode."""
        if self.imu_mode is ImuMode.DISABLED:
            return "disabled"
        if self.imu_mode is ImuMode.STANDARD:
            return "standard"
        return "quaternion"


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


class SwitchHidSession:
    """Own host-requested and IMU encoding state for one HID connection."""

    def __init__(self, profile: ControllerProfile) -> None:
        """Create a disabled session for the configured controller profile."""
        self._profile = profile
        self._state = SwitchHidSessionState()

    @property
    def state(self) -> SwitchHidSessionState:
        """Return the current immutable session state."""
        return self._state

    def set_report_mode(self, mode: int, *, supported: bool) -> None:
        """Record one host-selected input report mode."""
        self._state = replace(
            self._state,
            report_mode=mode,
            report_mode_supported=supported,
            unsupported_report_mode=None if supported else mode,
        )

    def observe_subcommand(self, subcommand_id: int) -> None:
        """Record one subcommand observed during this HID connection."""
        self._state = replace(
            self._state,
            observed_subcommands=self._state.observed_subcommands | {subcommand_id},
        )

    def restore_state(self, state: SwitchHidSessionState) -> None:
        """Restore a prior immutable state after a reply send did not complete."""
        self._state = state

    def set_imu_mode(self, mode: int) -> None:
        """Start a new IMU encoding epoch for an accepted host mode."""
        self._state = apply_imu_mode_request(
            self._state,
            requested_mode=mode,
            accepted_modes=self._profile.imu_enable_modes,
        )

    def set_player_lights(self, player_lights: int) -> None:
        """Record one host-selected player-light bitfield."""
        self._state = replace(self._state, player_lights=player_lights)

    def set_vibration_enabled(self, enabled: bool) -> None:
        """Record the host-selected vibration enable state."""
        self._state = replace(self._state, vibration_enabled=enabled)

    def encode_imu(
        self,
        frames: tuple[IMUFrame, IMUFrame, IMUFrame],
        *,
        now_ns: int,
    ) -> bytes:
        """Encode one IMU block and retain only its explicit next state."""
        result = encode_imu_block(
            state=self._state.imu_encoding_state,
            mode=self._state.imu_mode,
            frames=frames,
            gyro_calibration=self._profile.gyro_calibration,
            now_ns=now_ns,
        )
        self._state = replace(self._state, imu_encoding_state=result.state)
        return result.block
