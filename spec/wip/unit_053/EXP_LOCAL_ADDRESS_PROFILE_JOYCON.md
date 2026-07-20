# EXP_LOCAL_ADDRESS_PROFILE_JOYCON 仕様書

## 1. 概要

### 1.1 目的

unit_052 の `ProController` exp profile 経路を、`JoyConL` と `JoyConR` へ拡張する。各 Joy-Con は対応する controller kind を持つ profile だけを開き、profile の取り違えを adapter open 前に拒否する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| unit_052 | profile envelope、CSR preparation、ProController の基盤 | `spec/wip/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md` |
| 初期公開 API | JoyConL / JoyConR の公開 constructor と lifecycle | `spec/initial/api.md` |
| Joy-Con 実機観測 | Joy-Con L/R の既存 pairing / input 観測 | `spec/hardware-test-log.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| JoyConL 利用者 | 新規 left profile と `exp_local_address` | Joy-Con L として初回 pairing できる | unit_052 完了後、既知 CSR8510 A10 構成で確認 |
| JoyConR 利用者 | 既存 right profile | target identity で reconnect / pairing を再試行できる | Joy-Con L profile は使えない |
| profile 読込 | controller kind 不一致 | adapter を開かず profile mismatch error | pairing key を混在させない |

## 2. 対象範囲

- `JoyConL` / `JoyConR` の `profile_path` と `create_profile()`。
- profile envelope に controller kind を保存し、`pro` / `joycon_l` / `joycon_r` の不一致を検査する。
- unit_052 の raw CSR preparation、Bumble guard、KeyStore adapter の共通利用。
- Joy-Con L/R ごとの必須手動実機 gate。

## 3. 対象外

- unit_052 が未完了の状態での実装開始。
- `ProController` profile を Joy-Con profile として自動変換すること。
- Joy-Con L/R の二台を一つの controller として束ねる API。
- Joy-Con と Pro Controller の同一 profile / pairing key の共有。
- CSR8510 A10 以外の adapter 互換性。

## 4. 関連 docs

- `spec/wip/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md`
- `spec/initial/api.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/risks.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | unit_052 の identity profile 拡張であり、Joy-Con report layout は変更しない |
| Bumble / transport | required | inherited | unit_052 で確立する raw preparation / Bumble handoff を再利用する |
| controller kind と key store | required | todo | 異なる HID profile の pairing key を同じ envelope に混在させない contract を unit test で固定する |
| OS / driver / adapter | required | hardware-observed only | CSR8510 A10 / WinUSB の既知構成で Joy-Con L/R を各々確認する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Joy-Con profile 作成 | 新規 path、valid local address | controller kind を `joycon_l` または `joycon_r` として保存し、pairing を開始する | target identity 準備は unit_052 を共有 |
| profile 利用 | kind が concrete controller と一致 | current / target に応じて unit_052 の preparation を実行し、接続へ進む | address 再指定は不要 |
| kind mismatch | JoyConL へ `joycon_r` / `pro` profile を渡す | adapter open 前に専用 profile mismatch error | raw write を送らない |
| profile 分離 | 左右または Pro と同じ path を使おうとする | profile kind mismatch または既存 path error | pairing key を混在させない |
| close / retry | pairing failure または通常 close | unit_052 と同じ再試行・volatile target 継続利用 | Joy-Con 固有の recovery を追加しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| deferred | JoyConL の新規 profile は `joycon_l` kind を保存する | new | unit | no | unit_052 の envelope codec に依存 |
| deferred | JoyConR の新規 profile は `joycon_r` kind を保存する | new | unit | no | 同上 |
| deferred | Joy-Con と異なる kind の profile は adapter open 前に失敗する | edge | unit | no | raw preparation を呼ばない |
| deferred | Joy-Con profile は unit_052 と同じ target guard / recovery-required を使う | regression | integration | no | transport handoff の共有を確認 |
| deferred | JoyConL の profile 作成、pairing、通常 close 後の再利用を確認する | characterization | hardware | yes | 完了必須 |
| deferred | JoyConR の profile 作成、pairing、通常 close 後の再利用を確認する | characterization | hardware | yes | 完了必須 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/api.md` | Joy-Con profile API | 本仕様 §6 | link / code example 構文確認 | deferred | unit_052 / 本 unit 完了後に `docs-quality-review` |
| `spec/initial/risks.md` | controller kind 分離 | 本仕様 §2、§3 | link 確認 | deferred | 実機 gate 後に確認済み範囲を記録 |

## 9. 設計メモ

- profile envelope の controller kind は unit_052 の schema version 1 に含める。unit_052 がまだ未実装であるため、schema version を後から移行させずに済む。
- 同じ `exp_local_address` を別 profile で同時に使わないことは利用者の責任とする。ただし controller kind が異なる profile path の共有は拒否する。
- Joy-Con 固有 HID identity が Switch の既存登録とどう相互作用するかは未検証であり、各 side の手動 gate を省略しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/core.py` | modify | JoyConL / JoyConR の profile entry point |
| `src/swbt/transport/_exp_local_address.py` | modify | controller kind schema validation |
| `tests/unit/test_exp_local_address.py` | modify | kind mismatch と Joy-Con profile codec |
| `tests/integration/test_exp_local_profile.py` | modify | Joy-Con retry lifecycle |
| `spec/initial/api.md` | modify | 完了時の Joy-Con API 反映 |
| `spec/hardware-test-log.md` | modify | 実機 gate 実行時だけ追記 |

## 11. 検証

| command | result | notes |
|---|---|---|
| unit_052 の unit / integration gate | deferred | unit_052 完了が前提 |
| `uv run pytest tests/unit` | deferred | 実装後 |
| `uv run pytest tests/integration` | deferred | 実装後 |
| Joy-Con L/R 手動 gate | deferred | 明示承認が必要 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for completion |
| 承認範囲 | 専用 adapter open、CSR volatile write、warm reset、Joy-Con L/R の HID advertising、pairing / reconnect、neutral、close |
| adapter | 専用 `usb:0` / CSR8510 A10 / WinUSB。実行直前に再確認する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md` に side、Switch model / firmware、trace、cleanup を記録する |
| cleanup | unit_052 の規則を継承する |

## 13. 先送り事項

- Joy-Con Pair API は別 unit で扱う。
- controller kind の将来拡張値と schema migration は、version 1 公開後に必要になった場合だけ設計する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [ ] unit_052 の完了を確認した
- [ ] 実装と unit / integration gate を完了した
- [ ] Joy-Con L/R 手動 gate を完了した
- [ ] 初期設計と公開文書の Intent Delta を反映した