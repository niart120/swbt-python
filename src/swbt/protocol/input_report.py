"""Input report builders."""

from swbt.input import InputState, Stick
from swbt.protocol.imu_report import encode_standard_imu
from swbt.protocol.profiles.base import ControllerProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile


class InputReportBuilder:
    """Build Switch HID input reports from immutable input state."""

    def __init__(
        self,
        profile: ControllerProfile | None = None,
    ) -> None:
        """Create a report builder."""
        self._profile = profile or default_controller_profile()

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
        block = encode_standard_imu(state.imu_frames) if imu_block is None else imu_block
        self._place_imu_block(report, block)
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
