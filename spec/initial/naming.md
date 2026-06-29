# 命名方針

この文書では、`swbt-python` のプロジェクト名、公開パッケージ名、モジュールルート名、主要クラス名、避ける名前を定義する。

## 1. 採用名

| 種別 | 採用名 |
|---|---|
| プロジェクト表示名 | `swbt-python` |
| 公開パッケージ名 | `swbt-python` |
| Python モジュールルート | `swbt` |
| 主要公開クラス | `SwitchGamepad` |

インストールと import は次の形にする。

```bash
pip install swbt-python
```

```python
from swbt import SwitchGamepad, Button
```

公開パッケージ名と import 名は一致しない。これは意図した設計とする。リポジトリ名と package metadata では Python 版であることを示し、import 名は短く保つ。

## 2. 採用理由

### 2.1 `swbt-python`

`swbt-python` は既存 `swbt-daemon` との関係を保ちつつ、Python ライブラリ版であることを明示できる。

`switch-bumble` のように Bumble を名前へ含めると、将来別 transport を追加したときに名前が狭くなる。`switch-gamepad` のような一般名は目的が分かりやすいが、既存プロジェクトとの連続性が弱い。

### 2.2 `swbt`

`swbt` は import 名として短い。利用例も読みやすい。

```python
from swbt import SwitchGamepad, Button
```

`swbt_python` という import 名は避ける。Python package であることは import 名から表す必要がない。

### 2.3 `SwitchGamepad`

公開 API の中心は `SwitchGamepad` とする。

理由は次の通り。

- 利用者視点で「Switch 向け入力デバイス」を表す
- `Controller` と `Control` の混同を避けられる
- daemon や transport ではなく、入力デバイス API であることが伝わる
- `ProController` よりも実装の自由度が残る

## 3. 採用済みの内部名

| 名前 | 意味 |
|---|---|
| `InputState` | ボタン・スティック・IMU などの入力状態 |
| `InputStateStore` | 現在の入力状態を保持する内部コンポーネント |
| `ReportLoop` | input report と subcommand reply を周期送信する loop |
| `SwitchHidProtocol` | Switch 向け HID report の生成・解釈 |
| `InputReportBuilder` | `0x30` input report の生成 |
| `OutputReportParser` | `0x01` / `0x10` output report の解析 |
| `SubcommandResponder` | Switch からの subcommand に応答する処理 |
| `VirtualSpiFlash` | `0x10` SPI flash read へ応答する仮想 storage |
| `RumbleState` | Switch から受け取った raw rumble bytes の保持 |
| `HidDeviceTransport` | HID Device transport の抽象 interface |
| `BumbleHidTransport` | Bumble を用いた transport 実装 |
| `FakeHidTransport` | test 用 transport 実装 |
| `DiagnosticsRecorder` | trace event と counter の記録 |

## 4. 避ける名前

次の名前は採用しない。

| 避ける名前 | 理由 |
|---|---|
| `SwitchController` | `Control` 系の内部名と混同しやすい |
| `ControlEngine` | 何を制御するのか曖昧 |
| `ControllerState` | 入力状態なのか接続状態なのか曖昧 |
| `Controller` | 一般名すぎる |
| `Control` | 意味の範囲が広すぎる |
| `Device` | Bluetooth device、HID device、Switch device のどれか曖昧 |
| `Manager` | 責務が広がりやすい |
| `Service` | daemon / server 実装を連想しやすい |
| `Engine` | 具体的な責務を隠しやすい |

内部名では、できる限り「何を保持するか」「何を生成するか」「何を送るか」が名前から分かるようにする。

## 5. ファイル名の方針

Python module 名は短く、責務を直接表す名前にする。

| ファイル | 方針 |
|---|---|
| `gamepad.py` | 公開 API の中心 |
| `input.py` | 入力状態と入力値 |
| `state_store.py` | 現在入力の保持 |
| `report_loop.py` | 周期送信 loop |
| `protocol/input_report.py` | input report 生成 |
| `protocol/output_report.py` | output report 解析 |
| `protocol/subcommand.py` | subcommand 応答 |
| `transport/base.py` | transport 抽象 interface |
| `transport/bumble.py` | Bumble 実装 |
| `transport/fake.py` | test 実装 |

## 6. public import 方針

よく使う型は `swbt.__init__` から再 export する。

```python
from swbt import SwitchGamepad, Button, InputState, Stick
```

transport 実装は明示 import にする。

```python
from swbt.transport.fake import FakeHidTransport
from swbt.transport.bumble import BumbleHidTransport
```

`BumbleHidTransport` は通常の利用者が直接使う必要はない。test、実験、別 adapter injection のために公開する。

## 7. CLI 名

将来 CLI を追加する場合、名前は `swbt-probe` とする。

```bash
swbt-probe adapters
swbt-probe pair --adapter usb:0 --trace trace.jsonl
```

`swbt-daemon` という CLI 名は使わない。常駐 daemon を初期提供しないためである。

## 8. 旧候補

検討した候補は次の通り。

| 候補 | import 名 | 判断 |
|---|---|---|
| `swbt` | `swbt` | 短いが、Python 版であることが package 名から分かりにくい |
| `swbt-python` | `swbt` | 採用 |
| `switch-bumble` | `switch_bumble` | Bumble 依存が名前に出すぎる |
| `switch-gamepad` | `switch_gamepad` | 分かりやすいが一般名すぎる |
| `pyswbt` | `pyswbt` | `py` 接頭辞が冗長 |
| `joybt` | `joybt` | Joy-Con 専用に見えやすい |
| `procon-bt` | `procon_bt` | Pro Controller 相当に固定されすぎる |

## 9. 命名決定時の確認事項

公開前に次を確認する。

- PyPI 上で `swbt-python` が利用可能か
- GitHub 上で `swbt-python` の repository 名が利用可能か
- `swbt` import 名が既存 package と衝突しないか
- README と examples の import が `from swbt import ...` に統一されているか
- 文書内に古い placeholder 名が残っていないか
- `SwitchController`、`ControlEngine`、`ControllerState` が public API に残っていないか
