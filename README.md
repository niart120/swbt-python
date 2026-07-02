# swbt-python

NX 向けの仮想 Bluetooth HID 入力デバイスを Python から扱うためのライブラリです。

このリポジトリは pre-alpha です。実機挙動は Bluetooth adapter、driver、対象機器の firmware に依存します。

## 必要なもの

- Python 3.12 以降
- uv
- Bumble が利用可能な専用 USB Bluetooth dongle

## インストール

```powershell
pip install swbt-python
```

開発中の checkout では次を使います。

```powershell
uv sync --dev
```

## 最小利用例

```python
import asyncio
from swbt import Button, SwitchGamepad


async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.tap(Button.A)
        await pad.neutral()


asyncio.run(main())
```

この例は adapter open、HID advertising、pairing または reconnect、periodic report loop、入力送信を行います。実行前に、使う adapter、command、trace 保存先、cleanup 手順を確認してください。

## 実機検証の状態

実機観測の正本は `docs/hardware-test-log.md` です。README には release 前に必要な利用者向け要約だけを書きます。

### 確認済み構成

2026-07-03 時点で、次の構成は pairing、L2CAP、subcommand 応答、Button A 入力、neutral 後の入力残りなしを確認済みです。

| 項目 | 値 |
|---|---|
| OS | Windows 11 |
| Bluetooth dongle | CSR8510 A10 |
| driver | WinUSB / libwdi |
| adapter | `usb:0` |
| Python | 3.13.5 |
| Bumble | Bumble 0.0.230 |
| 入力反映 | 2026-07-02 に Button A が対象機器 UI に反映し、neutral 後の入力残りなしを目視確認 |

この結果は上記構成での観測です。対象機器の model / firmware は未記録のため、別 firmware での保証には使いません。

### 未確認構成

- Linux / libusb permission と udev rule。
- macOS。
- CSR8510 A10 以外の Bluetooth dongle。
- pairing-free incoming bond reuse。
- 対象機器 model / firmware 差分。

## Bluetooth adapter と driver

- Bumble から開く adapter は専用 USB Bluetooth dongle にしてください。OS 標準 Bluetooth stack が使っている adapter を共有しないでください。
- Windows では確認済み構成が WinUSB / libwdi です。標準 driver のままでは Bumble から開けない場合があります。
- Linux は libusb 権限設定が必要になる想定ですが、この repo ではまだ未検証です。
- `swbt-probe adapters --help` と `swbt-probe pair --help` は、adapter と実機操作の確認用 CLI surface です。adapter open や Switch-facing 動作を実行する前に、会話上の明示承認、対象 adapter、command、cleanup plan を揃えてください。

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

MIT です。詳細は `LICENSE` を参照してください。

## 非提携

このプロジェクトは、対象機器や関連商標の権利者から承認、後援、提携を受けたものではありません。
