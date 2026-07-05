from typing import cast

import pytest

from swbt.errors import InvalidInputError
from swbt.protocol.profile import (
    SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR,
    ControllerColors,
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


def test_controller_colors_default_to_daemon_body_button_seed_and_body_colored_grips() -> None:
    colors = ControllerColors()

    assert colors.body == 0x0D0D0D
    assert colors.buttons == 0xFFFFFF
    assert colors.left_grip == 0x0D0D0D
    assert colors.right_grip == 0x0D0D0D


def test_controller_colors_convert_to_spi_bytes_in_rgb_order() -> None:
    colors = ControllerColors(
        body=0x112233,
        buttons=0x445566,
        left_grip=0x778899,
        right_grip=0xAABBCC,
    )

    assert colors.to_spi_bytes() == bytes.fromhex("11 22 33 44 55 66 77 88 99 aa bb cc")


def test_controller_colors_default_grip_colors_to_body_color() -> None:
    colors = ControllerColors(body=0x112233, buttons=0x445566)

    assert colors.left_grip == 0x112233
    assert colors.right_grip == 0x112233
    assert colors.to_spi_bytes() == bytes.fromhex("11 22 33 44 55 66 11 22 33 11 22 33")


def _controller_colors_with_invalid_field(field: str, value: object) -> ControllerColors:
    if field == "body":
        return ControllerColors(body=cast("int", value), buttons=0x445566)
    if field == "buttons":
        return ControllerColors(body=0x112233, buttons=cast("int", value))
    if field == "left_grip":
        return ControllerColors(body=0x112233, buttons=0x445566, left_grip=cast("int", value))
    return ControllerColors(body=0x112233, buttons=0x445566, right_grip=cast("int", value))


@pytest.mark.parametrize("value", [-1, 0x1000000, "#112233", b"\x11\x22\x33", (0x11, 0x22, 0x33)])
@pytest.mark.parametrize("field", ["body", "buttons", "left_grip", "right_grip"])
def test_controller_colors_reject_invalid_rgb_values(field: str, value: object) -> None:
    with pytest.raises(InvalidInputError):
        _controller_colors_with_invalid_field(field, value)
