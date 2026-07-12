"""Input report builders."""

from collections.abc import Callable
from time import monotonic_ns
from typing import Protocol

from swbt.input import InputState, Stick
from swbt.protocol.imu_report import encode_standard_imu
from swbt.protocol.motion import QuaternionMotionPacker
from swbt.protocol.profiles.base import ControllerProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile


class _ImuSessionState(Protocol):
    imu_mode: int | None

    def consume_imu_mode_reset_request(self) -> bool: ...


class InputReportBuilder:
    """Build Switch HID input reports from immutable input state."""

    def __init__(
        self,
        profile: ControllerProfile | None = None,
        *,
        session_state: _ImuSessionState | None = None,
        clock_ns: Callable[[], int] = monotonic_ns,
    ) -> None:
        """Create a report builder."""
        self._profile = profile or default_controller_profile()
        self._session_state = session_state
        self._quaternion_packer = QuaternionMotionPacker(clock_ns=clock_ns)

    def build_0x30(
        self,
        state: InputState,
        *,
        timer: int = 0,
        imu_block: bytes | None = None,
    ) -> bytes:
        """Build a 0x30 standard full input report."""
        self._profile.validate_input_state(state)
        report = bytearray(49)
        report[0] = 0x30
        report[1] = timer & 0xFF
        report[2] = self._profile.battery_connection
        self._pack_buttons(report, state)
        report[6:9] = self._pack_stick(state.left_stick)
        report[9:12] = self._pack_stick(state.right_stick)
        report[12] = self._profile.vibrator_input
        if imu_block is None:
            self._pack_imu_frames(report, state)
        else:
            self._place_imu_block(report, imu_block)
        return bytes(report)

    @staticmethod
    def _place_imu_block(report: bytearray, imu_block: bytes) -> None:
        if len(imu_block) != 36:
            msg = f"IMU block must be 36 bytes, got {len(imu_block)}"
            raise ValueError(msg)
        report[13:49] = imu_block

    def _pack_buttons(self, report: bytearray, state: InputState) -> None:
        for button in state.buttons:
            offset, mask = self._profile.button_bit(button)
            report[offset] |= mask

    @staticmethod
    def _pack_stick(stick: Stick) -> bytes:
        return bytes(
            (
                stick.x & 0xFF,
                ((stick.x >> 8) & 0x0F) | ((stick.y & 0x0F) << 4),
                (stick.y >> 4) & 0xFF,
            )
        )

    def _pack_imu_frames(self, report: bytearray, state: InputState) -> None:
        if self._session_state is not None and self._session_state.consume_imu_mode_reset_request():
            self._quaternion_packer.reset()
        imu_mode = self._session_state.imu_mode if self._session_state is not None else None
        if self._session_state is not None and imu_mode == 0x00:
            report[13:49] = bytes(36)
            return
        if imu_mode in (0x02, 0x03, 0x04, 0x05):
            report[13:49] = self._quaternion_packer.pack(
                state.imu_frames,
                gyro_calibration=self._profile.gyro_calibration,
            )
            return
        report[13:49] = encode_standard_imu(state.imu_frames)
