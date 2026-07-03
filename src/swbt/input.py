"""Input state value objects."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

from swbt.errors import InvalidInputError


class Button(Enum):
    """Buttons exposed by the input model.

    Each member maps to one supported gamepad button. The HID bit positions are
    defined by the protocol layer and its tests, not by the enum values.
    """

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
    """12-bit raw stick position.

    Attributes:
        x: Horizontal raw axis value in the inclusive ``0..4095`` range.
        y: Vertical raw axis value in the inclusive ``0..4095`` range.
    """

    x: int
    y: int

    MIN = 0
    CENTER = 2048
    MAX = 4095

    def __post_init__(self) -> None:
        """Validate direct dataclass construction."""
        self._validate_axis("x", self.x)
        self._validate_axis("y", self.y)

    @classmethod
    def center(cls) -> "Stick":
        """Return the neutral stick position.

        Returns:
            Stick: Centered stick with both axes set to ``CENTER``.
        """
        return cls(x=cls.CENTER, y=cls.CENTER)

    @classmethod
    def raw(cls, *, x: int, y: int) -> "Stick":
        """Return a stick position from 12-bit raw values.

        Args:
            x: Horizontal raw axis value.
            y: Vertical raw axis value.

        Returns:
            Stick: Stick position with the supplied raw axis values.

        Raises:
            InvalidInputError: Either axis is outside the supported raw range.
        """
        cls._validate_axis("x", x)
        cls._validate_axis("y", y)
        return cls(x=x, y=y)

    @classmethod
    def normalized(cls, *, x: float, y: float) -> "Stick":
        """Return a stick position from normalized axis values.

        Args:
            x: Horizontal value in the inclusive ``-1.0..1.0`` range.
            y: Vertical value in the inclusive ``-1.0..1.0`` range.

        Returns:
            Stick: Raw stick position converted from normalized values.

        Raises:
            InvalidInputError: Either normalized axis is outside the supported range.
        """
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
    """One 6-axis IMU frame.

    Attributes:
        accel_x: Accelerometer X-axis raw value.
        accel_y: Accelerometer Y-axis raw value.
        accel_z: Accelerometer Z-axis raw value.
        gyro_x: Gyroscope X-axis raw value.
        gyro_y: Gyroscope Y-axis raw value.
        gyro_z: Gyroscope Z-axis raw value.
    """

    accel_x: int
    accel_y: int
    accel_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int

    MIN = -32768
    MAX = 32767

    def __post_init__(self) -> None:
        """Validate direct dataclass construction."""
        for field_name in (
            "accel_x",
            "accel_y",
            "accel_z",
            "gyro_x",
            "gyro_y",
            "gyro_z",
        ):
            self._validate_i16(field_name, getattr(self, field_name))

    @classmethod
    def neutral(cls) -> "IMUFrame":
        """Return an IMU frame with no movement.

        Returns:
            IMUFrame: Frame with all accelerometer and gyroscope values set to zero.
        """
        return cls(accel_x=0, accel_y=0, accel_z=0, gyro_x=0, gyro_y=0, gyro_z=0)

    @classmethod
    def _validate_i16(cls, field_name: str, value: int) -> None:
        if not cls.MIN <= value <= cls.MAX:
            msg = f"{field_name} must be between {cls.MIN} and {cls.MAX}: {value}"
            raise InvalidInputError(msg)


@dataclass(frozen=True)
class InputState:
    """Immutable controller input state.

    Attributes:
        buttons: Pressed buttons represented as an immutable set.
        left_stick: Current left stick position.
        right_stick: Current right stick position.
        imu_frames: Three IMU frames included in the next input report.
    """

    buttons: frozenset[Button]
    left_stick: Stick
    right_stick: Stick
    imu_frames: tuple[IMUFrame, IMUFrame, IMUFrame]

    @classmethod
    def neutral(cls) -> "InputState":
        """Return a state with no buttons pressed and centered sticks.

        Returns:
            InputState: Neutral state with centered sticks and neutral IMU frames.
        """
        neutral_imu = IMUFrame.neutral()
        return cls(
            buttons=frozenset(),
            left_stick=Stick.center(),
            right_stick=Stick.center(),
            imu_frames=(neutral_imu, neutral_imu, neutral_imu),
        )

    def with_buttons(self, buttons: Iterable[Button]) -> "InputState":
        """Return a state with a replaced button set.

        Args:
            buttons: Buttons that should be pressed in the returned state.

        Returns:
            InputState: Copy of this state with the supplied button set.
        """
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
        """Return a state with replaced stick values.

        Args:
            left_stick: Optional replacement for the left stick.
            right_stick: Optional replacement for the right stick.

        Returns:
            InputState: Copy of this state with supplied stick replacements.
        """
        return InputState(
            buttons=self.buttons,
            left_stick=left_stick if left_stick is not None else self.left_stick,
            right_stick=right_stick if right_stick is not None else self.right_stick,
            imu_frames=self.imu_frames,
        )
