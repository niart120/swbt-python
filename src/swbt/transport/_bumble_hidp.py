"""HIDP helpers for Bumble HID transport."""

HID_OUTPUT_REPORT_TYPE = 0x02
HIDP_DATA_MESSAGE_TYPE = 0x0A
HID_GET_SET_SUCCESS = 0xFF
HID_GET_SET_UNSUPPORTED_REQUEST = 0x02
HID_CONTROL_PSM = 0x0011
HID_INTERRUPT_PSM = 0x0013


def decode_hidp_output_report(pdu: bytes) -> bytes | None:
    if not pdu:
        return None
    message_type = pdu[0] >> 4
    report_type = pdu[0] & 0x03
    if message_type != HIDP_DATA_MESSAGE_TYPE:
        return None
    if report_type != HID_OUTPUT_REPORT_TYPE:
        return None
    return pdu[1:]


def hid_channel_name(psm: object) -> str:
    if psm == HID_CONTROL_PSM:
        return "control"
    if psm == HID_INTERRUPT_PSM:
        return "interrupt"
    return "unknown"


def format_psm(psm: object) -> str:
    if isinstance(psm, int):
        return f"0x{psm:04x}"
    return "unknown"
