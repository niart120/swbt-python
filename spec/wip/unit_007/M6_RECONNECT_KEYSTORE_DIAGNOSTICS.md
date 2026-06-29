# M6 Reconnect / Keystore / Diagnostics 仕様書

## 1. 概要

### 1.1 目的

pairing 情報の保存、reconnect 成功 / 失敗の区別、失敗時の advertising 復帰、diagnostics 拡充、hardware run metadata を扱う。M6 は全 dongle での reconnect 保証を目標にしない。観測条件を明確にし、release 時に保証できる範囲を分ける。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M6 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| lifecycle | reconnect 方針、key_store_path、disconnect 処理 | `spec/initial/lifecycle.md` |
| api | `key_store_path`、`status()` | `spec/initial/api.md` |
| testing | hardware test の reconnect 項目 | `spec/initial/testing.md` |
| risks | reconnect、dongle、OS / driver 差分 | `spec/initial/risks.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `SwitchGamepad(key_store_path=...)` | pairing 情報の保存先が設定される | 保存形式は Bumble と実装で確認 |
| developer | 初回 pairing 後 | key store 書き込み有無が diagnostics に残る | secret 値はログに出さない |
| developer | 再接続試行 | reconnect 成功 / 失敗を区別して記録する | dongle / firmware 条件付き |
| lifecycle | reconnect 失敗 | advertising へ戻る、または再 pairing 可能な状態になる | cleanup を記録 |

## 2. 対象範囲

- `key_store_path` の設定と diagnostics 記録。
- pairing 情報保存の確認。
- reconnect 成功 / 失敗の区別。
- reconnect 失敗時の advertising 復帰。
- hardware run metadata の trace 追加。
- trace schema の安定化。
- hardware matrix の更新。

## 3. 対象外

- 全 dongle での reconnect 保証。
- 複数 controller 同時 reconnect。
- daemon mode。
- link key の secret 値のログ出力。
- OS 標準 Bluetooth stack との併用。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/wip/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | reconnect 後の初期 output report sequence が初回 pairing と異なる可能性がある |
| Bumble / transport | required | todo | key store、link key、reconnect event、advertising 復帰は Bumble 挙動に依存する |
| OS / driver / adapter | required | todo | reconnect 成否は dongle、driver、Switch firmware 条件付きで記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| key store configured | `key_store_path` 指定 | path と存在確認結果を diagnostics に記録する | secret 内容は記録しない |
| pairing saved | 初回 pairing 後 | 保存成功 / 失敗が trace に残る | Bumble API 確認が必要 |
| reconnect attempt | 既存 pairing 情報あり | attempt start / result を記録する | active / incoming の区別は確認後 |
| reconnect success | channel ready | state が connected になる | M3 と同じ connected 条件 |
| reconnect failure | timeout / error | failure reason を記録し advertising へ戻る | 再 pairing 可能性を残す |
| key store reset | user deletes key store | 再 pairing 手順を docs に残す | CLI 化は M7 |
| trace metadata | hardware run | OS、driver、dongle、Bumble、Python、Switch model / firmware を含む | unit_010 と整合 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `key_store_path` 指定が diagnostics metadata に残る | new | unit | no | secret は出さない |
| todo | key store 書き込み失敗が diagnostics に残り、例外の扱いが明確になる | edge | unit | no | filesystem failure mock |
| todo | disconnect 後に reconnect disabled なら closed / failed の定義通りに遷移する | regression | integration | no | M1-M5 の保証維持 |
| todo | reconnect enabled で failure した場合に advertising へ戻る | new | integration | no | fake transport event |
| todo | trace event が schema に従い metadata を含む | regression | integration | no | unit_010 |
| todo | key store ありで reconnect 成功 / 失敗を実機で記録する | new | hardware | yes | 成功保証ではなく観測 |
| todo | reconnect 失敗後に再 pairing できるかを記録する | characterization | hardware | yes | release 判断材料 |
| todo | hardware matrix に reconnect 結果が反映される | new | hardware | yes | unit_011 |

## 8. 設計メモ

- reconnect は初期 release の保証対象に含めるか未決である。実装しても README では確認済み構成と未確認構成を分ける。
- key store の secret 値は diagnostics に出さない。path、存在、読み書き結果、例外型に留める。
- reconnect 失敗時は利用者が再 pairing へ戻れる状態を優先する。
- trace schema は M2 以降の実機 run で破綻しないよう、unit_010 で先に安定させる。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | reconnect option、lifecycle |
| `src/swbt/transport/bumble.py` | modify | key store / reconnect bridge |
| `src/swbt/diagnostics.py` | modify | metadata と reconnect events |
| `src/swbt/errors.py` | modify | reconnect / keystore error |
| `tests/unit/` | modify | key store metadata tests |
| `tests/integration/` | modify | fake reconnect lifecycle tests |
| `tests/hardware/` | modify | reconnect characterization tests |
| `docs/hardware-test-log.md` | modify | reconnect 観測 |
| `README.md` | modify | reconnect の保証範囲 |

## 10. 検証

この表は M6 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit tests/integration` | pending | M6 実装後に local automated gate として実行する |
| `uv run pytest -m hardware` | pending-approval | reconnect 実機検証の明示承認後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for reconnect observation |
| 承認範囲 | adapter open、HID advertising、pairing、key store 書き込み、disconnect、reconnect attempt、再 pairing、close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、hardware test log、key store path metadata |
| cleanup | neutral、report loop 停止、transport close、adapter release。必要なら key store 削除手順を記録 |

## 12. 先送り事項

- 複数 dongle / 複数 Switch firmware の網羅は初期 release 後の matrix 拡張に送る。
- daemon mode の reconnect 制御は初期対象外。
- CLI からの key store reset helper は M7 の `swbt-probe` で必要性を判断する。

## 13. チェックリスト

このチェックリストは M6 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] reconnect / key store / diagnostics の根拠監査を実施し、状態を更新した
- [ ] M6 の local automated gate を実行し、検証欄を結果で更新した
- [ ] 実機 reconnect 観測は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
