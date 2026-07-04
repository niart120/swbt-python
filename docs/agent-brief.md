# Agent Brief

Use public imports:

```python
from swbt import Button, InputState, Stick, SwitchGamepad
```

Prefer this minimal pattern:

```python
async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
    await pad.neutral()
```

Rules:

- Use `connect(..., allow_pairing=True)` for first-run examples.
- Use `pair()` only when the target device is in controller pairing/search mode.
- Use `reconnect()` only when a key store already contains one current bonded peer.
- Use `try_connect()` / `try_reconnect()` when code needs `ConnectionResult` instead of exceptions.
- Use `tap()` for immediate short button input.
- Use `press()` / `release()` for held button state.
- Use `lstick()` / `rstick()` for one-stick state updates.
- Use `sticks()` when both sticks should be updated in one state update.
- Use `Stick.up()`, `Stick.down()`, `Stick.left()`, `Stick.right()`, or `Stick.tilt()` to construct stick values.
- Use `imu()` for IMU state updates.
- Use `IMUFrame.gyro()`, `IMUFrame.accel()`, `IMUFrame.raw()`, `IMUFrame.with_gyro()`, or `IMUFrame.with_accel()` to construct IMU frames.
- Use `InputState` + `apply()` when buttons, sticks, and IMU must be one complete state.
- Do not assume `press()` / `release()` / `lstick()` / `rstick()` / `sticks()` / `imu()` / `neutral()` send immediately.
- Do not pass tuples or raw tuples to stick APIs.
- Do not invent `pad.gyro()` or `pad.accel()`.
- Do not invent `hold()`, `sequence()`, `send_current_input()`, fluent builder APIs, or macro helpers.
- Do not import internal modules unless writing tests or custom transport code.
- Do not present Linux, macOS, other dongles, other firmware, or pairing-free incoming bond reuse as confirmed.
