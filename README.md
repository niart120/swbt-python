# swbt-python

NX 向けの仮想 Bluetooth HID 入力デバイスを Python から扱うためのライブラリです。

本ライブラリは pre-alpha 版です。実機での動作は Bluetooth adapter、driver、対象機器の firmware に依存します。

## 必要なもの

- Python 3.12 以降
- uv
- Bumble が利用可能な専用 USB Bluetooth dongle

## インストール

```powershell
pip install swbt-python
```

ソースから動かす場合は次を使います。

```powershell
uv sync --dev
```

## ドキュメント

[公開ドキュメント](https://niart120.github.io/swbt-python/) には API、利用例、実機準備、AI エージェント向け要約があります。

- API 仕様: [API Reference](https://niart120.github.io/swbt-python/api/)
- 利用例: [Usage Guide](https://niart120.github.io/swbt-python/usage/)
- 実機構成と troubleshooting: [Hardware Guide](https://niart120.github.io/swbt-python/hardware/)
- AI エージェント向け要約: [Agent Brief](https://niart120.github.io/swbt-python/agent-brief/)

リポジトリを checkout している場合、同じ内容は `docs/` 配下でも確認できます。

## 利用例

```python
import asyncio
from swbt import Button, SwitchGamepad


async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(
            timeout=30.0,
            allow_pairing=True,
        )
        await pad.tap(Button.A)
        await pad.neutral()


asyncio.run(main())
```

この例は adapter を開き、HID advertising、pairing または reconnect、periodic report loop、入力送信を行います。専用 USB Bluetooth dongle と接続情報のファイルパスを指定し、終了時は neutral を送ってから接続を閉じます。

接続方法、`key_store_path`、入力 API の使い分けは [Usage Guide](https://niart120.github.io/swbt-python/usage/) にあります。

## 実機検証

実機接続には、PC の通常 Bluetooth 機能と共有しない専用 USB Bluetooth dongle と、OS ごとの driver 準備が必要です。Windows では、[Zadig](https://zadig.akeo.ie/) などで専用 dongle に WinUSB / libwdi driver を入れてから adapter 名を確認します。

driver 準備、adapter 名の確認、troubleshooting は [Hardware Guide](https://niart120.github.io/swbt-python/hardware/) にあります。実機ログの正本は [hardware-test-log](https://niart120.github.io/swbt-python/hardware-test-log/) です。

### 確認済み構成

2026-07-04 時点では、Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で、pairing、reconnect、Button A、D-pad、left / right stick、neutral 後の入力残りなしを確認済みです。adapter 名の例は `usb:0` です。

### 未対応構成

Linux / macOS は unsupported です。CSR8510 A10 以外の Bluetooth dongle、Switch 2 firmware 22.1.0 以外の対象機器は確認済み構成に含めていません。

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
