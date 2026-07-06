from pathlib import Path
from typing import cast

import pytest

from swbt.errors import InvalidInputError
from swbt.protocol.profile import (
    SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR,
    ControllerColors,
    ControllerKind,
    JoyConLeftProfile,
    JoyConRightProfile,
    ProControllerProfile,
)

ROOT = Path(__file__).resolve().parents[2]


def test_protocol_profile_implementation_is_split_by_profile_concern() -> None:
    from swbt.protocol.buttons import PRO_CONTROLLER_BUTTON_BITS
    from swbt.protocol.descriptors import SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR as descriptor
    from swbt.protocol.profiles.base import ControllerKind as SplitControllerKind
    from swbt.protocol.profiles.joycon import (
        JoyConLeftProfile as SplitJoyConLeftProfile,
        JoyConRightProfile as SplitJoyConRightProfile,
    )
    from swbt.protocol.profiles.pro_controller import (
        ProControllerProfile as SplitProControllerProfile,
        default_controller_profile as split_default_controller_profile,
    )

    assert SplitControllerKind is ControllerKind
    assert SplitProControllerProfile is ProControllerProfile
    assert SplitJoyConLeftProfile is JoyConLeftProfile
    assert SplitJoyConRightProfile is JoyConRightProfile
    assert descriptor is SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR
    assert ProControllerProfile().button_bits is PRO_CONTROLLER_BUTTON_BITS
    assert split_default_controller_profile().__class__ is ProControllerProfile


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


def test_controller_profiles_have_distinct_identity_values() -> None:
    pro = ProControllerProfile()
    left = JoyConLeftProfile()
    right = JoyConRightProfile()

    assert pro.kind is ControllerKind.PRO_CONTROLLER
    assert pro.device_name == "Pro Controller"
    assert pro.device_type == 0x03
    assert left.kind is ControllerKind.JOYCON_LEFT
    assert left.device_name == "Joy-Con (L)"
    assert left.device_type == 0x01
    assert right.kind is ControllerKind.JOYCON_RIGHT
    assert right.device_name == "Joy-Con (R)"
    assert right.device_type == 0x02


def test_joycon_profiles_use_joycontrol_sdp_policy() -> None:
    left_policy = JoyConLeftProfile().hid_sdp_policy
    right_policy = JoyConRightProfile().hid_sdp_policy

    assert left_policy == right_policy
    assert left_policy.service_name == "Wireless Gamepad"
    assert left_policy.service_description == "Gamepad"
    assert left_policy.provider_name == "Nintendo"
    assert left_policy.device_release_number == 0x0100
    assert left_policy.country_code == 0x00
    assert left_policy.profile_version == 0x0100
    assert left_policy.normally_connectable is False
    assert left_policy.boot_device is True
    assert left_policy.ssr_host_max_latency == 0x0640
    assert left_policy.ssr_host_min_timeout == 0x0320


def test_profile_build_device_info_uses_caller_bluetooth_address() -> None:
    bluetooth_address = bytes.fromhex("01 23 45 67 89 ab")

    assert ProControllerProfile().build_device_info(bluetooth_address) == bytes.fromhex(
        "04 00 03 02 01 23 45 67 89 ab 03 02"
    )
    assert JoyConLeftProfile().build_device_info(bluetooth_address) == bytes.fromhex(
        "04 00 01 02 01 23 45 67 89 ab 01 01"
    )
    assert JoyConRightProfile().build_device_info(bluetooth_address) == bytes.fromhex(
        "04 00 02 02 01 23 45 67 89 ab 01 01"
    )


def test_profile_build_device_info_rejects_non_address_length() -> None:
    with pytest.raises(InvalidInputError):
        ProControllerProfile().build_device_info(b"\x00\x01")


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_controller_profile_rejects_invalid_default_report_period(value: object) -> None:
    with pytest.raises(InvalidInputError):
        ProControllerProfile(default_report_period_us=cast("int", value))


def test_pro_controller_profile_direct_construction_is_limited_to_profile_factory() -> None:
    direct_construction_sites = []
    allowed_paths = {
        ROOT / "src" / "swbt" / "protocol" / "profile.py",
        ROOT / "src" / "swbt" / "protocol" / "profiles" / "pro_controller.py",
    }

    for path in (ROOT / "src" / "swbt").rglob("*.py"):
        if path in allowed_paths:
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "ProControllerProfile(" in line:
                direct_construction_sites.append(f"{path.relative_to(ROOT)}:{line_number}")

    assert direct_construction_sites == []


def test_controller_colors_default_to_joy_con_like_profile() -> None:
    colors = ControllerColors()

    assert colors.body == 0x323232
    assert colors.buttons == 0xFFFFFF
    assert colors.left_grip == 0x00B2FF
    assert colors.right_grip == 0xFF3B30


def test_controller_colors_convert_to_spi_bytes_in_rgb_order() -> None:
    colors = ControllerColors(
        body=0x112233,
        buttons=0x445566,
        left_grip=0x778899,
        right_grip=0xAABBCC,
    )

    assert colors.to_spi_bytes() == bytes.fromhex("11 22 33 44 55 66 77 88 99 aa bb cc")


def test_controller_colors_omitted_grips_keep_their_own_default_colors() -> None:
    colors = ControllerColors(body=0x112233, buttons=0x445566)

    assert colors.left_grip == 0x00B2FF
    assert colors.right_grip == 0xFF3B30
    assert colors.to_spi_bytes() == bytes.fromhex("11 22 33 44 55 66 00 b2 ff ff 3b 30")


def test_joycon_profiles_have_side_specific_default_controller_colors() -> None:
    left = JoyConLeftProfile().controller_colors
    right = JoyConRightProfile().controller_colors

    assert left == ControllerColors(
        body=0x00B2FF,
        buttons=0x323232,
        left_grip=0x00B2FF,
        right_grip=0x00B2FF,
    )
    assert right == ControllerColors(
        body=0xFF3B30,
        buttons=0x323232,
        left_grip=0xFF3B30,
        right_grip=0xFF3B30,
    )


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
