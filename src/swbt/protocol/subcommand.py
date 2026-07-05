"""Subcommand reply generation."""

from swbt.errors import ProtocolError
from swbt.input import InputState
from swbt.protocol.input_report import InputReportBuilder
from swbt.protocol.output_report import OutputReport
from swbt.protocol.profile import ProControllerProfile
from swbt.protocol.spi import VirtualSpiFlash

SIMPLE_ACK_SUBCOMMANDS = {0x03, 0x08, 0x30, 0x40, 0x48}
DEVICE_INFO_DATA = bytes.fromhex("04 00 03 02 00 00 00 00 00 00 01 01")
TRIGGER_BUTTONS_ELAPSED_DATA = bytes.fromhex("2c 01 2c 01 00 00 00 00 00 00 00 00 00 00")
MCU_CONFIG_DATA = bytes.fromhex(
    "01 00 ff 00 08 00 1b 01 00 00 00 00 00 00 00 00 00 00 00 00 "
    "00 00 00 00 00 00 00 00 00 00 00 00 00 c8"
)


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
        profile: ProControllerProfile | None = None,
    ) -> None:
        """Create a responder."""
        self._profile = profile or ProControllerProfile()
        self._spi_flash = spi_flash or VirtualSpiFlash(profile=self._profile)

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
        if subcommand_id in SIMPLE_ACK_SUBCOMMANDS:
            return 0x80, b""
        if subcommand_id == 0x02:
            return 0x82, DEVICE_INFO_DATA
        if subcommand_id == 0x04:
            return 0x83, TRIGGER_BUTTONS_ELAPSED_DATA
        if subcommand_id == 0x10:
            return 0x90, self._spi_read_reply_data(output_report.subcommand_payload)
        if subcommand_id == 0x21:
            return 0xA0, MCU_CONFIG_DATA
        raise UnsupportedSubcommandError(subcommand_id, output_report.subcommand_payload)

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
