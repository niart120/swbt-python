# swbt-python

NX 向けの仮想 Bluetooth HID 入力デバイスを Python から扱うためのライブラリです。

pre-alpha 版です。実機での動作は Bluetooth adapter、driver、対象機器の firmware に依存します。

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

詳細ドキュメントは `docs/index.md` から辿れます。公開サイトは `https://niart120.github.io/swbt-python/` です。

ローカルで確認する場合は次を使います。

```powershell
uv sync --group docs
uv run mkdocs serve
uv run mkdocs build --strict
```

## 利用例

詳しい API 仕様は `docs/api.md`、目的別の使い方は `docs/usage.md`、実機構成と troubleshooting は `docs/hardware.md` を参照してください。AI エージェント向けの要約は `docs/agent-brief.md` にあります。

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

接続方法、`key_store_path`、入力 API の使い分けは `docs/usage.md` にあります。

## 実機検証

詳細な実機条件、adapter / driver 注意、troubleshooting は `docs/hardware.md` にあります。実機ログの正本は `docs/hardware-test-log.md` です。

### 確認済み構成

2026-07-04 時点では、Windows 11 / CSR8510 A10 / WinUSB / `usb:0` / Python 3.13.5 / Bumble 0.0.230 / Switch 2 firmware 22.1.0 で、pairing、L2CAP、subcommand 応答、Button A、neutral 後の入力残りなし、D-pad、left / right stick、active bond reuse reconnect を確認済みです。

### 未確認構成

Linux、macOS、CSR8510 A10 以外の Bluetooth dongle、Switch 2 firmware 22.1.0 以外の対象機器、pairing-free incoming bond reuse は未確認です。

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

MIT ライセンス。詳細は `LICENSE` を参照してください。

## 注記

このプロジェクトは、対象機器や関連商標の権利者から承認、後援、提携を受けたものではありません。
