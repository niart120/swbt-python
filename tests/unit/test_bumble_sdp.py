from typing import Any, cast

from swbt.transport._bumble_sdp import build_hid_service_records


def test_bumble_sdp_builder_preserves_reference_hid_attributes() -> None:
    service_records = build_hid_service_records(b"\x00")
    attributes: dict[int, Any] = {}
    for attribute in service_records[0x00010001]:
        typed_attribute = cast("Any", attribute)
        attributes[typed_attribute.id] = typed_attribute.value

    assert attributes[0x0100].value == b"Pro Controller"
    assert attributes[0x0203].value == 0x21
    assert attributes[0x020A].value is True
    assert attributes[0x020C].value == 0x0C80
    assert attributes[0x020F].value == 0xFFFF
    assert attributes[0x0210].value == 0xFFFF
