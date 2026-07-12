# アーキテクチャ

この文書では、`swbt-python` のレイヤ構成、主要コンポーネント、依存方向、パッケージ構成を定義する。

## 1. 全体構成

`swbt-python` は、daemon ではなく Python ライブラリとして構成する。利用者は `SwitchGamepad` オブジェクトを作成し、そのオブジェクト経由で入力状態を更新する。

```text
利用者コード
  ↓
SwitchGamepad
  ↓
InputStateStore
  ↓
ReportLoop
  ↓
SwitchHidProtocol / SubcommandResponder
  ↓
HidDeviceTransport
  ↓
BumbleHidTransport
  ↓
Bumble Host + USB HCI transport
  ↓
USB Bluetooth dongle
  ↓
Nintendo Switch
```

### 1.1 レイヤ構成

| レイヤ | 主な責務 | 代表コンポーネント |
|---|---|---|
| Public API | 利用者に公開する操作面 | `SwitchGamepad` |
| Input model | ボタン、スティック、IMU の状態表現 | `InputState`, `Button`, `Stick` |
| State store | 現在入力の保持と snapshot 提供 | `InputStateStore` |
| Report loop | 周期送信、reply 優先制御 | `ReportLoop` |
| Switch HID protocol | report 生成、output report 解析、subcommand 応答 | `SwitchHidProtocol`, `SubcommandResponder` |
| Transport interface | HID Device transport の抽象化 | `HidDeviceTransport` |
| Bumble transport | Bumble 依存の実接続 | `BumbleHidTransport` |
| Test transport | 実機なしの検証 | `FakeHidTransport` |

### 1.2 依存方向

依存方向は上位から下位への一方向に限定する。

```text
gamepad
  → input
  → state_store
  → report_loop
  → protocol
  → transport.base

transport.bumble
  → bumble

protocol
  → input

input
  → 標準ライブラリのみ
```

禁止する依存は次の通り。

- `input` から `protocol`、`transport`、`bumble` へ依存しない
- `protocol` から `transport`、`bumble` へ依存しない
- `state_store` から `bumble` へ依存しない
- `gamepad` から `transport.bumble` の内部型へ依存しない
- public API に Bumble の型を露出しない

## 2. 主要コンポーネント

### 2.1 `SwitchGamepad`

利用者が直接扱う公開 API の中心。resource scope の `open()` / `close()`、明示接続 API の `pair()` / `connect()` / `reconnect()`、入力操作の `tap()`、`press()`、`release()`、`lstick()`、`rstick()`、`sticks()`、`imu()`、`apply()`、`neutral()` を提供する。

`SwitchGamepad` は内部に `InputStateStore`、`ReportLoop`、`SwitchHidProtocol`、`HidDeviceTransport` を保持する。ただし、利用者にそれらの内部状態を直接操作させない。

### 2.2 `InputState`

ボタン、左右スティック、IMU frame を表す値オブジェクト。外部から渡された後に内容が変わらないよう、immutable な設計に寄せる。`InputState` は button、stick、IMU それぞれの builder を持ち、complete state を組み立てて `SwitchGamepad.apply()` に渡せるようにする。

### 2.3 `InputStateStore`

現在の入力状態を保持する内部コンポーネント。`press()`、`release()`、`sticks()`、`imu()` はこの store を更新し、`ReportLoop` は送信前に snapshot を取得する。

複数の asyncio task から同時に入力更新される可能性があるため、更新処理は lock で保護する。

### 2.4 `ReportLoop`

一定周期で Switch へ HID input report を送る。reply queue に `0x21` subcommand reply がある場合は、periodic `0x30` input report より先に送る。

送信周期の初期値は `8000us` とする。ただし、この値は既定値であり、全環境での最適値とは扱わない。実送信時刻は diagnostics に記録する。

### 2.5 `SwitchHidProtocol`

Switch 向け HID report の生成と解釈を担当する。具体的には、hostのIMU modeに応じた`0x30` input reportの生成、`0x01` / `0x10` output reportの解析、`0x21` replyの組み立てを扱う。接続単位の`SwitchHidSession`がhost要求状態とIMU encoding stateを所有し、acceptedな同一modeの再要求でも新しいencoding epochを開始する。IMU wire生成は明示的なstate、3つのIMU frame、profile校正、report時刻から36 byte blockと次stateを返す。

この層は Bluetooth 接続状態や HCI transport を扱わない。

### 2.6 `SubcommandResponder`

Switch から送られる subcommand に対して、最小限の reply payload を生成する。

初期対応対象は次の subcommand とする。

- `0x02` request device info
- `0x03` set report mode
- `0x04` trigger buttons elapsed time
- `0x08` shipment / pairing related
- `0x10` SPI flash read
- `0x21` NFC/IR MCU config
- `0x30` set player lights
- `0x40` enable IMU
- `0x48` enable vibration

`SubcommandResponder` は configured `ControllerProfile` を参照して fixed identity / SPI seed / Device Info を生成する。report mode、IMU mode、vibration enable など Switch host の要求で変わる値は接続単位の`SwitchHidSessionState`に置き、profileや`InputState`には置かない。`0x40`によるsession遷移と`0x21` ACKは`ReportLoop`の送信lock内で処理し、新形式の周期入力レポートがACKを追い越さないようにする。

### 2.7 `HidDeviceTransport`

HID Device として bytes を送受信するための抽象 interface。Switch のボタンや subcommand の意味は扱わない。

### 2.8 `BumbleHidTransport`

Bumble を使った transport 実装。Bumble device の生成、Bluetooth Classic の有効化、SDP record、HID descriptor、control / interrupt channel、callback の橋渡しを担当する。

Bumble に関する import はこのモジュール内に閉じ込める。

### 2.9 `FakeHidTransport`

実機なしで API と report loop を検証するための transport。送信された report を memory に記録し、受信 callback を test から注入できるようにする。

## 3. パッケージ構成

想定する Python package 構成は次の通り。

```text
swbt/
  __init__.py
  gamepad.py
  input.py
  state_store.py
  report_loop.py

  protocol/
    __init__.py
    switch_hid.py
    input_report.py
    output_report.py
    subcommand.py
    spi.py
    rumble.py
    profiles/
      base.py
      pro_controller.py
      joycon.py

  transport/
    __init__.py
    base.py
    bumble.py
    fake.py

  diagnostics.py
  errors.py
  py.typed
```

### 3.1 各モジュールの責務

| モジュール | 責務 |
|---|---|
| `swbt.__init__` | 公開 API の再 export |
| `swbt.gamepad` | `SwitchGamepad` と設定オブジェクト |
| `swbt.input` | `InputState`, `Button`, `Stick`, `IMUFrame` |
| `swbt.imu` | 仮想ジャイロ校正値、rad/s と raw 値の相互変換、SPI 用 serialization |
| `swbt.state_store` | 現在入力の保持、snapshot 生成 |
| `swbt.report_loop` | 周期送信、reply queue 優先制御 |
| `swbt.protocol.switch_hid` | Switch HID protocol の統合 facade |
| `swbt.protocol.input_report` | `0x30` input report builder |
| `swbt.protocol.imu_report` | 明示state / timeによるIMU mode別36 byte block生成 |
| `swbt.protocol.session` | 接続単位のhost要求状態とIMU encoding state |
| `swbt.protocol.output_report` | `0x01` / `0x10` output report parser |
| `swbt.protocol.subcommand` | subcommand reply 生成 |
| `swbt.protocol.spi` | virtual SPI flash |
| `swbt.protocol.rumble` | raw rumble state |
| `swbt.protocol.profiles.base` | Controller profile の共通型、controller kind、色、SDP policy |
| `swbt.protocol.profiles.pro_controller` | Pro Controller の固定 identity 情報 |
| `swbt.protocol.profiles.joycon` | Joy-Con L/R の固定 identity 情報 |
| `swbt.transport.base` | transport protocol 定義 |
| `swbt.transport.bumble` | Bumble transport 実装 |
| `swbt.transport.fake` | テスト用 transport |
| `swbt.diagnostics` | trace event、counter、環境情報 |
| `swbt.errors` | 例外型 |

## 4. daemon ではなくライブラリにする理由

既存の `swbt-daemon` は、外部 client から入力状態を受け取り、Bluetooth HID Device として Switch へ入力を送る daemon である。`swbt-python` では、daemon と IPC を主軸にしない。

理由は次の通り。

- Python 利用者は、プロセス内オブジェクトとして扱える API を期待する
- daemon IPC を先に実装すると、protocol core と transport の検証が遅れる
- `tap()` や `press()` のような操作は library helper として自然に表現できる
- 将来 CLI や daemon が必要になった場合も、`SwitchGamepad` の薄い wrapper として追加できる

## 5. 既存 swbt-daemon から引き継ぐもの

既存実装は、そのまま Python へ逐語移植する対象ではない。主に次を参照元として扱う。

- Switch HID report の構造
- 初期化時に Switch から送られる output report / subcommand の扱い
- subcommand reply の基本構造
- report 送信周期の既定値
- neutral fail-safe の考え方
- 実機検証ログから得られた接続順序
- 確認済み hardware backend の制約

## 6. 既存 swbt-daemon から引き継がないもの

初期実装では、次を引き継がない。

- daemon process model
- JSON Lines IPC の完全互換
- BTstack backend の実装詳細
- C ABI のための構造体設計
- Windows 配布物の packaging 方式

これらは Python ライブラリとしての中核が固まった後、必要性が明確になった段階で検討する。
