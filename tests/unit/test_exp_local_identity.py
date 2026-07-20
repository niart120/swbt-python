import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from swbt.transport._exp_local_address import ExpLocalAddress
from swbt.transport._exp_local_identity import prepare_exp_local_identity


@dataclass(frozen=True)
class _FakeMetadata:
    company_identifier: int = 10


class _FakeSession:
    def __init__(self) -> None:
        self.events: list[str] = []

    async def initialize(
        self,
        *,
        response_timeout: float,
        hci_reset: bool,
        on_stage: Callable[[str], None] | None = None,
    ) -> _FakeMetadata:
        assert response_timeout == 2.0
        assert hci_reset is False
        assert on_stage is None
        self.events.append("initialize")
        return _FakeMetadata()

    async def read_standard_address(self, *, response_timeout: float) -> str:
        assert response_timeout == 2.0
        self.events.append("read_standard_address")
        return "02:12:34:56:78:9a"

    async def send_write(self, *_args: object, **_kwargs: object) -> object:
        message = "send_write must not be called"
        raise AssertionError(message)

    def enqueue_warm_reset(self, *_args: object, **_kwargs: object) -> None:
        message = "enqueue_warm_reset must not be called"
        raise AssertionError(message)

    async def close(self) -> None:
        self.events.append("close")


def test_prepare_exp_local_identity_skips_write_when_target_is_already_active() -> None:
    session = _FakeSession()

    async def open_session(adapter: str) -> _FakeSession:
        assert adapter == "usb:0"
        session.events.append("open")
        return session

    result = asyncio.run(
        prepare_exp_local_identity(
            adapter="usb:0",
            target=ExpLocalAddress.parse("02:12:34:56:78:9A"),
            _open_session=open_session,
        )
    )

    assert result.status == "already_active"
    assert result.current_address == "02:12:34:56:78:9A"
    assert result.target_address == "02:12:34:56:78:9A"
    assert session.events == [
        "open",
        "initialize",
        "read_standard_address",
        "close",
    ]
