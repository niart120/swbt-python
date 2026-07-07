"""Subcommand reply generation."""

from dataclasses import dataclass

from swbt.errors import ProtocolError
from swbt.input import InputState
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.output_report import OutputReport
from swbt.protocol.profiles.base import ControllerProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile
from swbt.protocol.spi import VirtualSpiFlash

SIMPLE_ACK_SUBCOMMANDS = {0x08, 0x30}
SESSION_STATE_SUBCOMMANDS = frozenset({0x03, 0x40, 0x48})
SUPPORTED_INPUT_REPORT_MODE = 0x30
DEFAULT_DEVICE_INFO_BLUETOOTH_ADDRESS = b"\x00\x00\x00\x00\x00\x00"
TRIGGER_BUTTONS_ELAPSED_DATA = bytes.fromhex("2c 01 2c 01 00 00 00 00 00 00 00 00 00 00")
MCU_CONFIG_DATA = bytes.fromhex(
    "01 00 ff 00 08 00 1b 01 00 00 00 00 00 00 00 00 00 00 00 00 "
    "00 00 00 00 00 00 00 00 00 00 00 00 00 c8"
)


@dataclass
class SubcommandSessionState:
    """Mutable host-requested subcommand state for one responder lifetime."""

    report_mode: int | None = None
    report_mode_supported: bool = False
    unsupported_report_mode: int | None = None
    imu_mode: int | None = None
    imu_enabled: bool = False
    vibration_enabled: bool = False


class UnsupportedSubcommandError(ProtocolError):
    """Raised when a subcommand is not supported by the responder."""

    def __init__(self, subcommand_id: int, payload: bytes) -> None:
        """Create an error with fields diagnostics can record."""
        self.subcommand_id = subcommand_id
        self.payload = bytes(payload)
        super().__init__(f"unsupported subcommand: 0x{subcommand_id:02x}")


class SubcommandResponder:
    """Build 0x21 replies for supported subcommands."""

    def __init__(
        self,
        *,
        spi_flash: VirtualSpiFlash | None = None,
        profile: ControllerProfile | None = None,
        session_state: SubcommandSessionState | None = None,
        device_info_bluetooth_address: bytes = DEFAULT_DEVICE_INFO_BLUETOOTH_ADDRESS,
    ) -> None:
        """Create a responder."""
        self._profile = profile or default_controller_profile()
        self._session_state = (
            session_state if session_state is not None else SubcommandSessionState()
        )
        self._device_info_bluetooth_address = bytes(device_info_bluetooth_address)
        self._spi_flash = spi_flash or VirtualSpiFlash(profile=self._profile)

    @property
    def session_state(self) -> SubcommandSessionState:
        """Return the mutable subcommand state owned by this responder."""
        return self._session_state

    def set_device_info_bluetooth_address(self, bluetooth_address: bytes) -> None:
        """Update the Bluetooth address returned by subcommand 0x02."""
        if len(bluetooth_address) != 6:
            msg = "bluetooth_address must be 6 bytes"
            raise ProtocolError(msg)
        self._device_info_bluetooth_address = bytes(bluetooth_address)

    def respond(self, output_report: OutputReport, *, state: InputState, timer: int = 0) -> bytes:
        """Return a 0x21 reply for an output report with a subcommand."""
        if output_report.subcommand_id is None:
            msg = "output report does not include a subcommand"
            raise ProtocolError(msg)

        ack, data = self._reply_data(output_report)
        return self._build_0x21_reply(
            subcommand_id=output_report.subcommand_id,
            ack=ack,
            data=data,
            state=state,
            timer=timer,
        )

    def _reply_data(self, output_report: OutputReport) -> tuple[int, bytes]:
        subcommand_id = output_report.subcommand_id
        if subcommand_id is None:
            msg = "output report does not include a subcommand"
            raise ProtocolError(msg)
        if subcommand_id == 0x03:
            return 0x80, self._set_input_report_mode(output_report.subcommand_payload)
        if subcommand_id == 0x40:
            return 0x80, self._set_imu_enabled(output_report.subcommand_payload)
        if subcommand_id == 0x48:
            return 0x80, self._set_vibration_enabled(output_report.subcommand_payload)
        if subcommand_id in SIMPLE_ACK_SUBCOMMANDS:
            return 0x80, b""
        if subcommand_id == 0x02:
            return 0x82, self._profile.build_device_info(self._device_info_bluetooth_address)
        if subcommand_id == 0x04:
            return 0x83, TRIGGER_BUTTONS_ELAPSED_DATA
        if subcommand_id == 0x10:
            return 0x90, self._spi_read_reply_data(output_report.subcommand_payload)
        if subcommand_id == 0x21:
            return 0xA0, MCU_CONFIG_DATA
        if subcommand_id == 0x22:
            return 0x80, _nfc_ir_mcu_state_payload(output_report.subcommand_payload)
        raise UnsupportedSubcommandError(subcommand_id, output_report.subcommand_payload)

    def _set_input_report_mode(self, payload: bytes) -> bytes:
        mode = _first_payload_byte(payload, "set input report mode")
        self._session_state.report_mode = mode
        self._session_state.report_mode_supported = mode == SUPPORTED_INPUT_REPORT_MODE
        self._session_state.unsupported_report_mode = (
            None if self._session_state.report_mode_supported else mode
        )
        return b""

    def _set_imu_enabled(self, payload: bytes) -> bytes:
        imu_mode = _imu_enable_payload(payload, self._profile.imu_enable_modes)
        self._session_state.imu_mode = imu_mode
        self._session_state.imu_enabled = imu_mode != 0x00
        return b""

    def _set_vibration_enabled(self, payload: bytes) -> bytes:
        self._session_state.vibration_enabled = _enable_payload(payload, "enable vibration")
        return b""

    def _spi_read_reply_data(self, payload: bytes) -> bytes:
        if len(payload) < 5:
            msg = "SPI read subcommand must include address and size"
            raise ProtocolError(msg)
        address = int.from_bytes(payload[0:4], "little")
        size = payload[4]
        return payload[:5] + self._spi_flash.read(address, size)

    def _build_0x21_reply(
        self,
        *,
        subcommand_id: int,
        ack: int,
        data: bytes,
        state: InputState,
        timer: int,
    ) -> bytes:
        if len(data) > 35:
            msg = f"subcommand reply data is too large: {len(data)}"
            raise ProtocolError(msg)

        prefix = InputReportBuilder(self._profile).build_0x30(state, timer=timer)[:13]
        reply = bytearray(50)
        reply[:13] = prefix
        reply[0] = 0x21
        reply[13] = ack
        reply[14] = subcommand_id
        reply[15 : 15 + len(data)] = data
        return bytes(reply)


def _first_payload_byte(payload: bytes, subcommand_name: str) -> int:
    if not payload:
        msg = f"{subcommand_name} subcommand must include one argument byte"
        raise ProtocolError(msg)
    return payload[0]


def _enable_payload(payload: bytes, subcommand_name: str) -> bool:
    value = _first_payload_byte(payload, subcommand_name)
    if value not in (0x00, 0x01):
        msg = f"{subcommand_name} subcommand argument must be 0x00 or 0x01"
        raise ProtocolError(msg)
    return value == 0x01


def _imu_enable_payload(payload: bytes, accepted_modes: tuple[int, ...]) -> int:
    value = _first_payload_byte(payload, "enable IMU")
    if value in accepted_modes:
        return value
    msg = "enable IMU subcommand argument must be 0x00 or 0x01"
    raise ProtocolError(msg)


def _nfc_ir_mcu_state_payload(payload: bytes) -> bytes:
    value = _first_payload_byte(payload, "set NFC/IR MCU state")
    if value in (0x00, 0x01, 0x02):
        return b""
    msg = "set NFC/IR MCU state subcommand argument must be 0x00, 0x01, or 0x02"
    raise ProtocolError(msg)
