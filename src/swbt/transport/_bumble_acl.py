"""ACL queue drain helper for Bumble HID transport."""

from collections.abc import Awaitable, Callable


class BumbleAclCompletionObserver:
    """Temporarily observe one connection's private Bumble completion handler."""

    def __init__(self, l2cap_channel: object, *, now_ns: Callable[[], int]) -> None:
        """Resolve the queue and connection whose completions are observed."""
        self._now_ns = now_ns
        self._connection = getattr(l2cap_channel, "connection", None)
        resolved = _acl_queue_and_handle(l2cap_channel)
        self._acl_packet_queue: object | None = None
        self._connection_handle: int | None = None
        if resolved is not None:
            self._acl_packet_queue, self._connection_handle = resolved
        self._original_handler: Callable[[int, int], object] | None = None
        self._enqueue_started_ns: int | None = None
        self.completion_delay_ns: int | None = None
        self.completion_packet_count: int | None = None
        self.classic_mode_at_enqueue: int | None = None
        self.classic_interval_at_enqueue: int | None = None
        self.classic_mode_at_completion: int | None = None
        self.classic_interval_at_completion: int | None = None

    def attach(self) -> None:
        """Attach the temporary observer when Bumble exposes a writable handler."""
        if self._acl_packet_queue is None or self._connection_handle is None:
            return
        handler = getattr(self._acl_packet_queue, "on_packets_completed", None)
        if not callable(handler):
            return

        def observed_handler(packet_count: int, connection_handle: int) -> object:
            if (
                self._enqueue_started_ns is not None
                and self.completion_delay_ns is None
                and connection_handle == self._connection_handle
            ):
                self.completion_delay_ns = max(0, self._now_ns() - self._enqueue_started_ns)
                self.completion_packet_count = packet_count
                (
                    self.classic_mode_at_completion,
                    self.classic_interval_at_completion,
                ) = _classic_link_snapshot(self._connection)
            return handler(packet_count, connection_handle)

        try:
            setattr(  # noqa: B010 - Bumble handler name is intentionally private.
                self._acl_packet_queue,
                "on_packets_completed",
                observed_handler,
            )
        except (AttributeError, TypeError):
            return
        self._original_handler = handler

    def arm(self, enqueue_started_ns: int) -> None:
        """Start measuring immediately before the HID payload is enqueued."""
        self._enqueue_started_ns = enqueue_started_ns
        (
            self.classic_mode_at_enqueue,
            self.classic_interval_at_enqueue,
        ) = _classic_link_snapshot(self._connection)

    def detach(self) -> None:
        """Restore Bumble's original completion handler."""
        if self._acl_packet_queue is None or self._original_handler is None:
            return
        try:
            setattr(  # noqa: B010 - Bumble handler name is intentionally private.
                self._acl_packet_queue,
                "on_packets_completed",
                self._original_handler,
            )
        except (AttributeError, TypeError):
            return
        self._original_handler = None


def bumble_acl_pending(l2cap_channel: object) -> int | None:
    """Return Bumble's host-wide pending ACL count, when available."""
    resolved = _acl_queue_and_handle(l2cap_channel)
    if resolved is None:
        return None
    acl_packet_queue, _ = resolved
    pending = getattr(acl_packet_queue, "pending", None)
    return pending if isinstance(pending, int) else None


async def drain_bumble_acl_queue(l2cap_channel: object) -> None:
    """Wait until Bumble reports no pending ACL packets for the channel."""
    resolved = _acl_queue_and_handle(l2cap_channel)
    if resolved is None:
        return
    acl_packet_queue, connection_handle = resolved
    drain = getattr(acl_packet_queue, "drain", None)
    if not callable(drain):
        return
    try:
        last_pending: int | None = None
        while True:
            pending = getattr(acl_packet_queue, "pending", 0)
            if not isinstance(pending, int) or pending <= 0 or pending == last_pending:
                return
            last_pending = pending
            drain_result = drain(connection_handle)
            if isinstance(drain_result, Awaitable):
                await drain_result
                continue
            return
    except ValueError:
        return


def _acl_queue_and_handle(l2cap_channel: object) -> tuple[object, int] | None:
    """Resolve the ACL queue and connection handle used by Bumble's drain API."""
    connection = getattr(l2cap_channel, "connection", None)
    connection_handle = getattr(connection, "handle", None)
    acl_packet_queue = getattr(connection, "acl_packet_queue", None)
    if acl_packet_queue is None and isinstance(connection_handle, int):
        device = getattr(connection, "device", None)
        host = getattr(device, "host", None)
        get_data_packet_queue = getattr(host, "get_data_packet_queue", None)
        if callable(get_data_packet_queue):
            acl_packet_queue = get_data_packet_queue(connection_handle)
    if not isinstance(connection_handle, int) or acl_packet_queue is None:
        return None
    return acl_packet_queue, connection_handle


def _classic_link_snapshot(connection: object) -> tuple[int | None, int | None]:
    """Return Bumble's current Classic link mode and interval, when exposed."""
    classic_mode = getattr(connection, "classic_mode", None)
    classic_interval = getattr(connection, "classic_interval", None)
    return (
        classic_mode if isinstance(classic_mode, int) else None,
        classic_interval if isinstance(classic_interval, int) else None,
    )
