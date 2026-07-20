# EXP_LOCAL_ADDRESS_PROFILE_DIRECT 仕様書

## 1. 概要

### 1.1 目的

unit_052 の exp profile 経路を、periodic report loop を持たない `DirectProController`、`DirectJoyConL`、`DirectJoyConR` へ拡張する。identity preparation と pairing key の境界は periodic controller と共有し、Direct 固有の input send semantics を変えない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| unit_052 | profile envelope、CSR preparation、ProController の基盤 | `spec/complete/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md` |
| unit_053 | Joy-Con の controller kind と profile 分離 | `spec/wip/unit_053/EXP_LOCAL_ADDRESS_PROFILE_JOYCON.md` |
| 初期公開 API | Direct controller の constructor / send / close lifecycle | `spec/initial/api.md` |
| 初期 lifecycle | Direct は periodic task を持たない | `spec/initial/lifecycle.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Direct Pro 利用者 | 新規 Pro direct profile | target identity で pairing し、`send()` を既存どおり使える | unit_052 の完了後 |
| Direct Joy-Con 利用者 | left / right direct profile | controller kind に一致する profile で接続できる | unit_053 の kind contract を継承 |
| periodic / direct 境界 | 同じ profile を別 reporting type へ渡す | adapter open 前に controller kind mismatch error | pairing key を共有しない |

## 2. 対象範囲

- `DirectProController`、`DirectJoyConL`、`DirectJoyConR` の `profile_path` と `create_profile()`。
- direct controller kind と profile kind の一致検査。
- unit_052 の raw preparation、Bumble guard、KeyStore adapter の再利用。
- Direct controller ごとの手動実機 gate。

## 3. 対象外

- periodic / direct 間の profile 共有または自動変換。
- Direct の `send()`、state commit、input operation lock、neutral fail-safe の意味変更。
- profile から reporting type を動的に選択する API。
- CSR8510 A10 以外の adapter 互換性。

## 4. 関連 docs

- `spec/complete/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md`
- `spec/wip/unit_053/EXP_LOCAL_ADDRESS_PROFILE_JOYCON.md`
- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | Direct report layout / send semantics は既存実装を変更しない |
| Bumble / transport | required | inherited | unit_052 の preparation / handoff を共有する |
| Direct lifecycle | required | todo | profile preparation が Direct の periodic task 不在を変えないことを unit / integration test で固定する |
| OS / driver / adapter | required | hardware-observed only | controller kind ごとに既知構成の manual gate を行う |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Direct profile 作成 | 新規 path、valid address | concrete Direct controller の kind を保存し、target identity で pairing を開始する | unit_052 preparation を共有 |
| Direct profile 利用 | profile kind が concrete class と一致 | target guard 後に Direct transport を open する | report loop を作らない |
| kind mismatch | DirectPro / DirectJoyCon に別 kind profile | adapter open 前に失敗する | raw write / pairing を開始しない |
| direct input | profile 接続後の `send()` / `tap()` / `neutral()` | 既存の送信成功後 commit を維持する | identity feature は入力状態へ影響しない |
| close / retry | pairing failure または通常 close | unit_052 と同じ retry / target 継続利用 | periodic task を停止しようとしない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | DirectPro profile は `direct_pro` kind を保存する | regression | integration | no | `test_direct_create_profile_saves_kind_and_leaves_profile_for_retry` |
| done | DirectJoyConL/R profile は対応する direct kind を保存する | regression | integration | no | `test_direct_create_profile_saves_kind_and_leaves_profile_for_retry` |
| done | Direct controller と profile kind の不一致は adapter open 前に失敗する | edge | unit | no | `test_direct_profile_kind_mismatch_stops_before_preparation_and_transport_creation` |
| done | Direct profile の preparation は report loop を作らない | regression | integration | no | Direct profile retry integration が `_report_loop is None` を確認 |
| done | Direct profile の `send()` は成功後 commit を維持する | regression | integration | no | `test_direct_send_waits_for_transport_and_commits_exactly_one_report` |
| done | DirectPro の profile 作成、pairing、通常 close 後の再利用を確認する | characterization | hardware | yes | 2026-07-21 unit_054 で pass |
| done | DirectJoyConL/R の同じ確認を行う | characterization | hardware | yes | 2026-07-21 unit_054 で pass |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/api.md` | Direct profile API | 本仕様 §6 | `uv run mkdocs build --strict` | done | なし |
| `spec/initial/lifecycle.md` | Direct preparation と close | 本仕様 §6 | `uv run mkdocs build --strict` | done | なし |

## 9. 設計メモ

- profile kind は `direct_pro`、`direct_joycon_l`、`direct_joycon_r` を区別する。periodic profile を Direct controller へ渡すことは許可しない。
- controller kind は Switch の Bluetooth address そのものではない。profile / pairing key を異なる HID reporting type 間で混在させないための swbt 側 contract である。
- raw preparation は Direct の `open()` より前に終える。Direct の report loop 不在は identity preparation の再利用を妨げない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/core.py` | modify | Direct concrete controller の profile entry point |
| `src/swbt/transport/_exp_local_address.py` | modify | direct controller kind validation |
| `tests/unit/test_exp_local_address.py` | modify | direct kind codec / mismatch |
| `tests/integration/test_exp_local_profile.py` | modify | Direct lifecycle と send semantics |
| `spec/initial/api.md` | modify | 完了時の Direct profile API 反映 |
| `spec/initial/lifecycle.md` | modify | Direct preparation / close の記述 |
| `spec/hardware-test-log.md` | modify | 実機 gate 実行時だけ追記 |

## 11. 検証

| command | result | notes |
|---|---|---|
| unit_052 / unit_053 の gate | pass | profile foundation と Periodic Joy-Con profile gate は完了 |
| `uv run pytest tests/unit` | pass | profile-only 移行後に 454 passed |
| `uv run pytest tests/integration` | pass | profile-only 移行後に 131 passed |
| Direct controller 手動 gate | pass | 2026-07-21 unit_054。Direct Pro / Joy-Con L / Joy-Con R の fresh pairing、`send()`、active reconnect、neutral close を記録 |
| `uv run mkdocs build --strict` | pass | profile-only 移行後 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for completion |
| 承認範囲 | 専用 adapter open、CSR volatile write、warm reset、Direct HID advertising、pairing / reconnect、`send()`、neutral、close |
| adapter | 専用 `usb:0` / CSR8510 A10 / WinUSB。実行直前に再確認する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md` に controller kind、Switch model / firmware、trace、cleanup を記録する |
| cleanup | unit_052 の規則を継承する |

## 13. 先送り事項

- periodic / Direct 間で同じ Bluetooth identity を安全に共有できるかの検証は別 Issue で扱う。
- Direct と periodic を切り替える profile migration は提供しない。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] unit_052 / unit_053 の完了を確認した
- [x] 実装と unit / integration gate を完了した
- [x] Direct controller 手動 gate を完了した
- [x] 初期設計と公開文書の Intent Delta を反映した
