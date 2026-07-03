from swbt.transport._bumble_hidp import decode_hidp_output_report


def test_decode_hidp_output_report_strips_data_header() -> None:
    assert decode_hidp_output_report(bytes.fromhex("a2 01 02")) == bytes.fromhex("01 02")


def test_decode_hidp_output_report_ignores_non_output_data_message() -> None:
    assert decode_hidp_output_report(bytes.fromhex("a1 30")) is None
    assert decode_hidp_output_report(bytes.fromhex("50 01")) is None
    assert decode_hidp_output_report(b"") is None
