"""Async-safe input state storage."""

import asyncio

from swbt.input import Button, IMUFrame, InputState, Stick


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

    async def sticks(self, *, left: Stick | None = None, right: Stick | None = None) -> InputState:
        """Replace one or both stick positions."""
        async with self._lock:
            self._state = self._state.with_sticks(left_stick=left, right_stick=right)
            return self._state

    async def imu(self, *frames: IMUFrame) -> InputState:
        """Replace IMU frames."""
        async with self._lock:
            self._state = self._state.with_imu(*frames)
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

    async def neutral(self) -> InputState:
        """Replace the current input state with neutral input."""
        async with self._lock:
            self._state = InputState.neutral()
            return self._state
