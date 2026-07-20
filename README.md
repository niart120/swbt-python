# swbt-python

NX 向けの仮想 Bluetooth HID 入力デバイスを Python から扱うためのライブラリです。

本ライブラリは pre-alpha 版です。実機での動作は Bluetooth ドングル、ドライバー、対象機器の FW バージョンに依存します。

## 必要なもの

- Python 3.12 以降
- uv
- Bumble が利用可能な専用 USB Bluetooth ドングル

## インストール

```powershell
pip install swbt-python
```

ソースから動かす場合は次を使います。

```powershell
uv sync --dev
```

## ドキュメント

[公開ドキュメント](https://niart120.github.io/swbt-python/) には API、利用例、実機準備手順、AI エージェント向け要約があります。

- API 仕様: [API Reference](https://niart120.github.io/swbt-python/api/)
- 利用例: [Usage Guide](https://niart120.github.io/swbt-python/usage/)
- 実機準備手順とトラブルシューティング: [Hardware Guide](https://niart120.github.io/swbt-python/hardware/)
- AI エージェント向け要約: [Agent Brief](https://niart120.github.io/swbt-python/agent-brief/)

同じ内容は `docs/` 配下でも確認できます。

## 利用例
### Pro Controller
```python
import asyncio
from swbt import Button, ProController


async def main() -> None:
    async with ProController(adapter="usb:0") as pad:
        await pad.connect(
            timeout=30.0,
            allow_pairing=True,
        )
        await pad.tap(Button.A)
        await pad.neutral()


asyncio.run(main())
```

Pro Controller 相当の一時的な仮想デバイスを作成し、ペアリング後に A ボタン入力を送信するコードの例です。接続情報を永続化する場合は、利用者が管理するローカル Bluetooth アドレスを `ProController.create_profile()` に渡します。作成手順は[利用例](docs/usage.md)、対応する専用 USB Bluetooth ドングルと復旧手順は[実機準備手順](docs/hardware.md)を参照してください。

### Joy-Con L/R

Joy-Con 相当の仮想デバイスは `JoyConL(...)` または `JoyConR(...)` で作成します。接続と入力の扱い方は `ProController` と同じです。

```python
import asyncio
from swbt import Button, JoyConL, Stick


async def main() -> None:
    async with JoyConL(
        adapter="usb:0",
        key_store_path="switch-left-joycon-bond.json",
    ) as left:
        await left.connect(timeout=30.0, allow_pairing=True)
        await left.tap(Button.SR, Button.SL)
        await left.tap(Button.L)
        await left.lstick(Stick.left())
        await left.neutral()


asyncio.run(main())
```

「持ちかた/順番を変える」画面で Joy-Con としてペアリングする場合は、接続後に `await left.tap(Button.SR, Button.SL)` のように SR+SL を送信する必要があります。

Pro Controller は `profile_path`、Joy-Con L/R は移行前の `key_store_path` を使います。コントローラー種別ごとに保存先を分けてください。Joy-Con L で右スティックや A/B/X/Y、Joy-Con R で左スティックや十字キーを入力すると `UnsupportedInputError` が送出されます。`JoyConPair` は未実装です。

## 接続方法

実機接続には、PC の通常 Bluetooth 機能と共有しない専用 USB Bluetooth ドングルと、OS ごとのドライバー準備が必要です。Windows では、[Zadig](https://zadig.akeo.ie/) などで専用ドングルに WinUSB / libwdi ドライバーを入れてから アダプタ名を確認します。

ドライバー準備、アダプタ名の確認、トラブルシューティングの詳細は [Hardware Guide](https://niart120.github.io/swbt-python/hardware/) にあります。

### 確認済み構成

2026-07-07 時点では、Windows 11 / CSR8510 A10 / WinUSB / `usb:0` / Switch 2 firmware 22.1.0 で、Pro Controller のペアリング、保存済みペアリング情報を使う再接続、主要なボタン / スティック入力、ニュートラル復帰を確認済みです。

同じ Windows 構成で、Joy-Con L/R も部分的に動作確認済みです。確認済み範囲と未確認範囲の詳細は Hardware Guide にあります。

macOS 15.7.7 / CSR8510 A10 では、Pro Controller のペアリング、保存済みペアリング情報を使う再接続、ボタン入力、ニュートラル復帰を記録しています。

### 実験的構成

Linux は experimental です。手順は Hardware Guide に整備されていますが、専用 USB Bluetooth ドングルにアクセスできるか、ペアリングできるか、入力が反映されるかは未確認です。macOS は Pro Controller の一部挙動のみ検証済みです。Joy-Con、別ドングル、別ファームウェアでの互換性は未確認です。

## 開発

```powershell
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run ty check --no-progress
uv run pytest tests/unit
uv run pytest tests/integration
```

## ライセンス

MIT ライセンスです。全文は [LICENSE](https://github.com/niart120/swbt-python/blob/main/LICENSE) にあります。

## 注記

このプロジェクトは、対象機器や関連商標の権利者から承認、後援、提携を受けたものではありません。
