"""Async-safe input state storage."""

import asyncio

from swbt.input import Button, InputState


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

    async def press(self, *buttons: Button) -> InputState:
        """Add buttons to the current input state."""
        async with self._lock:
            self._state = self._state.with_buttons((*self._state.buttons, *buttons))
            return self._state

    async def release(self, *buttons: Button) -> InputState:
        """Remove buttons from the current input state."""
        async with self._lock:
            self._state = self._state.with_buttons(self._state.buttons.difference(buttons))
            return self._state
