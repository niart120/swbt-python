"""No-open USB Bluetooth adapter discovery."""

# ruff: noqa: N802

import platform as platform_module
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Protocol, cast

from swbt.errors import AdapterDiscoveryError
from swbt.transport import _bumble_usb_devices

USB_DEVICE_CLASS_DEVICE = 0x00
USB_DEVICE_CLASS_WIRELESS_CONTROLLER = 0xE0
USB_DEVICE_SUBCLASS_RF_CONTROLLER = 0x01
USB_DEVICE_PROTOCOL_BLUETOOTH_PRIMARY_CONTROLLER = 0x01

USB_BT_HCI_CLASS_TUPLE = (
    USB_DEVICE_CLASS_WIRELESS_CONTROLLER,
    USB_DEVICE_SUBCLASS_RF_CONTROLLER,
    USB_DEVICE_PROTOCOL_BLUETOOTH_PRIMARY_CONTROLLER,
)


class _UsbSetting(Protocol):
    """USB interface setting shape used for HCI class detection."""

    def getClass(self) -> int: ...
    def getSubClass(self) -> int: ...
    def getProtocol(self) -> int: ...


class _UsbInterface(Protocol):
    """USB interface shape used for HCI class detection."""

    def __iter__(self) -> Iterator[_UsbSetting]: ...


class _UsbConfiguration(Protocol):
    """USB configuration shape used for HCI class detection."""

    def __iter__(self) -> Iterator[_UsbInterface]: ...


class _UsbDevice(Protocol):
    """USB device shape consumed without opening the device handle."""

    def getVendorID(self) -> int: ...
    def getProductID(self) -> int: ...
    def getDeviceClass(self) -> int: ...
    def getDeviceSubClass(self) -> int: ...
    def getDeviceProtocol(self) -> int: ...
    def getSerialNumber(self) -> str | None: ...
    def getManufacturer(self) -> str | None: ...
    def getProduct(self) -> str | None: ...
    def getBusNumber(self) -> int: ...
    def getDeviceAddress(self) -> int: ...
    def getPortNumberList(self) -> list[int]: ...
    def __iter__(self) -> Iterator[_UsbConfiguration]: ...


@dataclass(frozen=True, slots=True)
class AdapterInfo:
    """USB Bluetooth adapter candidate.

    Args:
        name: Primary adapter moniker passed to ``ProController(adapter=...)``.
        aliases: Alternative adapter monikers for the same USB device.
        vendor_id: USB vendor ID.
        product_id: USB product ID.
        manufacturer: USB manufacturer string when available.
        product: USB product string when available.
        serial_number: USB serial number when available.
        bus_number: USB bus number when available.
        device_address: USB device address when available.
        port_numbers: USB port path numbers when available.
        is_bluetooth_hci: Whether the USB device is classified as Bluetooth HCI.

    Attributes:
        name: Primary adapter moniker passed to ``ProController(adapter=...)``.
        aliases: Alternative adapter monikers for the same USB device.
        vendor_id: USB vendor ID.
        product_id: USB product ID.
        manufacturer: USB manufacturer string when available.
        product: USB product string when available.
        serial_number: USB serial number when available.
        bus_number: USB bus number when available.
        device_address: USB device address when available.
        port_numbers: USB port path numbers when available.
        is_bluetooth_hci: Whether the USB device is classified as Bluetooth HCI.
    """

    name: str
    aliases: tuple[str, ...] = ()
    vendor_id: int | None = None
    product_id: int | None = None
    manufacturer: str | None = None
    product: str | None = None
    serial_number: str | None = None
    bus_number: int | None = None
    device_address: int | None = None
    port_numbers: tuple[int, ...] = ()
    is_bluetooth_hci: bool = True


def list_adapters() -> tuple[AdapterInfo, ...]:
    """Return USB Bluetooth adapter candidates without opening them.

    Returns:
        Immutable snapshot of adapter candidates. An empty tuple means no
        Bluetooth HCI candidates were found.

    Raises:
        AdapterDiscoveryError: USB device enumeration cannot be started.
    """
    try:
        return tuple(_build_adapter_infos(_iter_usb_devices()))
    except AdapterDiscoveryError:
        raise
    except Exception as error:
        msg = "failed to discover USB Bluetooth adapters without opening them"
        raise _discovery_error(msg) from error


def _build_adapter_infos(devices: Iterable[_UsbDevice]) -> Iterator[AdapterInfo]:
    seen_serials_by_id: dict[tuple[int, int], list[str | None]] = {}
    hci_index = 0

    for device in devices:
        if not _is_bluetooth_hci(device):
            continue

        vendor_id = device.getVendorID()
        product_id = device.getProductID()
        device_id = (vendor_id, product_id)
        serial_number = _optional_descriptor(device.getSerialNumber)
        manufacturer = _optional_descriptor(device.getManufacturer)
        product = _optional_descriptor(device.getProduct)
        primary_name = f"usb:{hci_index}"
        basic_name = f"usb:{vendor_id:04X}:{product_id:04X}"
        transport_names = [primary_name]

        if device_id not in seen_serials_by_id:
            transport_names.append(basic_name)
        else:
            transport_names.append(f"{basic_name}#{len(seen_serials_by_id[device_id])}")

        if serial_number is not None and (
            device_id not in seen_serials_by_id
            or serial_number not in seen_serials_by_id[device_id]
        ):
            transport_names.append(f"{basic_name}/{serial_number}")

        seen_serials_by_id.setdefault(device_id, []).append(serial_number)
        hci_index += 1

        yield AdapterInfo(
            name=primary_name,
            aliases=tuple(name for name in transport_names if name != primary_name),
            vendor_id=vendor_id,
            product_id=product_id,
            manufacturer=manufacturer,
            product=product,
            serial_number=serial_number,
            bus_number=device.getBusNumber(),
            device_address=device.getDeviceAddress(),
            port_numbers=tuple(device.getPortNumberList()),
            is_bluetooth_hci=True,
        )


def _iter_usb_devices() -> Iterator[_UsbDevice]:
    yield from cast("Iterator[_UsbDevice]", _bumble_usb_devices.iter_usb_devices())


def _is_bluetooth_hci(device: _UsbDevice) -> bool:
    if (
        device.getDeviceClass(),
        device.getDeviceSubClass(),
        device.getDeviceProtocol(),
    ) == USB_BT_HCI_CLASS_TUPLE:
        return True

    if device.getDeviceClass() != USB_DEVICE_CLASS_DEVICE:
        return False

    for configuration in device:
        for interface in configuration:
            for setting in interface:
                if (
                    setting.getClass(),
                    setting.getSubClass(),
                    setting.getProtocol(),
                ) == USB_BT_HCI_CLASS_TUPLE:
                    return True

    return False


def _optional_descriptor(getter: Callable[[], str | None]) -> str | None:
    try:
        value = getter()
    except Exception as error:  # descriptor access differs by OS and driver
        if _is_usb_error(error):
            return None
        raise
    if value is None:
        return None
    return str(value)


def _is_usb_error(error: Exception) -> bool:
    return _bumble_usb_devices.is_usb_error(error)


def _discovery_error(message: str) -> AdapterDiscoveryError:
    return AdapterDiscoveryError(
        message,
        platform=platform_module.platform(),
        backend="bumble-usb",
        libusb_available=None,
        bumble_version=_package_version("bumble"),
    )


def _package_version(package_name: str) -> str:
    try:
        return version(package_name)
    except PackageNotFoundError:
        return "unknown"
