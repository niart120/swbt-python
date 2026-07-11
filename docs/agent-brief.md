# Agent Brief

Use public imports:

```python
from swbt import Button, InputState, JoyConL, JoyConR, ProController, Stick, SwitchGamepad
```

Prefer this minimal pattern:

```python
async with ProController(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
    await pad.neutral()
```

For a single Joy-Con L/R, use `JoyConL(...)` or `JoyConR(...)`:

```python
async with JoyConL(adapter="usb:0", key_store_path="switch-left-joycon-bond.json") as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.L)
    await left.neutral()
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
- Use `IMUFrame.gyro()`, `IMUFrame.accel()`, `IMUFrame.raw()`, `IMUFrame.with_gyro()`, or `IMUFrame.with_accel()` for raw IMU values.
- Use `IMUFrame.gyro_rate()` or `IMUFrame.with_gyro_rate()` for angular velocity in rad/s, and `IMUFrame.to_gyro_rate()` for conversion back to rad/s. The scale is fixed at `0.070 dps/raw`.
- Use `InputState` + `apply()` when buttons, sticks, and IMU must be one complete state.
- Use a separate `key_store_path` for Pro Controller, Joy-Con L, and Joy-Con R profiles, even when the target device is the same.
- Treat unsupported one-sided Joy-Con inputs as `UnsupportedInputError`: left does not support right stick or A/B/X/Y, right does not support left stick or D-pad.
- Use `SwitchGamepad` as a shared type annotation only; instantiate `ProController`, `JoyConL`, or `JoyConR`.
- Do not assume `press()` / `release()` / `lstick()` / `rstick()` / `sticks()` / `imu()` / `neutral()` send immediately.
- Do not pass tuples or raw tuples to stick APIs.
- Do not invent `pad.gyro()` or `pad.accel()`.
- Do not invent `hold()`, `sequence()`, `send_current_input()`, fluent builder APIs, or macro helpers.
- Do not invent `JoyConPair`; paired left/right Joy-Con support is not implemented.
- Do not show low-level Joy-Con profile classes or the removed side-string Joy-Con wrapper in user-facing examples.
- Do not import internal modules unless writing swbt's own tests.
- Do not present Joy-Con hardware compatibility beyond the recorded Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 profile scenarios. Exact SDP parity, Linux, Joy-Con on macOS, other dongles, other firmware, and pairing-free incoming bond reuse are not confirmed.
