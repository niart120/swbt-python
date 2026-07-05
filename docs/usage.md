# Usage

目的別の利用例です。API の引数と例外は `docs/api.md`、実機条件は `docs/hardware.md` にあります。実機接続には専用 USB Bluetooth dongle、Bumble、対象機器側の pairing / reconnect 操作が必要です。

## Minimal Example

初回実行では `allow_pairing=True` を付け、対象機器を controller pairing / search 画面に置きます。

```python
import asyncio
from swbt import Button, SwitchGamepad


async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.tap(Button.A)
        await pad.neutral()


asyncio.run(main())
```

`async with` は終了時に `close(neutral=True)` 相当で閉じます。`neutral()` は state update API であり、即時送信を保証しません。接続中は後続の periodic report で反映されます。

## Connection

### First-Run Pairing Or Reconnect Fallback

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
```

`connect()` は保存済み bond があれば reconnect を先に試します。bond がない場合、`allow_pairing=True` のときだけ pairing へ進みます。

### Pairing Only

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.pair(timeout=30.0)
```

`pair()` は対象機器が controller pairing / search 画面にいるときだけ使います。

### Reconnect Only

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.reconnect(timeout=10.0)
```

`reconnect()` は key store に current bonded peer が 1 件ある状態だけを扱います。pairing fallback はしません。

### Handling Result Values

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    result = await pad.try_connect(timeout=30.0, allow_pairing=True)
    if result.status != "connected":
        print(result.status, result.route, result.peer_count)
```

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    result = await pad.try_reconnect(timeout=10.0)
    if result.status == "no_bond":
        print("pairing is required")
```

`try_connect()` / `try_reconnect()` は接続戦略の結果を `ConnectionResult` で返します。key store の形式不一致や複数 current peers は `InvalidKeyStoreError` として扱います。

### Separate Key Stores By Target Device And Profile

```python
first = SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-2-fw-22-1-0.json",
)
second = SwitchGamepad(
    adapter="usb:0",
    key_store_path="other-switch.json",
)
```

1 つの key store に複数の current peer を混ぜないでください。別の対象機器へ pairing したい場合は、対象機器ごとに別の `key_store_path` を使います。Pro Controller、Joy-Con L、Joy-Con R のように profile が違う場合も、同じ対象機器で key store を共有しません。

## Single Joy-Con L/R

単体 Joy-Con 相当の仮想デバイスは `JoyCon("left", ...)` または `JoyCon("right", ...)` で作ります。`JoyCon` は `SwitchGamepad` の薄い wrapper で、`connect()`、`pair()`、`reconnect()`、入力 API、`close(neutral=True)` の契約は同じです。

### Left Joy-Con

```python
import asyncio
from swbt import Button, JoyCon, Stick


async def main() -> None:
    async with JoyCon(
        "left",
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

左 Joy-Con では D-pad、L/ZL、MINUS、CAPTURE、SL/SR、left stick を使います。

### Right Joy-Con

```python
import asyncio
from swbt import Button, JoyCon, Stick


async def main() -> None:
    async with JoyCon(
        "right",
        adapter="usb:0",
        key_store_path="switch-right-joycon-bond.json",
    ) as right:
        await right.connect(timeout=30.0, allow_pairing=True)
        await right.tap(Button.A)
        await right.rstick(Stick.right())
        await right.neutral()


asyncio.run(main())
```

右 Joy-Con では A/B/X/Y、R/ZR、PLUS、HOME、SL/SR、right stick を使います。

### Unsupported Inputs

片側 Joy-Con が持たない button や stick は `UnsupportedInputError` になります。

```python
from swbt import Button, JoyCon, Stick, UnsupportedInputError

async with JoyCon(
    "left",
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

`InputState` + `apply()` でも同じ検査を行います。左 Joy-Con に right stick、右 Joy-Con に left stick や D-pad を含めると `UnsupportedInputError` です。

Change Grip/Order 画面で単体 Joy-Con として順番登録する場合は、接続後に `await joycon.tap(Button.SR, Button.SL)` のように SR+SL を送ります。

左右ペアの `JoyConPair` は未実装です。左右を 1 つの controller として扱う API は別 issue の範囲です。

Joy-Con profile の実機互換、SDP 完全一致、OS / dongle / firmware をまたぐ互換性は未検証です。2026-07-06 の Joy-Con L 実機観測では、HID 通信上の device name と device-info reply は Joy-Con L になりましたが、Switch UI では Pro Controller として登録され、コントローラーの順番画面は Joy-Con L の SR+SL 入力待ちで止まりました。Joy-Con L/R を実機で試す場合は、Pro Controller 相当で確認済みの結果とは分けて記録してください。

## Button Input

### Tap A

```python
await pad.tap(Button.A)
```

`tap()` は action API です。接続済みを要求し、押下と release の input report を即時送信します。

### Hold ZL And Tap A

```python
await pad.press(Button.ZL)
await pad.tap(Button.A)
await pad.release(Button.ZL)
```

`tap(Button.A)` は A だけを release します。事前に `press(Button.ZL)` した ZL は維持されます。

### Hold L+R Then Release

```python
import asyncio
from swbt import Button

await pad.press(Button.L, Button.R)
await asyncio.sleep(0.5)
await pad.release(Button.L, Button.R)
await pad.neutral()
```

`press()` / `release()` は state update API です。接続を要求せず、即時送信を保証しません。

## Stick Input

### Tilt The Left Stick

```python
from swbt import Stick

await pad.lstick(Stick.up())
await pad.lstick(Stick.up(0.5))
```

`lstick()` は left stick だけを置き換える state update API です。`Stick.up()` は全倒し、`Stick.up(0.5)` は半倒しです。

### Tilt The Right Stick

```python
from swbt import Stick

await pad.rstick(Stick.right())
```

`rstick()` は right stick だけを置き換えます。

### Arbitrary Stick Coordinates

```python
from swbt import Stick

await pad.sticks(left=Stick.tilt(0.7, 0.7))
```

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ `-1.0..1.0` の正規化座標を使う短い生成 API です。`sticks()`、`lstick()`、`rstick()` は `Stick` だけを受けます。tuple や raw tuple は受けません。

### Press B And Tilt The Left Stick

複数の state update API 呼び出しは、同一 HID report に入る保証はありません。

```python
await pad.press(Button.B)
await pad.lstick(Stick.up())
```

完全同時入力が必要な場合は、complete `InputState` を作って `apply()` します。

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

`imu()` は IMU だけを置き換える state update API です。`imu(frame)` は 3 frame すべてに同じ値を設定します。即時送信を保証しません。

### Set Accel And Gyro In One Frame

```python
from swbt import IMUFrame

frame = IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)
await pad.imu(frame)
```

`IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)` は accel を設定した frame に gyro を追加します。`IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, 0))` と同じ値です。

### Three IMU Frames

```python
from swbt import IMUFrame

await pad.imu(
    IMUFrame.gyro(100, 0, 0),
    IMUFrame.gyro(120, 0, 0),
    IMUFrame.gyro(140, 0, 0),
)
```

3 frame を渡した場合は順に設定します。0 個、2 個、4 個以上、`IMUFrame` 以外は `InvalidInputError` です。

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

`with_accel((0, 0, 4096))` と `with_gyro((100, 0, 0))` は 1 sample を 3 frame すべてに複製します。3 sample を渡すと、各 frame の accel または gyro を順に置き換えます。button、stick、IMU を同じ complete state として扱いたい場合は `InputState` + `apply()` を使います。

## Neutral And Close

```python
await pad.neutral()
```

`neutral()` は local state を neutral に戻します。即時送信を保証しません。

```python
await pad.close(neutral=True)
```

`close(neutral=True)` は接続中なら trailing neutral を試みてから transport を閉じます。`async with` の scope 終了時に同じ処理が走るため、scope の最後で重ねて呼ぶ必要はありません。

## Diagnostics

```python
from pathlib import Path
from swbt import DiagnosticsConfig, SwitchGamepad

with Path("trace.jsonl").open("w", encoding="utf-8") as trace:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
        diagnostics=DiagnosticsConfig(trace_writer=trace),
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        status = pad.status()
        print(status.connection_state)
```

`DiagnosticsConfig(trace_writer=trace)` は JSON Lines trace を出します。`pad.status()` は connection state、report counter、last subcommand、raw rumble、last error を返します。

## Scope

初期 public API には duration 付き保持入力、入力列 runner、公開の現在入力送信 API、fluent builder API はありません。入力列や macro runner が必要になった場合は、利用者側で `asyncio` と公開 API を組み合わせてください。
