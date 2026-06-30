import asyncio

from swbt import SwitchGamepad
from swbt.transport.fake import FakeHidTransport


def test_async_context_opens_and_closes_fake_transport() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        assert transport.is_open is False

        async with SwitchGamepad(transport=transport):
            assert transport.is_open is True
            assert transport.open_count == 1
            assert transport.close_count == 0

        assert transport.is_open is False
        assert transport.open_count == 1
        assert transport.close_count == 1
        assert transport.events == ("open", "close")

    asyncio.run(run())
