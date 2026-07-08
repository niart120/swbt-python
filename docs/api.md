# Public API

`swbt-python` の公開 API は `swbt` module root から import します。

```python
from swbt import (
    AdapterInfo,
    Button,
    ControllerColors,
    IMUFrame,
    InputState,
    JoyConL,
    JoyConR,
    ProController,
    Stick,
    SwitchGamepad,
)
```

## Top-Level Exports

トップレベルでの公開APIと主な利用用途を説明します。

| name | 用途 |
|---|---|
| `list_adapters` | concrete controller の `adapter=...` に渡せる USB Bluetooth adapter 候補の列挙 |
| `AdapterInfo` | adapter 候補の no-open snapshot |
| `SwitchGamepad` | concrete controller 共通の abstract interface |
| `ProController` | Pro Controller 相当の concrete controller |
| `JoyConL` | 単体 Joy-Con L 相当の concrete controller |
| `JoyConR` | 単体 Joy-Con R 相当の concrete controller |
| `ControllerColors` | controller body / buttons / left grip / right grip の固定 profile 色 |
| `ConnectionResult` | `try_connect()` / `try_reconnect()` の結果 |
| `Button` | 対応する各種ボタン |
| `Stick` | スティック入力 |
| `IMUFrame` | IMU frame |
| `InputState` | イミュータブルな完全入力状態 |
| `DiagnosticsConfig` | diagnostics trace 設定 |
| `GamepadStatus` | `status()` のスナップショット |
| `SwbtError` | swbt 例外基底 class |
| `AdapterDiscoveryError` | no-open adapter 列挙の失敗 |
| `TransportOpenError` | adapter / transport open 失敗 |
| `ConnectionTimeoutError` | 接続待ちのタイムアウト |
| `ConnectionFailedError` | timeout 以外の接続不成立 |
| `ClosedError` | 接続済みまたは open 済み resource が必要な操作の失敗 |
| `InvalidInputError` | 引数値や入力値の不正 |
| `UnsupportedInputError` | profile が対応しない入力の拒否 |
| `InvalidKeyStoreError` | key store の未対応形式または複数 current peer |

## Adapter Discovery

```python
from swbt import AdapterDiscoveryError, list_adapters

try:
    adapters = list_adapters()
except AdapterDiscoveryError as error:
    print(error.backend, error.platform, error.bumble_version)
else:
    for info in adapters:
        print(info.name, info.aliases)
```

`list_adapters()` は PC に接続されている利用可能な専用 USB Bluetooth ドングル候補を返します。接続可能なデバイスの名称(`AdaptroInfo.name`)を取得するのに用います。

戻り値は `tuple[AdapterInfo, ...]` です。候補が 0 件の場合は空 tuple を返します。libusb の読み込みやUSB コンテキストの作成、デバイス列挙の開始に失敗した場合は `AdapterDiscoveryError` が送出されます。

通常、`AdaptroInfo.name`には`usb:N`などの値が入ります。この値はUSB 接続状態で変わり得ることに注意してください。`AdapterInfo.aliases` には `usb:0A12:0001`、`usb:0A12:0001#1`、`usb:0A12:0001/ABC123` などのエイリアス名が入ります。

`list_adapters()` は  libusb 列挙にてUSB descriptor を読みますが、デバイスハンドルを開くことはありません。 同様に、HID 接続待ち受け、ペアリング、レポートループが開始されることもありません。候補が返っても、当該で `ProController(adapter=...)` などの controller が open できることや対象機器と接続できることは保証しません。

## Controller Classes

### Construction

```python
pad = ProController(
    adapter="usb:0",
    key_store_path="switch-bond.json",
    report_period_us=8000,
    controller_colors=ControllerColors(
        body=0x323232,
        buttons=0xFFFFFF,
        left_grip=0x00B2FF,
        right_grip=0xFF3B30,
    ),
    diagnostics=None,
)
```

`ProController`、`JoyConL`、`JoyConR` 生成用の具象クラスです。`SwitchGamepad` は直接生成せず、関数引数や型注釈で共通 interface として使います。

`adapter` は Bumble transport に渡す アダプタの名称です。

`key_store_path` は Bumble transport がペアリングキーを保存する JSON key store のファイルパス です。1 つの仮想コントローラーと 1 つの対象機器の組み合わせごとに分けてください。`None` は永続 bond を持たない一時的なコントローラーを意味します。

`report_period_us` は レポートループの送信周期です。`None` が指定された場合既定周期 (8 ms) を使います。

`controller_colors` は controller body / buttons / left grip / right grip のプロファイルカラーです。`None` は既定の Joy-Con-ish profile `ControllerColors(body=0x323232, buttons=0xFFFFFF, left_grip=0x00B2FF, right_grip=0xFF3B30)` を使います。各 field は独立した既定値を持ちます。

### Resource Scope

```python
async with ProController(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` の resource scope です。`__aenter__()` は HID 接続待ち受け、ペアリング、(ペアリング情報を用いた)再接続を開始しません。

`open()` は transport、下位レイヤーのコールバック、ロギング、レポートループを準備します。 HID 接続待ち受けは開始しません。transport open に失敗した場合は `TransportOpenError` または 下位レイヤーの例外を返します。

`close(neutral=True)` は接続中ならニュートラル入力を試み、レポートループを停止し、接続先に対する切断要求を試み、最終的に transport を閉じます。複数回呼んでも未完了の後処理のみを実行します。

### Connection

| method | contract |
|---|---|
| `pair(timeout=None)` | 初回ペアリング用API。HID 接続待ち受けを開始し、ホストからの接続を待つ。 |
| `reconnect(timeout=None)` | 保存済み接続情報が 1 件ある場合だけペアリング情報を用いた再接続を試みる。 |
| `try_reconnect(timeout=None)` | 再接続を試みた結果を `ConnectionResult` として返す。 |
| `connect(timeout=None, allow_pairing=False)` | 保存済み接続情報があれば reconnect を優先し、ない場合は `allow_pairing=True` のときだけペアリングを試みる。 |
| `try_connect(timeout=None, allow_pairing=False)` | `connect()` と同じ戦略で接続を試み、接続結果を `ConnectionResult` として返す。 |

`connect()` / `reconnect()` は成功した場合だけ値が返却されます。接続できない場合は `ConnectionFailedError`、タイムアウト時は `ConnectionTimeoutError` が送出されます。 現在の接続先が複数ある `key_store_path` が渡されていた場合、`InvalidKeyStoreError` が送出されます。

`ConnectionResult` は `route`、`status`、`peer_address`、`peer_count` を持ちます。`status` は `"connected"`(接続済み)、`"no_bond"`(接続先無し)、`"timeout"`(タイムアウト)、`"failed"`(接続失敗) のいずれかです。

### Input

入力 API は state update API、action API、complete state API に分類されます。

| method | 種別 | contract |
|---|---|---|
| `press(*buttons)` | state update API | 現在のボタン入力状態に指定されたボタンを追加する。即時送信を保証しない。 |
| `release(*buttons)` | state update API | 現在のボタン入力状態から指定されたボタンを取り除く。即時送信を保証しない。 |
| `sticks(left=None, right=None)` | state update API | 指定されたスティック入力だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `lstick(stick)` | state update API | 左スティック入力だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `rstick(stick)` | state update API | 右スティック入力だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `imu(*frames)` | state update API | IMU(6軸センサー入力)を置き換える。1入力単位分が与えられた場合は3入力単位分に複製し、3入力単位分が与えられた場合は順に設定する。即時送信を保証しない。 |
| `neutral()` | state update API | `InputState.neutral()` 相当に戻す。即時送信を保証しない。 |
| `apply(state)` | complete state | 構築済みの `InputState` で現在入力全体を置き換える。 |
| `tap(*buttons, duration=0.08)` | action API | 押下レポートを即時送信後、 `duration` 秒待機して押上レポートを送信する。 |

`tap()` 内で呼び出される `release` は、この呼び出しで渡したボタンだけを解除します。事前に `press()` していた他のボタンは維持されます。

`lstick(stick)` は `sticks(left=stick)`、`rstick(stick)` は `sticks(right=stick)` と同じ state update API です。左右を同じ状態更新で置き換える場合は `sticks(left=..., right=...)` を使います。

`imu(*frames)` は現在入力の IMU 部分だけを置き換える state update API です。`imu(frame)` は 3 frame すべてへ同じ値を設定し、`imu(frame1, frame2, frame3)` は順に設定します。0 個、2 個、4 個以上、`IMUFrame` 以外が与えられた場合は `InvalidInputError` が送出されます。

`press()` の直後に `lstick()`、`rstick()`、`sticks()`、`imu()` を呼んでも、同一 HID report に入る保証はありません。button、stick、IMU を完全な同時入力として扱う場合は 構築済みの `InputState` を作り、`apply(state)` に渡してください。

```python
state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.up(),
).with_imu(
    IMUFrame.gyro(100, 0, 0),
)
await pad.apply(state)
```

## Input Model

`Button` は `A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`LEFT_STICK`、`RIGHT_STICK`、`SL`、`SR`、`DPAD_UP`、`DPAD_DOWN`、`DPAD_LEFT`、`DPAD_RIGHT` を持ちます。profile が対応しない button は state update API で `UnsupportedInputError` になります。

`Stick.center()` はスティックの中央位置を返します。`Stick.raw(x=..., y=...)` は `0..4095` の生の値を受けます。`Stick.normalized(x=..., y=...)` は `-1.0..1.0` を生の値へ変換します。

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ正規化座標を使う短い生成 API です。`Stick.tilt(1.0, 1.0)` は矩形座標モデルとみなしたときの正当な入力として受理されます。
`Stick.up(amount=1.0)`、`Stick.down(amount=1.0)`、`Stick.left(amount=1.0)`、`Stick.right(amount=1.0)` は各方向の倒し込み量を `0.0..1.0` で受けとります。`amount=0.0` は無入力、`amount=1.0` はスティックが完全に倒れた状態を表します。

`IMUFrame.neutral()` は移動なしの IMU 入力単位 (IMU frame)を返します。`IMUFrame.raw(accel=None, gyro=None)` は accelerometer(加速度) / gyroscope(ジャイロ) の 3軸 生値　を扱う tuple から入力単位を作ります。未指定側は `(0, 0, 0)` として扱います。`IMUFrame.accel(x=0, y=0, z=0)` は accel だけ、`IMUFrame.gyro(x=0, y=0, z=0)` は gyro だけを指定します。

メソッドチェーンによって `IMUFrame` を構築することも可能です。 `IMUFrame.with_gyro(x=0, y=0, z=0)` は既存 accel を維持して gyro を置き換え、`IMUFrame.with_accel(x=0, y=0, z=0)` は既存 gyro を維持して accel を置き換えます。

`InputState.neutral()` は ボタン入力なし、左右スティックが中央、ニュートラルのIMU frame の状態を返します。`InputState.with_buttons(...)`、`InputState.with_sticks(...)`、`InputState.with_imu(...)`、`InputState.with_gyro(...)`、`InputState.with_accel(...)` は新しい immutable state を返します。`with_imu(frame)` は 1 frame を 3 frame に複製し、`with_imu(frame1, frame2, frame3)` は順に設定します。`with_gyro((x, y, z))` と `with_accel((x, y, z))` も 1 sample を 3 frame に複製し、3 sample では順に片側の sensor だけを置き換えます。

`ControllerColors(body=..., buttons=..., left_grip=..., right_grip=...)` は 24-bit RGB だけを受けます。`body=0x112233`、`buttons=0x445566`、`left_grip=0x778899`、`right_grip=0xAABBCC` は SPI 上で `11 22 33 44 55 66 77 88 99 aa bb cc` になります。範囲外値、文字列、bytes、tuple は `InvalidInputError` です。

### Observation

`snapshot()` は現在の `InputState` を返します。`status()` は `GamepadStatus` を返します。

`GamepadStatus` は `connection_state`、`report_counters`、`last_subcommand_id`、`raw_rumble`、`last_error` を持ちます。

## JoyConL / JoyConR

`JoyConL` と `JoyConR` は単体 Joy-Con L/R 相当の concrete controller です。`side` 引数はありません。接続、入力、diagnostics、`close()` の契約は `SwitchGamepad` interface と同じです。

```python
from swbt import Button, JoyConL, JoyConR, Stick

left = JoyConL(
    adapter="usb:0",
    key_store_path="switch-left-joycon-bond.json",
)
right = JoyConR(
    adapter="usb:0",
    key_store_path="switch-right-joycon-bond.json",
)
```

`JoyConL` は `L`、`ZL`、`MINUS`、`CAPTURE`、`LEFT_STICK`(ボタン)、`SL`、`SR`、十字キー、左スティック入力を扱います。 `JoyConR` は `A`、`B`、`X`、`Y`、`R`、`ZR`、`PLUS`、`HOME`、`RIGHT_STICK`(ボタン)、`SL`、`SR`、右スティック入力を扱います。


```python
async with JoyConL(
    adapter="usb:0",
    key_store_path="switch-left-joycon-bond.json",
) as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.SR, Button.SL)
    await left.lstick(Stick.left())
    await left.tap(Button.L)
    await left.rstick(Stick.right())  # UnsupportedInputError
```

`apply(state)` でも同じ制約を検査します。 `JoyConL` に 右スティック入力や `A`, `B`, `X`, `Y` 入力を含む `InputState`、 `JoyConR` に左スティック入力や十字キー入力を含む `InputState` を渡すと `UnsupportedInputError` が送出されます

Pro Controller、Joy-Con L、Joy-Con R は HID identity と pairing key の対応を分けるため、別々の `key_store_path` を使ってください。
Change Grip/Order 画面で単体 Joy-Con として順番登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送る必要があります。

OS / dongle / firmware をまたぐ互換性は未検証です。

## Errors And Diagnostics

例外は `SwbtError` を基底例外とします。アダプタ列挙の失敗は `AdapterDiscoveryError`、利用者入力の不正は `InvalidInputError`、コントローラーが対応しない入力は `UnsupportedInputError`、transport open 失敗は `TransportOpenError`、接続タイムアウトは `ConnectionTimeoutError`、接続不成立は `ConnectionFailedError`、key store 形式不一致は `InvalidKeyStoreError` が送出されます。
