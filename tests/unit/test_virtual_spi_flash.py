import pytest

from swbt.errors import ProtocolError
from swbt.imu import AccelerometerCalibration, GyroCalibration
from swbt.protocol.profiles.base import ControllerColors
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import ProControllerProfile
from swbt.protocol.spi import VirtualSpiFlash


def test_virtual_spi_flash_returns_seeded_device_type() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x6012, 1) == b"\x03"


def test_virtual_spi_flash_seeds_device_type_from_profile() -> None:
    assert VirtualSpiFlash(profile=JoyConLeftProfile()).read(0x6012, 1) == b"\x01"
    assert VirtualSpiFlash(profile=JoyConRightProfile()).read(0x6012, 1) == b"\x02"


def test_virtual_spi_flash_returns_seeded_default_controller_colors() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x6050, 12) == bytes.fromhex("32 32 32 ff ff ff 00 b2 ff ff 3b 30")


def test_virtual_spi_flash_returns_seeded_color_info_exists_flag() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x601B, 1) == b"\x01"


def test_virtual_spi_flash_seeds_factory_gyro_calibration_from_profile() -> None:
    assert VirtualSpiFlash().read(0x602C, 12) == bytes.fromhex(
        "00 00 00 00 00 00 3b 34 3b 34 3b 34"
    )

    profile = ProControllerProfile(
        gyro_calibration=GyroCalibration(
            zero_raw=(-1, 2, -3),
            reference_raw=(0x343B, 0x343A, 0x3439),
        )
    )
    assert VirtualSpiFlash(profile=profile).read(0x602C, 12) == bytes.fromhex(
        "ff ff 02 00 fd ff 3b 34 3a 34 39 34"
    )


def test_virtual_spi_flash_seeds_factory_accelerometer_calibration_from_profile() -> None:
    assert VirtualSpiFlash().read(0x6020, 12) == bytes.fromhex(
        "00 00 00 00 00 00 00 40 00 40 00 40"
    )

    profile = ProControllerProfile(
        accelerometer_calibration=AccelerometerCalibration(
            zero_raw=(-1, 2, -3),
            reference_raw=(0x4000, 0x3FFF, 0x3FFE),
        )
    )
    assert VirtualSpiFlash(profile=profile).read(0x6020, 12) == bytes.fromhex(
        "ff ff 02 00 fd ff 00 40 ff 3f fe 3f"
    )


def test_virtual_spi_flash_returns_complete_factory_six_axis_calibration() -> None:
    assert VirtualSpiFlash().read(0x6020, 24) == bytes.fromhex(
        "00 00 00 00 00 00 00 40 00 40 00 40 "
        "00 00 00 00 00 00 3b 34 3b 34 3b 34"
    )


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


def test_virtual_spi_flash_seeds_joycon_default_controller_colors_from_profile() -> None:
    assert VirtualSpiFlash(profile=JoyConLeftProfile()).read(0x6050, 12) == bytes.fromhex(
        "00 b2 ff 32 32 32 00 b2 ff 00 b2 ff"
    )
    assert VirtualSpiFlash(profile=JoyConRightProfile()).read(0x6050, 12) == bytes.fromhex(
        "ff 3b 30 32 32 32 ff 3b 30 ff 3b 30"
    )


def test_virtual_spi_flash_returns_erased_bytes_for_unseeded_address() -> None:
    spi = VirtualSpiFlash()

    assert spi.read(0x70000, 2) == b"\xff\xff"


@pytest.mark.parametrize("profile", [JoyConLeftProfile(), JoyConRightProfile()])
def test_virtual_spi_flash_seeds_factory_sensor_calibration_for_joycon_profiles(
    profile: JoyConLeftProfile | JoyConRightProfile,
) -> None:
    spi = VirtualSpiFlash(profile=profile)

    assert profile.gyro_calibration is not None
    assert spi.read(0x6020, 12) == bytes.fromhex("00 00 00 00 00 00 00 40 00 40 00 40")
    assert spi.read(0x602C, 12) == bytes.fromhex("00 00 00 00 00 00 3b 34 3b 34 3b 34")
    assert spi.read(0x603D, 9) == b"\xff" * 9
    assert spi.read(0x6046, 9) == b"\xff" * 9


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
