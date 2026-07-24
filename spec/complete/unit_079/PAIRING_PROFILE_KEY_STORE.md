# pairing profile key store の単一実装化

## 概要

current / previous 世代を扱う pairing profile key store を、継承ではなく
`_PairingProfileKeyStore` 1個に統合する。profile JSON、diagnostics、Bumble の
key-store 初期化経路は維持する。

## 起点

| source | 内容 |
|---|---|
| GitHub Issue #131 | profile key store を単一実装へ統合する |
| `spec/initial/transport-bumble.md` | pairing profile と Bumble transport の境界 |
| `spec/initial/testing.md` | fake transport / profile test による検証 |

## 対象範囲

- current / previous 世代管理を単一 production class に統合する。
- 固定 namespace と adapter-default の遅延 namespace resolver を同じ class が所有する。
- diagnostics wrapper の generation 判定を統合後の class に追従させる。

## 対象外

- profile schema、保存形式、previous からの復元 API、reconnect fallback、key material 暗号化。
- Bumble dependency と実機操作。

## 根拠監査

| 項目 | 状態 | 理由 |
|---|---|---|
| Bumble key-store contract | implementation fact | 既存の `_PairingProfileNamespaceStore` API と Bumble transport unit test を維持する |
| profile JSON / diagnostics | done | 既存 integration / unit test を characterization baseline にする |
| HID / adapter / hardware | not applicable | report、adapter lifecycle、実機操作を変更しない |

## TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | 初回 update は current のみを保存する | characterization | integration | no | 既存 profile test を維持する |
| refactor-done | overwrite は直前 current を previous namespace へ1世代だけ退避する | characterization | integration | no | profile JSON 形式を維持する |
| refactor-done | adapter-default namespace と Bumble transport 初期化を維持する | regression | unit / integration | no | 既存 Bumble transport test を維持する |
| refactor-done | diagnostics の generation / previous_saved field を維持する | regression | unit | no | Bumble transport unit test を含む full gate で確認した |

この unit は既存の観測可能な契約を変えない構造変更である。新規の人工的 red test は
追加せず、既存の current / previous / namespace / diagnostics test を baseline とする。

## 実機実行条件

not required。Bumble adapter、pairing、HID advertising は実行しない。

## 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/integration/test_pairing_profile.py -q -k "profile_key_store"` | pass | 1 passed。current / previous profile JSON を確認した |
| `uv run pytest tests/unit/test_bumble_transport.py -q -k "profile_key_store or adapter_default_key_store or key_store_update_failure"` | pass | 2 passed。Bumble 初期化と diagnostics を確認した |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 440 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `git diff --check` | pass | whitespace error なし |

## 先送り事項

- none
