# 05. 完了記録と保守チェックリスト

この文書セットで計画したリアーキテクチャは完了している。移行途中のクラス、内部設定型、テスト用の差し替え境界は現行構造の目標ではない。実装時の詳細は各完了作業単位を証跡として参照する。

| 対象 | 完了作業単位 |
|---|---|
| 公開コントローラーの構成 | unit_038, unit_040 |
| 実行状態と生成経路 | unit_039, unit_041, unit_071, unit_072, unit_074 |
| 下位通信実装の境界とプロファイル分割 | unit_042, unit_043, unit_073 |
| 具象コントローラーのモジュール | unit_075 |
| 文書と実機記録 | unit_044, unit_076 |

## 現在の保守チェックリスト

構造変更を行う場合は、次を確認する。

- 具象コントローラーは `controllers.py`、共通公開操作は `interface.py`、状態を持つ処理は `runtime.py` に置かれている。
- 具象コントローラーと共通公開操作を、責務を表さない単一モジュールへ再集約しない。
- 公開コンストラクターに `profile`、`device_name`、`transport` を追加しない。
- プロファイル型、下位通信実装の型、テスト補助を `swbt` モジュール直下から公開しない。
- 擬似通信実装の差し替えは `tests/gamepad_factory.py` に閉じ込める。
- `ControllerKind` の分岐をプロファイル生成とテスト以外へ増やさない。
- 公開 API と docs を変更する場合は、`spec/initial/` と `docs/` を同時に照合する。

## 検証

構造変更では、少なくとも次を実行する。

```console
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run ty check --no-progress
uv run pytest tests/unit
uv run pytest tests/integration
```

Bumble のアダプタまたは対象機器を使う検証は、このチェックリストだけを理由に実行しない。実行には別途、対象アダプタ、Switch に対する動作、終了後の復帰手順を含む明示承認が必要である。
