# テスト方針

この文書では、`swbt-python` の unit test、fake transport integration test、Bumble adapter test、hardware test の方針を定義する。

## 1. テスト分類

| 分類 | 実機 | Bumble | 目的 |
|---|---:|---:|---|
| Unit tests | 不要 | 不要 | 入力状態、report 生成、parser、subcommand を固定する |
| Fake transport integration tests | 不要 | 不要 | Periodic / Direct gamepad、`ReportSender`、`ReportLoop` の振る舞いを検証する |
| Bumble adapter tests | 不要または adapter のみ | 必要 | adapter open、power on、close を検証する |
| Hardware tests | 必要 | 必要 | Switch との pairing、L2CAP、入力反映を確認する |

実装順序としては、unit tests と fake transport integration tests を先に完成させる。Bumble と実機の不確実性を protocol core に持ち込まない。

## 2. Unit tests

Unit tests は `tests/unit/` に置く。

### 2.1 入力状態

対象:

- `Button`
- `Stick`
- `IMUFrame`
- `InputState`
- `InputState.neutral()`

検証項目:

- `Stick.raw()` が範囲外値を拒否する
- `Stick.normalized()` が `-1.0` から `1.0` の値を raw 値へ変換する
- `Stick.tilt()` が `Stick.normalized()` と同じ正規化座標を扱う
- `Stick.up()` / `down()` / `left()` / `right()` が方向 preset と `amount` 範囲を固定する
- `IMUFrame.raw()` / `gyro()` / `accel()` が raw int16 軸値から frame を作る
- `IMUFrame.with_gyro()` / `with_accel()` が反対側の sensor 値を維持する
- `IMUFrame.gyro_rate()` / `to_gyro_rate()` が固定 `0.070 dps/raw` で 3 軸の rad/s と raw 値を相互変換する
- `IMUFrame.with_gyro_rate()` が accel を維持し、signed int16 境界を受理して範囲外を `InvalidInputError` にする
- `IMUFrame.accel_g()` / `to_accel_g()` が固定 `1/4096 G/raw` で 3 軸の G と raw 値を相互変換する
- `IMUFrame.with_accel_g()` が gyro を維持し、signed int16 境界を受理して範囲外を `InvalidInputError` にする
- `InputState.neutral()` が空の button 集合と center stick を持つ
- `InputState.with_imu()` / `with_gyro()` / `with_accel()` が 1 個を 3 frame に複製し、3 個は順に設定する
- `InputState` が immutable に扱える

### 2.2 input report 生成

対象:

- `InputReportBuilder`
- `ProControllerProfile`

検証項目:

- neutral `0x30` report の長さが 49 bytes である
- report ID が `0x30` である
- `Button.A` が期待する bit に反映される
- `Button.L` と `Button.R` が同時に反映される
- d-pad が期待する bit に反映される
- stick center が期待する bytes へ pack される
- mode未指定 / `0x00`のIMU blockが36 byteゼロになる
- mode `0x01`がraw 3 frameをInt16LEで保持する
- mode `0x02-0x05`がquaternion packing mode 2になる
- explicit state / timeのIMU encoderが同じ入力から同じbytesと次stateを返す

### 2.3 output report parse

対象:

- `OutputReportParser`

検証項目:

- `0x01` report から packet id を読める
- `0x01` report から raw rumble bytes を抽出できる
- `0x01` report から subcommand id と payload を抽出できる
- `0x10` report を rumble only として扱える
- 不正長 report を `ProtocolError` として扱える

### 2.4 subcommand reply 生成

対象:

- `SubcommandResponder`
- `VirtualSpiFlash`

検証項目:

- `0x02` request device info に reply できる
- `0x03` set report mode に reply できる
- `0x04` trigger buttons elapsed time に reply できる
- `0x08` shipment / pairing related に reply できる
- `0x10` SPI flash read に reply できる
- `0x21` NFC/IR MCU config に reply できる
- `0x30` set player lights に reply できる
- `0x40` enable IMU に reply できる
- `0x40`のaccepted modeがdisabled / standard / quaternionのencoding形式を選び、同一modeの再要求でもencoding stateを初期化する
- 未対応IMU modeがsession stateを変更しない
- SPI `0x10` readとIMU mode遷移が互いの状態を変更しない
- `0x48` enable vibration に reply できる
- 未対応 subcommand を diagnostics に記録できる

### 2.5 virtual SPI flash

対象:

- `VirtualSpiFlash`

検証項目:

- 既知 address の読み取りが期待値を返す
- 範囲外 address の扱いが明確である
- 読み取り size が過大な場合に例外または切り詰めが定義通りになる

### 2.6 公開 reporting type と共通 sender

検証項目:

- root export に `PeriodicSwitchGamepad` / `DirectSwitchGamepad` と6具象型が含まれる
- Periodic だけが `apply(state)` と `report_period_us`、Direct だけが `send(state)` を公開する
- `ReportSender` が input report と subcommand reply の送信を直列化する
- timer byte と接続 session の IMU encoding state が送信順に更新される
- subcommand reply の state prefix が sender lock 内の current state と一致する

## 3. Fake transport integration tests

Fake transport integration tests は `tests/integration/` に置く。

### 3.1 gamepad の open / close

検証項目:

- internal fake transport constructor で Periodic / Direct の `async with` が動く
- `open()` 後に fake transport が open 済みになる
- `close()` 後に fake transport が closed になる
- `close()` を複数回呼んでも破綻しない

### 3.2 Periodic `ReportLoop` の周期送信

検証項目:

- `ReportLoop` が periodic `0x30` を fake transport に送る
- `report_period_us` を短くした test clock で決定的に検証できる
- 遅延時に過去 tick 分をまとめて送らない

### 3.3 input report と reply の共通送信順

検証項目:

- output report を fake transport から注入できる
- subcommand reply が reporting type に関係なく自動送信される
- `0x40` の session 遷移と ACK が input report と同じ sender lock で直列化され、新形式の `0x30` が ACK を追い越さない
- Direct input の直後に並ぶ reply の state prefix と timer が実際の送信順に一致する
- close後の再openで前回接続のhost要求状態とquaternion状態を引き継がない

### 3.4 neutral fail-safe

検証項目:

- `close(neutral=True)` で trailing neutral report が送られる
- Bumble transport の明示切断では、保留中の interrupt ACL queue を drain してから channel を切断する
- Bumble ACL queue の drain 失敗では channel を切断せず、失敗結果を返す
- Direct の `close(neutral=False)` は input report を追加しない
- disconnect callback で `InputStateStore` が neutral へ戻る
- 例外発生時にも内部 state が neutral へ戻る
- `SwitchGamepad.imu()` が IMU だけを更新し、接続不要かつ即時送信しない state update API として振る舞う

### 3.5 Direct transaction

検証項目:

- 接続後に待機しても周期 `0x30` を送らない
- `send(state)` が transport の受理まで待ち、受理後だけ state を commit する
- Direct の意味的入力操作が各正常終了につき `0x30` を1件送る
- 未接続、profile validation、transport受理前の失敗で最後に受理されたstateを維持する
- concurrent input operation が直列化され、開始順の候補 state を失わない
- `tap()` が押下から解放まで input operation lock を保持し、解放失敗時は押下 state を維持する
- Pro Controller / Joy-Con L / Joy-Con R が同じ transaction と profile validation を共有する

### 3.5 callback 例外

検証項目:

- transport callback 内の例外が diagnostics に記録される
- 継続不能な例外で lifecycle が `failed` へ遷移する
- `close()` で後始末できる

## 4. Bumble adapter tests

Bumble adapter tests は、Switch 実機なしで USB Bluetooth dongle だけを使う test とする。

pytest marker は `bumble` とする。

```python
@pytest.mark.bumble
async def test_bumble_transport_open_close():
    ...
```

検証項目:

- `adapter="usb:0"` で transport を開ける
- Bumble device を生成できる
- Bluetooth Classic を有効化できる
- power on できる
- discoverable / connectable にできる
- close を複数回呼んでも破綻しない

この test は CI の必須 test にはしない。developer machine または hardware test machine で実行する。

## 5. Hardware tests

Hardware tests は Switch 実機を使う。pytest marker は `hardware` とする。

```python
@pytest.mark.hardware
async def test_switch_pairing_and_tap_a():
    ...
```

### 5.1 pairing

検証項目:

- Switch 側から device が見える
- pairing が完了する
- diagnostics に pairing sequence が記録される

### 5.2 L2CAP open

検証項目:

- HID control channel が open する
- HID interrupt channel が open する
- disconnect 時に close event が記録される

### 5.3 subcommand sequence

検証項目:

- Switch から `0x01` output report を受け取れる
- `0x02`, `0x03`, `0x04`, `0x08`, `0x10`, `0x21`, `0x30`, `0x40`, `0x48` のうち観測されたものが diagnostics に記録される
- accepted IMU modeと導出されたencoding形式がトレース出力に記録され、IMU値と内部reset flag用語は記録されない
- 各 subcommand に `0x21` reply を返せる

### 5.4 Button A 反映

検証項目:

- `await pad.tap(Button.A)` が Switch UI に反映される
- `await pad.press(Button.L, Button.R)` が一定期間維持される
- `await pad.neutral()` 後に入力が残らない

### 5.5 reconnect

M6 以降で扱う。

検証項目:

- key store ありで再接続できるか
- key store なしで再 pairing になるか
- reconnect 失敗時に failure diagnostics を残して clean close するか
- reconnect 失敗後に自動 advertising recovery / retry loop を開始しないか

## 6. 実機検証マトリクス

実機検証結果は次の表で管理する。

| OS | Bluetooth dongle | Driver | Switch model | Firmware | Pairing | L2CAP | Subcommands | Input reflected | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Windows | CSR8510 A10 | WinUSB | Switch 2 | 22.1.0 | 未検証 | 未検証 | 未検証 | 未検証 | 既存 swbt-daemon の確認済み構成に近い |
| Linux | 未定 | libusb | Switch 2 | 未定 | 未検証 | 未検証 | 未検証 | 未検証 | 初期保証対象に含めるか未決 |
| macOS | 未定 | 未定 | Switch 2 | 未定 | 未検証 | 未検証 | 未検証 | 未検証 | 初期対象外 |

## 7. 診断ログの確認項目

Hardware tests では、少なくとも次の event を trace に残す。

- `transport_open_start`
- `transport_open_complete`
- `advertising_start`
- `connected`
- `l2cap_channel_open`
- `output_report_rx`
- `subcommand_rx`
- `subcommand_reply_tx`
- `input_report_tx`
- `neutral_tx`
- `disconnected`
- `transport_close_complete`
- `error`

ログ形式は JSON Lines とする。

`report_tx` は report が transport に受理されたことを表す。controller flow-control completion、air delivery、Switch への反映完了は表さない。

```json
{"event":"subcommand_rx","subcommand":"0x02","packet_id":18}
{"event":"report_tx","report_id":"0x21","reason":"subcommand_reply"}
{"event":"report_tx","report_id":"0x30","reason":"periodic"}
```

## 8. CI 方針

CI で必須にする test は次の通り。

- static type check
- lint
- unit tests
- fake transport integration tests

CI で必須にしない test は次の通り。

- Bumble adapter tests
- Hardware tests

Bumble adapter tests と Hardware tests は、developer machine または dedicated hardware runner で実行する。
