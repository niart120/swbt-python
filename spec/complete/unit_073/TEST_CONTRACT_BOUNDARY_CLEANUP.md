# テスト契約境界の整理 仕様書

## 1. 概要

### 1.1 目的

Issue #119 に従い、公開挙動・構造化された根拠データを検証するテストを残し、内部クラス名・private field・実装順序・自然言語の特定語句を固定する assertion を削除する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #119 | テスト契約の整理と完了条件 | `https://github.com/niart120/swbt-python/issues/119` |
| project guide | 自然言語の意味要件を固定語句 assertion にしない方針 | `AGENTS.md` |
| 初期設計 | unit / fake transport integration の責務境界 | `spec/initial/testing.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 公開 API boundary | controller の公開 export、signature、型、例外 | 公開契約の回帰を検出する | private class / field / owner type は固定しない |
| source audit fixture | TOML の entry | ID、分類、status、source、handoff、hardware condition の構造を検証する | `value` / `condition` の自然言語断片は検証しない |
| fake transport integration | connection、report、trace、exception、cleanup | 観測可能な protocol / lifecycle を検証する | production private field を probe seam にしない |

## 2. 対象範囲

- `tests/unit/test_public_api_boundary.py` の内部構造 assertion を削除または公開挙動 assertion へ整理する。
- transport factory の private factory class 不在 assertion を削除する。
- `tests/unit/test_source_audit_fixtures.py` を構造化 field の検査へ限定する。
- fake/integration test の runtime/config/state private field 直接参照を test fixture 境界または公開観測へ移す。
- unit 仕様を `spec/complete/unit_073/` へ移し、検証結果を記録する。

## 3. 対象外

- public API export、signature、return type、例外、report、trace、cleanup の削除。
- protocol byte fixture、source path、hardware observation の根拠データ削除。
- production package への test-only seam 追加。
- snapshot test の大量導入。
- Bumble adapter、Switch pairing、HID advertising、report loop の実機実行。

## 4. 関連 docs

- `AGENTS.md`
- `spec/initial/testing.md`
- `spec/initial/architecture.md`
- `spec/initial/risks.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | byte fixture と protocol test は変更しない |
| Bumble / transport | not applicable | not applicable | transport 実装と adapter behavior は変更しない |
| OS / driver / adapter | not applicable | not applicable | 実機・adapter を使わない |
| source audit fixture schema | required | done | TOML entry の機械的構造だけを検査する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| 公開境界 | 公開 controller / reporting type | export、継承、signature、公開 method の契約を検証する | private implementation identity は検証しない |
| source audit 構造 | entry の ID、分類、status、source、handoff | 許容値、重複、型、非空を検証する | 説明文の正しさは review と正本照合で扱う |
| hardware observation 構造 | classification が hardware observation | status と condition が存在する | condition の単語列は固定しない |
| fake/integration lifecycle | fake transport で接続・入力・失敗・cleanup | report、state、trace、exception の観測結果を維持する | private runtime field は fixture 内へ閉じる |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | 公開 boundary test が内部 class / field / owner type を固定しない | regression | unit | no | 公開 export/signature/behavior は維持 |
| refactor-done | source audit test が構造化 field と参照形式だけを検証する | regression | unit | no | 自然言語断片 assertion を削除 |
| refactor-done | fake/integration test が private runtime seam を直接 probe しない | regression | integration | no | race 制御は test fixture 境界へ移動 |

## 8. 文書検証計画

公開文書を変更しないため `not applicable`。作業仕様自身は checklist、gate 結果、未検証範囲を機械的に確認する。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| 作業仕様 | maintainer / test contract | Issue #119, `AGENTS.md` | path / checklist / diff review | done | none |

## 9. 設計メモ

- `value` と `condition` は source audit の説明本文であり、特定の言い換えを拒否する assertion を持たない。
- source path / URL は形式と非空を検査するが、外部 source の本文を pytest で再検証しない。
- race test の deterministic control は `tests/gamepad_factory.py` の明示的な test fixture 境界に置く。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tests/unit/test_public_api_boundary.py` | modify | private structure assertion の整理 |
| `tests/unit/test_gamepad_transport_factory.py` | modify | private factory class assertion の削除 |
| `tests/unit/test_source_audit_fixtures.py` | modify | schema / reference structure のみ検証 |
| `tests/integration/test_pairing_profile.py` | modify | private runtime field 参照を公開観測へ変更 |
| `tests/unit/test_pairing_profile_runtime.py` | modify | open/close 経路で profile preparation を検証 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | state lock access を fixture helper 経由へ変更 |
| `tests/gamepad_factory.py` | modify | race-test 用 explicit fixture boundary |
| `spec/complete/unit_073/TEST_CONTRACT_BOUNDARY_CLEANUP.md` | new | 完了記録 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_api_boundary.py tests/unit/test_gamepad_transport_factory.py tests/unit/test_gamepad_config.py tests/unit/test_source_audit_fixtures.py tests/integration/test_pairing_profile.py tests/unit/test_pairing_profile_runtime.py tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 198 passed |
| `uv sync --dev` | pass | 53 packages resolved, 41 checked |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | all checks passed |
| `uv run ty check --no-progress` | pass | all checks passed |
| `uv run pytest tests/unit` | pass | 439 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `git diff --check` | pass | no whitespace errors |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | adapter、Bumble、Switch-facing command は実行しない |
| adapter | none |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | none |
| cleanup | pytest が作成した一時ファイルのみ通常の test cleanup |

## 13. 先送り事項

- none

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
