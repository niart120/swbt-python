"""Output report parser."""

from dataclasses import dataclass

from swbt.errors import ProtocolError


@dataclass(frozen=True)
class OutputReport:
    """Parsed host-to-device output report."""

    report_id: int
    packet_id: int | None
    rumble: bytes | None
    subcommand_id: int | None
    subcommand_payload: bytes


class OutputReportParser:
    """Parse Switch HID output reports."""

    def parse(self, raw_report: bytes) -> OutputReport:
        """Parse a raw output report."""
        if not raw_report:
            msg = "output report is empty"
            raise ProtocolError(msg)
        if raw_report[0] == 0x01:
            return self._parse_0x01(raw_report)
        if raw_report[0] == 0x10:
            return self._parse_0x10(raw_report)
        msg = f"unsupported output report id: 0x{raw_report[0]:02x}"
        raise ProtocolError(msg)

    @staticmethod
    def _parse_0x01(raw_report: bytes) -> OutputReport:
        if len(raw_report) < 11:
            msg = "0x01 output report must include packet, rumble, and subcommand"
            raise ProtocolError(msg)
        return OutputReport(
            report_id=0x01,
            packet_id=raw_report[1],
            rumble=raw_report[2:10],
            subcommand_id=raw_report[10],
            subcommand_payload=raw_report[11:],
        )

    @staticmethod
    def _parse_0x10(raw_report: bytes) -> OutputReport:
        if len(raw_report) < 10:
            msg = "0x10 output report must include packet and rumble"
            raise ProtocolError(msg)
        return OutputReport(
            report_id=0x10,
            packet_id=raw_report[1],
            rumble=raw_report[2:10],
            subcommand_id=None,
            subcommand_payload=b"",
        )
