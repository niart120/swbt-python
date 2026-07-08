# Usage

目的別の利用例です。API の引数と例外は `docs/api.md`、実機での検証条件は `docs/hardware.md` にあります。実機接続には専用 USB Bluetooth ドングル、Bumble、対象機器側のペアリングまたは再接続操作が必要です。

## Minimal Example

初回実行では `allow_pairing=True` を指定し、対象機器側はコントローラー接続画面にセットします。

```python
import asyncio
from swbt import Button, ProController


async def main() -> None:
    async with ProController(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.tap(Button.A)
        await pad.neutral()


asyncio.run(main())
```

`async with` の終了時には、`close(neutral=True)` 相当の処理が自動で実行されます。`neutral()` は入力状態をニュートラルに戻す state update API です。即時送信は保証せず、接続中の後続の入力レポートで反映されます。

## Connection

### First-Run Pairing Or Reconnect Fallback

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
```

`connect()` は保存済みペアリング情報があれば `reconnect()` を先に試します。保存済みペアリング情報がない場合は、`allow_pairing=True` のときだけペアリングへ進みます。

### Pairing Only

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.pair(timeout=30.0)
```

`pair()` は初回ペアリング用です。対象機器をコントローラー接続画面に置いてから呼び出します。

### Reconnect Only

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.reconnect(timeout=10.0)
```

`reconnect()` は key store に保存済みペアリング情報が 1 件だけある場合に、その情報で再接続を試みます。ペアリングには進みません。

### Handling Result Values

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    result = await pad.try_connect(timeout=30.0, allow_pairing=True)
    if result.status != "connected":
        print(result.status, result.route, result.peer_count)
```

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    result = await pad.try_reconnect(timeout=10.0)
    if result.status == "no_bond":
        print("pairing is required")
```

`try_connect()` / `try_reconnect()` は接続結果を `ConnectionResult` で返します。key store の形式不一致や、現在の再接続候補が複数ある状態は `InvalidKeyStoreError` として扱います。

### Separate Key Stores By Target Device And Profile

```python
first = ProController(
    adapter="usb:0",
    key_store_path="switch-2-fw-22-1-0.json",
)
second = ProController(
    adapter="usb:0",
    key_store_path="other-switch.json",
)
```

1 つの key store に複数の保存済みペアリング情報を混ぜないでください。別の対象機器とペアリングする場合は、対象機器ごとに別の `key_store_path` を使います。Pro Controller、Joy-Con L、Joy-Con R のように profile が違う場合も、同じ対象機器で key store を共有しません。

## Single Joy-Con L/R

Joy-Con 相当の仮想デバイスは `JoyConL(...)` または `JoyConR(...)` で作成します。接続と入力の扱い方は `ProController` と同じです。

### Left Joy-Con

```python
import asyncio
from swbt import Button, JoyConL, Stick


async def main() -> None:
    async with JoyConL(
        adapter="usb:0",
        key_store_path="switch-left-joycon-bond.json",
    ) as left:
        await left.connect(timeout=30.0, allow_pairing=True)
        await left.tap(Button.SR, Button.SL)
        await left.tap(Button.L)
        await left.lstick(Stick.left())
        await left.neutral()


asyncio.run(main())
```

Joy-Con（L）では十字キー、L/ZL、MINUS、CAPTURE、SL/SR、左スティックを使います。

### Right Joy-Con

```python
import asyncio
from swbt import Button, JoyConR, Stick


async def main() -> None:
    async with JoyConR(
        adapter="usb:0",
        key_store_path="switch-right-joycon-bond.json",
    ) as right:
        await right.connect(timeout=30.0, allow_pairing=True)
        await right.tap(Button.A)
        await right.rstick(Stick.right())
        await right.neutral()


asyncio.run(main())
```

Joy-Con（R）では A/B/X/Y、R/ZR、PLUS、HOME、SL/SR、右スティックを使います。

### Unsupported Inputs

各 Joy-Con が持たないボタンやスティック入力は `UnsupportedInputError` になります。

```python
from swbt import Button, JoyConL, Stick, UnsupportedInputError

async with JoyConL(
    adapter="usb:0",
    key_store_path="switch-left-joycon-bond.json",
) as left:
    try:
        await left.rstick(Stick.right())
    except UnsupportedInputError as error:
        print(error)

    try:
        await left.tap(Button.A)
    except UnsupportedInputError as error:
        print(error)
```

`InputState` + `apply()` でも同じ検査を行います。Joy-Con L に右スティック入力、Joy-Con R に左スティック入力や十字キー入力を含めると `UnsupportedInputError` になります。

"持ち方/順番を変える" 画面で Joy-Con として登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送信します。

左右ペアを 1 つのコントローラーとして扱う `JoyConPair` は未実装です。

## Button Input

### Tap A

```python
await pad.tap(Button.A)
```

`tap()` は action API です。接続済みであることを要求し、押下レポートと押上レポートを即時送信します。

### Hold ZL And Tap A

```python
await pad.press(Button.ZL)
await pad.tap(Button.A)
await pad.release(Button.ZL)
```

`tap(Button.A)` は、この呼び出しで押した A だけを離します。事前に `press(Button.ZL)` した ZL は維持されます。

### Hold L+R Then Release

```python
import asyncio
from swbt import Button

await pad.press(Button.L, Button.R)
await asyncio.sleep(0.5)
await pad.release(Button.L, Button.R)
await pad.neutral()
```

`press()` / `release()` は state update API です。接続済みであることを要求せず、即時送信も保証しません。

## Stick Input

### Tilt The Left Stick

```python
from swbt import Stick

await pad.lstick(Stick.up())
await pad.lstick(Stick.up(0.5))
```

`lstick()` は左スティック入力だけを置き換える state update API です。`Stick.up()` は全倒し、`Stick.up(0.5)` は半倒しです。

### Tilt The Right Stick

```python
from swbt import Stick

await pad.rstick(Stick.right())
```

`rstick()` は右スティック入力だけを置き換える state update API です。

### Arbitrary Stick Coordinates

```python
from swbt import Stick

await pad.sticks(left=Stick.tilt(0.7, 0.7))
```

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ `-1.0..1.0` の正規化座標を使う短い生成 API です。`sticks()`、`lstick()`、`rstick()` は `Stick` だけを受けます。tuple や raw tuple は受けません。

### Press B And Tilt The Left Stick

複数の state update API 呼び出しは、同じ HID レポートに入る保証はありません。

```python
await pad.press(Button.B)
await pad.lstick(Stick.up())
```

完全同時入力が必要な場合は、構築済みの `InputState` を作って `apply()` に渡します。

```python
from swbt import Button, InputState, Stick

state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.up(),
)
await pad.apply(state)
```

`apply()` は現在入力全体を置き換えます。差分適用ではありません。

## IMU Input

### Update Gyro Only

```python
from swbt import IMUFrame

await pad.imu(IMUFrame.gyro(100, 0, 0))
```

`imu()` は IMU 入力だけを置き換える state update API です。`imu(frame)` は 3 つの IMU frame すべてに同じ値を設定します。即時送信は保証しません。

### Set Accel And Gyro In One Frame

```python
from swbt import IMUFrame

frame = IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)
await pad.imu(frame)
```

`IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)` は、加速度を設定した frame にジャイロを追加します。`IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, 0))` と同じ値です。

### Three IMU Frames

```python
from swbt import IMUFrame

await pad.imu(
    IMUFrame.gyro(100, 0, 0),
    IMUFrame.gyro(120, 0, 0),
    IMUFrame.gyro(140, 0, 0),
)
```

3 つの IMU frame を渡した場合は順に設定します。0 個、2 個、4 個以上、または `IMUFrame` 以外を渡すと `InvalidInputError` になります。

### Complete State With Button, Stick, And IMU

```python
from swbt import Button, IMUFrame, InputState, Stick

state = (
    InputState.neutral()
    .with_buttons([Button.B])
    .with_sticks(left_stick=Stick.up())
    .with_accel((0, 0, 4096))
    .with_gyro((100, 0, 0))
)
await pad.apply(state)
```

`with_accel((0, 0, 4096))` と `with_gyro((100, 0, 0))` は 1 sample を 3 つの IMU frame すべてに複製します。3 sample を渡すと、各 frame の加速度またはジャイロを順に置き換えます。ボタン、スティック、IMU を同じ入力状態として扱う場合は `InputState` + `apply()` を使います。

## Neutral And Close

```python
await pad.neutral()
```

`neutral()` は現在の入力状態をニュートラルに戻します。即時送信は保証しません。

```python
await pad.close(neutral=True)
```

`close(neutral=True)` は接続中なら終了前のニュートラル入力を試みてから transport を閉じます。`async with` の scope 終了時に同じ処理が実行されるため、scope の最後で重ねて呼ぶ必要はありません。

## Diagnostics

```python
from pathlib import Path
from swbt import DiagnosticsConfig, ProController

with Path("trace.jsonl").open("w", encoding="utf-8") as trace:
    async with ProController(
        adapter="usb:0",
        key_store_path="switch-bond.json",
        diagnostics=DiagnosticsConfig(trace_writer=trace),
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        status = pad.status()
        print(status.connection_state)
```

`DiagnosticsConfig(trace_writer=trace)` は JSON Lines trace を出力します。`pad.status()` は接続状態、レポートカウンター、最後に処理した subcommand、raw rumble、最後のエラーを返します。
