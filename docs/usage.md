# 利用例

目的別の利用例です。API の引数、例外、送信方式ごとの契約は `docs/api.md`、実機での検証条件は `docs/hardware.md` にあります。実機接続には専用 USB Bluetooth ドングル、Bumble、対象機器側のペアリングまたは再接続操作が必要です。

## クイックスタート

### 周期送信型

以下の例は作成済みの `profiles/switch-pro.json` を使います。初回作成は「Pro Controller プロファイルの初回作成」を先に実行します。ペアリングを再試行する場合は `allow_pairing=True` を指定し、対象機器側でコントローラー接続画面を開きます。

```python
import asyncio
from swbt import Button, ProController


async def main() -> None:
    async with ProController(
        adapter="usb:0",
        profile_path="profiles/switch-pro.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.press(Button.A)
        await asyncio.sleep(0.5)
        await pad.release(Button.A)
        await pad.neutral()


asyncio.run(main())
```

`ProController` は周期送信型です。`async with` の有効範囲を抜けると、`close(neutral=True)` 相当の終了処理が実行されます。

### 直接送信型

```python
import asyncio
from swbt import Button, DirectProController, InputState, Stick


async def main() -> None:
    async with DirectProController(
        adapter="usb:0",
        profile_path="switch-direct-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)

        state = InputState.neutral().with_buttons([Button.B]).with_sticks(
            left_stick=Stick.up(),
        )
        await pad.send(state)
        await pad.neutral()


asyncio.run(main())
```

`DirectProController` は直接送信型です。構築した `InputState` は `send(state)` へ渡します。

## 接続

### プロファイルの初回作成

全 concrete controller の exp local identity と接続情報を永続化する場合は、最初の 1 回だけ各 class の `create_profile()` を使います。`exp_local_address` は利用者が生成し、同時に使う他の Bluetooth デバイスと重複しない値を選びます。例示した値を共通値として使わず、controller kind と対象機器ごとに管理する値へ置き換えてください。

```python
pad = await ProController.create_profile(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
    exp_local_address="02:12:34:56:78:9A",
    pair_timeout=60.0,
)
try:
    await pad.neutral()
finally:
    await pad.close()
```

Joy-Con も同じ手順で作成します。左右で同じ `profile_path` または `exp_local_address` を共有しません。

```python
left = await JoyConL.create_profile(
    adapter="usb:0",
    profile_path="profiles/switch-left-joycon.json",
    exp_local_address="06:12:34:56:78:9A",
    pair_timeout=60.0,
)
await left.close()
```

対象は CSR8510 A10 の揮発領域への書換経路です。アダプタの永続領域は変更しません。既存のパスは上書きされません。ペアリングが失敗してもプロファイルは残るため、作成時と同じ具象クラスの `profile_path` から再試行します。`ExpLocalAddressRecoveryRequired` が送出された場合は、USB ドングルを抜き差ししてから再試行してください。別の controller kind の profile を渡した場合は `ProfileControllerMismatchError` がアダプタを開く前に送出されます。

### 接続時の再接続・ペアリング選択

```python
async with ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
) as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
```

プロファイルに保存済みペアリング情報があれば再接続を試し、ない場合はペアリングを行います。初回接続では対象機器をコントローラー接続画面に置いてから呼び出します。

### ペアリングのみ

```python
async with ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
) as pad:
    await pad.pair(timeout=30.0)
```

保存済みペアリング情報を使わず、初回ペアリングだけを行う場合に使います。呼び出す前に対象機器をコントローラー接続画面に置いてください。

### 再接続のみ

```python
async with ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
) as pad:
    await pad.reconnect(timeout=10.0)
```

保存済みペアリング情報だけを使って再接続する場合に使います。ペアリングは開始しません。

### 結果の扱い

接続できなかった場合も処理を続けるときは、`try_connect()` または `try_reconnect()` を使います。

```python
async with ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
) as pad:
    result = await pad.try_connect(timeout=30.0, allow_pairing=True)
    if result.status != "connected":
        print(f"接続できませんでした: {result.status}")
```

```python
async with ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
) as pad:
    result = await pad.try_reconnect(timeout=10.0)
    if result.status == "no_bond":
        print("ペアリングが必要です")
```

### 対象機器・プロファイル別の保存ファイル

```python
first = ProController(
    adapter="usb:0",
    profile_path="profiles/switch-2-fw-22-1-0-pro.json",
)
second = ProController(
    adapter="usb:0",
    profile_path="profiles/other-switch-pro.json",
)
```

1 つの保存ファイルに複数の保存済みペアリング情報を混ぜないでください。全 concrete controller で、controller kind と対象機器ごとに別の `profile_path` を使います。

## Joy-Con L/R

周期送信型には `JoyConL(...)` または `JoyConR(...)`、直接送信型には `DirectJoyConL(...)` または `DirectJoyConR(...)` を使います。以下は周期送信型の例です。

### Joy-Con L

```python
import asyncio
from swbt import Button, JoyConL, Stick


async def main() -> None:
    async with JoyConL(
        adapter="usb:0",
        profile_path="profiles/switch-left-joycon.json",
    ) as left:
        await left.connect(timeout=30.0, allow_pairing=True)
        await left.tap(Button.SR, Button.SL)
        await left.tap(Button.L)
        await left.lstick(Stick.left())
        await left.neutral()


asyncio.run(main())
```

「持ちかた/順番を変える」画面で Joy-Con として登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送信します。

### Joy-Con R

```python
import asyncio
from swbt import Button, JoyConR, Stick


async def main() -> None:
    async with JoyConR(
        adapter="usb:0",
        profile_path="profiles/switch-right-joycon.json",
    ) as right:
        await right.connect(timeout=30.0, allow_pairing=True)
        await right.tap(Button.A)
        await right.rstick(Stick.right())
        await right.neutral()


asyncio.run(main())
```

### 非対応入力の扱い

対応しない入力を検出する場合は、`UnsupportedInputError` を捕捉します。

```python
from swbt import Button, JoyConL, Stick, UnsupportedInputError

async with JoyConL(
    adapter="usb:0",
    profile_path="profiles/switch-left-joycon.json",
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

左右ペアを 1 つのコントローラーとして扱う `JoyConPair` は未実装です。

## ボタン入力

以下の入力例では、接続済みのコントローラーを `pad` とします。

### A ボタンの押下と解放

```python
await pad.tap(Button.A)
```

短いボタン入力には `tap()` を使います。

### ZL 押下中の A ボタン操作

```python
await pad.press(Button.ZL)
await pad.tap(Button.A)
await pad.release(Button.ZL)
```

`tap(Button.A)` の後も、先に `press(Button.ZL)` した ZL は維持されます。

### L+R の押下と解放

```python
import asyncio
from swbt import Button

await pad.press(Button.L, Button.R)
await asyncio.sleep(0.5)
await pad.release(Button.L, Button.R)
await pad.neutral()
```

## スティック入力

### 左スティックの倒し込み

```python
from swbt import Stick

await pad.lstick(Stick.up())
await pad.lstick(Stick.up(0.5))
```

`Stick.up()` は全倒し、`Stick.up(0.5)` は半倒しです。

### 右スティックの倒し込み

```python
from swbt import Stick

await pad.rstick(Stick.right())
```

### 任意座標のスティック入力

```python
from swbt import Stick

await pad.sticks(left=Stick.tilt(0.7, 0.7))
```

`Stick.tilt(x, y)` は正規化座標でスティックの位置を指定します。左右のスティックを一度に指定する場合は `sticks(left=..., right=...)` を使います。

## 6 軸センサー入力

### ジャイロだけの設定

```python
from swbt import IMSFrame

await pad.imu(IMSFrame.gyro(100, 0, 0))
```

### 角速度の指定

```python
from math import radians
from swbt import IMSFrame

omega_x = radians(90.0)
omega_y = radians(-45.0)
omega_z = 0.0
frame = IMSFrame.gyro_rate(
    x_rad_s=omega_x,
    y_rad_s=omega_y,
    z_rad_s=omega_z,
)
await pad.imu(frame)

x_rad_s, y_rad_s, z_rad_s = frame.to_gyro_rate()
```

`IMSFrame.gyro_rate()` は角速度を rad/s 単位で指定するときに使います。

### 加速度とジャイロの設定

```python
from swbt import IMSFrame

frame = IMSFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)
await pad.imu(frame)
```

### 3 入力分の個別設定

```python
from swbt import IMSFrame

await pad.imu(
    IMSFrame.gyro(100, 0, 0),
    IMSFrame.gyro(120, 0, 0),
    IMSFrame.gyro(140, 0, 0),
)
```

## 完全入力状態の送信

ボタン、スティック、6 軸センサーをまとめて指定する場合は、`InputState` を組み立てます。

```python
from swbt import Button, InputState, Stick

state = (
    InputState.neutral()
    .with_buttons([Button.B])
    .with_sticks(left_stick=Stick.up())
    .with_accel((0, 0, 4096))
    .with_gyro((100, 0, 0))
)
```

周期送信型では `apply(state)` を使います。

```python
await pad.apply(state)
```

直接送信型では `send(state)` を使います。

```python
await pad.send(state)
```

## ニュートラル入力と終了

```python
await pad.neutral()
```

`neutral()` は、ボタンを離し、左右のスティックを中央へ戻し、6 軸センサーをニュートラルに戻します。入力操作の区切りで使います。

`async with` を使う場合は、有効範囲を抜けると終了処理が自動で実行されます。

## トレース出力

```python
from pathlib import Path
from swbt import Button, DiagnosticsConfig, ProController

with Path("trace.jsonl").open("w", encoding="utf-8") as trace:
    async with ProController(
        adapter="usb:0",
        profile_path="profiles/switch-pro.json",
        diagnostics=DiagnosticsConfig(trace_writer=trace),
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.tap(Button.A)
        print(pad.status().connection_state)
```

`DiagnosticsConfig` は実行記録をトレースログへ出力します。`trace_writer` に渡すストリームは、`async with` の有効範囲が終わるまで開いておきます。`pad.status()` は、その時点の接続状態をコードから確認するときに使います。
