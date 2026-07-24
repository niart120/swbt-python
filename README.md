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

- [API リファレンス](https://niart120.github.io/swbt-python/api/)
- [利用例](https://niart120.github.io/swbt-python/usage/)
- [実機準備手順](https://niart120.github.io/swbt-python/hardware/)
- [AI エージェント向け要約](https://niart120.github.io/swbt-python/agent-brief/)

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

Pro Controller 相当の仮想デバイスを作成し、ペアリング後に A ボタン入力を送信する例です。

接続情報を保存して再利用する場合は、先に `ProController.create_profile()` で `profile_path` を作成します。アドレスの選択方法と復旧手順は[利用例](docs/usage.md)、専用 USB Bluetooth ドングルの準備は[実機準備手順](docs/hardware.md)を参照してください。

### Joy-Con L/R

Joy-Con 相当の仮想デバイスは `JoyConL(...)` または `JoyConR(...)` で作成します。以下の例は `JoyConL.create_profile()` で作成済みのプロファイルを再利用します。接続と入力の扱い方は `ProController` と同じです。

```python
import asyncio
from swbt import Button, JoyConL, Stick


async def main() -> None:
    async with JoyConL(
        adapter="usb:0",
        profile_path="switch-left-joycon-profile.json",
    ) as left:
        await left.connect(timeout=30.0, allow_pairing=True)
        await left.tap(Button.L)
        await left.lstick(Stick.left())
        await left.neutral()


asyncio.run(main())
```

「持ちかた/順番を変える」画面でペアリングするときも、登録用の SR+SL 入力を追加送信する必要はありません。`connect()` は Joy-Con 用の初期化とプレイヤーライトの設定が完了してから戻ります。

`profile_path` はコントローラー形状と対象機器ごとに分けます。Joy-Con L では右スティックと A/B/X/Y、Joy-Con R では左スティックと十字キーを使えません。これらを指定すると `UnsupportedInputError` が送出されます。`JoyConPair` は未実装です。

## 接続方法

実機接続には、PC の通常 Bluetooth 機能と共有しない専用 USB Bluetooth ドングルと、OS ごとのドライバー準備が必要です。Windows では、[Zadig](https://zadig.akeo.ie/) などで専用ドングルに WinUSB / libwdi ドライバーを入れてからアダプタ名を確認します。

ドライバー準備、アダプタ名の確認、トラブルシューティングの詳細は[実機準備手順](https://niart120.github.io/swbt-python/hardware/)にあります。

### 確認済み構成

Windows 11 / CSR8510 A10 / WinUSB では、Pro Controller、Joy-Con L、Joy-Con R のペアリング、再接続、対応する入力操作を確認しています。macOS 15.7.7 / CSR8510 A10 では Pro Controller の限定的な動作を確認しています。条件と未確認範囲は[実機準備手順](https://niart120.github.io/swbt-python/hardware/)を参照してください。

### 実験的構成

Linux は experimental です。専用 USB Bluetooth ドングルへのアクセス、ペアリング、入力反映は未確認です。macOS の Joy-Con、別ドングル、別ファームウェアでの互換性も未確認です。

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
