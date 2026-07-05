# ruff: noqa: D101,D102,D105,D107,N802

from collections.abc import Iterator

import pytest

from swbt import AdapterDiscoveryError, AdapterInfo, SwbtError, adapter_discovery, list_adapters


class FakeUsbDevice:
    def __init__(
        self,
        *,
        vendor_id: int = 0x0A12,
        product_id: int = 0x0001,
        device_class: int = 0xE0,
        device_subclass: int = 0x01,
        device_protocol: int = 0x01,
        serial_number: str = "ABC123",
        manufacturer: str = "Cambridge Silicon Radio",
        product: str = "Bluetooth Dongle",
        bus_number: int = 1,
        device_address: int = 7,
        port_numbers: list[int] | None = None,
    ) -> None:
        self.vendor_id = vendor_id
        self.product_id = product_id
        self.device_class = device_class
        self.device_subclass = device_subclass
        self.device_protocol = device_protocol
        self.serial_number = serial_number
        self.manufacturer = manufacturer
        self.product = product
        self.bus_number = bus_number
        self.device_address = device_address
        self.port_numbers = [2, 4] if port_numbers is None else port_numbers

    def getVendorID(self) -> int:
        return self.vendor_id

    def getProductID(self) -> int:
        return self.product_id

    def getDeviceClass(self) -> int:
        return self.device_class

    def getDeviceSubClass(self) -> int:
        return self.device_subclass

    def getDeviceProtocol(self) -> int:
        return self.device_protocol

    def getSerialNumber(self) -> str | None:
        return self.serial_number

    def getManufacturer(self) -> str | None:
        return self.manufacturer

    def getProduct(self) -> str | None:
        return self.product

    def getBusNumber(self) -> int:
        return self.bus_number

    def getDeviceAddress(self) -> int:
        return self.device_address

    def getPortNumberList(self) -> list[int]:
        return self.port_numbers

    def __iter__(self) -> Iterator[object]:
        return iter(())

    def open(self) -> object:
        pytest.fail("list_adapters() must not open USB devices")


def test_list_adapters_and_adapter_info_are_public_root_exports() -> None:
    assert callable(list_adapters)
    assert AdapterInfo.__name__ == "AdapterInfo"


def test_adapter_discovery_error_is_public_swbt_error() -> None:
    assert issubclass(AdapterDiscoveryError, SwbtError)


def test_list_adapters_returns_hci_device_name_from_fake_enumerator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (FakeUsbDevice(),),
    )

    adapters = list_adapters()

    assert adapters[0].name == "usb:0"


def test_list_adapters_copies_usb_descriptor_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (
            FakeUsbDevice(
                vendor_id=0x0A12,
                product_id=0x0001,
                manufacturer="Cambridge Silicon Radio",
                product="Bluetooth Dongle",
                serial_number="ABC123",
                bus_number=1,
                device_address=7,
                port_numbers=[2, 4],
            ),
        ),
    )

    adapter = list_adapters()[0]

    assert adapter.vendor_id == 0x0A12
    assert adapter.product_id == 0x0001
    assert adapter.manufacturer == "Cambridge Silicon Radio"
    assert adapter.product == "Bluetooth Dongle"
    assert adapter.serial_number == "ABC123"
    assert adapter.bus_number == 1
    assert adapter.device_address == 7
    assert adapter.port_numbers == (2, 4)
    assert adapter.is_bluetooth_hci is True


def test_list_adapters_adds_duplicate_and_serial_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (
            FakeUsbDevice(serial_number="ABC123"),
            FakeUsbDevice(serial_number="XYZ789"),
        ),
    )

    first, second = list_adapters()

    assert first.name == "usb:0"
    assert first.aliases == ("usb:0A12:0001", "usb:0A12:0001/ABC123")
    assert second.name == "usb:1"
    assert second.aliases == ("usb:0A12:0001#1", "usb:0A12:0001/XYZ789")


def test_list_adapters_keeps_candidate_when_descriptor_strings_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DescriptorFailureError(Exception):
        pass

    class DescriptorFailingDevice(FakeUsbDevice):
        def getSerialNumber(self) -> str:
            raise DescriptorFailureError

        def getManufacturer(self) -> str:
            raise DescriptorFailureError

        def getProduct(self) -> str:
            raise DescriptorFailureError

    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (DescriptorFailingDevice(),),
    )
    monkeypatch.setattr(
        adapter_discovery,
        "_is_usb_error",
        lambda error: isinstance(error, DescriptorFailureError),
    )

    adapter = list_adapters()[0]

    assert adapter.name == "usb:0"
    assert adapter.serial_number is None
    assert adapter.manufacturer is None
    assert adapter.product is None


def test_list_adapters_keeps_none_descriptor_values_as_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MissingDescriptorDevice(FakeUsbDevice):
        def getSerialNumber(self) -> str | None:
            return None

        def getManufacturer(self) -> str | None:
            return None

        def getProduct(self) -> str | None:
            return None

    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (MissingDescriptorDevice(),),
    )

    adapter = list_adapters()[0]

    assert adapter.aliases == ("usb:0A12:0001",)
    assert adapter.serial_number is None
    assert adapter.manufacturer is None
    assert adapter.product is None


def test_list_adapters_excludes_non_hci_usb_devices_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (
            FakeUsbDevice(
                vendor_id=0x1234,
                product_id=0x5678,
                device_class=0x03,
                device_subclass=0x00,
                device_protocol=0x00,
            ),
            FakeUsbDevice(serial_number="ABC123"),
        ),
    )

    adapters = list_adapters()

    assert [adapter.name for adapter in adapters] == ["usb:0"]
    assert adapters[0].vendor_id == 0x0A12


def test_list_adapters_returns_empty_tuple_when_no_hci_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        adapter_discovery,
        "_iter_usb_devices",
        lambda: (
            FakeUsbDevice(
                vendor_id=0x1234,
                product_id=0x5678,
                device_class=0x03,
                device_subclass=0x00,
                device_protocol=0x00,
            ),
        ),
    )

    assert list_adapters() == ()


def test_list_adapters_wraps_enumeration_failure_as_discovery_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DiscoveryBackendFailureError(Exception):
        pass

    backend_failure = DiscoveryBackendFailureError("libusb unavailable")

    def fail_enumeration() -> tuple[FakeUsbDevice, ...]:
        raise backend_failure

    monkeypatch.setattr(adapter_discovery, "_iter_usb_devices", fail_enumeration)

    with pytest.raises(AdapterDiscoveryError) as exc_info:
        list_adapters()

    error = exc_info.value
    assert error.__cause__ is backend_failure
    assert error.backend == "bumble-usb"
    assert error.platform
    assert error.libusb_available is None
    assert error.bumble_version


def test_list_adapters_does_not_open_transport_or_gamepad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class NoOpenDevice(FakeUsbDevice):
        def open(self) -> object:
            calls.append("device.open")
            return object()

    def fail_open_transport(*_args: object, **_kwargs: object) -> None:
        calls.append("open_transport")

    def fail_open_usb_transport(*_args: object, **_kwargs: object) -> None:
        calls.append("open_usb_transport")

    def fail_gamepad(*_args: object, **_kwargs: object) -> None:
        calls.append("SwitchGamepad")

    monkeypatch.setattr(adapter_discovery, "_iter_usb_devices", lambda: (NoOpenDevice(),))
    monkeypatch.setattr(adapter_discovery, "open_transport", fail_open_transport, raising=False)
    monkeypatch.setattr(
        adapter_discovery,
        "open_usb_transport",
        fail_open_usb_transport,
        raising=False,
    )
    monkeypatch.setattr(adapter_discovery, "SwitchGamepad", fail_gamepad, raising=False)

    list_adapters()

    assert calls == []
