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


def test_wait_connected_completes_after_fake_connected_callback() -> None:
    async def run() -> None:
        transport = FakeHidTransport()

        async with SwitchGamepad(transport=transport) as pad:
            connected = asyncio.create_task(pad.wait_connected(timeout=1.0))
            await asyncio.sleep(0)

            assert connected.done() is False

            await transport.connect()
            await asyncio.wait_for(connected, timeout=0.1)

            assert transport.events == ("open", "connected")

    asyncio.run(run())
