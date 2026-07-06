"""Default transport factory for SwitchGamepad."""

from dataclasses import dataclass
from typing import Protocol

from swbt.diagnostics import DiagnosticsRecorder
from swbt.protocol.profile import ControllerProfile
from swbt.transport.base import HidDeviceTransport


class _TransportFactory(Protocol):
    def create(
        self,
        *,
        adapter: str,
        device_name: str,
        profile: ControllerProfile,
        diagnostics: DiagnosticsRecorder,
        key_store_path: str | None,
    ) -> HidDeviceTransport: ...


@dataclass(frozen=True)
class _StaticTransportFactory:
    transport: HidDeviceTransport

    def create(
        self,
        *,
        adapter: str,
        device_name: str,
        profile: ControllerProfile,
        diagnostics: DiagnosticsRecorder,
        key_store_path: str | None,
    ) -> HidDeviceTransport:
        _ = (adapter, device_name, profile, diagnostics, key_store_path)
        return self.transport


def create_default_transport(
    *,
    adapter: str,
    device_name: str,
    profile: ControllerProfile,
    diagnostics: DiagnosticsRecorder,
    key_store_path: str | None,
) -> HidDeviceTransport:
    """Create the default Bumble-backed transport without importing Bumble at API import time."""
    from swbt.transport.bumble import BumbleHidTransport  # noqa: PLC0415

    return BumbleHidTransport(
        adapter=adapter,
        device_name=device_name,
        profile=profile,
        diagnostics=diagnostics,
        key_store_path=key_store_path,
    )
