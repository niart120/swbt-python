"""Input state value objects."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

from swbt.errors import InvalidInputError


class Button(Enum):
    """Buttons exposed by the input model."""

    A = auto()
    B = auto()
    X = auto()
    Y = auto()
    L = auto()
    R = auto()
    ZL = auto()
    ZR = auto()
    PLUS = auto()
    MINUS = auto()
    HOME = auto()
    CAPTURE = auto()
    LEFT_STICK = auto()
    RIGHT_STICK = auto()
    DPAD_UP = auto()
    DPAD_DOWN = auto()
    DPAD_LEFT = auto()
    DPAD_RIGHT = auto()


@dataclass(frozen=True)
class Stick:
    """12-bit raw stick position."""

    x: int
    y: int

    MIN = 0
    CENTER = 2048
    MAX = 4095

    @classmethod
    def center(cls) -> "Stick":
        """Return the neutral stick position."""
        return cls(x=cls.CENTER, y=cls.CENTER)

    @classmethod
    def raw(cls, *, x: int, y: int) -> "Stick":
        """Return a stick position from 12-bit raw values."""
        cls._validate_axis("x", x)
        cls._validate_axis("y", y)
        return cls(x=x, y=y)

    @classmethod
    def normalized(cls, *, x: float, y: float) -> "Stick":
        """Return a stick position from values in the -1.0..1.0 range."""
        return cls.raw(
            x=cls._normalized_axis_to_raw("x", x),
            y=cls._normalized_axis_to_raw("y", y),
        )

    @classmethod
    def _validate_axis(cls, axis_name: str, value: int) -> None:
        if not cls.MIN <= value <= cls.MAX:
            msg = f"{axis_name} must be between {cls.MIN} and {cls.MAX}: {value}"
            raise InvalidInputError(msg)

    @classmethod
    def _normalized_axis_to_raw(cls, axis_name: str, value: float) -> int:
        if not -1.0 <= value <= 1.0:
            msg = f"{axis_name} must be between -1.0 and 1.0: {value}"
            raise InvalidInputError(msg)
        if value < 0:
            return cls.CENTER + round(value * (cls.CENTER - cls.MIN))
        return cls.CENTER + round(value * (cls.MAX - cls.CENTER))


@dataclass(frozen=True)
class IMUFrame:
    """One neutral 6-axis IMU frame."""

    accel_x: int
    accel_y: int
    accel_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int

    @classmethod
    def neutral(cls) -> "IMUFrame":
        """Return an IMU frame with no movement."""
        return cls(accel_x=0, accel_y=0, accel_z=0, gyro_x=0, gyro_y=0, gyro_z=0)


@dataclass(frozen=True)
class InputState:
    """Immutable controller input state."""

    buttons: frozenset[Button]
    left_stick: Stick
    right_stick: Stick
    imu_frames: tuple[IMUFrame, IMUFrame, IMUFrame]

    @classmethod
    def neutral(cls) -> "InputState":
        """Return a state with no buttons pressed and centered sticks."""
        neutral_imu = IMUFrame.neutral()
        return cls(
            buttons=frozenset(),
            left_stick=Stick.center(),
            right_stick=Stick.center(),
            imu_frames=(neutral_imu, neutral_imu, neutral_imu),
        )

    def with_buttons(self, buttons: Iterable[Button]) -> "InputState":
        """Return a state with a replaced button set."""
        return InputState(
            buttons=frozenset(buttons),
            left_stick=self.left_stick,
            right_stick=self.right_stick,
            imu_frames=self.imu_frames,
        )

    def with_sticks(
        self,
        *,
        left_stick: Stick | None = None,
        right_stick: Stick | None = None,
    ) -> "InputState":
        """Return a state with replaced stick values."""
        return InputState(
            buttons=self.buttons,
            left_stick=left_stick if left_stick is not None else self.left_stick,
            right_stick=right_stick if right_stick is not None else self.right_stick,
            imu_frames=self.imu_frames,
        )
