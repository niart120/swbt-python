from collections.abc import Callable

from swbt.transport._bumble_lifecycle import ConnectionDiagnostics


class _FakeConnection:
    EVENT_DISCONNECTION = "disconnection"
    EVENT_PAIRING = "pairing"
    EVENT_CONNECTION_AUTHENTICATION = "connection_authentication"
    EVENT_CONNECTION_ENCRYPTION_CHANGE = "connection_encryption_change"
    EVENT_CONNECTION_ENCRYPTION_KEY_REFRESH = "connection_encryption_key_refresh"
    EVENT_LINK_KEY = "link_key"
    EVENT_MODE_CHANGE = "mode_change"

    def __init__(self) -> None:
        self.authenticated = False
        self.classic_interval = 0
        self.classic_mode = 0
        self.encryption = 0
        self.encryption_key_size = 0
        self.sc = False
        self._callbacks: dict[str, list[Callable[..., None]]] = {}

    def on(self, event: str, callback: Callable[..., None]) -> None:
        self._callbacks.setdefault(event, []).append(callback)

    def emit(self, event: str, *args: object) -> None:
        for callback in self._callbacks.get(event, []):
            callback(*args)


class _FakePairingKeys:
    link_key = object()


def test_connection_diagnostics_records_security_and_mode_events() -> None:
    events: list[dict[str, object]] = []
    disconnected_reasons: list[int | None] = []

    def record_event(event: str, **fields: object) -> None:
        events.append({"event": event, **fields})

    diagnostics = ConnectionDiagnostics(
        adapter="usb:0",
        handle_disconnection=disconnected_reasons.append,
        record_event=record_event,
    )
    connection = _FakeConnection()

    diagnostics.register(connection)
    connection.authenticated = True
    connection.encryption = 1
    connection.encryption_key_size = 16
    connection.sc = True
    connection.classic_mode = 2
    connection.classic_interval = 24
    connection.emit(connection.EVENT_PAIRING, _FakePairingKeys())
    connection.emit(connection.EVENT_CONNECTION_AUTHENTICATION)
    connection.emit(connection.EVENT_CONNECTION_ENCRYPTION_CHANGE)
    connection.emit(connection.EVENT_CONNECTION_ENCRYPTION_KEY_REFRESH)
    connection.emit(connection.EVENT_LINK_KEY)
    connection.emit(connection.EVENT_MODE_CHANGE)
    connection.emit(connection.EVENT_DISCONNECTION, 0x13)

    assert {
        "event": "pairing_complete",
        "adapter": "usb:0",
        "authenticated": True,
        "encryption": 1,
        "encryption_key_size": 16,
        "secure_connections": True,
        "has_link_key": True,
    } in events
    assert {
        "event": "connection_encryption_change",
        "adapter": "usb:0",
        "authenticated": True,
        "encryption": 1,
        "encryption_key_size": 16,
        "secure_connections": True,
    } in events
    assert {"event": "classic_mode_change", "adapter": "usb:0", "mode": 2, "interval": 24} in events
    assert disconnected_reasons == [0x13]
