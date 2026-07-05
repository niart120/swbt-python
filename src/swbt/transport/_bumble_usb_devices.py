"""Bumble USB device enumeration boundary."""

from collections.abc import Iterator


def iter_usb_devices() -> Iterator[object]:
    """Yield libusb USB devices without opening device handles.

    Yields:
        USB device objects from ``usb1.USBContext.getDeviceIterator()``.
    """
    import usb1  # noqa: PLC0415
    from bumble.transport.usb import load_libusb  # noqa: PLC0415

    load_libusb()
    with usb1.USBContext() as context:
        yield from context.getDeviceIterator(skip_on_error=True)


def is_usb_error(error: Exception) -> bool:
    """Return whether an exception is a usb1 USBError.

    Args:
        error: Exception raised while reading USB descriptors.

    Returns:
        True when ``error`` is a ``usb1.USBError``.
    """
    try:
        import usb1  # noqa: PLC0415
    except ImportError:
        return False
    return isinstance(error, usb1.USBError)
