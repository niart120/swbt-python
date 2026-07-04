# テスト方針

この文書では、`swbt-python` の unit test、fake transport integration test、Bumble adapter test、hardware test の方針を定義する。

## 1. テスト分類

| 分類 | 実機 | Bumble | 目的 |
|---|---:|---:|---|
| Unit tests | 不要 | 不要 | 入力状態、report 生成、parser、subcommand を固定する |
| Fake transport integration tests | 不要 | 不要 | `SwitchGamepad` と `ReportLoop` の振る舞いを検証する |
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
- `InputState.neutral()` が空の button 集合と center stick を持つ
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
- IMU neutral frame が期待する bytes になる

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
- `0x48` enable vibration に reply できる
- 未対応 subcommand を diagnostics に記録できる

### 2.5 virtual SPI flash

対象:

- `VirtualSpiFlash`

検証項目:

- 既知 address の読み取りが期待値を返す
- 範囲外 address の扱いが明確である
- 読み取り size が過大な場合に例外または切り詰めが定義通りになる

## 3. Fake transport integration tests

Fake transport integration tests は `tests/integration/` に置く。

### 3.1 `SwitchGamepad` の open / close

検証項目:

- `async with SwitchGamepad(transport=fake)` が動く
- `open()` 後に fake transport が open 済みになる
- `close()` 後に fake transport が closed になる
- `close()` を複数回呼んでも破綻しない

### 3.2 `ReportLoop` の周期送信

検証項目:

- `ReportLoop` が periodic `0x30` を fake transport に送る
- `report_period_us` を短くした test clock で決定的に検証できる
- 遅延時に過去 tick 分をまとめて送らない

### 3.3 reply queue 優先

検証項目:

- output report を fake transport から注入できる
- subcommand reply が reply queue に積まれる
- reply queue に `0x21` がある場合、次送信で `0x30` より先に送られる

### 3.4 neutral fail-safe

検証項目:

- `close(neutral=True)` で trailing neutral report が送られる
- disconnect callback で `InputStateStore` が neutral へ戻る
- 例外発生時にも内部 state が neutral へ戻る

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
