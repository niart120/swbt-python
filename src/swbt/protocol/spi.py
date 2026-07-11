"""Virtual SPI flash."""

from swbt.errors import ProtocolError
from swbt.protocol.profiles.base import ControllerProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile


class VirtualSpiFlash:
    """Read-only SPI flash data used by subcommand replies."""

    ADDRESS_LIMIT = 0x80000
    STORAGE_SIZE = 0x10000
    MAX_READ_SIZE = 0x1D
    ERASED_BYTE = 0xFF
    DEVICE_TYPE_ADDRESS = 0x6012
    COLOR_INFO_EXISTS_ADDRESS = 0x601B
    COLOR_INFO_EXISTS = 0x01
    CONTROLLER_COLORS_ADDRESS = 0x6050
    FACTORY_ACCELEROMETER_CALIBRATION_ADDRESS = 0x6020
    FACTORY_GYRO_CALIBRATION_ADDRESS = 0x602C

    def __init__(self, *, profile: ControllerProfile | None = None) -> None:
        """Create a virtual SPI flash image."""
        profile = profile or default_controller_profile()
        self._data = bytearray([self.ERASED_BYTE] * self.STORAGE_SIZE)
        self._data[self.DEVICE_TYPE_ADDRESS] = profile.device_type
        self._data[self.COLOR_INFO_EXISTS_ADDRESS] = self.COLOR_INFO_EXISTS
        controller_colors = profile.controller_colors.to_spi_bytes()
        self._data[
            self.CONTROLLER_COLORS_ADDRESS : self.CONTROLLER_COLORS_ADDRESS + len(controller_colors)
        ] = controller_colors
        accelerometer_calibration = profile.accelerometer_calibration.to_spi_bytes()
        self._data[
            self.FACTORY_ACCELEROMETER_CALIBRATION_ADDRESS : self.FACTORY_ACCELEROMETER_CALIBRATION_ADDRESS
            + len(accelerometer_calibration)
        ] = accelerometer_calibration
        if profile.gyro_calibration is not None:
            gyro_calibration = profile.gyro_calibration.to_spi_bytes()
            self._data[
                self.FACTORY_GYRO_CALIBRATION_ADDRESS : self.FACTORY_GYRO_CALIBRATION_ADDRESS
                + len(gyro_calibration)
            ] = gyro_calibration

    def read(self, address: int, size: int) -> bytes:
        """Read bytes from the virtual SPI address space."""
        if size > self.MAX_READ_SIZE:
            msg = f"SPI read size must be {self.MAX_READ_SIZE} bytes or less: {size}"
            raise ProtocolError(msg)
        if address < 0 or size < 0 or address + size > self.ADDRESS_LIMIT:
            msg = f"SPI read is outside address space: address=0x{address:x}, size={size}"
            raise ProtocolError(msg)

        out = bytearray()
        for offset in range(size):
            absolute_address = address + offset
            if absolute_address < self.STORAGE_SIZE:
                out.append(self._data[absolute_address])
            else:
                out.append(self.ERASED_BYTE)
        return bytes(out)
