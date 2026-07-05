from typing import Any, cast

from swbt.protocol.profile import JoyConLeftProfile
from swbt.transport._bumble_sdp import build_hid_service_records


def _attributes_for(service_records: dict[int, list[object]]) -> dict[int, Any]:
    attributes: dict[int, Any] = {}
    for attribute in service_records[0x00010001]:
        typed_attribute = cast("Any", attribute)
        attributes[typed_attribute.id] = typed_attribute.value
    return attributes


def test_bumble_sdp_builder_preserves_reference_hid_attributes() -> None:
    attributes = _attributes_for(build_hid_service_records(b"\x00"))

    assert attributes[0x0100].value == b"Pro Controller"
    assert 0x0101 not in attributes
    assert 0x0102 not in attributes
    assert 0x0200 not in attributes
    assert attributes[0x0203].value == 0x21
    assert attributes[0x020A].value is True
    assert attributes[0x020B].value == 0x0101
    assert attributes[0x020C].value == 0x0C80
    assert attributes[0x020D].value is True
    assert attributes[0x020E].value is False
    assert attributes[0x020F].value == 0xFFFF
    assert attributes[0x0210].value == 0xFFFF


def test_bumble_sdp_builder_uses_joycon_policy() -> None:
    policy = JoyConLeftProfile().hid_sdp_policy

    attributes = _attributes_for(
        build_hid_service_records(
            b"\x00",
            device_name="Joy-Con (L)",
            sdp_policy=policy,
        )
    )

    assert attributes[0x0100].value == b"Wireless Gamepad"
    assert attributes[0x0101].value == b"Gamepad"
    assert attributes[0x0102].value == b"Nintendo"
    assert attributes[0x0200].value == 0x0100
    assert attributes[0x0203].value == 0x00
    assert 0x020A not in attributes
    assert attributes[0x020B].value == 0x0100
    assert attributes[0x020C].value == 0x0C80
    assert attributes[0x020D].value is False
    assert attributes[0x020E].value is True
    assert attributes[0x020F].value == 0x0640
    assert attributes[0x0210].value == 0x0320


def test_bumble_sdp_builder_uses_supplied_hid_descriptor() -> None:
    descriptor = bytes.fromhex("85 30 09 01")

    attributes = _attributes_for(build_hid_service_records(descriptor))

    descriptor_list = attributes[0x0206].value
    assert descriptor_list[0].value[0].value == 0x22
    assert descriptor_list[0].value[1].value == descriptor
