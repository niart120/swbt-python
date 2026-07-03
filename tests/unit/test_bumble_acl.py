import asyncio

from swbt.transport._bumble_acl import drain_bumble_acl_queue


class FakeAclPacketQueue:
    """Fake Bumble ACL packet queue."""

    def __init__(self) -> None:
        """Create a fake queue with pending data."""
        self.pending = 2
        self.drain_calls: list[int] = []

    async def drain(self, connection_handle: int) -> None:
        """Record one drain call and clear pending data."""
        self.drain_calls.append(connection_handle)
        self.pending = 0


class FakeHost:
    """Fake Bumble host exposing ACL queue lookup."""

    def __init__(self, acl_packet_queue: FakeAclPacketQueue) -> None:
        """Create a host backed by one fake queue."""
        self._acl_packet_queue = acl_packet_queue

    def get_data_packet_queue(self, connection_handle: int) -> FakeAclPacketQueue:
        """Return the fake queue for any handle."""
        _ = connection_handle
        return self._acl_packet_queue


def test_drain_bumble_acl_queue_uses_host_fallback_queue() -> None:
    async def run() -> None:
        acl_packet_queue = FakeAclPacketQueue()
        l2cap_channel = type(
            "FakeL2capChannel",
            (),
            {
                "connection": type(
                    "FakeConnection",
                    (),
                    {
                        "acl_packet_queue": None,
                        "device": type("FakeDevice", (), {"host": FakeHost(acl_packet_queue)})(),
                        "handle": 64,
                    },
                )()
            },
        )()

        await drain_bumble_acl_queue(l2cap_channel)

        assert acl_packet_queue.drain_calls == [64]

    asyncio.run(run())
