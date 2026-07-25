"""ACL queue drain helper for the pinned Bumble HID transport."""

from typing import Any, cast


async def drain_bumble_acl_queue(l2cap_channel: object) -> None:
    """Wait for the pinned Bumble connection's pending ACL packets to complete."""
    channel = cast("Any", l2cap_channel)
    connection = channel.connection
    acl_packet_queue = connection.device.host.get_data_packet_queue(connection.handle)
    if acl_packet_queue is None:
        return
    try:
        await acl_packet_queue.drain(connection.handle)
    except ValueError:
        # Bumble raises when the queue has no state for a channel that was already drained.
        return
