# 利用例

目的別の利用例です。API の引数と例外は `docs/api.md`、実機での検証条件は `docs/hardware.md` にあります。実機接続には専用 USB Bluetooth ドングル、Bumble、対象機器側のペアリングまたは再接続操作が必要です。

## クイックスタート

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

`async with` の終了時には、`close(neutral=True)` 相当の処理が自動で実行されます。`neutral()` は入力状態をニュートラルに戻す状態更新 API です。即時送信は保証せず、接続中の後続の入力レポートで反映されます。

## 直接送信型の利用例

直接送信型では入力レポートの送信頻度を利用者が管理します。レポートループは開始されないため、対象機器が必要とする最低送信頻度も利用者側の処理で満たしてください。ライブラリは送信間隔を補完しません。

```python
import asyncio
from swbt import Button, DirectProController, InputState, Stick


async def main() -> None:
    async with DirectProController(
        adapter="usb:0",
        key_store_path="switch-direct-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)

        state = InputState.neutral().with_buttons([Button.B]).with_sticks(
            left_stick=Stick.up(),
        )
        await pad.send(state)
        await pad.release(Button.B)
        await pad.neutral()


asyncio.run(main())
```

`send(state)` は入力レポートを 1 件送り、下位の通信実装（`transport`）の送信完了後に状態を確定します。`press()`、`release()`、`sticks()`、`lstick()`、`rstick()`、`imu()`、`neutral()` も、直接送信型では各正常終了につき入力レポートを 1 件送信します。未接続、プロファイル検査、`transport` の送信で失敗した場合、`snapshot()` は最後に正常送信した状態を維持します。

直接送信型の `tap()` は押下と解放の 2 件を送ります。ホストから届くサブコマンドへの応答は直接送信型でも自動送信されます。`close(neutral=True)` は終了時の処理としてニュートラル入力を 1 件試み、`close(neutral=False)` は入力レポートを追加しません。

Joy-Con の直接送信型には `DirectJoyConL(...)` と `DirectJoyConR(...)` を使います。対応するボタンとスティック、`UnsupportedInputError` の条件は周期送信型の `JoyConL(...)` / `JoyConR(...)` と同じです。

## 接続

### 接続時の再接続・ペアリング選択

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
```

`connect()` は保存済みペアリング情報があれば `reconnect()` を先に試します。保存済みペアリング情報がない場合は、`allow_pairing=True` のときだけペアリングへ進みます。

### ペアリングのみ

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.pair(timeout=30.0)
```

`pair()` は初回ペアリング用です。対象機器をコントローラー接続画面に置いてから呼び出します。

### 再接続のみ

```python
async with ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.reconnect(timeout=10.0)
```

`reconnect()` は指定した保存ファイルにペアリング情報が 1 件だけある場合に、その情報で再接続を試みます。ペアリングには進みません。

### 結果の扱い

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
        print("ペアリングが必要です")
```

`try_connect()` / `try_reconnect()` は接続結果を `ConnectionResult` で返します。指定した保存ファイルの形式不一致や、現在の再接続候補が複数ある状態は `InvalidKeyStoreError` として扱います。

### 対象機器・プロファイル別の保存ファイル

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

1 つの保存ファイルに複数の保存済みペアリング情報を混ぜないでください。別の対象機器とペアリングする場合は、対象機器ごとに別の `key_store_path` を使います。Pro Controller、Joy-Con L、Joy-Con R のようにプロファイルが違う場合も、同じ対象機器で保存ファイルを共有しません。

## Joy-Con L/R

Joy-Con 相当の仮想デバイスは `JoyConL(...)` または `JoyConR(...)` で作成します。接続と入力の扱い方は `ProController` と同じです。

### Joy-Con L

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

### Joy-Con R

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

### 非対応入力の扱い

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

「持ちかた/順番を変える」画面で Joy-Con として登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送信します。

左右ペアを 1 つのコントローラーとして扱う `JoyConPair` は未実装です。

## ボタン入力

### A ボタンの押下と解放

```python
await pad.tap(Button.A)
```

`tap()` は操作 API です。接続済みであることを要求し、押下レポートと解放レポートを即時送信します。

### ZL 押下中の A ボタン操作

```python
await pad.press(Button.ZL)
await pad.tap(Button.A)
await pad.release(Button.ZL)
```

`tap(Button.A)` は、この呼び出しで押した A だけを離します。事前に `press(Button.ZL)` した ZL は維持されます。

### L+R の押下と解放

```python
import asyncio
from swbt import Button

await pad.press(Button.L, Button.R)
await asyncio.sleep(0.5)
await pad.release(Button.L, Button.R)
await pad.neutral()
```

`press()` / `release()` は状態更新 API です。接続済みであることを要求せず、即時送信も保証しません。

## スティック入力

### 左スティックの倒し込み

```python
from swbt import Stick

await pad.lstick(Stick.up())
await pad.lstick(Stick.up(0.5))
```

`lstick()` は左スティック入力だけを置き換える状態更新 API です。`Stick.up()` は全倒し、`Stick.up(0.5)` は半倒しです。

### 右スティックの倒し込み

```python
from swbt import Stick

await pad.rstick(Stick.right())
```

`rstick()` は右スティック入力だけを置き換える状態更新 API です。

### 任意座標のスティック入力

```python
from swbt import Stick

await pad.sticks(left=Stick.tilt(0.7, 0.7))
```

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ `-1.0..1.0` の正規化座標を使う短い生成 API です。`sticks()`、`lstick()`、`rstick()` は `Stick` だけを受けます。タプルや生の座標組は受けません。

### ボタンとスティックの同時入力

複数の状態更新 API 呼び出しは、同じ HID レポートに入る保証はありません。

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

## 6 軸センサー入力

### ジャイロだけの設定

```python
from swbt import IMUFrame

await pad.imu(IMUFrame.gyro(100, 0, 0))
```

`imu()` は現在の 6 軸センサー入力だけを置き換えます。1 つの `IMUFrame` を渡すと、同じ値が 3 入力分に設定されます。値はレポートループから送信されるため、呼び出し時の即時送信は保証しません。

### 角速度の指定

```python
from math import radians
from swbt import IMUFrame

omega_x = radians(90.0)
omega_y = radians(-45.0)
omega_z = 0.0
frame = IMUFrame.gyro_rate(x_rad_s=omega_x, y_rad_s=omega_y, z_rad_s=omega_z)
await pad.imu(frame)

x_rad_s, y_rad_s, z_rad_s = frame.to_gyro_rate()
```

`gyro_rate()` は角速度を rad/s 単位で受け取ります。設定値を同じ単位で取得するには `to_gyro_rate()` を使います。センサーの生値を直接指定する場合は `IMUFrame.gyro()` を使います。

内部では `0.070 dps/raw` の尺度で生値へ変換します。変換結果が 16 ビット符号付き整数の範囲を超える場合は、上限値や下限値への丸めを行わず `InvalidInputError` が送出されます。Switch との通信形式は自動で選ばれます。

### 加速度とジャイロの設定

```python
from swbt import IMUFrame

frame = IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)
await pad.imu(frame)
```

`IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)` は、加速度を設定した入力値にジャイロを追加します。`IMUFrame.raw(accel=(0, 0, 4096), gyro=(100, 0, 0))` と同じ値です。

加速度を G 単位で指定する場合は `IMUFrame.accel_g(x_g=0.0, y_g=0.0, z_g=1.0)` を使います。`frame.to_accel_g()` は設定値を G 単位の 3 軸値として返します。内部の変換尺度は `1/4096 G/raw` です。ジャイロを維持して加速度だけを置き換える場合は `frame.with_accel_g(x_g=..., y_g=..., z_g=...)` を使います。

加速度を維持したまま物理角速度を設定する場合は、`frame.with_gyro_rate(x_rad_s=..., y_rad_s=..., z_rad_s=...)` を使います。

### 3 入力分の個別設定

```python
from swbt import IMUFrame

await pad.imu(
    IMUFrame.gyro(100, 0, 0),
    IMUFrame.gyro(120, 0, 0),
    IMUFrame.gyro(140, 0, 0),
)
```

3 つの `IMUFrame` を渡すと、それぞれの値が順に設定されます。引数の数が 1 個または 3 個でない場合や、`IMUFrame` 以外を渡した場合は `InvalidInputError` が送出されます。

### ボタン・スティック・6 軸センサーの同時更新

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

`with_accel((0, 0, 4096))` と `with_gyro((100, 0, 0))` は、1 入力分の値を 3 入力分に複製します。3 入力分を渡すと、各値の加速度またはジャイロを順に置き換えます。ボタン、スティック、6 軸センサーを同じタイミングで更新する場合は、`InputState` を組み立てて `apply()` に渡します。

## ニュートラル入力と終了

```python
await pad.neutral()
```

`neutral()` は現在の入力状態をニュートラルに戻します。即時送信は保証しません。

```python
await pad.close(neutral=True)
```

`close(neutral=True)` は接続中なら終了前のニュートラル入力を試みてから `transport` を閉じます。`async with` の有効範囲の終了時に同じ処理が実行されるため、有効範囲の最後で重ねて呼ぶ必要はありません。

## トレース出力

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

`DiagnosticsConfig(trace_writer=trace)` は JSON Lines のトレースログを出力します。出力されるのは接続状態の遷移、送信したレポート、受信したサブコマンド、エラー、実行時のメタデータです。原因を自動判定する機能ではありません。

`pad.status()` は接続状態、レポートカウンター、最後に処理したサブコマンド、振動の生値、最後のエラーを返します。ファイルに残す必要がある実行記録は `DiagnosticsConfig`、その時点の状態をコードから読む用途は `status()` を使います。
