import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from swbt.transport._csr_bd_addr import (
    CsrBdAddrRewritePlan,
    CsrBdAddrStore,
    CsrVendorCommand,
)
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

    async def send_write(
        self,
        plan: CsrBdAddrRewritePlan,
        *,
        response_timeout: float,
    ) -> object:
        _ = (plan, response_timeout)
        message = "send_write must not be called"
        raise AssertionError(message)

    def enqueue_warm_reset(self, command: CsrVendorCommand) -> None:
        _ = command
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


class _WritableFakeSession(_FakeSession):
    def __init__(
        self,
        *,
        address: str,
        events: list[str],
        label: str,
    ) -> None:
        super().__init__()
        self.address = address
        self.events = events
        self.label = label

    async def initialize(
        self,
        *,
        response_timeout: float,
        hci_reset: bool,
        on_stage: Callable[[str], None] | None = None,
    ) -> _FakeMetadata:
        self.events.append(f"{self.label}:initialize")
        assert response_timeout == 2.0
        assert hci_reset is False
        assert on_stage is None
        return _FakeMetadata()

    async def read_standard_address(self, *, response_timeout: float) -> str:
        assert response_timeout == 2.0
        self.events.append(f"{self.label}:read_standard_address")
        return self.address

    async def send_write(
        self,
        plan: CsrBdAddrRewritePlan,
        *,
        response_timeout: float,
    ) -> object:
        assert response_timeout == 2.0
        assert plan.store is CsrBdAddrStore.VOLATILE
        assert plan.address == "02:12:34:56:78:9A"
        self.events.append(f"{self.label}:write")
        return {"status": 0}

    def enqueue_warm_reset(self, command: CsrVendorCommand) -> None:
        assert command.parameters.hex().startswith("c2020009")
        self.events.append(f"{self.label}:warm_reset")

    async def close(self) -> None:
        self.events.append(f"{self.label}:close")


def test_prepare_exp_local_identity_rewrites_then_reopens_and_reads_back() -> None:
    events: list[str] = []
    sessions = [
        _WritableFakeSession(
            address="00:1B:DC:F9:9F:7D",
            events=events,
            label="before",
        ),
        _WritableFakeSession(
            address="02:12:34:56:78:9A",
            events=events,
            label="after",
        ),
    ]

    open_attempt = 0

    async def open_session(adapter: str) -> _WritableFakeSession:
        nonlocal open_attempt
        assert adapter == "usb:0"
        open_attempt += 1
        if open_attempt == 2:
            events.append("reenumeration_open_failed")
            raise OSError
        session = sessions.pop(0)
        events.append(f"{session.label}:open")
        return session

    async def sleep(delay: float) -> None:
        assert delay == 0.25
        events.append("wait_reenumeration")

    result = asyncio.run(
        prepare_exp_local_identity(
            adapter="usb:0",
            target=ExpLocalAddress.parse("02:12:34:56:78:9A"),
            reenumeration_poll_interval=0.25,
            _open_session=open_session,
            _sleep=sleep,
        )
    )

    assert result.status == "rewritten"
    assert result.current_address == "00:1B:DC:F9:9F:7D"
    assert result.target_address == "02:12:34:56:78:9A"
    assert events == [
        "before:open",
        "before:initialize",
        "before:read_standard_address",
        "before:write",
        "before:warm_reset",
        "before:close",
        "wait_reenumeration",
        "reenumeration_open_failed",
        "wait_reenumeration",
        "after:open",
        "after:initialize",
        "after:read_standard_address",
        "after:close",
    ]
    assert sessions == []
