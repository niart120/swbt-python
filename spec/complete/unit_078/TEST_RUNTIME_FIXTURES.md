# runtime 中継 property の test fixture 移動

## 1. 概要

`SwitchGamepad` が test や hardware probe のためだけに runtime 内部を再公開する
private property を削除する。内部観測が必要な test は `tests/gamepad_factory.py` の
明示的 helper だけを使用する。

## 2. 起点 / source

| source | 内容 |
|---|---|
| GitHub Issue #130 | runtime 中継 property を test fixture へ移す |
| `spec/initial/architecture.md` | public API と runtime の責務境界 |
| `spec/initial/testing.md` | fake transport と hardware test の分離 |

## 3. 対象範囲

- `SwitchGamepad._state_store` と `_output_report_dispatcher` を削除する。
- deterministic race test と controller colors probe の内部参照を test helper へ移す。
- 不要になる production import を削除する。

## 4. 対象外

- `_runtime` の公開または削除。
- runtime private field 名の安定契約化。
- public diagnostics API、fake transport の production 配置、hardware 観測内容の変更。

## 5. 根拠監査

| 項目 | 状態 | 理由 |
|---|---|---|
| Switch HID / report bytes | not applicable | protocol と report を変更しない |
| Bumble / adapter | not applicable | hardware test の観測口だけを test 側へ移す |
| public / test boundary | done | Issue #130、interface、test fixture の参照を照合した |

## 6. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `SwitchGamepad` が runtime 内部を中継しない | regression | unit | no | red: property が存在するため失敗、green: 削除後に成功 |
| green | deterministic race test が test fixture 経由で state lock を取得できる | characterization | integration | no | 既存 test を維持する |
| green | controller colors probe が test fixture 経由で dispatcher を置換できる | characterization | hardware collect-only | no | collect-only で import / fixture を確認する |
| refactor-done | 6具象 controller の公開 API と fake transport 契約を維持する | regression | unit / integration | no | full gate で確認した |

## 7. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | `hardware` marker は実行せず collect-only に限定する |
| 完了 gate | unit / integration / hardware collect-only |

## 8. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_api_boundary.py -q -k "does_not_reexpose_runtime_internals"` | red → pass | property 存在時に失敗し、削除後に成功した |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q -k "concurrent_press_waiting_on_state_lock_uses_latest_state"` | pass | fixture 経由の state lock 観測を確認した |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 440 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `uv run pytest tests/hardware --collect-only -q` | pass | 33 tests collected。実機操作なし |
| private seam residue search | pass | production の中継 property と pad 経由の参照は 0件 |
| `git diff --check` | pass | whitespace error なし |

## 9. 先送り事項

- none

## 10. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 根拠監査の要否を確認した
- [x] 実機実行条件を記録した
- [x] 検証結果を記録した
- [x] complete へ移動した
