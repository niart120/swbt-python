import pytest

from swbt.errors import ProtocolError
from swbt.protocol.output_report import OutputReportParser


def test_0x01_output_report_extracts_packet_rumble_subcommand_and_payload() -> None:
    raw = bytes.fromhex("01 ab 00 01 40 40 00 01 40 40 03 30")

    report = OutputReportParser().parse(raw)

    assert report.report_id == 0x01
    assert report.packet_id == 0xAB
    assert report.rumble == bytes.fromhex("00 01 40 40 00 01 40 40")
    assert report.subcommand_id == 0x03
    assert report.subcommand_payload == b"\x30"


def test_0x01_output_report_rejects_missing_subcommand_byte() -> None:
    with pytest.raises(ProtocolError):
        OutputReportParser().parse(bytes.fromhex("01 ab 00 01 40 40 00 01 40 40"))


def test_0x10_output_report_is_rumble_only() -> None:
    raw = bytes.fromhex("10 2a 00 01 40 40 00 01 40 40")

    report = OutputReportParser().parse(raw)

    assert report.report_id == 0x10
    assert report.packet_id == 0x2A
    assert report.rumble == bytes.fromhex("00 01 40 40 00 01 40 40")
    assert report.subcommand_id is None
    assert report.subcommand_payload == b""
