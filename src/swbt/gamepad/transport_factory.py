"""Default transport factory for SwitchGamepad."""

from dataclasses import dataclass
from typing import Protocol

from swbt.diagnostics import DiagnosticsRecorder
from swbt.protocol.profiles.base import ControllerProfile
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
        profile_path: str | None = None,
        expected_local_bluetooth_address: bytes | None = None,
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
        profile_path: str | None = None,
        expected_local_bluetooth_address: bytes | None = None,
    ) -> HidDeviceTransport:
        _ = (
            adapter,
            device_name,
            profile,
            diagnostics,
            key_store_path,
            profile_path,
            expected_local_bluetooth_address,
        )
        return self.transport


@dataclass(frozen=True)
class _BumbleTransportFactory:
    def create(
        self,
        *,
        adapter: str,
        device_name: str,
        profile: ControllerProfile,
        diagnostics: DiagnosticsRecorder,
        key_store_path: str | None,
        profile_path: str | None = None,
        expected_local_bluetooth_address: bytes | None = None,
    ) -> HidDeviceTransport:
        if profile_path is None and expected_local_bluetooth_address is None:
            return create_default_transport(
                adapter=adapter,
                device_name=device_name,
                profile=profile,
                diagnostics=diagnostics,
                key_store_path=key_store_path,
            )
        return create_default_transport(
            adapter=adapter,
            device_name=device_name,
            profile=profile,
            diagnostics=diagnostics,
            key_store_path=key_store_path,
            profile_path=profile_path,
            expected_local_bluetooth_address=expected_local_bluetooth_address,
        )


def create_default_transport(
    *,
    adapter: str,
    device_name: str,
    profile: ControllerProfile,
    diagnostics: DiagnosticsRecorder,
    key_store_path: str | None,
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
            key_store_path=key_store_path,
        )
    return BumbleHidTransport(
        adapter=adapter,
        device_name=device_name,
        profile=profile,
        diagnostics=diagnostics,
        key_store_path=key_store_path,
        profile_path=profile_path,
        expected_local_bluetooth_address=expected_local_bluetooth_address,
    )
