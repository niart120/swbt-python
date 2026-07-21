# 公開 API

`swbt-python` の公開 API は、`swbt` モジュール直下からインポートします。

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

## top-level export

トップレベルの公開 API と主な用途を説明します。

| 名前 | 用途 |
|---|---|
| `list_adapters` | `adapter=...` に指定できる専用 USB Bluetooth ドングル候補の列挙 |
| `AdapterInfo` | ドングルを開かずに取得したアダプタ候補の情報 |
| `SwitchGamepad` | 生成から終了までの管理、接続、意味的な入力操作を共有する抽象型 |
| `PeriodicSwitchGamepad` | 入力レポートの送信周期をライブラリが管理する抽象型 |
| `DirectSwitchGamepad` | 入力レポートの送信頻度を利用者が管理する抽象型 |
| `ProController` | Pro Controller 相当の周期送信型の具象クラス |
| `JoyConL` | Joy-Con L 相当の周期送信型の具象クラス |
| `JoyConR` | Joy-Con R 相当の周期送信型の具象クラス |
| `DirectProController` | Pro Controller 相当の直接送信型の具象クラス |
| `DirectJoyConL` | Joy-Con L 相当の直接送信型の具象クラス |
| `DirectJoyConR` | Joy-Con R 相当の直接送信型の具象クラス |
| `ControllerColors` | `body` / `buttons` / `left_grip` / `right_grip` に対応する固定プロファイル色 |
| `ConnectionResult` | `try_connect()` / `try_reconnect()` の結果 |
| `Button` | 対応する各種ボタン |
| `Stick` | スティック入力 |
| `IMUFrame` | IMU 入力単位 |
| `InputState` | 変更不能な完全入力状態 |
| `DiagnosticsConfig` | トレース出力設定 |
| `GamepadStatus` | `status()` のスナップショット |
| `SwbtError` | `swbt` 例外の基底クラス |
| `AdapterDiscoveryError` | ドングルを開かないアダプタ列挙の失敗 |
| `TransportOpenError` | `adapter` または transport を開く処理の失敗 |
| `ConnectionTimeoutError` | 接続待ちのタイムアウト |
| `ConnectionFailedError` | タイムアウト以外の接続不成立 |
| `ClosedError` | 接続済み、または開かれたリソースを必要とする操作の失敗 |
| `InvalidInputError` | 引数値または入力値の不正 |
| `UnsupportedInputError` | プロファイルが対応しない入力の拒否 |
| `InvalidKeyStoreError` | ペアリング情報の保存形式が未対応、または現在の接続先が複数ある状態 |
| `InvalidProfileError` | swbt プロファイル JSON の形式、バージョン、コントローラー種別、アドレスが不正な状態 |
| `ProfileControllerMismatchError` | swbt プロファイルのコントローラー種別と生成する具象クラスが一致しない状態。`InvalidProfileError` の派生型 |
| `AdapterIdentityRecoveryRequired` | 揮発領域のアドレス書換開始後の状態を確定できず、専用 USB Bluetooth ドングルの抜き差しが必要な状態 |

## アダプタの列挙

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

`list_adapters()` は、PC に接続されている専用 USB Bluetooth ドングルの候補を返します。コントローラーの `adapter` に指定するアダプタ名（`AdapterInfo.name`）を取得できます。

戻り値は `tuple[AdapterInfo, ...]` です。候補が 0 件の場合は空のタプルを返します。libusb の読み込み、USB コンテキストの作成、またはデバイス列挙の開始に失敗した場合は `AdapterDiscoveryError` が送出されます。

通常、`AdapterInfo.name` には `usb:N` などの値が入ります。この値は USB の接続状態によって変わる場合があります。`AdapterInfo.aliases` には、`usb:0A12:0001`、`usb:0A12:0001#1`、`usb:0A12:0001/ABC123` などの別名が入ります。

`list_adapters()` は libusb による列挙で USB ディスクリプターを読みますが、デバイスハンドルは開きません。HID 接続待ち受け、ペアリング、レポートループも開始しません。候補が返っても、そのアダプタで `ProController(adapter=...)` などのコントローラーを開けることや、対象機器と接続できることは保証しません。

## コントローラー

### 生成

```python
pad = ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
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
    profile_path="switch-direct-bond.json",
    controller_colors=None,
    diagnostics=None,
)
```

`ProController`、`JoyConL`、`JoyConR` は周期送信型の具象クラスです。対応する直接送信型の具象クラスは、`DirectProController`、`DirectJoyConL`、`DirectJoyConR` です。`SwitchGamepad` は直接生成しません。

`adapter` は Bumble transport に渡すアダプタ名です。

全 concrete controller の `profile_path` は、利用者が用意したローカル Bluetooth アドレスとペアリングキーを同じ swbt プロファイル JSON に保存するパスです。既存プロファイルを再利用する場合だけコンストラクタに渡します。

全 concrete controller は `profile_path` を受け取ります。1 つの仮想コントローラーと 1 つの対象機器の組み合わせごとに保存先を分けてください。

新しいプロファイルは、各 concrete controller の `create_profile()` で作成します。`local_address` の生成と重複回避は利用者の責任です。例示した `02:12:34:56:78:9A` を共通値として使わず、controller shape と対象機器ごとに別の値を管理してください。この経路は CSR8510 A10 の揮発領域への書換として提供され、永続領域は変更しません。

```python
pad = await ProController.create_profile(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
    local_address="02:12:34:56:78:9A",
    pair_timeout=60.0,
)
try:
    await pad.tap(Button.A)
finally:
    await pad.close()
```

`create_profile()` は既存のパスを上書きしません。アドレスまたはプロファイルが不正ならアダプタを開く前に失敗します。別の controller shape の profile は `ProfileControllerMismatchError` になります。ペアリング失敗後もプロファイルは残るため、作成時と同じ controller shape の `profile_path` から再試行できます。揮発領域への書換開始後の状態を確定できない場合は `AdapterIdentityRecoveryRequired` が送出されます。この場合は専用 USB Bluetooth ドングルを抜き差ししてから再試行します。

`report_period_us` は、周期送信型の具象クラスが使うレポートループの送信周期です。`None` を指定した場合は、既定周期（8 ms）を使います。直接送信型の具象クラスは `report_period_us` を受け取りません。入力レポートの送信頻度は利用者が管理します。

`controller_colors` は、`body` / `buttons` / `left_grip` / `right_grip` に対応するプロファイル色です。`None` を指定した場合は、Joy-Con 風の既定プロファイル `ControllerColors(body=0x323232, buttons=0xFFFFFF, left_grip=0x00B2FF, right_grip=0xFF3B30)` を使います。各項目には独立した既定値があります。

`ControllerColors(body=..., buttons=..., left_grip=..., right_grip=...)` は、24 ビット RGB だけを受け取ります。範囲外の値、文字列、`bytes`、`tuple` を渡すと `InvalidInputError` が送出されます。

`diagnostics` はトレース出力設定です。`DiagnosticsConfig(trace_writer=...)` を渡すと、接続、送信レポート、サブコマンド、エラー、実行時のメタデータを指定したトレースログ出力先へ JSON 形式で出力します。`None` を指定した場合はトレースログを出力しません。

### リソースのスコープ

```python
async with ProController(adapter="usb:0", profile_path="profiles/switch-pro.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

`async with` は、`open()` から `close(neutral=True)` までのリソースを管理します。`__aenter__()` は、HID 接続待ち受け、ペアリング、ペアリング情報を用いた再接続を開始しません。

`open()` は、transport、下位レイヤーのコールバック、トレース出力、送信処理を準備します。周期送信型ではレポートループも準備し、直接送信型では周期タスクを作りません。HID 接続待ち受けは開始しません。transport を開く処理に失敗した場合は、`TransportOpenError` または下位レイヤーの例外が送出されます。

`close(neutral=True)` は、接続中ならニュートラル入力を試み、周期送信型のレポートループを停止し、接続先に対する切断要求を試み、最後に transport を閉じます。直接送信型でも、`close(neutral=True)` に限ってニュートラル入力を 1 件送信し、成功後に入力状態を確定します。`close(neutral=False)` は、終了処理用の入力レポートを追加しません。

### 接続

| メソッド | 契約 |
|---|---|
| `pair(timeout=None)` | 初回ペアリング用 API。HID 接続待ち受けを開始し、ホストからの接続を待つ。 |
| `reconnect(timeout=None)` | 保存済みペアリング情報が 1 件ある場合だけ、そのペアリング情報を用いた再接続を試みる。 |
| `try_reconnect(timeout=None)` | 再接続を試みた結果を `ConnectionResult` として返す。 |
| `connect(timeout=None, allow_pairing=False)` | 保存済みペアリング情報があれば再接続を優先し、ない場合は `allow_pairing=True` のときだけペアリングを試みる。 |
| `try_connect(timeout=None, allow_pairing=False)` | `connect()` と同じ戦略で接続を試み、接続結果を `ConnectionResult` として返す。 |

`connect()` / `reconnect()` は、成功した場合だけ値を返します。接続できない場合は `ConnectionFailedError`、タイムアウト時は `ConnectionTimeoutError` が送出されます。現在の接続先が複数記録されたプロファイルまたはペアリング情報の保存ファイルを指定した場合は、`InvalidKeyStoreError` が送出されます。

`ConnectionResult` は、`route`、`status`、`peer_address`、`peer_count` を持ちます。`status` は `"connected"`（接続済み）、`"no_bond"`（接続先なし）、`"timeout"`（タイムアウト）、`"failed"`（接続失敗）のいずれかです。

### 状態の取得

`snapshot()` は現在の `InputState` を返します。周期送信型の `snapshot()` はライブラリ内部の最新の入力状態、直接送信型の `snapshot()` は最後に正常送信した入力状態を返します。`status()` は `GamepadStatus` を返します。

`GamepadStatus` は `connection_state`、`report_counters`、`last_subcommand_id`、`raw_rumble`、`last_error` を持ちます。

## 入力

### 共通の入力操作

入力 API は、状態更新 API、操作 API、完全入力状態 API に分類されます。

| メソッド | 種別 | 契約 |
|---|---|---|
| `press(*buttons)` | 状態更新 API | 現在のボタン入力状態に指定されたボタンを追加する。 |
| `release(*buttons)` | 状態更新 API | 現在のボタン入力状態から指定されたボタンを取り除く。 |
| `sticks(left=None, right=None)` | 状態更新 API | 指定されたスティック入力だけを置き換える。`Stick` 以外は `InvalidInputError`。 |
| `lstick(stick)` | 状態更新 API | 左スティック入力だけを置き換える。`Stick` 以外は `InvalidInputError`。 |
| `rstick(stick)` | 状態更新 API | 右スティック入力だけを置き換える。`Stick` 以外は `InvalidInputError`。 |
| `imu(*frames)` | 状態更新 API | 6 軸センサー入力を置き換える。1 入力分を渡すと 3 入力分に複製し、3 入力分を渡すと順に設定する。 |
| `neutral()` | 状態更新 API | `InputState.neutral()` 相当に戻す。 |
| `tap(*buttons, duration=0.08)` | 操作 API | 押下レポートを即時送信し、`duration` 秒待機してから解放レポートを送信する。 |

`tap()` 内で呼び出される `release()` は、この呼び出しで渡したボタンだけを解除します。事前に `press()` していた他のボタンは維持されます。

`lstick(stick)` は `sticks(left=stick)`、`rstick(stick)` は `sticks(right=stick)` と同じ状態更新 API です。左右を同じ状態更新で置き換える場合は、`sticks(left=..., right=...)` を使います。

`imu(*frames)` は、現在の 6 軸センサー入力だけを置き換えます。`imu(frame)` は同じ値を 3 入力分に設定し、`imu(frame1, frame2, frame3)` は 3 つの値を順に設定します。引数の数が 1 個または 3 個でない場合や、`IMUFrame` 以外を渡した場合は `InvalidInputError` が送出されます。

### 周期送信型

周期送信型の操作が正常終了すると、ライブラリ内部の入力状態が確定します。`ProController`、`JoyConL`、`JoyConR` はレポートループを持ち、状態更新後の入力レポートを周期送信します。状態更新 API は接続を必要とせず、即時送信を保証しません。

完全な入力状態は `apply(state)` で確定します。

周期送信型で `press()` の直後に `lstick()`、`rstick()`、`sticks()`、`imu()` を呼んでも、同じ HID 入力レポートに入る保証はありません。

### 直接送信型

直接送信型の操作が正常終了すると、入力レポート 1 件の送信と入力状態の確定が完了します。`DirectProController`、`DirectJoyConL`、`DirectJoyConR` はレポートループを持ちません。完全な入力状態は `send(state)` で送信します。意味的な入力操作も、最後に正常送信した状態から候補を作り、送信に成功した場合だけ確定します。未接続、プロファイル検査、transport 送信で失敗した場合、`snapshot()` は直前に正常送信した状態を維持します。

直接送信型では、`press()`、`release()`、`sticks()`、`lstick()`、`rstick()`、`imu()`、`neutral()` が正常終了するたびに入力レポートを 1 件送信します。直接送信型の `send(state)` と意味的な入力操作は接続済みであることを必要とし、送信に失敗した場合は入力状態を確定しません。

直接送信型でも、サブコマンド応答は自動送信されます。入力レポートとサブコマンド応答は同じ送信直列化処理とタイマーを使うため、利用者がホストからの出力レポートを処理する必要はありません。

直接送信型の `tap()` は押下と解放の 2 件を送り、押下から解放まで他の入力操作を割り込ませません。解放送信に失敗した場合、`snapshot()` は最後に正常送信した押下状態を返します。

### 完全入力状態の送信

ボタン、スティック、IMU を同じ入力レポートに含める必要がある場合は、構築済みの `InputState` を作り、周期送信型では `apply(state)`、直接送信型では `send(state)` に渡してください。

```python
state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.up(),
).with_imu(
    IMUFrame.gyro(100, 0, 0),
)
await pad.apply(state)
```

## 入力モデル

`Button` は、`A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`LEFT_STICK`、`RIGHT_STICK`、`SL`、`SR`、`DPAD_UP`、`DPAD_DOWN`、`DPAD_LEFT`、`DPAD_RIGHT` を持ちます。プロファイルが対応しないボタンを状態更新 API に渡すと、`UnsupportedInputError` が送出されます。

`Stick.center()` はスティックの中央位置を返します。`Stick.raw(x=..., y=...)` は `0..4095` の生の値を受けます。`Stick.normalized(x=..., y=...)` は `-1.0..1.0` を生の値へ変換します。

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ正規化座標を使う短い生成 API です。`Stick.tilt(1.0, 1.0)` は矩形座標モデルとみなしたときの正当な入力として受理されます。
`Stick.up(amount=1.0)`、`Stick.down(amount=1.0)`、`Stick.left(amount=1.0)`、`Stick.right(amount=1.0)` は各方向の倒し込み量を `0.0..1.0` で受け取ります。`amount=0.0` は無入力、`amount=1.0` はスティックが完全に倒れた状態を表します。

`IMUFrame` は、加速度とジャイロをまとめた 1 入力分の値です。`IMUFrame.neutral()` は動きのない値を返します。`IMUFrame.raw(accel=None, gyro=None)` は加速度とジャイロの 3 軸の生値から作成し、未指定側を `(0, 0, 0)` として扱います。加速度だけを指定する場合は `IMUFrame.accel(x=0, y=0, z=0)`、ジャイロだけを指定する場合は `IMUFrame.gyro(x=0, y=0, z=0)` を使います。

加速度を G 単位で指定する場合は `IMUFrame.accel_g(x_g=0.0, y_g=0.0, z_g=0.0)` を使います。`IMUFrame.to_accel_g()` は設定値を G 単位の `(x, y, z)` として返します。変換尺度は `1/4096 G/raw` です。

角速度を rad/s 単位で指定する場合は `IMUFrame.gyro_rate(x_rad_s=0.0, y_rad_s=0.0, z_rad_s=0.0)` を使います。`IMUFrame.to_gyro_rate()` は設定値を rad/s 単位の `(x, y, z)` として返します。変換尺度は `0.070 dps/raw` です。

生値への変換結果が 16 ビット符号付き整数の範囲を超える場合は、上限値や下限値への丸めを行わず `InvalidInputError` が送出されます。Switch との通信に使う形式は接続先の要求に応じて自動で選ばれるため、利用者が指定する必要はありません。

既存の `IMUFrame` の一部だけを変更することもできます。`IMUFrame.with_gyro(x=0, y=0, z=0)` と `IMUFrame.with_gyro_rate(x_rad_s=0.0, y_rad_s=0.0, z_rad_s=0.0)` は加速度を維持してジャイロを置き換えます。`IMUFrame.with_accel(x=0, y=0, z=0)` と `IMUFrame.with_accel_g(x_g=0.0, y_g=0.0, z_g=0.0)` はジャイロを維持して加速度を置き換えます。

`InputState.neutral()` は、ボタン入力なし、左右のスティックが中央、IMU がニュートラルの状態を返します。`InputState.with_buttons(...)`、`InputState.with_sticks(...)`、`InputState.with_imu(...)`、`InputState.with_gyro(...)`、`InputState.with_accel(...)` は、新しい `InputState` を返します。`with_imu(frame)` は 1 入力分を 3 入力分に複製し、`with_imu(frame1, frame2, frame3)` は 3 つの値を順に設定します。`with_gyro((x, y, z))` と `with_accel((x, y, z))` も、1 組の値を 3 入力分に複製します。3 組を渡した場合は、順に片方のセンサー値だけを置き換えます。

## JoyConL / JoyConR

`JoyConL` と `JoyConR` は、Joy-Con L/R 相当の具象クラスです。直接送信型には `DirectJoyConL` と `DirectJoyConR` を使います。`side` 引数はありません。プロファイルごとの対応入力は、送信方式にかかわらず同じです。
```python
from swbt import Button, JoyConL, JoyConR, Stick

left = JoyConL(
    adapter="usb:0",
    profile_path="switch-left-joycon-bond.json",
)
right = JoyConR(
    adapter="usb:0",
    profile_path="switch-right-joycon-bond.json",
)
```

`JoyConL` は、`L`、`ZL`、`MINUS`、`CAPTURE`、`LEFT_STICK`（ボタン）、`SL`、`SR`、十字キー、左スティック入力を扱います。`JoyConR` は、`A`、`B`、`X`、`Y`、`R`、`ZR`、`PLUS`、`HOME`、`RIGHT_STICK`（ボタン）、`SL`、`SR`、右スティック入力を扱います。


```python
async with JoyConL(
    adapter="usb:0",
    profile_path="profiles/switch-left-joycon.json",
) as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.SR, Button.SL)
    await left.lstick(Stick.left())
    await left.tap(Button.L)
    await left.rstick(Stick.right())  # UnsupportedInputError
```

`apply(state)` と `send(state)` でも同じ制約を検査します。`JoyConL` または `DirectJoyConL` に右スティック入力や `A`、`B`、`X`、`Y` 入力を含む `InputState`、`JoyConR` または `DirectJoyConR` に左スティック入力や十字キー入力を含む `InputState` を渡すと `UnsupportedInputError` が送出されます。

全 concrete controller は `profile_path` を使えます。profile は `pro` / `joycon_l` / `joycon_r` の controller shape を持つため、異なる shape では別の保存先を使ってください。Direct と Periodic は同じ controller shape の profile を共有できますが、方式間再利用の実機検証は未実施です。
「持ちかた/順番を変える」画面で単体 Joy-Con として順番登録する場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送る必要があります。

OS、ドングル、ファームウェアをまたぐ互換性は未検証です。

## 例外とトレース出力

例外は `SwbtError` を基底例外とします。アダプタ列挙の失敗では `AdapterDiscoveryError`、利用者入力の不正では `InvalidInputError`、コントローラーが対応しない入力では `UnsupportedInputError`、transport を開けなかった場合は `TransportOpenError`、接続タイムアウトでは `ConnectionTimeoutError`、接続不成立では `ConnectionFailedError`、ペアリング情報の保存形式が一致しない場合は `InvalidKeyStoreError`、プロファイルが不正な場合は `InvalidProfileError` が送出されます。コントローラー種別の不一致は `ProfileControllerMismatchError` で区別できます。揮発領域への書換開始後の状態を確定できない場合は `AdapterIdentityRecoveryRequired` が送出されます。

`DiagnosticsConfig` はトレース出力のための設定です。`trace_writer` にテキストストリームを渡すと、接続状態の遷移、送信したレポート、受信したサブコマンド、エラー、`adapter`、`profile_path` などの実行時メタデータを、1 行 1 件の JSON オブジェクトとして出力します。このトレースログは、実機接続時の挙動確認や失敗時の切り分けに使います。
