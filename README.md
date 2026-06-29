# swbt-python

NX 向けの仮想 Bluetooth HID 入力デバイスを Python から扱うためのライブラリです。

このリポジトリは初期再構築中です。実装面はまだ最小限で、設計メモは `spec/initial` に置いています。

## 必要なもの

- Python 3.12 以降
- uv
- Bumble が利用可能な USB Bluetooth アダプター

## 実機検証の状態

確認済み構成はまだありません。Bumble adapter、pairing、入力反映の結果は未記録です。

未検証構成は `docs/hardware-test-log.md` の matrix で管理します。README には、release 前に同 matrix から確認済み構成と未確認構成を反映します。

## 開発

```powershell
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run ty check --no-progress
uv run pytest
```

## ライセンス

MIT です。詳細は `LICENSE` を参照してください。

## 非提携

このプロジェクトは、対象機器や関連商標の権利者から承認、後援、提携を受けたものではありません。
