"""Async-safe input state storage."""

import asyncio
from collections.abc import Callable

from swbt.input import InputState


class InputStateStore:
    """Store the current immutable input state behind an async lock."""

    def __init__(self, initial_state: InputState | None = None) -> None:
        """Create a state store."""
        self._state = initial_state or InputState.neutral()
        self._lock = asyncio.Lock()

    async def snapshot(self) -> InputState:
        """Return the current input state."""
        async with self._lock:
            return self._state

    @property
    def current(self) -> InputState:
        """Return the latest committed input state."""
        return self._state

    async def apply(self, state: InputState) -> InputState:
        """Replace the current input state."""
        async with self._lock:
            self._state = state
            return self._state

    async def update(
        self,
        transform: Callable[[InputState], InputState],
        *,
        validate: Callable[[InputState], None] | None = None,
    ) -> InputState:
        """Apply a read-modify-write update while holding the state lock."""
        async with self._lock:
            next_state = transform(self._state)
            if validate is not None:
                validate(next_state)
            self._state = next_state
            return self._state
