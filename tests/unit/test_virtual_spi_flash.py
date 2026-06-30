import pytest

from swbt.errors import ProtocolError
from swbt.protocol.spi import VirtualSpiFlash


def test_virtual_spi_flash_returns_seeded_device_type() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x6012, 1) == b"\x03"


def test_virtual_spi_flash_returns_erased_bytes_for_unseeded_address() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x70000, 2) == b"\xff\xff"


@pytest.mark.parametrize(
    ("address", "size"),
    [
        (0x80000, 1),
        (0x7FFFF, 2),
        (0x6012, 0x1E),
    ],
)
def test_virtual_spi_flash_rejects_out_of_range_reads(address: int, size: int) -> None:
    with pytest.raises(ProtocolError):
        VirtualSpiFlash().read(address, size)
