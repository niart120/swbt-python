"""CSR volatile identity preparation without Switch-facing behavior."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol, cast

from swbt.transport._exp_local_address import ExpLocalAddress


class _CsrMetadata(Protocol):
    company_identifier: int


class _CsrSession(Protocol):
    async def initialize(
        self,
        *,
        response_timeout: float,
        hci_reset: bool,
        on_stage: Callable[[str], None] | None = None,
    ) -> _CsrMetadata: ...

    async def read_standard_address(self, *, response_timeout: float) -> str: ...

    async def close(self) -> None: ...


type _SessionOpener = Callable[[str], Awaitable[_CsrSession]]


@dataclass(frozen=True)
class ExpLocalIdentityPreparationResult:
    """Result of comparing the active CSR identity with a profile target."""

    status: Literal["already_active", "rewrite_required"]
    current_address: str
    target_address: str


async def prepare_exp_local_identity(
    *,
    adapter: str,
    target: ExpLocalAddress,
    response_timeout: float = 2.0,
    _open_session: _SessionOpener | None = None,
) -> ExpLocalIdentityPreparationResult:
    """Read the active address and avoid CSR writes when it already matches."""
    open_session = _open_session or _open_default_session
    session = await open_session(adapter)
    try:
        metadata = await session.initialize(
            response_timeout=response_timeout,
            hci_reset=False,
        )
        if metadata.company_identifier != 10:
            msg = (
                "exp local address preparation requires a CSR controller "
                f"(company identifier 10), got {metadata.company_identifier}"
            )
            raise RuntimeError(msg)
        current_address = (
            await session.read_standard_address(response_timeout=response_timeout)
        ).upper()
        target_address = str(target)
        status: Literal["already_active", "rewrite_required"] = (
            "already_active" if current_address == target_address else "rewrite_required"
        )
        return ExpLocalIdentityPreparationResult(
            status=status,
            current_address=current_address,
            target_address=target_address,
        )
    finally:
        await session.close()


async def _open_default_session(adapter: str) -> _CsrSession:
    from swbt.transport._csr_bd_addr_harness import CsrAdapterSession  # noqa: PLC0415

    session = await CsrAdapterSession.open(adapter)
    return cast("_CsrSession", session)
