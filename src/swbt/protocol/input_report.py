"""Input report builders."""

from collections.abc import Callable
from time import monotonic_ns
from typing import Protocol

from swbt.input import InputState, Stick
from swbt.protocol.motion import QuaternionMotionPacker
from swbt.protocol.profiles.base import ControllerProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile


class _ImuSessionState(Protocol):
    imu_mode: int | None
    imu_mode_revision: int


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
        self._last_imu_request: tuple[int | None, int] | None = None

    def build_0x30(self, state: InputState, *, timer: int = 0) -> bytes:
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
        self._pack_imu_frames(report, state)
        return bytes(report)

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
        imu_mode = self._session_state.imu_mode if self._session_state is not None else None
        imu_revision = (
            self._session_state.imu_mode_revision if self._session_state is not None else 0
        )
        imu_request = (imu_mode, imu_revision)
        if imu_mode in (0x02, 0x03, 0x04, 0x05):
            if imu_request != self._last_imu_request:
                self._quaternion_packer.reset()
            report[13:49] = self._quaternion_packer.pack(
                state.imu_frames,
                gyro_calibration=self._profile.gyro_calibration,
            )
            self._last_imu_request = imu_request
            return

        self._last_imu_request = imu_request
        cursor = 13
        for frame in state.imu_frames:
            for value in (
                frame.accel_x,
                frame.accel_y,
                frame.accel_z,
                frame.gyro_x,
                frame.gyro_y,
                frame.gyro_z,
            ):
                report[cursor : cursor + 2] = int(value).to_bytes(2, "little", signed=True)
                cursor += 2
