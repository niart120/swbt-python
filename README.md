# swbt-python

NX 向けの仮想 Bluetooth HID 入力デバイスを Python から扱うためのライブラリです。

このリポジトリは初期再構築中です。実装面はまだ最小限で、設計メモは `spec/initial` に置いています。

## 必要なもの

- Python 3.12 以降
- uv
- Bumble が利用可能な USB Bluetooth アダプター

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
