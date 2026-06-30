from swbt.protocol.profile import (
    SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR,
    ProControllerProfile,
)


def test_pro_controller_hid_descriptor_is_203_bytes() -> None:
    descriptor = ProControllerProfile().hid_report_descriptor

    assert descriptor == SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR
    assert len(descriptor) == 203


def test_pro_controller_hid_descriptor_report_ids_are_fixed() -> None:
    descriptor = ProControllerProfile().hid_report_descriptor

    report_ids = [
        descriptor[index + 1] for index, item in enumerate(descriptor[:-1]) if item == 0x85
    ]

    assert report_ids == [0x30, 0x21, 0x81, 0x01, 0x10, 0x80, 0x82]
