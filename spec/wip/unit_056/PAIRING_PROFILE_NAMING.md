# Pairing Profile 命名整理

## 1. 概要

### 1.1 目的

ローカル Bluetooth アドレスと pairing key を保存するプロファイルから、意味を説明しない `ExpLocal` / `exp_local` 接頭辞を取り除く。保存物の役割を `PairingProfile`、アダプター側の準備を `adapter identity` として表す。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | 命名を実験状態ではなく役割で表す | #99 |
| API contract | `create_profile()` と `profile_path` の公開契約 | `spec/initial/api.md` |
| lifecycle | adapter identity 準備の順序 | `spec/initial/lifecycle.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 利用者 | `create_profile(local_address=...)` | ローカルアドレスと pairing key を保存して初回 pairing を開始できる | 保存 JSON は既存形式 |
| runtime | profile path を指定して open | adapter identity を準備してから transport を開く | HID / Bumble の順序は不変 |

## 2. 対象範囲

- `PairingProfile`、`LocalAddress`、`AdapterIdentityRecoveryRequired` への Python 識別子変更。
- `local_address` を `create_profile()` の公開キーワード引数にする。
- adapter identity 準備、診断イベント、内部モジュール、test 名、公開文書の用語を更新する。
- profile の controller shape が ReportingMode を含む設計の見直しは unit_057 で扱う。この実装では、両方の変更を一つの互換性レビューとして統合する。

## 3. 対象外

- JSON のキー、`identity.kind: "exp-local-address"`、schema version を変更しない。
- HID report、Bumble adapter 操作、pairing 手順を変更しない。
- controller shape と reporting mode のデータモデル変更は unit_057 で扱う。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/risks.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report byte と生成規則を変更しない |
| Bumble / transport | not applicable | not applicable | adapter を開く順序と Bumble API 呼び出しを変更しない |
| OS / driver / adapter | not applicable | not applicable | 名前だけを変更する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile 作成 | `local_address` | individual / locally administered address を検査し、新規 JSON を作成する | JSON payload は従来互換 |
| profile 再利用 | profile path | ローカルアドレスを読み、adapter identity を準備する | 従来と同じ順序 |
| 書換え不確実 | write 開始後の失敗 | `AdapterIdentityRecoveryRequired` を送出する | 従来と同じ復旧指示 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| implemented / smoke passed | `local_address` で作成した profile が従来の JSON payload を保存・読み込みできる | regression | unit | no | system Python の smoke test で確認。pytest は環境遮断 |
| implemented / blocked | adapter identity 準備失敗が新しい例外型で復旧を要求する | regression | unit | no | adapter は開かない fake session。pytest は環境遮断 |
| implemented / blocked | concrete controller が `local_address` で profile を作成して再利用できる | regression | integration | no | fake transport。pytest は環境遮断 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| API / usage / hardware docs | profile の作成と再利用 | 本仕様 §6、実装 | `uv run mkdocs build --strict` | manual pass / build blocked | `uv` cache が read-only |
| release notes / agent brief | 例外名と用語 | 本仕様 §6、実装 | link / build | manual pass / build blocked | `uv` cache が read-only |

## 9. 設計メモ

- `PairingProfile` は profile 内の JSON `identity.kind` を表す型名ではなく、pairing 情報を再利用する保存物の役割を表す。
- JSON の `exp-local-address` は既存プロファイル互換の識別子であり、Python の命名整理の対象外とする。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_pairing_profile.py` | rename / modify | profile と address 型の役割名化 |
| `src/swbt/transport/_adapter_identity.py` | rename / modify | adapter identity 準備の役割名化 |
| `src/swbt/gamepad/` | modify | public API と runtime の用語更新 |
| `src/swbt/errors.py` | modify | 復旧例外の改名 |
| `tests/` | rename / modify | 新名称の回帰検証 |
| `docs/`, `spec/initial/`, `examples/` | modify | 利用者向け用語更新 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `git diff --check` | passed | whitespace error なし |
| `PYTHONPYCACHEPREFIX=/tmp/swbt-pycache python -m compileall -q src tests examples` | passed | syntax compile |
| pairing profile normalization smoke test | passed | 新規 `joycon_l` 保存と旧 `direct_pro` の正規化 |
| `uv run ruff format --check .` | blocked | `uv` が `/root/.local/share/uv/python` へ書き込めない |
| `uv run ruff check .` | blocked | 同上 |
| `uv run ty check --no-progress` | blocked | 同上 |
| `uv run pytest tests/unit` | blocked | 同上。Bumble を含む依存が未導入 |
| `uv run pytest tests/integration` | blocked | 同上 |
| `uv run mkdocs build --strict` | blocked | 同上 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | 実機・adapter を開く操作は行わない |
| adapter | not applicable |
| 実行遮断 | 環境変数による実行遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | not applicable |
| cleanup | not applicable |

## 13. 先送り事項

- ReportingMode 分類の削除は unit_057 で扱う。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
