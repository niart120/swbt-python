# Pairing Profile から ReportingMode 分類を除去

## 1. 概要

### 1.1 目的

pairing profile の `controller_kind` から、入力レポートの送信方式を表す `direct_*` 分類を削除する。Periodic / Direct は runtime の送信セマンティクスであり、local address と pairing key を保存する profile のアイデンティティではない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | profile から ReportingMode 分類を廃止する | #100 |
| protocol profile | controller の形状を表す既存 `ControllerKind` | `src/swbt/protocol/profiles/base.py` |
| API contract | Periodic / Direct の送信セマンティクス | `spec/initial/api.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Direct / Periodic Pro Controller | 同じ Pro profile path | controller shape が一致すれば両方で profile を開ける | input 送信方式は各 runtime のまま |
| 以前の Direct profile | `controller_kind: "direct_pro"` | adapter open 前に未対応値として失敗する | 別の profile path で作成し直し、再ペアリングする |
| Joy-Con / Pro | 異なる controller shape の profile | adapter open 前に不一致として拒否する | profile 混在は許可しない |

## 2. 対象範囲

- `PairingProfile.controller_kind` に既存 `ControllerKind` を使う。
- 新規保存は `pro` / `joycon_l` / `joycon_r` だけを出力する。
- `direct_pro` / `direct_joycon_l` / `direct_joycon_r` を含む既存 profile との互換性は提供しない。新しい profile を作成して再ペアリングする。
- Runtime config と concrete controller から ReportingMode を含む profile kind を削除する。
- 同一 controller shape の Direct / Periodic が同じ profile を受け付けることを fake transport test で固定する。

## 3. 対象外

- JSON のキー、`identity.kind: "exp-local-address"`、schema version を変更しない。
- 旧 `direct_*` 値を判別する専用の migration / rejection 分岐は追加しない。未対応の `controller_kind` として既存の検証で扱う。
- Periodic の周期送信、Direct の送信成功後 commit、HID report、Bumble adapter 操作を変更しない。
- Direct / Periodic 間の同一 profile を使う実機接続は、この変更では実行しない。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | input report の構造・送信処理を変更しない |
| Bumble / transport | not applicable | not applicable | adapter identity と key store の API 呼び出しを変更しない |
| OS / driver / adapter | not applicable | not applicable | 実機挙動の保証は追加しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile 作成 | Pro / Joy-Con concrete controller | protocol profile の `ControllerKind` を保存値へ変換する | direct prefix を出力しない |
| 既存 Direct profile の load | 旧 direct kind | `InvalidProfileError` で adapter open 前に失敗する | profile を別 path に作り直して再ペアリングする |
| cross-mode reuse | 同じ shape の Direct / Periodic | profile kind mismatch を起こさない | fake transport で検証 |
| shape mismatch | Pro profile を Joy-Con で開く | adapter open 前に `ProfileControllerMismatchError` | 既存保護を維持 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| implemented / CI passed | 新規 profile が ReportingMode を含まない controller shape を保存する | regression | unit | no | 新規保存は `pro` / `joycon_l` / `joycon_r`。GitHub Actions CI #142 で確認 |
| implemented / CI passed | 旧 direct kind を持つ JSON が未対応値として adapter open 前に失敗する | regression | unit | no | `direct_*` を特別扱いせず、既存の `controller_kind` 検証で拒否。GitHub Actions CI #142 で確認 |
| implemented / CI passed | 同じ controller shape の periodic / direct が profile を相互利用できる | regression | unit | no | runtime guard test を追加。GitHub Actions CI #142 で確認 |
| implemented / CI passed | controller shape が異なる profile は adapter open 前に拒否される | regression | unit | no | `ControllerKind` 比較の guard を GitHub Actions CI #142 で確認 |
| deferred | Direct / Periodic 間 profile 再利用の実機 pairing / reconnect | characterization | hardware | yes | 明示承認と専用 adapter が必要 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| API / usage / hardware docs | profile の再利用範囲 | 本仕様 §6、test | `uv run mkdocs build --strict` | GitHub Actions Docs #99 passed | 実機共有は未検証 |

## 9. 設計メモ

- `ControllerKind` は protocol profile が持つ controller shape の enum であり、PairingProfile が必要とする意味と一致する。
- direct / periodic は PairingProfile に保存しない。profile 読み込み時の guard は runtime config の `ControllerProfile.kind` と比較する。
- `direct_*` は未対応の `controller_kind` と同じ扱いである。既存 profile の読み込み互換、migration、schema version 更新は行わず、利用者が別 path に profile を作成して再ペアリングする。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_pairing_profile.py` | modify | `ControllerKind` 化と shape-only の値だけの受理 |
| `src/swbt/gamepad/_config.py` | modify | profile kind config の削除 |
| `src/swbt/gamepad/core.py` | modify | direct / periodic 共通の shape 利用 |
| `src/swbt/gamepad/runtime.py` | modify | protocol profile の kind による guard |
| `tests/` | modify | legacy / cross-mode / mismatch 回帰 |
| `docs/`, `spec/initial/` | modify | profile 共有範囲の説明 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `git diff --check` | passed | whitespace error なし |
| `PYTHONPYCACHEPREFIX=/tmp/swbt-pycache python -m compileall -q src tests examples` | passed | syntax compile |
| GitHub Actions CI #142 | passed | 新規 shape-only 値の保存と `direct_*` の未対応扱いを含む unit / integration test |
| `ruff 0.15.20 format --check .` | passed | CI と同じ Ruff version を一時領域で実行 |
| `ruff 0.15.20 check .` | passed | CI と同じ Ruff version を一時領域で実行 |
| `uv run ty check --no-progress` | blocked | 同上 |
| `uv run pytest tests/unit` | blocked | 同上。Bumble を含む依存が未導入 |
| `uv run pytest tests/integration` | blocked | 同上 |
| `uv run mkdocs build --strict` | blocked | 同上 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for deferred characterization |
| 承認範囲 | dedicated adapter open、target Switch pairing、active reconnect、normal close |
| adapter | 実行直前に確認する専用 adapter |
| 実行遮断 | 環境変数による実行遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md` に環境、command、result、cleanup を記録する |
| cleanup | normal close 後に dedicated adapter を切り離す |

## 13. 先送り事項

- Direct / Periodic 間での実機 pairing / reconnect は hardware characterization として別途実行する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
