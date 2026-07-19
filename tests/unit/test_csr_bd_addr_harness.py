import asyncio
from collections.abc import Callable

import pytest

from swbt.transport._csr_bd_addr_harness import (
    CsrAdapterSession,
    CsrHostMetadata,
    probe_csr_identity,
)


class _FakeCsrSession:
    def __init__(self, *, initialize_error: Exception | None = None) -> None:
        self.initialize_error = initialize_error
        self.closed = False

    async def initialize(
        self,
        *,
        response_timeout: float,
        hci_reset: bool,
        on_stage: Callable[[str], None] | None = None,
    ) -> CsrHostMetadata:
        assert response_timeout == 2.0
        assert hci_reset is False
        if on_stage is not None:
            on_stage("read_local_supported_commands")
            on_stage("read_local_version")
        if self.initialize_error is not None:
            raise self.initialize_error
        return CsrHostMetadata(
            supported_commands=b"\x01\x02",
            hci_version=6,
            hci_subversion=8891,
            lmp_version=6,
            company_identifier=10,
            lmp_subversion=8891,
        )

    async def read_standard_address(self, *, response_timeout: float) -> str:
        assert response_timeout == 2.0
        return "00:11:22:33:44:55"

    async def read_csr_address(
        self,
        *,
        store: int,
        sequence_number: int,
        response_timeout: float,
    ) -> tuple[str, str]:
        assert store == 0
        assert sequence_number == 0x4711
        assert response_timeout == 2.0
        return (
            "00:11:22:33:44:55",
            "c201000c001147037000000100040000003300554422001100",
        )

    async def close(self) -> None:
        self.closed = True


def test_probe_csr_identity_preserves_read_only_result_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeCsrSession()

    async def fake_open(adapter: str) -> _FakeCsrSession:
        assert adapter == "usb:0"
        return session

    monkeypatch.setattr(CsrAdapterSession, "open", staticmethod(fake_open))

    result = asyncio.run(
        probe_csr_identity(
            "usb:0",
            response_timeout=2.0,
            hci_reset=False,
        )
    )

    assert result["status"] == "passed"
    assert result["stage"] == "complete"
    assert result["cleanup"] == "adapter_closed"
    assert result["standard_hci"] == {
        "address": "00:11:22:33:44:55",
        "supported_commands_hex": "0102",
        "hci_version": 6,
        "hci_subversion": 8891,
        "lmp_version": 6,
        "company_identifier": 10,
        "lmp_subversion": 8891,
    }
    assert result["csr"] == {
        "opcode": "0xfc00",
        "request_parameters_hex": "c200000c001147037000000100040000000000000000000000",
        "vendor_event_hex": "c201000c001147037000000100040000003300554422001100",
        "address": "00:11:22:33:44:55",
        "raw_value_hex": "3300554422001100",
        "status": 0,
        "matches_standard_hci": True,
    }
    assert session.closed is True


def test_probe_csr_identity_preserves_failure_stage_and_closes_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeCsrSession(initialize_error=TimeoutError("version timeout"))

    async def fake_open(adapter: str) -> _FakeCsrSession:
        assert adapter == "usb:0"
        return session

    monkeypatch.setattr(CsrAdapterSession, "open", staticmethod(fake_open))

    result = asyncio.run(
        probe_csr_identity(
            "usb:0",
            response_timeout=2.0,
            hci_reset=False,
        )
    )

    assert result["status"] == "failed"
    assert result["stage"] == "read_local_version"
    assert result["error_type"] == "TimeoutError"
    assert result["cleanup"] == "adapter_closed"
    assert session.closed is True
