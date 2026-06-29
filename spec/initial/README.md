# swbt-python 初期設計

作成日: 2026-06-29

この文書群は、既存の `swbt-daemon` を参照しながら、Python ネイティブライブラリとして `swbt-python` を実装するための設計方針、実装順序、検証条件を整理する。

再構築後の主目的は、常駐 daemon を提供することではない。Python コードから仮想 Switch 入力デバイスを生成し、ボタン、スティック、neutral 入力などを送信できる API を提供する。

## 1. 名称

本計画では、名称を次のように固定する。

| 種別 | 名称 |
|---|---|
| プロジェクト表示名 | `swbt-python` |
| 公開パッケージ名 | `swbt-python` |
| Python モジュールルート | `swbt` |
| 主要公開クラス | `SwitchGamepad` |

インストールと import の想定は次の通り。

```bash
pip install swbt-python
```

```python
from swbt import SwitchGamepad, Button
```

## 2. 目的

`swbt-python` は、Python から Nintendo Switch 向けの仮想入力デバイスを扱うためのライブラリとして設計する。

目的は次の通り。

- Python から扱える仮想 Switch 入力デバイスを提供する
- Bluetooth Classic HID Device として Switch に接続する
- Switch 側には Pro Controller 相当の入力デバイスとして認識させる
- daemon IPC ではなく、Python オブジェクト API を主な利用面にする
- Bumble 依存を transport 層に閉じ込め、protocol core を単体で検証できるようにする

## 3. 対象範囲

### 3.1 対象にするもの

- 単一の仮想 Switch 入力デバイス
- Pro Controller 相当の HID report
- ボタン入力
- 左右スティック入力
- neutral 入力
- Switch からの主要 subcommand への応答
- fake transport を使った実機なしのテスト
- Bumble transport を使った Bluetooth Classic HID Device 接続
- 実機接続時の診断ログ

### 3.2 初期実装では対象外にするもの

- 常駐 daemon の再実装
- 既存 JSON Lines IPC の完全互換
- 複数コントローラ同時接続
- amiibo emulation
- NFC / IR MCU の意味的実装
- IR camera
- 高水準 rumble API
- GUI
- Switch 以外のホスト対応

対象外の機能は、将来の拡張を妨げない範囲で切り離しておく。初期設計では、それらの機能を public API に含めない。

## 4. 設計方針の要約

- 公開 API は `SwitchGamepad` に集約する
- 入力状態は `InputState` として表現する
- 現在の入力状態は `InputStateStore` が保持する
- 周期送信は `ReportLoop` が担当する
- Switch HID report の生成と解釈は `SwitchHidProtocol` が担当する
- Switch からの subcommand 応答は `SubcommandResponder` が担当する
- Bluetooth 実装は `BumbleHidTransport` に閉じ込める
- 上位層は Bumble を直接 import しない
- 実機なしで検証できる protocol core を先に作る
- `0x21` subcommand reply は periodic `0x30` input report より優先して送信する

## 5. 全体構成

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

この構成では、Switch 固有の HID protocol 処理と、Bumble による Bluetooth 接続処理を分離する。これにより、実機接続が不安定な段階でも、入力状態、report 生成、subcommand 応答、送信優先順位を unit test で固定できる。

## 6. ドキュメント一覧

| ファイル | 内容 |
|---|---|
| `architecture.md` | 全体アーキテクチャ、責務分離、依存方向 |
| `api.md` | 公開 API、利用例、例外設計 |
| `protocol.md` | Switch HID protocol、report 生成、subcommand 応答 |
| `transport-bumble.md` | Bumble を用いた HID Device transport |
| `lifecycle.md` | 接続ライフサイクル、close、neutral fail-safe、reconnect |
| `testing.md` | unit test、fake transport integration test、hardware test |
| `roadmap.md` | M0 から M7 までの実装ロードマップ |
| `risks.md` | 既知のリスク、影響、対策 |
| `naming.md` | 命名方針、採用名、避ける名前 |

## 7. 現在の未決事項

- 初期検証対象 OS を Windows のみにするか、Linux も含めるか
- 初期検証対象 Bluetooth dongle を CSR8510 A10 に限定するか
- reconnect を初期 release に含めるか
- HID descriptor を既存実装からどの粒度で移植するか
- virtual SPI flash の初期内容をどこまで固定するか
- IMU 入力を初期 API で公開するか、内部 neutral frame のみ扱うか

## 8. 参考資料

- `swbt-daemon` repository: https://github.com/niart120/swbt-daemon
- `swbt-daemon` status: https://github.com/niart120/swbt-daemon/blob/main/docs/status.md
- Switch HID core spec: https://github.com/niart120/swbt-daemon/blob/main/spec/protocols/switch-hid-core.md
- Bumble documentation: https://google.github.io/bumble/
- Bumble HID Device example: https://github.com/google/bumble/blob/main/examples/run_hid_device.py
