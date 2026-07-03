"""Lifecycle and connection diagnostics helpers for Bumble HID transport."""

from collections.abc import Callable
from contextlib import suppress
from typing import Any, Protocol, cast


class EventRecorder(Protocol):
    def __call__(self, event: str, **fields: object) -> None:
        """Record one diagnostics event."""


class ConnectionDiagnostics:
    """Register diagnostics callbacks on a Bumble connection object."""

    def __init__(
        self,
        *,
        adapter: str,
        handle_disconnection: Callable[[int | None], None],
        record_event: EventRecorder,
    ) -> None:
        self._adapter = adapter
        self._handle_disconnection = handle_disconnection
        self._record_event = record_event

    def register(self, connection: object) -> None:
        """Register all connection diagnostics callbacks supported by the connection."""
        on_event = getattr(connection, "on", None)
        if not callable(on_event):
            return
        on_event(
            getattr(connection, "EVENT_DISCONNECTION", "disconnection"),
            self._handle_disconnection,
        )
        on_event(
            getattr(connection, "EVENT_CLASSIC_PAIRING", "classic_pairing"),
            lambda *_args: self._record_event("classic_pairing", adapter=self._adapter),
        )
        on_event(
            getattr(connection, "EVENT_CLASSIC_PAIRING_FAILURE", "classic_pairing_failure"),
            lambda reason=None, *_args: self._record_event(
                "classic_pairing_failure",
                adapter=self._adapter,
                reason=reason,
            ),
        )
        on_event(
            getattr(connection, "EVENT_PAIRING_START", "pairing_start"),
            lambda *_args: self._record_event("pairing_start", adapter=self._adapter),
        )
        on_event(
            getattr(connection, "EVENT_PAIRING", "pairing"),
            lambda keys=None, *_args: self._record_pairing_complete(connection, keys),
        )
        on_event(
            getattr(connection, "EVENT_PAIRING_FAILURE", "pairing_failure"),
            lambda reason=None, *_args: self._record_event(
                "pairing_failure",
                adapter=self._adapter,
                reason=reason,
            ),
        )
        on_event(
            getattr(connection, "EVENT_CONNECTION_AUTHENTICATION", "connection_authentication"),
            lambda *_args: self._record_connection_authentication(connection),
        )
        on_event(
            getattr(
                connection,
                "EVENT_CONNECTION_AUTHENTICATION_FAILURE",
                "connection_authentication_failure",
            ),
            lambda error=None, *_args: self._record_event(
                "connection_authentication_failure",
                adapter=self._adapter,
                error=safe_event_value(error),
            ),
        )
        on_event(
            getattr(
                connection,
                "EVENT_CONNECTION_ENCRYPTION_CHANGE",
                "connection_encryption_change",
            ),
            lambda *_args: self._record_connection_encryption_change(connection),
        )
        on_event(
            getattr(
                connection,
                "EVENT_CONNECTION_ENCRYPTION_FAILURE",
                "connection_encryption_failure",
            ),
            lambda error=None, *_args: self._record_event(
                "connection_encryption_failure",
                adapter=self._adapter,
                error=safe_event_value(error),
            ),
        )
        on_event(
            getattr(
                connection,
                "EVENT_CONNECTION_ENCRYPTION_KEY_REFRESH",
                "connection_encryption_key_refresh",
            ),
            lambda *_args: self._record_connection_encryption_refresh(connection),
        )
        on_event(
            getattr(connection, "EVENT_LINK_KEY", "link_key"),
            lambda *_args: self._record_event("link_key_available", adapter=self._adapter),
        )
        on_event(
            getattr(connection, "EVENT_MODE_CHANGE", "mode_change"),
            lambda *_args: self._record_classic_mode_change(connection),
        )
        on_event(
            getattr(connection, "EVENT_MODE_CHANGE_FAILURE", "mode_change_failure"),
            lambda status=None, *_args: self._record_event(
                "classic_mode_change_failure",
                adapter=self._adapter,
                status=status,
            ),
        )

    def _record_pairing_complete(self, connection: object, keys: object | None) -> None:
        fields = connection_security_fields(connection)
        fields["has_link_key"] = keys_include_link_key(keys)
        self._record_event("pairing_complete", adapter=self._adapter, **fields)

    def _record_connection_authentication(self, connection: object) -> None:
        self._record_event(
            "connection_authentication",
            adapter=self._adapter,
            authenticated=getattr(connection, "authenticated", None),
        )

    def _record_connection_encryption_change(self, connection: object) -> None:
        self._record_event(
            "connection_encryption_change",
            adapter=self._adapter,
            **connection_security_fields(connection),
        )

    def _record_connection_encryption_refresh(self, connection: object) -> None:
        self._record_event(
            "connection_encryption_key_refresh",
            adapter=self._adapter,
            **connection_security_fields(connection),
        )

    def _record_classic_mode_change(self, connection: object) -> None:
        self._record_event(
            "classic_mode_change",
            adapter=self._adapter,
            mode=getattr(connection, "classic_mode", None),
            interval=getattr(connection, "classic_interval", None),
        )


def register_connection_diagnostics(
    *,
    adapter: str,
    connection: object,
    handle_disconnection: Callable[[int | None], None],
    record_event: EventRecorder,
) -> None:
    """Register connection-level diagnostics callbacks."""
    ConnectionDiagnostics(
        adapter=adapter,
        handle_disconnection=handle_disconnection,
        record_event=record_event,
    ).register(connection)


def register_connection_request_bridge(
    *,
    adapter: str,
    device: object,
    record_event: EventRecorder,
) -> None:
    """Wrap Bumble's connection request callback while avoiding deprecated sync APIs."""
    original_connection_request = cast("Any", device).on_connection_request

    def on_connection_request(
        bd_addr: object,
        class_of_device: int,
        link_type: int,
    ) -> None:
        record_event(
            "connection_request",
            adapter=adapter,
            class_of_device=f"0x{class_of_device:06x}",
            link_type=link_type,
            peer_address=str(bd_addr),
        )
        call_connection_request_without_deprecated_sync_command(
            device,
            original_connection_request,
            bd_addr,
            class_of_device,
            link_type,
        )

    device_with_attrs = cast("Any", device)
    device_with_attrs.on_connection_request = on_connection_request
    replace_host_connection_request_listener(
        device,
        original_connection_request,
        on_connection_request,
    )


def register_l2cap_lifecycle_bridge(
    *,
    hid_device: object,
    notify_connected_if_ready: Callable[[], None],
    notify_disconnected_if_channels_closed: Callable[[], None],
    record_l2cap_channel_event: Callable[[str, object], None],
    set_l2cap_connected_emitted: Callable[[bool], None],
) -> None:
    """Wrap HID L2CAP lifecycle callbacks and emit transport diagnostics."""
    hid_device_with_attrs = cast("Any", hid_device)
    original_open = hid_device_with_attrs.on_l2cap_channel_open
    original_close = hid_device_with_attrs.on_l2cap_channel_close

    def on_l2cap_channel_open(l2cap_channel: object) -> None:
        original_open(l2cap_channel)
        record_l2cap_channel_event("l2cap_channel_open", l2cap_channel)
        notify_connected_if_ready()

    def on_l2cap_channel_close(l2cap_channel: object) -> None:
        original_close(l2cap_channel)
        record_l2cap_channel_event("l2cap_channel_close", l2cap_channel)
        set_l2cap_connected_emitted(False)
        notify_disconnected_if_channels_closed()

    hid_device_with_attrs.on_l2cap_channel_open = on_l2cap_channel_open
    hid_device_with_attrs.on_l2cap_channel_close = on_l2cap_channel_close


def connection_security_fields(connection: object) -> dict[str, object]:
    return {
        "authenticated": getattr(connection, "authenticated", None),
        "encryption": getattr(connection, "encryption", None),
        "encryption_key_size": getattr(connection, "encryption_key_size", None),
        "secure_connections": getattr(connection, "sc", None),
    }


def keys_include_link_key(keys: object | None) -> bool | None:
    if keys is None:
        return None
    return getattr(keys, "link_key", None) is not None


def safe_event_value(value: object) -> object:
    if value is None or isinstance(value, int | str | bool | float):
        return value
    return str(value)


def call_connection_request_without_deprecated_sync_command(
    device: object,
    connection_request: Callable[[object, int, int], None],
    bd_addr: object,
    class_of_device: int,
    link_type: int,
) -> None:
    """Run Bumble's connection request handler without its deprecated sync helper."""
    host = getattr(device, "host", None)
    send_async_command = getattr(host, "send_async_command", None)
    if host is None or not callable(send_async_command):
        connection_request(bd_addr, class_of_device, link_type)
        return

    from bumble import utils  # noqa: PLC0415

    missing = object()
    host_dict = getattr(host, "__dict__", None)
    previous_instance_attr = (
        host_dict.get("send_command_sync", missing) if isinstance(host_dict, dict) else missing
    )

    def send_command_sync(command: object) -> None:
        utils.AsyncRunner.spawn(send_async_command(command))

    host_with_attrs = cast("Any", host)
    host_with_attrs.send_command_sync = send_command_sync
    try:
        connection_request(bd_addr, class_of_device, link_type)
    finally:
        if previous_instance_attr is missing:
            del host_with_attrs.send_command_sync
        else:
            host_with_attrs.send_command_sync = previous_instance_attr


def replace_host_connection_request_listener(
    device: object,
    original_connection_request: Callable[[object, int, int], None],
    replacement_connection_request: Callable[[object, int, int], None],
) -> None:
    host = getattr(device, "host", None)
    remove_listener = getattr(host, "remove_listener", None)
    on = getattr(host, "on", None)
    if not callable(remove_listener) or not callable(on):
        return

    with suppress(KeyError, ValueError):
        remove_listener("connection_request", original_connection_request)
    on("connection_request", replacement_connection_request)
