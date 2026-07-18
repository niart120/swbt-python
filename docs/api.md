# Public API

`swbt-python` の公開 API は `swbt` module root から import します。

```python
from swbt import (
    AdapterInfo,
    Button,
    ControllerColors,
    DirectJoyConL,
    DirectJoyConR,
    DirectProController,
    DirectSwitchGamepad,
    IMUFrame,
    InputState,
    JoyConL,
    JoyConR,
    PeriodicSwitchGamepad,
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
| `SwitchGamepad` | lifecycle、接続、意味的入力操作を共有する抽象 interface |
| `PeriodicSwitchGamepad` | ライブラリが入力レポートの送信周期を管理する抽象 interface |
| `DirectSwitchGamepad` | 利用者が入力レポートの送信頻度を管理する抽象 interface |
| `ProController` | Pro Controller 相当の Periodic 具象クラス |
| `JoyConL` | 単体 Joy-Con L 相当の Periodic 具象クラス |
| `JoyConR` | 単体 Joy-Con R 相当の Periodic 具象クラス |
| `DirectProController` | Pro Controller 相当の Direct 具象クラス |
| `DirectJoyConL` | 単体 Joy-Con L 相当の Direct 具象クラス |
| `DirectJoyConR` | 単体 Joy-Con R 相当の Direct 具象クラス |
| `ControllerColors` | controller body / buttons / left grip / right grip の固定 profile 色 |
| `ConnectionResult` | `try_connect()` / `try_reconnect()` の結果 |
| `Button` | 対応する各種ボタン |
| `Stick` | スティック入力 |
| `IMUFrame` | IMU frame |
| `InputState` | イミュータブルな完全入力状態 |
| `DiagnosticsConfig` | トレース出力設定 |
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

`list_adapters()` は  libusb 列挙にてUSB descriptor を読みますが、デバイスハンドルを開くことはありません。 同様に、HID 接続待ち受け、ペアリング、レポートループが開始されることもありません。候補が返っても、当該で `ProController(adapter=...)` などのコントローラーが open できることや対象機器と接続できることは保証しません。

## Controller Classes

### Reporting Types

`SwitchGamepad` は lifecycle、接続、状態参照、意味的入力操作を共有する抽象型です。送信契約を型注釈で区別する場合は `PeriodicSwitchGamepad` または `DirectSwitchGamepad` を使います。

Periodic の正常終了は local state の確定を表します。`ProController`、`JoyConL`、`JoyConR` はレポートループを持ち、状態更新後の入力レポートを周期送信します。完全な状態は `apply(state)` で確定します。状態更新 API は接続を要求せず、即時送信を保証しない契約です。

Direct の正常終了は入力レポート1件の送信完了と state の確定を表します。`DirectProController`、`DirectJoyConL`、`DirectJoyConR` はレポートループを持ちません。完全な状態は `send(state)` で送信します。意味的入力操作も、最後に正常送信した状態から候補を作り、送信に成功した場合だけ確定します。未接続、profile 検査、transport 送信で失敗した場合、`snapshot()` は直前の正常送信状態を維持します。

Direct でも subcommand reply は自動送信されます。入力レポートと reply は同じ送信直列化境界と timer を使うため、利用者が host output report を処理する必要はありません。

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

direct_pad = DirectProController(
    adapter="usb:0",
    key_store_path="switch-direct-bond.json",
    controller_colors=None,
    diagnostics=None,
)
```

`ProController`、`JoyConL`、`JoyConR` 生成用の具象クラスです。対応する Direct 具象クラスは `DirectProController`、`DirectJoyConL`、`DirectJoyConR` です。`SwitchGamepad` は直接生成しません。

`adapter` は Bumble transport に渡す アダプタの名称です。

`key_store_path` は Bumble transport がペアリングキーを保存する JSON key store のファイルパス です。1 つの仮想コントローラーと 1 つの対象機器の組み合わせごとに分けてください。`None` を指定した場合はペアリング情報を永続化しない一時的なコントローラーとして扱われます。

`report_period_us` は Periodic 具象クラスのレポートループ送信周期です。`None` が指定された場合既定周期 (8 ms) を使います。Direct は `report_period_us` を受け取りません。Direct では入力レポートの送信頻度を利用者が管理します。

`controller_colors` は controller body / buttons / left grip / right grip のプロファイルカラーです。`None` は既定の Joy-Con-ish profile `ControllerColors(body=0x323232, buttons=0xFFFFFF, left_grip=0x00B2FF, right_grip=0xFF3B30)` を使います。それぞれの値は独立した既定値を持ちます。

`diagnostics` はトレース出力設定です。`DiagnosticsConfig(trace_writer=...)` を渡すと、接続、送信レポート、subcommand、エラー、実行時のメタデータを指定したトレースログ出力先へ JSON 形式で出力します。`None` を指定した場合はトレースログを出力しません。

### Resource Scope

```python
async with ProController(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` の resource scope です。`__aenter__()` は HID 接続待ち受け、ペアリング、(ペアリング情報を用いた)再接続を開始しません。

`open()` は transport、下位レイヤーのコールバック、トレース出力、送信処理を準備します。Periodic ではレポートループも準備し、Direct では周期 task を作りません。HID 接続待ち受けは開始しません。transport open に失敗した場合は `TransportOpenError` または下位レイヤーの例外を返します。

`close(neutral=True)` は接続中ならニュートラル入力を試み、Periodic のレポートループを停止し、接続先に対する切断要求を試み、最終的に transport を閉じます。Direct の `close(neutral=True)` は例外としてニュートラル入力を1件送信し、成功後に state を確定します。`close(neutral=False)` は終了処理用の入力レポートを追加しません。

### Connection

| method | contract |
|---|---|
| `pair(timeout=None)` | 初回ペアリング用API。HID 接続待ち受けを開始し、ホストからの接続を待つ。 |
| `reconnect(timeout=None)` | 保存済みペアリング情報が 1 件ある場合だけ、そのペアリング情報を用いた再接続を試みる。 |
| `try_reconnect(timeout=None)` | 再接続を試みた結果を `ConnectionResult` として返す。 |
| `connect(timeout=None, allow_pairing=False)` | 保存済みペアリング情報があれば reconnect を優先し、ない場合は `allow_pairing=True` のときだけペアリングを試みる。 |
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
| `imu(*frames)` | state update API | 6軸センサー入力を置き換える。1入力分を渡すと3入力分に複製し、3入力分を渡すと順に設定する。即時送信を保証しない。 |
| `neutral()` | state update API | `InputState.neutral()` 相当に戻す。即時送信を保証しない。 |
| `apply(state)` | complete state | 構築済みの `InputState` で現在入力全体を置き換える。 |
| `send(state)` | complete state | Direct で構築済みの `InputState` を1件送信し、成功後に現在入力全体を置き換える。 |
| `tap(*buttons, duration=0.08)` | action API | 押下レポートを即時送信後、 `duration` 秒待機して押上レポートを送信する。 |

表中の「即時送信を保証しない」は Periodic の状態更新 API に対する契約です。Direct では `press()`、`release()`、`sticks()`、`lstick()`、`rstick()`、`imu()`、`neutral()` が各正常終了につき入力レポートを1件送信します。Direct の `send(state)` と意味的入力操作は接続済みであることを要求し、送信失敗時は state を確定しません。

`tap()` 内で呼び出される `release` は、この呼び出しで渡したボタンだけを解除します。事前に `press()` していた他のボタンは維持されます。

`lstick(stick)` は `sticks(left=stick)`、`rstick(stick)` は `sticks(right=stick)` と同じ state update API です。左右を同じ状態更新で置き換える場合は `sticks(left=..., right=...)` を使います。

`imu(*frames)` は現在の6軸センサー入力だけを置き換えます。`imu(frame)` は同じ値を3入力分に設定し、`imu(frame1, frame2, frame3)` は3つの値を順に設定します。引数の数が1個または3個でない場合や、`IMUFrame` 以外を渡した場合は `InvalidInputError` が送出されます。

Periodic で `press()` の直後に `lstick()`、`rstick()`、`sticks()`、`imu()` を呼んでも、同一 HID report に入る保証はありません。button、stick、IMU を完全な同時入力として扱う場合は構築済みの `InputState` を作り、Periodic では `apply(state)`、Direct では `send(state)` に渡してください。

```python
state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.up(),
).with_imu(
    IMUFrame.gyro(100, 0, 0),
)
await pad.apply(state)
```

Direct では同じ状態を `await pad.send(state)` で1件送信します。Direct の `tap()` は押下と解放の2件を送り、押下から解放まで他の入力操作を割り込ませません。解放送信が失敗した場合、`snapshot()` は最後に正常送信した押下状態を返します。

## Input Model

`Button` は `A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`LEFT_STICK`、`RIGHT_STICK`、`SL`、`SR`、`DPAD_UP`、`DPAD_DOWN`、`DPAD_LEFT`、`DPAD_RIGHT` を持ちます。profile が対応しない button は state update API で `UnsupportedInputError` になります。

`Stick.center()` はスティックの中央位置を返します。`Stick.raw(x=..., y=...)` は `0..4095` の生の値を受けます。`Stick.normalized(x=..., y=...)` は `-1.0..1.0` を生の値へ変換します。

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ正規化座標を使う短い生成 API です。`Stick.tilt(1.0, 1.0)` は矩形座標モデルとみなしたときの正当な入力として受理されます。
`Stick.up(amount=1.0)`、`Stick.down(amount=1.0)`、`Stick.left(amount=1.0)`、`Stick.right(amount=1.0)` は各方向の倒し込み量を `0.0..1.0` で受けとります。`amount=0.0` は無入力、`amount=1.0` はスティックが完全に倒れた状態を表します。

`IMUFrame` は、加速度とジャイロをまとめた1入力分の値です。`IMUFrame.neutral()` は動きのない値を返します。`IMUFrame.raw(accel=None, gyro=None)` は加速度とジャイロの3軸の生値から作成し、未指定側を `(0, 0, 0)` として扱います。加速度だけを指定する場合は `IMUFrame.accel(x=0, y=0, z=0)`、ジャイロだけを指定する場合は `IMUFrame.gyro(x=0, y=0, z=0)` を使います。

加速度を G 単位で指定する場合は `IMUFrame.accel_g(x_g=0.0, y_g=0.0, z_g=0.0)` を使います。`IMUFrame.to_accel_g()` は設定値を G 単位の `(x, y, z)` として返します。変換尺度は `1/4096 G/raw` です。

角速度を rad/s 単位で指定する場合は `IMUFrame.gyro_rate(x_rad_s=0.0, y_rad_s=0.0, z_rad_s=0.0)` を使います。`IMUFrame.to_gyro_rate()` は設定値を rad/s 単位の `(x, y, z)` として返します。変換尺度は `0.070 dps/raw` です。

生値への変換結果が16ビット符号付き整数の範囲を超える場合は、上限値や下限値への丸めを行わず `InvalidInputError` が送出されます。Switchとの通信に使う形式は接続先の要求に応じて自動で選ばれるため、利用者が指定する必要はありません。

既存の `IMUFrame` の一部だけを変更することもできます。`IMUFrame.with_gyro(x=0, y=0, z=0)` と `IMUFrame.with_gyro_rate(x_rad_s=0.0, y_rad_s=0.0, z_rad_s=0.0)` は加速度を維持してジャイロを置き換えます。`IMUFrame.with_accel(x=0, y=0, z=0)` と `IMUFrame.with_accel_g(x_g=0.0, y_g=0.0, z_g=0.0)` はジャイロを維持して加速度を置き換えます。

`InputState.neutral()` は ボタン入力なし、左右スティックが中央、ニュートラルのIMU frame の状態を返します。`InputState.with_buttons(...)`、`InputState.with_sticks(...)`、`InputState.with_imu(...)`、`InputState.with_gyro(...)`、`InputState.with_accel(...)` は新しい immutable state を返します。`with_imu(frame)` は 1 frame を 3 frame に複製し、`with_imu(frame1, frame2, frame3)` は順に設定します。`with_gyro((x, y, z))` と `with_accel((x, y, z))` も 1 sample を 3 frame に複製し、3 sample では順に片側の sensor だけを置き換えます。

`ControllerColors(body=..., buttons=..., left_grip=..., right_grip=...)` は 24-bit RGB だけを受けます。`body=0x112233`、`buttons=0x445566`、`left_grip=0x778899`、`right_grip=0xAABBCC` は SPI 上で `11 22 33 44 55 66 77 88 99 aa bb cc` になります。範囲外値、文字列、bytes、tuple は `InvalidInputError` です。

### Observation

`snapshot()` は現在の `InputState` を返します。Periodic の `snapshot()` は最新の local state、Direct の `snapshot()` は最後に正常送信した入力状態を返します。`status()` は `GamepadStatus` を返します。

`GamepadStatus` は `connection_state`、`report_counters`、`last_subcommand_id`、`raw_rumble`、`last_error` を持ちます。

## JoyConL / JoyConR

`JoyConL` と `JoyConR` は単体 Joy-Con L/R 相当の concrete controller です。Direct の単体型には `DirectJoyConL` と `DirectJoyConR` を使います。`side` 引数はありません。profile ごとの対応入力は reporting type に関係なく同じです。

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

`apply(state)` と `send(state)` でも同じ制約を検査します。`JoyConL` または `DirectJoyConL` に右スティック入力や `A`, `B`, `X`, `Y` 入力を含む `InputState`、`JoyConR` または `DirectJoyConR` に左スティック入力や十字キー入力を含む `InputState` を渡すと `UnsupportedInputError` が送出されます。

Pro Controller、Joy-Con L、Joy-Con R は HID identity と pairing key の対応を分けるため、別々の `key_store_path` を使ってください。
Change Grip/Order 画面で単体 Joy-Con として順番登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送る必要があります。

OS / dongle / firmware をまたぐ互換性は未検証です。

## Errors And Diagnostics

例外は `SwbtError` を基底例外とします。アダプタ列挙の失敗は `AdapterDiscoveryError`、利用者入力の不正は `InvalidInputError`、コントローラーが対応しない入力は `UnsupportedInputError`、transport open 失敗は `TransportOpenError`、接続タイムアウトは `ConnectionTimeoutError`、接続不成立は `ConnectionFailedError`、key store 形式不一致は `InvalidKeyStoreError` が送出されます。

`DiagnosticsConfig` はトレース出力のための設定です。`trace_writer` にテキストストリームを渡すと、接続状態の遷移、送信したレポート、受信した subcommand、エラー、`adapter` や `key_store_path` などの実行時メタデータを 1 行 1 件の JSON object として出力します。このトレースログは、実機接続時の挙動確認や失敗時の切り分けに使います。`DiagnosticsConfig` 自体は原因を自動判定する機能ではありません。
