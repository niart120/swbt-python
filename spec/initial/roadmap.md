# 実装ロードマップ

この文書では、`swbt-python` の実装順序と milestone ごとの完了条件を定義する。

## 1. 実装順序の考え方

実装は、実機に依存しない core から始める。

```text
M0 protocol core
  ↓
M1 SwitchGamepad + fake transport
  ↓
M2 Bumble transport
  ↓
M3 pairing / L2CAP
  ↓
M4 subcommand responder実機通過
  ↓
M5 入力操作API完成
  ↓
M6 reconnect / keystore / diagnostics
  ↓
M7 packaging / examples / CLI
```

最初から Bumble と実機接続に入らない。Bluetooth 接続は不確実性が高いため、入力状態、report layout、subcommand reply、送信順序を fake transport で固定してから扱う。

## 2. M0: 入力モデルと Switch HID report 中核

### 2.1 対象範囲

- `Button`
- `Stick`
- `IMUFrame`
- `InputState`
- `InputReportBuilder`
- `OutputReportParser`
- `SubcommandResponder`
- `VirtualSpiFlash`
- `RumbleState`

### 2.2 非対象範囲

- Bumble
- USB Bluetooth adapter
- Switch 実機接続
- pairing
- reconnect
- packaging

### 2.3 実装項目

- neutral `InputState` を定義する
- `0x30` standard full input report を生成する
- `0x01` output report を parse する
- `0x10` output report を parse する
- 主要 subcommand の最小 reply を生成する
- virtual SPI flash の初期内容を定義する
- raw rumble state を保持する

### 2.4 完了条件

- `pytest tests/unit` が通る
- neutral `0x30` report の長さが 49 bytes で固定されている
- Button A、L+R、d-pad、stick center の report bytes が test で固定されている
- `0x01` / `0x10` parser の test がある
- `0x02` / `0x03` / `0x04` / `0x08` / `0x10` / `0x21` / `0x30` / `0x40` / `0x48` の reply test がある
- protocol 層が Bumble を import していない

## 3. M1: fake transport 上の SwitchGamepad API

### 3.1 対象範囲

- `SwitchGamepad`
- `SwitchGamepadConfig`
- `InputStateStore`
- `ReportLoop`
- `HidDeviceTransport`
- `FakeHidTransport`
- `DiagnosticsRecorder` の最小実装

### 3.2 非対象範囲

- Bumble
- Switch 実機接続
- OS 別 driver 処理
- reconnect

### 3.3 実装項目

- `async with SwitchGamepad(transport=fake)` を実装する
- `open()` / `close()` を実装する
- `wait_connected()` を fake transport で検証できるようにする
- `set_input()` / `neutral()` を実装する
- `press()` / `release()` / `tap()` を実装する
- `ReportLoop` で periodic `0x30` を送る
- reply queue 優先制御を実装する
- close 時の neutral fail-safe を実装する

### 3.4 完了条件

- fake transport で `tap(Button.A)` の report が記録される
- output report 注入から `0x21` reply 送信まで test できる
- `0x21` reply が `0x30` より優先送信される
- `close(neutral=True)` で neutral report が記録される
- 複数 task から入力更新しても state が破壊されない
- public API が Bumble 型に依存していない

## 4. M2: Bumble HID transport

### 4.1 対象範囲

- `BumbleHidTransport`
- Bumble device 初期化
- Bluetooth Classic 有効化
- HID Device helper の利用
- SDP record
- HID descriptor
- adapter open / close

### 4.2 非対象範囲

- Switch pairing 成功の保証
- Button A の実機反映
- reconnect
- Linux / macOS の動作保証

### 4.3 実装項目

- `adapter="usb:0"` などの moniker を受け取る
- Bumble transport を開く
- Bumble device を作る
- Classic を有効化する
- HID Device を初期化する
- discoverable / connectable にする
- interrupt / control callback を上位へ渡す
- close を冪等に近い形で実装する
- transport open 失敗を `TransportOpenError` に変換する

### 4.4 完了条件

- USB Bluetooth dongle を使って transport open / close できる
- power on できる
- discoverable / connectable にできる
- close を複数回呼んでも破綻しない
- adapter 情報、OS、Python version、Bumble version が diagnostics に残る
- `swbt.transport.bumble` 以外が Bumble を import していない

## 5. M3: pairing / L2CAP 接続

### 5.1 対象範囲

- Switch との pairing
- HID control channel open
- HID interrupt channel open
- 接続・切断 event の記録

### 5.2 非対象範囲

- 入力反映の完全確認
- reconnect
- 複数 Switch model の互換性確認

### 5.3 実装項目

- Switch 側の pairing 操作から device が見えることを確認する
- pairing complete event を記録する
- HID control channel open を記録する
- HID interrupt channel open を記録する
- disconnect event を記録する
- pairing 失敗時の trace を残す

### 5.4 完了条件

- Switch と pairing できる
- HID control channel が open する
- HID interrupt channel が open する
- 手動 close で transport が停止する
- pairing / L2CAP sequence が diagnostics で追える

## 6. M4: subcommand 応答処理

### 6.1 対象範囲

- Switch からの output report 受信
- subcommand sequence 記録
- `0x21` reply 送信
- 初期化 sequence の前進確認

### 6.2 非対象範囲

- 高水準 NFC / IR 意味処理
- 高水準 rumble API
- reconnect

### 6.3 実装項目

- `0x01` output report を実機で受信する
- subcommand id と payload を diagnostics に記録する
- `SubcommandResponder` の不足を trace から補う
- `0x21` reply を priority queue へ投入する
- periodic `0x30` と reply の送信順序を確認する

### 6.4 完了条件

- 実機で output report を受信できる
- 観測された subcommand sequence を diagnostics に残せる
- 主要 subcommand に `0x21` reply を返せる
- 初期化 sequence が入力反映手前まで進む
- 未対応 subcommand があれば文書化されている

## 7. M5: 入力操作 API

### 7.1 対象範囲

- 実機での `tap()`
- 実機での `press()` / `release()`
- 実機での stick 入力
- `neutral()`
- `status()`

### 7.2 非対象範囲

- 複雑な macro scheduler
- 高水準 rumble API
- 複数 controller
- reconnect の正式保証

### 7.3 実装項目

- `tap(Button.A)` が Switch UI に反映されることを確認する
- `press(Button.L, Button.R)` が一定期間維持されることを確認する
- `release()` で該当 button が解除されることを確認する
- `neutral()` で全入力が戻ることを確認する
- `status()` に connection state、report counters、last subcommand、rumble raw を載せる

### 7.4 完了条件

- `await pad.tap(Button.A)` が Switch UI に反映される
- `await pad.press(Button.L, Button.R)` が一定 tick 数以上送信される
- `await pad.neutral()` 後に入力が残らない
- disconnect 時に内部 state が neutral へ戻る
- `status()` で接続状態と report counter を読める

## 8. M6: 再接続・鍵保存・診断

### 8.1 対象範囲

- `key_store_path`
- pairing 情報の保存
- reconnect
- diagnostics 拡充
- hardware run metadata

### 8.2 非対象範囲

- 全 dongle での reconnect 保証
- 複数 controller 同時 reconnect
- daemon mode

### 8.3 実装項目

- key store の保存先を設定できるようにする
- pairing 情報が保存されたか diagnostics に記録する
- bond reuse reconnect の成功 / 失敗を active / incoming に分けて記録する
- reconnect 失敗時は failure diagnostics を残して clean close する
- reconnect 失敗後の自動 advertising recovery と retry loop は M6 に含めない
- hardware matrix を更新する
- trace の schema を安定させる

### 8.4 完了条件

- key store ありの接続情報保存が確認できる
- reconnect の成功 / 失敗が diagnostics で追える
- reconnect 失敗後に明示 API で再 pairing できる
- hardware run metadata が trace に含まれる

## 9. M7: 配布・サンプル・CLI

### 9.1 対象範囲

- `pyproject.toml`
- package metadata
- examples
- `swbt-probe` CLI
- README
- 開発者向け手順

### 9.2 非対象範囲

- 常駐 daemon
- GUI
- 既存 IPC 互換 server

### 9.3 実装項目

- `pip install swbt-python` で install できる package にする
- `from swbt import SwitchGamepad, Button` を公開する
- `examples/tap_a.py` を作る
- `examples/pairing_probe.py` を作る
- `examples/hardware_bringup.py` を作る
- `swbt-probe adapters` を作る
- `swbt-probe pair --adapter usb:0 --trace trace.jsonl` を作る
- README に Windows / Linux の注意点を書く

### 9.4 完了条件

- package build が通る
- examples が fake transport で test されている
- hardware bring-up 手順が README から辿れる
- `swbt-probe` で adapter と trace を確認できる
- public API の最小利用例が動く

## 10. release gate

初期 release の gate は次の通り。

- unit tests が通る
- fake transport integration tests が通る
- Windows + 専用 USB Bluetooth dongle で adapter open が確認されている
- 少なくとも 1 つの Switch 実機構成で pairing と Button A 反映が確認されている
- 対応済み構成と未確認構成が README に明記されている
- 既知のリスクが `risks.md` に反映されている
