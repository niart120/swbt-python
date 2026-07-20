"""CSR volatile identity preparation without Switch-facing behavior."""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal, Protocol, cast

from swbt.errors import ExpLocalAddressRecoveryRequired
from swbt.transport._csr_bd_addr import (
    CsrBdAddrRewritePlan,
    CsrVendorCommand,
    build_csr_bd_addr_volatile_experiment_plan,
)
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

    async def send_write(
        self,
        plan: CsrBdAddrRewritePlan,
        *,
        response_timeout: float,
    ) -> object: ...

    def enqueue_warm_reset(self, command: CsrVendorCommand) -> None: ...

    async def close(self) -> None: ...


type _SessionOpener = Callable[[str], Awaitable[_CsrSession]]
type _Sleep = Callable[[float], Awaitable[None]]


@dataclass(frozen=True)
class ExpLocalIdentityPreparationResult:
    """Result of applying a profile target to the active CSR identity."""

    status: Literal["already_active", "rewritten"]
    current_address: str
    target_address: str


@dataclass
class _PreparationState:
    stage: str = "opening"
    write_started: bool = False


async def prepare_exp_local_identity(
    *,
    adapter: str,
    target: ExpLocalAddress,
    response_timeout: float = 2.0,
    reenumeration_timeout: float = 10.0,
    reenumeration_poll_interval: float = 0.25,
    _open_session: _SessionOpener | None = None,
    _sleep: _Sleep = asyncio.sleep,
) -> ExpLocalIdentityPreparationResult:
    """Apply a volatile target and classify uncertainty after write starts."""
    state = _PreparationState()
    try:
        return await _prepare_exp_local_identity(
            adapter=adapter,
            target=target,
            response_timeout=response_timeout,
            reenumeration_timeout=reenumeration_timeout,
            reenumeration_poll_interval=reenumeration_poll_interval,
            open_session=_open_session or _open_default_session,
            sleep=_sleep,
            state=state,
        )
    except ExpLocalAddressRecoveryRequired:
        raise
    except Exception as error:
        if not state.write_started:
            raise
        raise ExpLocalAddressRecoveryRequired(
            target_address=str(target),
            stage=state.stage,
        ) from error


async def _prepare_exp_local_identity(
    *,
    adapter: str,
    target: ExpLocalAddress,
    response_timeout: float,
    reenumeration_timeout: float,
    reenumeration_poll_interval: float,
    open_session: _SessionOpener,
    sleep: _Sleep,
    state: _PreparationState,
) -> ExpLocalIdentityPreparationResult:
    state.stage = "opening"
    session = await open_session(adapter)
    reset_enqueued = False
    current_address: str
    try:
        state.stage = "initializing"
        await _initialize_csr_session(session, response_timeout=response_timeout)
        state.stage = "read_current"
        current_address = (
            await session.read_standard_address(response_timeout=response_timeout)
        ).upper()
        target_address = str(target)
        if current_address == target_address:
            return ExpLocalIdentityPreparationResult(
                status="already_active",
                current_address=current_address,
                target_address=target_address,
            )

        experiment = build_csr_bd_addr_volatile_experiment_plan(
            original_address=current_address,
            requested_address=target_address,
        )
        state.stage = "write"
        state.write_started = True
        await session.send_write(
            experiment.apply,
            response_timeout=response_timeout,
        )
        state.stage = "warm_reset"
        session.enqueue_warm_reset(experiment.apply.reset_command)
        reset_enqueued = True
    finally:
        try:
            await session.close()
        except Exception:
            if not reset_enqueued:
                raise

    state.stage = "reenumeration"
    readback_session = await _open_reenumerated_session(
        adapter=adapter,
        open_session=open_session,
        reenumeration_timeout=reenumeration_timeout,
        poll_interval=reenumeration_poll_interval,
        sleep=sleep,
    )
    try:
        state.stage = "readback"
        await _initialize_csr_session(
            readback_session,
            response_timeout=response_timeout,
        )
        readback_address = (
            await readback_session.read_standard_address(
                response_timeout=response_timeout,
            )
        ).upper()
    finally:
        await readback_session.close()

    if readback_address != target_address:
        msg = f"expected active address {target_address}, got {readback_address}"
        raise RuntimeError(msg)
    return ExpLocalIdentityPreparationResult(
        status="rewritten",
        current_address=current_address,
        target_address=target_address,
    )


async def _initialize_csr_session(
    session: _CsrSession,
    *,
    response_timeout: float,
) -> None:
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


async def _open_reenumerated_session(
    *,
    adapter: str,
    open_session: _SessionOpener,
    reenumeration_timeout: float,
    poll_interval: float,
    sleep: _Sleep,
) -> _CsrSession:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + reenumeration_timeout
    while True:
        await sleep(poll_interval)
        try:
            return await open_session(adapter)
        except Exception as error:
            if loop.time() >= deadline:
                msg = "CSR adapter did not re-enumerate before timeout"
                raise TimeoutError(msg) from error


async def _open_default_session(adapter: str) -> _CsrSession:
    from swbt.transport._csr_bd_addr_harness import CsrAdapterSession  # noqa: PLC0415

    session = await CsrAdapterSession.open(adapter)
    return cast("_CsrSession", session)
