"""Virtual SPI flash."""

from swbt.errors import ProtocolError


class VirtualSpiFlash:
    """Read-only SPI flash data used by subcommand replies."""

    ADDRESS_LIMIT = 0x80000
    STORAGE_SIZE = 0x10000
    MAX_READ_SIZE = 0x1D
    ERASED_BYTE = 0xFF
    DEVICE_TYPE_ADDRESS = 0x6012
    PRO_CONTROLLER_DEVICE_TYPE = 0x03

    def __init__(self) -> None:
        """Create a virtual SPI flash image."""
        self._data = bytearray([self.ERASED_BYTE] * self.STORAGE_SIZE)
        self._data[self.DEVICE_TYPE_ADDRESS] = self.PRO_CONTROLLER_DEVICE_TYPE

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
