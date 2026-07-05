"""SDP service record builder for Bumble HID transport."""

from swbt.protocol.profile import HidSdpPolicy
from swbt.transport._bumble_hidp import HID_CONTROL_PSM, HID_INTERRUPT_PSM

_HID_SERVICE_RECORD_HANDLE = 0x00010001
_HID_REPORT_DESCRIPTOR_TYPE = 0x22
_DEFAULT_DEVICE_NAME = "Pro Controller"

_SDP_HID_PARSER_VERSION_ATTRIBUTE_ID = 0x0201
_SDP_HID_DEVICE_SUBCLASS_ATTRIBUTE_ID = 0x0202
_SDP_HID_COUNTRY_CODE_ATTRIBUTE_ID = 0x0203
_SDP_HID_VIRTUAL_CABLE_ATTRIBUTE_ID = 0x0204
_SDP_HID_RECONNECT_INITIATE_ATTRIBUTE_ID = 0x0205
_SDP_HID_DESCRIPTOR_LIST_ATTRIBUTE_ID = 0x0206
_SDP_HID_LANG_ID_BASE_LIST_ATTRIBUTE_ID = 0x0207
_SDP_HID_REMOTE_WAKE_ATTRIBUTE_ID = 0x020A
_SDP_HID_PROFILE_VERSION_ATTRIBUTE_ID = 0x020B
_SDP_HID_SUPERVISION_TIMEOUT_ATTRIBUTE_ID = 0x020C
_SDP_HID_NORMALLY_CONNECTABLE_ATTRIBUTE_ID = 0x020D
_SDP_HID_BOOT_DEVICE_ATTRIBUTE_ID = 0x020E
_SDP_HIDSSR_HOST_MAX_LATENCY_ATTRIBUTE_ID = 0x020F
_SDP_HIDSSR_HOST_MIN_TIMEOUT_ATTRIBUTE_ID = 0x0210
_SDP_PRIMARY_LANGUAGE_SERVICE_NAME_ATTRIBUTE_ID = 0x0100

_LANGUAGE_BASE_EN_US = 0x0100
_SDP_LANGUAGE_CODE_ENGLISH = 0x656E
_SDP_CHARACTER_ENCODING_UTF8 = 0x006A
_LANGUAGE_ID_EN_US = 0x0409
_DEFAULT_SDP_POLICY = HidSdpPolicy()


def build_hid_service_records(
    hid_descriptor: bytes,
    *,
    device_name: str = _DEFAULT_DEVICE_NAME,
    sdp_policy: HidSdpPolicy | None = None,
) -> dict[int, list[object]]:
    """Build the Classic HID SDP service record used by the reference controller."""
    from bumble import core  # noqa: PLC0415
    from bumble.sdp import (  # noqa: PLC0415
        SDP_ADDITIONAL_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
        SDP_BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRIBUTE_ID,
        SDP_BROWSE_GROUP_LIST_ATTRIBUTE_ID,
        SDP_LANGUAGE_BASE_ATTRIBUTE_ID_LIST_ATTRIBUTE_ID,
        SDP_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
        SDP_PUBLIC_BROWSE_ROOT,
        SDP_SERVICE_CLASS_ID_LIST_ATTRIBUTE_ID,
        SDP_SERVICE_RECORD_HANDLE_ATTRIBUTE_ID,
        DataElement,
        ServiceAttribute,
    )

    policy = sdp_policy or _DEFAULT_SDP_POLICY
    service_name = policy.service_name or device_name

    record_attributes = [
        ServiceAttribute(
            SDP_SERVICE_RECORD_HANDLE_ATTRIBUTE_ID,
            DataElement.unsigned_integer_32(_HID_SERVICE_RECORD_HANDLE),
        ),
        ServiceAttribute(
            SDP_SERVICE_CLASS_ID_LIST_ATTRIBUTE_ID,
            DataElement.sequence([DataElement.uuid(core.BT_HUMAN_INTERFACE_DEVICE_SERVICE)]),
        ),
        ServiceAttribute(
            SDP_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
            DataElement.sequence(
                [
                    DataElement.sequence(
                        [
                            DataElement.uuid(core.BT_L2CAP_PROTOCOL_ID),
                            DataElement.unsigned_integer_16(HID_CONTROL_PSM),
                        ]
                    ),
                    DataElement.sequence([DataElement.uuid(core.BT_HIDP_PROTOCOL_ID)]),
                ]
            ),
        ),
        ServiceAttribute(
            SDP_BROWSE_GROUP_LIST_ATTRIBUTE_ID,
            DataElement.sequence([DataElement.uuid(SDP_PUBLIC_BROWSE_ROOT)]),
        ),
        ServiceAttribute(
            SDP_LANGUAGE_BASE_ATTRIBUTE_ID_LIST_ATTRIBUTE_ID,
            DataElement.sequence(
                [
                    DataElement.unsigned_integer_16(_SDP_LANGUAGE_CODE_ENGLISH),
                    DataElement.unsigned_integer_16(_SDP_CHARACTER_ENCODING_UTF8),
                    DataElement.unsigned_integer_16(_LANGUAGE_BASE_EN_US),
                ]
            ),
        ),
        ServiceAttribute(
            _SDP_PRIMARY_LANGUAGE_SERVICE_NAME_ATTRIBUTE_ID,
            DataElement.text_string(service_name.encode("utf-8")),
        ),
    ]
    if policy.service_description is not None:
        record_attributes.append(
            ServiceAttribute(
                _SDP_PRIMARY_LANGUAGE_SERVICE_NAME_ATTRIBUTE_ID + 1,
                DataElement.text_string(policy.service_description.encode("utf-8")),
            )
        )
    if policy.provider_name is not None:
        record_attributes.append(
            ServiceAttribute(
                _SDP_PRIMARY_LANGUAGE_SERVICE_NAME_ATTRIBUTE_ID + 2,
                DataElement.text_string(policy.provider_name.encode("utf-8")),
            )
        )
    record_attributes.extend(
        [
            ServiceAttribute(
                SDP_BLUETOOTH_PROFILE_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.uuid(core.BT_HUMAN_INTERFACE_DEVICE_SERVICE),
                                DataElement.unsigned_integer_16(policy.bluetooth_profile_version),
                            ]
                        )
                    ]
                ),
            ),
            ServiceAttribute(
                SDP_ADDITIONAL_PROTOCOL_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.sequence(
                                    [
                                        DataElement.uuid(core.BT_L2CAP_PROTOCOL_ID),
                                        DataElement.unsigned_integer_16(HID_INTERRUPT_PSM),
                                    ]
                                ),
                                DataElement.sequence([DataElement.uuid(core.BT_HIDP_PROTOCOL_ID)]),
                            ]
                        )
                    ]
                ),
            ),
        ]
    )
    if policy.device_release_number is not None:
        record_attributes.append(
            ServiceAttribute(
                0x0200,
                DataElement.unsigned_integer_16(policy.device_release_number),
            )
        )
    record_attributes.extend(
        [
            ServiceAttribute(
                _SDP_HID_PARSER_VERSION_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(policy.parser_version),
            ),
            ServiceAttribute(
                _SDP_HID_DEVICE_SUBCLASS_ATTRIBUTE_ID,
                DataElement.unsigned_integer_8(policy.device_subclass),
            ),
            ServiceAttribute(
                _SDP_HID_COUNTRY_CODE_ATTRIBUTE_ID,
                DataElement.unsigned_integer_8(policy.country_code),
            ),
            ServiceAttribute(
                _SDP_HID_VIRTUAL_CABLE_ATTRIBUTE_ID,
                DataElement.boolean(policy.virtual_cable),
            ),
            ServiceAttribute(
                _SDP_HID_RECONNECT_INITIATE_ATTRIBUTE_ID,
                DataElement.boolean(policy.reconnect_initiate),
            ),
            ServiceAttribute(
                _SDP_HID_DESCRIPTOR_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.unsigned_integer_8(_HID_REPORT_DESCRIPTOR_TYPE),
                                DataElement.text_string(hid_descriptor),
                            ]
                        )
                    ]
                ),
            ),
            ServiceAttribute(
                _SDP_HID_LANG_ID_BASE_LIST_ATTRIBUTE_ID,
                DataElement.sequence(
                    [
                        DataElement.sequence(
                            [
                                DataElement.unsigned_integer_16(_LANGUAGE_ID_EN_US),
                                DataElement.unsigned_integer_16(_LANGUAGE_BASE_EN_US),
                            ]
                        )
                    ]
                ),
            ),
        ]
    )
    if policy.remote_wake is not None:
        record_attributes.append(
            ServiceAttribute(
                _SDP_HID_REMOTE_WAKE_ATTRIBUTE_ID,
                DataElement.boolean(policy.remote_wake),
            )
        )
    record_attributes.extend(
        [
            ServiceAttribute(
                _SDP_HID_PROFILE_VERSION_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(policy.profile_version),
            ),
            ServiceAttribute(
                _SDP_HID_SUPERVISION_TIMEOUT_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(policy.supervision_timeout),
            ),
            ServiceAttribute(
                _SDP_HID_NORMALLY_CONNECTABLE_ATTRIBUTE_ID,
                DataElement.boolean(policy.normally_connectable),
            ),
            ServiceAttribute(
                _SDP_HID_BOOT_DEVICE_ATTRIBUTE_ID,
                DataElement.boolean(policy.boot_device),
            ),
            ServiceAttribute(
                _SDP_HIDSSR_HOST_MAX_LATENCY_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(policy.ssr_host_max_latency),
            ),
            ServiceAttribute(
                _SDP_HIDSSR_HOST_MIN_TIMEOUT_ATTRIBUTE_ID,
                DataElement.unsigned_integer_16(policy.ssr_host_min_timeout),
            ),
        ]
    )
    return {_HID_SERVICE_RECORD_HANDLE: record_attributes}
