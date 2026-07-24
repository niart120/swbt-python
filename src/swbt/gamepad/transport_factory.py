"""Default transport construction for SwitchGamepad."""

from swbt.diagnostics import DiagnosticsRecorder
from swbt.protocol.profiles.base import ControllerProfile
from swbt.transport.base import HidDeviceTransport


def create_default_transport(
    *,
    adapter: str,
    device_name: str,
    profile: ControllerProfile,
    diagnostics: DiagnosticsRecorder,
    profile_path: str | None = None,
    expected_local_bluetooth_address: bytes | None = None,
) -> HidDeviceTransport:
    """Create the default Bumble-backed transport without importing Bumble at API import time."""
    from swbt.transport.bumble import BumbleHidTransport  # noqa: PLC0415

    if profile_path is None and expected_local_bluetooth_address is None:
        return BumbleHidTransport(
            adapter=adapter,
            device_name=device_name,
            profile=profile,
            diagnostics=diagnostics,
        )
    return BumbleHidTransport(
        adapter=adapter,
        device_name=device_name,
        profile=profile,
        diagnostics=diagnostics,
        profile_path=profile_path,
        expected_local_bluetooth_address=expected_local_bluetooth_address,
    )
