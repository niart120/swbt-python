import pytest

from swbt.errors import ProtocolError
from swbt.protocol.profile import ControllerColors, ProControllerProfile
from swbt.protocol.spi import VirtualSpiFlash


def test_virtual_spi_flash_returns_seeded_device_type() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x6012, 1) == b"\x03"


def test_virtual_spi_flash_returns_seeded_default_controller_colors() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x6050, 12) == bytes.fromhex("32 32 32 ff ff ff 00 b2 ff ff 3b 30")


def test_virtual_spi_flash_returns_seeded_color_info_exists_flag() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x601B, 1) == b"\x01"


def test_virtual_spi_flash_returns_seeded_custom_controller_colors() -> None:
    profile = ProControllerProfile(
        controller_colors=ControllerColors(
            body=0x112233,
            buttons=0x445566,
            left_grip=0x778899,
            right_grip=0xAABBCC,
        )
    )
    spi = VirtualSpiFlash(profile=profile)

    assert spi.read(0x6050, 12) == bytes.fromhex("11 22 33 44 55 66 77 88 99 aa bb cc")


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
