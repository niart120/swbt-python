"""Input report builders."""

from swbt.input import Button, InputState, Stick
from swbt.protocol.profile import ProControllerProfile

BUTTON_BITS = {
    Button.Y: (3, 0x01),
    Button.X: (3, 0x02),
    Button.B: (3, 0x04),
    Button.A: (3, 0x08),
    Button.R: (3, 0x40),
    Button.ZR: (3, 0x80),
    Button.MINUS: (4, 0x01),
    Button.PLUS: (4, 0x02),
    Button.RIGHT_STICK: (4, 0x04),
    Button.LEFT_STICK: (4, 0x08),
    Button.HOME: (4, 0x10),
    Button.CAPTURE: (4, 0x20),
    Button.DPAD_DOWN: (5, 0x01),
    Button.DPAD_UP: (5, 0x02),
    Button.DPAD_RIGHT: (5, 0x04),
    Button.DPAD_LEFT: (5, 0x08),
    Button.L: (5, 0x40),
    Button.ZL: (5, 0x80),
}


class InputReportBuilder:
    """Build Switch HID input reports from immutable input state."""

    def __init__(self, profile: ProControllerProfile | None = None) -> None:
        """Create a report builder."""
        self._profile = profile or ProControllerProfile()

    def build_0x30(self, state: InputState, *, timer: int = 0) -> bytes:
        """Build a 0x30 standard full input report."""
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

    @staticmethod
    def _pack_buttons(report: bytearray, state: InputState) -> None:
        for button in state.buttons:
            offset, mask = BUTTON_BITS[button]
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

    @staticmethod
    def _pack_imu_frames(report: bytearray, state: InputState) -> None:
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
