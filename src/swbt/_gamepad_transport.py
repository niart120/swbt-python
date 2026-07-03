"""Default transport factory for SwitchGamepad."""

from swbt.diagnostics import DiagnosticsRecorder
from swbt.transport.base import HidDeviceTransport


def create_default_transport(
    *,
    adapter: str,
    device_name: str,
    diagnostics: DiagnosticsRecorder,
    key_store_path: str | None,
) -> HidDeviceTransport:
    """Create the default Bumble-backed transport without importing Bumble at API import time."""
    from swbt.transport.bumble import BumbleHidTransport  # noqa: PLC0415

    return BumbleHidTransport(
        adapter=adapter,
        device_name=device_name,
        diagnostics=diagnostics,
        key_store_path=key_store_path,
    )
