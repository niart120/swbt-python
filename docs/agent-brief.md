# Agent Brief

Use public imports:

```python
from swbt import (
    Button,
    DirectJoyConL, DirectJoyConR, DirectProController,
    IMUFrame,
    InputState,
    JoyConL, JoyConR, ProController,
    PeriodicSwitchGamepad, DirectSwitchGamepad,
    Stick,
    SwitchGamepad,
)
```

Prefer this minimal pattern:

```python
async with ProController(adapter="usb:0", profile_path="profiles/switch-pro.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
    await pad.neutral()
```

Create a new persistent Pro Controller profile once with
`await ProController.create_profile(adapter=..., profile_path=...,
pair_timeout=...)`. This keeps the adapter's current default address and does not
write volatile identity state. Pass `local_address=...` only when the caller owns
address generation and collision avoidance. The path must not already exist. Reuse
the returned connected controller or close it and pass the same `profile_path` to
`ProController(...)`. The adapter-default path has been verified for a Pro
Controller profile on Windows 11 with CSR8510 A10 and WinUSB; other controller
profiles, operating systems, and adapters remain unverified. The explicit-address
CSR8510 A10 path writes only volatile state. On
`AdapterIdentityRecoveryRequired`, unplug and reconnect the dedicated USB Bluetooth
dongle before retrying.

For a single Joy-Con L/R, use `JoyConL(...)` or `JoyConR(...)`:

```python
async with JoyConL(adapter="usb:0", profile_path="switch-left-joycon-bond.json") as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.L)
    await left.neutral()
```

Use `DirectProController(...)`, `DirectJoyConL(...)`, or `DirectJoyConR(...)`
when caller code owns every input-report trigger:

```python
async with DirectProController(adapter="usb:0", profile_path="switch-direct.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.send(InputState.neutral().with_buttons([Button.A]))
```

Rules:

- Use `connect(..., allow_pairing=True)` for first-run examples.
- Use `pair()` only when the target device is in controller pairing/search mode.
- Use `reconnect()` only when the profile contains one current bonded peer.
- Use `try_connect()` / `try_reconnect()` when code needs `ConnectionResult` instead of exceptions.
- Use `tap()` for immediate short button input.
- Use `press()` / `release()` for held button state.
- Use `lstick()` / `rstick()` for one-stick state updates.
- Use `sticks()` when both sticks should be updated in one state update.
- Use `Stick.up()`, `Stick.down()`, `Stick.left()`, `Stick.right()`, or `Stick.tilt()` to construct stick values.
- Use `imu()` for IMU state updates.
- Use `IMUFrame.gyro()`, `IMUFrame.accel()`, `IMUFrame.raw()`, `IMUFrame.with_gyro()`, or `IMUFrame.with_accel()` for raw IMU values.
- Use `IMUFrame.gyro_rate()` or `IMUFrame.with_gyro_rate()` for angular velocity in rad/s, and `IMUFrame.to_gyro_rate()` for conversion back to rad/s. The scale is fixed at `0.070 dps/raw`.
- Do not pre-pack quaternion motion. The runtime selects standard or quaternion wire packing from the host IMU mode.
- Treat an unspecified host IMU mode or mode `0x00` as disabled; the runtime sends a zero IMU block and does not carry host mode or quaternion state across reopen.
- Use `IMUFrame.accel_g()` or `IMUFrame.with_accel_g()` for acceleration in G, and `IMUFrame.to_accel_g()` for conversion back to G. The scale is fixed at `1/4096 G/raw`.
- Use `InputState` + `apply()` when buttons, sticks, and IMU must be one complete state.
- Use `InputState` + `send()` for one complete Direct input report. Awaiting it means Bumble accepted the report for enqueue; it does not guarantee HCI completion or target-device reflection. State commits after enqueue acceptance.
- Use a separate `profile_path` for every controller shape and target device. When an explicit local address is used, manage it separately as well.
- Treat unsupported one-sided Joy-Con inputs as `UnsupportedInputError`: left does not support right stick or A/B/X/Y, right does not support left stick or D-pad.
- Use `SwitchGamepad` only when code accepts either reporting contract. Use `PeriodicSwitchGamepad` or `DirectSwitchGamepad` when the sending contract matters.
- Instantiate `ProController`, `JoyConL`, or `JoyConR` for Periodic reporting. Instantiate the corresponding `Direct*` class for Direct reporting.
- Do not call `apply()` on Direct types or `send()` on Periodic types.
- Do not assume Periodic `press()` / `release()` / `lstick()` / `rstick()` / `sticks()` / `imu()` / `neutral()` send immediately.
- Direct semantic input operations send one report and commit only after successful enqueue acceptance.
- Do not pass tuples or raw tuples to stick APIs.
- Do not invent `pad.gyro()` or `pad.accel()`.
- Do not invent `hold()`, `sequence()`, `send_current_input()`, fluent builder APIs, or macro helpers.
- Do not invent `JoyConPair`; paired left/right Joy-Con support is not implemented.
- Do not show low-level Joy-Con profile classes or the removed side-string Joy-Con wrapper in user-facing examples.
- Do not import internal modules unless writing swbt's own tests.
- Do not present Joy-Con hardware compatibility beyond the recorded Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.5.0 profile scenarios. Exact SDP parity, Linux, Joy-Con on macOS, other dongles, other firmware, and pairing-free incoming bond reuse are not confirmed.
