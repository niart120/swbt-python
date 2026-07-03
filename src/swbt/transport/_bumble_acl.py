"""ACL queue drain helper for Bumble HID transport."""

from collections.abc import Awaitable


async def drain_bumble_acl_queue(l2cap_channel: object) -> None:
    """Wait until Bumble reports no pending ACL packets for the channel."""
    connection = getattr(l2cap_channel, "connection", None)
    connection_handle = getattr(connection, "handle", None)
    acl_packet_queue = getattr(connection, "acl_packet_queue", None)
    if acl_packet_queue is None and isinstance(connection_handle, int):
        device = getattr(connection, "device", None)
        host = getattr(device, "host", None)
        get_data_packet_queue = getattr(host, "get_data_packet_queue", None)
        if callable(get_data_packet_queue):
            acl_packet_queue = get_data_packet_queue(connection_handle)
    drain = getattr(acl_packet_queue, "drain", None)
    if not isinstance(connection_handle, int) or not callable(drain):
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
