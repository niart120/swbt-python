"""Public concrete gamepad controllers."""

from swbt.diagnostics import DiagnosticsConfig
from swbt.gamepad.interface import DirectSwitchGamepad, PeriodicSwitchGamepad
from swbt.protocol.profiles.base import ControllerColors
from swbt.protocol.profiles.joycon import JoyConLeftProfile, JoyConRightProfile
from swbt.protocol.profiles.pro_controller import default_controller_profile


class ProController(PeriodicSwitchGamepad):
    """Runtime-backed Pro Controller-compatible gamepad."""

    _profile = default_controller_profile()

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a Pro Controller-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned pairing profile path.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: adapter is omitted or report_period_us is not positive.
        """
        self._initialize_runtime(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class JoyConL(PeriodicSwitchGamepad):
    """Runtime-backed Joy-Con L-compatible gamepad."""

    _profile = JoyConLeftProfile()

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a left Joy-Con-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned pairing profile path.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        self._initialize_runtime(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class JoyConR(PeriodicSwitchGamepad):
    """Runtime-backed Joy-Con R-compatible gamepad."""

    _profile = JoyConRightProfile()

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a right Joy-Con-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned pairing profile path.
            report_period_us: Optional periodic input report interval in microseconds.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted or ``report_period_us`` is not positive.
        """
        self._initialize_runtime(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=report_period_us,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class DirectProController(DirectSwitchGamepad):
    """Direct-reporting Pro Controller-compatible gamepad."""

    _profile = default_controller_profile()

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a direct-reporting Pro Controller-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned pairing profile path.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted.
        """
        self._initialize_runtime(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=None,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class DirectJoyConL(DirectSwitchGamepad):
    """Direct-reporting Joy-Con L-compatible gamepad."""

    _profile = JoyConLeftProfile()

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a direct-reporting Joy-Con L-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned pairing profile path.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted.
        """
        self._initialize_runtime(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=None,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )


class DirectJoyConR(DirectSwitchGamepad):
    """Direct-reporting Joy-Con R-compatible gamepad."""

    _profile = JoyConRightProfile()

    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None:
        """Create a direct-reporting Joy-Con R-compatible gamepad.

        Args:
            adapter: Bumble adapter moniker used for the Bluetooth backend.
            profile_path: Optional swbt-owned pairing profile path.
            controller_colors: Optional fixed controller body, button, and grip colors.
            diagnostics: Optional diagnostics configuration for trace output.

        Raises:
            InvalidInputError: ``adapter`` is omitted.
        """
        self._initialize_runtime(
            adapter=adapter,
            profile_path=profile_path,
            report_period_us=None,
            controller_colors=controller_colors,
            diagnostics=diagnostics,
        )
