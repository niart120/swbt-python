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

`swbt.gamepad.*` や `swbt.transport.*` の deep import は、テストと移行作業に限定します。Bumble 型や transport protocol を public API に露出しません。

## Top-Level Exports

`swbt.__all__` の公開名は次の通りです。

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

`list_adapters()` は PC に接続された専用 USB Bluetooth dongle 候補を返します。Nintendo Switch 本体や周辺 Bluetooth host は列挙しません。

戻り値は `tuple[AdapterInfo, ...]` です。候補が 0 件の場合は空 tuple を返します。libusb の読み込み、USB context 作成、device iteration の開始に失敗した場合は `AdapterDiscoveryError` を投げます。候補 0 件と列挙不能は別の状態です。

`AdapterInfo.name` は `ProController(adapter=info.name)` など concrete controller の `adapter` に渡す adapter moniker です。`AdapterInfo.aliases` には `usb:0A12:0001`、`usb:0A12:0001#1`、`usb:0A12:0001/ABC123` のような別指定を入れます。`usb:N` は USB 接続状態で変わり得ます。`serial_number` が取れる場合は serial alias を永続的な指定として使います。

`list_adapters()` は USB descriptor を読むために libusb enumeration を行いますが、Bumble transport として device handle を開きません。adapter open、Bluetooth controller power on、HID advertising、pairing、periodic report loop は開始しません。候補が返っても、その adapter で `ProController(adapter=...)` などの controller が open できることや対象機器と接続できることは保証しません。

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

`ProController`、`JoyConL`、`JoyConR` が生成用の concrete controller です。`SwitchGamepad` は直接生成せず、関数引数や型注釈で共通 interface として使います。

`adapter` は default Bumble transport に渡す adapter 名称です。public controller では必須です。

`key_store_path` は default Bumble transport が pairing key を保存する JSON key store path です。1 つの仮想コントローラーと 1 つの対象機器の組み合わせごとに分けてください。`None` は永続 bond を持たない一時的なコントローラーを意味します。

`report_period_us` は periodic input report の送信周期です。`None` は controller profile の既定周期を使います。HID Device として出す表示名は concrete controller class が内部 profile から選びます。

`controller_colors` は controller body / buttons / left grip / right grip の固定 profile 色です。`None` は既定の Joy-Con-ish profile `ControllerColors(body=0x323232, buttons=0xFFFFFF, left_grip=0x00B2FF, right_grip=0xFF3B30)` を使います。各 field は独立した既定値を持ちます。この値は作成時に固定し、`set_color()` や `controller_colors=` setter は提供しません。Switch からの SPI read に対して `0x6050` から body、buttons、left grip、right grip を各 3 bytes の順で返します。

### Resource Scope

```python
async with ProController(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` の resource scope です。`__aenter__()` は advertising、pairing、reconnect を開始しません。

`open()` は transport、callback、diagnostics、report loop を準備します。HID advertising は開始しません。transport open に失敗した場合は `TransportOpenError` または lower layer の例外を返します。

`close(neutral=True)` は接続中なら trailing neutral を試み、report loop を止め、remote disconnect request を試し、transport を閉じます。複数回呼んでも未完了の後始末だけを処理します。

### Connection

| method | contract |
|---|---|
| `pair(timeout=None)` | 初回 pairing 用。HID advertising を開始し、host 接続を待つ。 |
| `reconnect(timeout=None)` | 保存済み bond が 1 件ある場合だけ active reconnect を試す。pairing fallback はしない。 |
| `try_reconnect(timeout=None)` | reconnect 結果を `ConnectionResult` として返す。 |
| `connect(timeout=None, allow_pairing=False)` | bond があれば reconnect を優先し、bond がない場合は `allow_pairing=True` のときだけ pairing へ進む。 |
| `try_connect(timeout=None, allow_pairing=False)` | `connect()` と同じ戦略を使い、結果を `ConnectionResult` として返す。 |

`connect()` / `reconnect()` は成功した場合だけ戻ります。接続できない場合は `ConnectionFailedError`、timeout は `ConnectionTimeoutError` です。current peer が複数ある key store は推測せず、`InvalidKeyStoreError` とします。

`ConnectionResult` は `route`、`status`、`peer_address`、`peer_count` を持ちます。`status` は `"connected"`、`"no_bond"`、`"timeout"`、`"failed"` のいずれかです。

### Input

入力 API は state update API、action API、complete state API に分類されます。

| method | 種別 | contract |
|---|---|---|
| `press(*buttons)` | state update API | 現在の button set に button を追加する。即時送信を保証しない。 |
| `release(*buttons)` | state update API | 現在の button set から button を取り除く。即時送信を保証しない。 |
| `sticks(left=None, right=None)` | state update API | 指定された stick だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `lstick(stick)` | state update API | left stick だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `rstick(stick)` | state update API | right stick だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `imu(*frames)` | state update API | IMU 3 frame を置き換える。1 frame は 3 frame に複製し、3 frame は順に設定する。即時送信を保証しない。 |
| `neutral()` | state update API | `InputState.neutral()` 相当に戻す。即時送信を保証しない。 |
| `apply(state)` | complete state | 完成済み `InputState` で現在入力全体を置き換える。差分適用ではない。 |
| `tap(*buttons, duration=0.08)` | action API | 接続済みを要求し、押下 report と release report を即時送信する。 |

`tap()` の release は、この呼び出しで渡した button だけを解除します。事前に `press()` していた別 button は維持します。

`lstick(stick)` は `sticks(left=stick)`、`rstick(stick)` は `sticks(right=stick)` と同じ state update API です。左右を同じ状態更新で置き換える場合は `sticks(left=..., right=...)` を使います。

`imu(*frames)` は現在入力の IMU 部分だけを置き換える state update API です。`imu(frame)` は 3 frame すべてへ同じ値を設定し、`imu(frame1, frame2, frame3)` は順に設定します。0 個、2 個、4 個以上、`IMUFrame` 以外は `InvalidInputError` です。

`press()` の直後に `lstick()`、`rstick()`、`sticks()`、`imu()` を呼んでも、同一 HID report に入る保証はありません。button、stick、IMU を完全な同時入力として扱う場合は complete state を作り、`apply(state)` に渡してください。

```python
state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.up(),
).with_imu(
    IMUFrame.gyro(100, 0, 0),
)
await pad.apply(state)
```

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

左 Joy-Con は `Button.L`、`Button.ZL`、`Button.MINUS`、`Button.CAPTURE`、D-pad、`Button.LEFT_STICK`、`Button.SL`、`Button.SR`、left stick を扱います。右 Joy-Con は `Button.A`、`Button.B`、`Button.X`、`Button.Y`、`Button.R`、`Button.ZR`、`Button.PLUS`、`Button.HOME`、`Button.RIGHT_STICK`、`Button.SL`、`Button.SR`、right stick を扱います。

片側 profile が持たない入力は `UnsupportedInputError` です。

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

`apply(state)` でも同じ制約を検査します。左 Joy-Con に right stick を含む `InputState`、右 Joy-Con に left stick や D-pad を含む `InputState` を渡すと `UnsupportedInputError` です。

Pro Controller、Joy-Con L、Joy-Con R は HID identity と pairing key の対応を分けるため、別々の `key_store_path` を使ってください。同じ対象機器でも profile を変える場合は key store を共有しません。

Change Grip/Order 画面で単体 Joy-Con として順番登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送ります。

左右ペアの `JoyConPair` は public API にありません。単体 L/R だけを作れます。

2026-07-06 の Joy-Con L 実機観測では、HID 通信上の device name と device-info reply が Joy-Con L になり、SDP policy 反映後に Switch UI で Joy-Con として登録されたことをユーザ目視で確認しました。Joy-Con R、reconnect、Joy-Con profile の通常入力反映、SDP 完全一致、OS / dongle / firmware をまたぐ互換性は未検証です。

## Input Model

`Button` は `A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`LEFT_STICK`、`RIGHT_STICK`、`SL`、`SR`、`DPAD_UP`、`DPAD_DOWN`、`DPAD_LEFT`、`DPAD_RIGHT` を持ちます。profile が対応しない button は state update API で `UnsupportedInputError` になります。

`Stick.center()` はスティックの中央位置を返します。`Stick.raw(x=..., y=...)` は `0..4095` の生の値を受けます。`Stick.normalized(x=..., y=...)` は `-1.0..1.0` を生の値へ変換します。

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ正規化座標を使う短い生成 API です。`Stick.up(amount=1.0)`、`Stick.down(amount=1.0)`、`Stick.left(amount=1.0)`、`Stick.right(amount=1.0)` は単一方向の倒し込み量を `0.0..1.0` で受けます。`amount=0.0` は中央、`amount=1.0` は全倒しです。`Stick.tilt(1.0, 1.0)` は x/y を個別に検証する既存の矩形座標モデルとして許可します。

`IMUFrame.neutral()` は移動なしの IMU frame を返します。`IMUFrame.raw(accel=None, gyro=None)` は accelerometer / gyroscope の raw 3 軸 tuple から frame を作ります。未指定側はゼロです。`IMUFrame.gyro(x=0, y=0, z=0)` は gyro だけ、`IMUFrame.accel(x=0, y=0, z=0)` は accel だけを指定します。`IMUFrame.with_gyro(x=0, y=0, z=0)` は既存 accel を維持して gyro を置き換え、`IMUFrame.with_accel(x=0, y=0, z=0)` は既存 gyro を維持して accel を置き換えます。

`InputState.neutral()` は button なし、左右 stick 中央、neutral IMU frame の状態を返します。`InputState.with_buttons(...)`、`InputState.with_sticks(...)`、`InputState.with_imu(...)`、`InputState.with_gyro(...)`、`InputState.with_accel(...)` は新しい immutable state を返します。`with_imu(frame)` は 1 frame を 3 frame に複製し、`with_imu(frame1, frame2, frame3)` は順に設定します。`with_gyro((x, y, z))` と `with_accel((x, y, z))` も 1 sample を 3 frame に複製し、3 sample では順に片側の sensor だけを置き換えます。

`ControllerColors(body=..., buttons=..., left_grip=..., right_grip=...)` は 24-bit RGB integer だけを受けます。`body=0x112233`、`buttons=0x445566`、`left_grip=0x778899`、`right_grip=0xAABBCC` は SPI 上で `11 22 33 44 55 66 77 88 99 aa bb cc` になります。範囲外値、文字列、bytes、tuple は `InvalidInputError` です。

## Errors And Diagnostics

例外は `SwbtError` を基底にします。no-open adapter 列挙の失敗は `AdapterDiscoveryError`、利用者入力の不正は `InvalidInputError`、profile が対応しない入力は `UnsupportedInputError`、transport open 失敗は `TransportOpenError`、接続 timeout は `ConnectionTimeoutError`、接続不成立は `ConnectionFailedError`、key store 形式不一致は `InvalidKeyStoreError` です。

`DiagnosticsConfig(trace_writer=...)` を渡すと JSON Lines trace を記録します。raw link key などの secret material は記録しません。

## Transport Boundary

Bluetooth HID transport は runtime の内部境界です。利用者向け API では backend object を渡さず、`adapter`、`key_store_path`、`diagnostics` などの resource 設定だけを concrete controller に渡します。

別 backend の公式 API はまだありません。必要になった場合は、この API reference ではなく別の設計単位で扱います。
