"""Input state value objects."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

from swbt.errors import InvalidInputError
from swbt.imu import DEFAULT_GYRO_CALIBRATION


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
    SL = auto()
    SR = auto()
    DPAD_UP = auto()
    DPAD_DOWN = auto()
    DPAD_LEFT = auto()
    DPAD_RIGHT = auto()


@dataclass(frozen=True)
class Stick:
    """12-bit raw stick position.

    Args:
        x: Horizontal raw axis value in the inclusive ``0..4095`` range.
        y: Vertical raw axis value in the inclusive ``0..4095`` range.

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
    def tilt(cls, x: float, y: float) -> "Stick":
        """Return a stick position from normalized tilt values.

        Args:
            x: Horizontal tilt in the inclusive ``-1.0..1.0`` range.
            y: Vertical tilt in the inclusive ``-1.0..1.0`` range.

        Returns:
            Stick: Raw stick position converted from normalized tilt values.

        Raises:
            InvalidInputError: Either tilt axis is outside the supported range.
        """
        return cls.normalized(x=x, y=y)

    @classmethod
    def up(cls, amount: float = 1.0) -> "Stick":
        """Return an upward stick tilt.

        Args:
            amount: Tilt amount in the inclusive ``0.0..1.0`` range.

        Returns:
            Stick: Stick tilted upward by ``amount``.

        Raises:
            InvalidInputError: ``amount`` is outside the supported range.
        """
        cls._validate_amount(amount)
        return cls.tilt(0.0, amount)

    @classmethod
    def down(cls, amount: float = 1.0) -> "Stick":
        """Return a downward stick tilt.

        Args:
            amount: Tilt amount in the inclusive ``0.0..1.0`` range.

        Returns:
            Stick: Stick tilted downward by ``amount``.

        Raises:
            InvalidInputError: ``amount`` is outside the supported range.
        """
        cls._validate_amount(amount)
        return cls.tilt(0.0, -amount)

    @classmethod
    def left(cls, amount: float = 1.0) -> "Stick":
        """Return a leftward stick tilt.

        Args:
            amount: Tilt amount in the inclusive ``0.0..1.0`` range.

        Returns:
            Stick: Stick tilted left by ``amount``.

        Raises:
            InvalidInputError: ``amount`` is outside the supported range.
        """
        cls._validate_amount(amount)
        return cls.tilt(-amount, 0.0)

    @classmethod
    def right(cls, amount: float = 1.0) -> "Stick":
        """Return a rightward stick tilt.

        Args:
            amount: Tilt amount in the inclusive ``0.0..1.0`` range.

        Returns:
            Stick: Stick tilted right by ``amount``.

        Raises:
            InvalidInputError: ``amount`` is outside the supported range.
        """
        cls._validate_amount(amount)
        return cls.tilt(amount, 0.0)

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

    @classmethod
    def _validate_amount(cls, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            msg = f"amount must be between 0.0 and 1.0: {value}"
            raise InvalidInputError(msg)


@dataclass(frozen=True)
class IMUFrame:
    """One 6-axis IMU frame.

    Args:
        accel_x: Accelerometer X-axis raw value.
        accel_y: Accelerometer Y-axis raw value.
        accel_z: Accelerometer Z-axis raw value.
        gyro_x: Gyroscope X-axis raw value.
        gyro_y: Gyroscope Y-axis raw value.
        gyro_z: Gyroscope Z-axis raw value.

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
    def raw(
        cls,
        *,
        accel: tuple[int, int, int] | None = None,
        gyro: tuple[int, int, int] | None = None,
    ) -> "IMUFrame":
        """Return an IMU frame from raw accelerometer and gyroscope axes.

        Args:
            accel: Optional accelerometer ``(x, y, z)`` raw values.
            gyro: Optional gyroscope ``(x, y, z)`` raw values.

        Returns:
            IMUFrame: Frame with omitted sensor axes set to zero.

        Raises:
            InvalidInputError: A supplied axis tuple does not contain three values
                or any value is outside the supported signed 16-bit range.
        """
        accel_x, accel_y, accel_z = cls._defaulted_axes("accel", accel)
        gyro_x, gyro_y, gyro_z = cls._defaulted_axes("gyro", gyro)
        return cls(
            accel_x=accel_x,
            accel_y=accel_y,
            accel_z=accel_z,
            gyro_x=gyro_x,
            gyro_y=gyro_y,
            gyro_z=gyro_z,
        )

    @classmethod
    def gyro(cls, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame":
        """Return an IMU frame with only gyroscope axes set.

        Args:
            x: Gyroscope X-axis raw value.
            y: Gyroscope Y-axis raw value.
            z: Gyroscope Z-axis raw value.

        Returns:
            IMUFrame: Frame with gyroscope values set and accelerometer values zeroed.

        Raises:
            InvalidInputError: Any value is outside the supported signed 16-bit range.
        """
        return cls.raw(gyro=(x, y, z))

    @classmethod
    def gyro_rate(
        cls,
        *,
        x_rad_s: float = 0.0,
        y_rad_s: float = 0.0,
        z_rad_s: float = 0.0,
    ) -> "IMUFrame":
        """Return a frame from XYZ gyroscope rates in radians per second.

        Args:
            x_rad_s: X-axis angular velocity in radians per second.
            y_rad_s: Y-axis angular velocity in radians per second.
            z_rad_s: Z-axis angular velocity in radians per second.

        Returns:
            IMUFrame: Frame with converted gyroscope raw values and zero accelerometer.

        Raises:
            InvalidInputError: A converted raw value is outside the signed 16-bit range.
        """
        return cls.raw(gyro=DEFAULT_GYRO_CALIBRATION.gyro_rates_to_raw((x_rad_s, y_rad_s, z_rad_s)))

    def to_gyro_rate(self) -> tuple[float, float, float]:
        """Return XYZ gyroscope rates in radians per second.

        Returns:
            tuple[float, float, float]: X, Y, and Z angular velocities in radians per
                second.
        """
        return DEFAULT_GYRO_CALIBRATION.raw_to_gyro_rates((self.gyro_x, self.gyro_y, self.gyro_z))

    @classmethod
    def accel(cls, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame":
        """Return an IMU frame with only accelerometer axes set.

        Args:
            x: Accelerometer X-axis raw value.
            y: Accelerometer Y-axis raw value.
            z: Accelerometer Z-axis raw value.

        Returns:
            IMUFrame: Frame with accelerometer values set and gyroscope values zeroed.

        Raises:
            InvalidInputError: Any value is outside the supported signed 16-bit range.
        """
        return cls.raw(accel=(x, y, z))

    def with_gyro(self, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame":
        """Return a frame with replaced gyroscope axes.

        Args:
            x: Replacement gyroscope X-axis raw value.
            y: Replacement gyroscope Y-axis raw value.
            z: Replacement gyroscope Z-axis raw value.

        Returns:
            IMUFrame: Copy of this frame with accelerometer axes preserved.

        Raises:
            InvalidInputError: Any value is outside the supported signed 16-bit range.
        """
        return IMUFrame.raw(
            accel=(self.accel_x, self.accel_y, self.accel_z),
            gyro=(x, y, z),
        )

    def with_accel(self, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame":
        """Return a frame with replaced accelerometer axes.

        Args:
            x: Replacement accelerometer X-axis raw value.
            y: Replacement accelerometer Y-axis raw value.
            z: Replacement accelerometer Z-axis raw value.

        Returns:
            IMUFrame: Copy of this frame with gyroscope axes preserved.

        Raises:
            InvalidInputError: Any value is outside the supported signed 16-bit range.
        """
        return IMUFrame.raw(
            accel=(x, y, z),
            gyro=(self.gyro_x, self.gyro_y, self.gyro_z),
        )

    @classmethod
    def _validate_i16(cls, field_name: str, value: object) -> int:
        if not isinstance(value, int) or not cls.MIN <= value <= cls.MAX:
            msg = f"{field_name} must be an int between {cls.MIN} and {cls.MAX}: {value}"
            raise InvalidInputError(msg)
        return value

    @classmethod
    def _defaulted_axes(
        cls,
        name: str,
        values: tuple[int, int, int] | None,
    ) -> tuple[int, int, int]:
        if values is None:
            return (0, 0, 0)
        return cls._validate_axes(name, values)

    @classmethod
    def _validate_axes(cls, name: str, values: object) -> tuple[int, int, int]:
        if not isinstance(values, tuple) or len(values) != 3:
            msg = f"{name} must be a tuple of three raw values"
            raise InvalidInputError(msg)
        x, y, z = values
        return (
            cls._validate_i16(f"{name}_x", x),
            cls._validate_i16(f"{name}_y", y),
            cls._validate_i16(f"{name}_z", z),
        )


@dataclass(frozen=True)
class InputState:
    """Immutable controller input state.

    Args:
        buttons: Pressed buttons represented as an immutable set.
        left_stick: Current left stick position.
        right_stick: Current right stick position.
        imu_frames: Three IMU frames included in the next input report.

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

    def with_imu(self, *frames: IMUFrame) -> "InputState":
        """Return a state with replaced IMU frames.

        Args:
            frames: One frame to repeat across all three IMU slots, or exactly three
                frames to store in order.

        Returns:
            InputState: Copy of this state with supplied IMU frames.

        Raises:
            InvalidInputError: The frame count is not one or three, or any value is
                not an ``IMUFrame``.
        """
        return InputState(
            buttons=self.buttons,
            left_stick=self.left_stick,
            right_stick=self.right_stick,
            imu_frames=self._normalize_imu_frames(frames),
        )

    def with_gyro(self, *samples: tuple[int, int, int]) -> "InputState":
        """Return a state with replaced gyroscope axes.

        Args:
            samples: One ``(x, y, z)`` sample to repeat across all frames, or exactly
                three samples to apply in order.

        Returns:
            InputState: Copy of this state with accelerometer axes preserved.

        Raises:
            InvalidInputError: The sample count is not one or three, a sample is not a
                three-value tuple, or any value is outside the signed 16-bit range.
        """
        normalized = self._normalize_imu_samples("gyro", samples)
        return self.with_imu(
            *(
                frame.with_gyro(*sample)
                for frame, sample in zip(self.imu_frames, normalized, strict=True)
            )
        )

    def with_accel(self, *samples: tuple[int, int, int]) -> "InputState":
        """Return a state with replaced accelerometer axes.

        Args:
            samples: One ``(x, y, z)`` sample to repeat across all frames, or exactly
                three samples to apply in order.

        Returns:
            InputState: Copy of this state with gyroscope axes preserved.

        Raises:
            InvalidInputError: The sample count is not one or three, a sample is not a
                three-value tuple, or any value is outside the signed 16-bit range.
        """
        normalized = self._normalize_imu_samples("accel", samples)
        return self.with_imu(
            *(
                frame.with_accel(*sample)
                for frame, sample in zip(self.imu_frames, normalized, strict=True)
            )
        )

    @staticmethod
    def _normalize_imu_frames(
        frames: tuple[IMUFrame, ...],
    ) -> tuple[IMUFrame, IMUFrame, IMUFrame]:
        if len(frames) == 1:
            frame = frames[0]
            if not isinstance(frame, IMUFrame):
                msg = "frames must contain IMUFrame values"
                raise InvalidInputError(msg)
            return (frame, frame, frame)
        if len(frames) == 3:
            frame1, frame2, frame3 = frames
            if not all(isinstance(frame, IMUFrame) for frame in frames):
                msg = "frames must contain IMUFrame values"
                raise InvalidInputError(msg)
            return (frame1, frame2, frame3)
        msg = f"expected 1 or 3 IMU frames, got {len(frames)}"
        raise InvalidInputError(msg)

    @staticmethod
    def _normalize_imu_samples(
        name: str,
        samples: tuple[tuple[int, int, int], ...],
    ) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]:
        if len(samples) == 1:
            sample = IMUFrame._validate_axes(name, samples[0])
            return (sample, sample, sample)
        if len(samples) == 3:
            sample1, sample2, sample3 = (
                IMUFrame._validate_axes(name, sample) for sample in samples
            )
            return (sample1, sample2, sample3)
        msg = f"expected 1 or 3 IMU {name} samples, got {len(samples)}"
        raise InvalidInputError(msg)
