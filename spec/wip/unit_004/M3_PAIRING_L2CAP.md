# M3 Pairing / L2CAP 接続 仕様書

## 1. 概要

### 1.1 目的

M2 の Bumble HID transport を使い、Switch との pairing、HID control channel、HID interrupt channel の open を観測できる状態にする。M3 は入力反映の完全確認を完了条件にしない。接続 sequence と切断 event を diagnostics と hardware log に残す。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M3 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| lifecycle | advertising、pairing、connected、disconnect 状態 | `spec/initial/lifecycle.md` |
| transport-bumble | control / interrupt channel、callback 境界 | `spec/initial/transport-bumble.md` |
| testing | hardware test の pairing / L2CAP 項目 | `spec/initial/testing.md` |
| hardware-harness skill | pairing と channel open の承認境界 | `.agents/skills/hardware-harness/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| developer | Switch の pairing 操作 | `swbt-python` device が Switch 側に見える | 明示承認が必要 |
| transport | HID control channel open | connected 判定に必要な event が diagnostics に残る | channel ready 条件を明確にする |
| transport | HID interrupt channel open | input / reply を送れる channel として記録される | 入力反映は M5 |
| developer | 手動 close または Switch 側 disconnect | disconnect event と cleanup 結果が残る | reconnect は M6 |

## 2. 対象範囲

- Switch pairing 手順の実機確認。
- HID control channel open の検出。
- HID interrupt channel open の検出。
- connected 判定の定義。
- disconnect event と reason の記録。
- pairing 失敗時の raw event / trace 記録。
- hardware test log への OS、driver、dongle、Bumble、Switch model / firmware 記録。

## 3. 対象外

- 入力反映の完全確認。
- `tap(Button.A)` の実機通過。
- subcommand reply 不足の修正全体。
- reconnect。
- 複数 Switch model の互換性保証。
- 複数 controller。

## 4. 関連 docs

- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/wip/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/wip/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | channel open 後に Switch から来る初期 output report の report ID と sequence を記録する |
| Bumble / transport | required | todo | L2CAP control / interrupt callback の event 名、connected 判定、disconnect reason を確認する |
| OS / driver / adapter | required | todo | pairing 成否は driver、dongle、firmware に依存するため観測条件を記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| advertising visible | Switch pairing UI | device が発見可能になる | M2 の advertising が前提 |
| pairing complete | Switch が pairing を進める | pairing complete 相当の event を diagnostics に記録する | Bumble event 名は実装時に確認 |
| control channel open | L2CAP control ready | `l2cap_channel_open` に channel=`control` を記録する | trace schema に従う |
| interrupt channel open | L2CAP interrupt ready | `l2cap_channel_open` に channel=`interrupt` を記録する | 両 channel ready で connected |
| connected state | 両 channel ready | `SwitchGamepad` state が `connected` になる | `wait_connected()` が完了 |
| disconnect | Switch 側または手動 close | reason、cleanup、final state を記録する | reconnect はしない |
| pairing failure | timeout または error | 失敗位置と raw event を残す | 未対応 subcommand は M4 へ |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | fake channel event で control / interrupt 両方が ready になった時だけ `connected` になる | new | integration | no | 実機前の lifecycle 固定 |
| todo | `wait_connected()` が connected event で完了する | regression | integration | no | M1 から channel 条件を拡張 |
| todo | disconnect callback で state が neutral へ戻り report loop が停止する | regression | integration | no | 実機なしで先に固定 |
| todo | pairing timeout が diagnostics に失敗位置を残す | new | integration | no | manual run 解析用 |
| todo | Switch pairing UI から device が見える | new | hardware | yes | 明示承認が必要 |
| todo | Switch と pairing complete まで進む | new | hardware | yes | `@pytest.mark.hardware` または manual bring-up |
| todo | HID control channel open が trace に残る | new | hardware | yes | channel metadata を記録 |
| todo | HID interrupt channel open が trace に残る | new | hardware | yes | connected 判定の根拠 |
| todo | 手動 close で transport が停止し adapter が release される | new | hardware | yes | cleanup 記録 |

## 8. 設計メモ

- connected 判定は「HID control / interrupt channel の両方が利用可能」を基準にする。
- M3 では `0x21` reply の不足を深追いしない。観測された output report と subcommand sequence は M4 の入力にする。
- 実機観測は `hardware observation` として扱い、別 dongle や別 firmware の一般事実にしない。
- `wait_connected(timeout=...)` の timeout 値は test と manual bring-up で明示する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/bumble.py` | modify | pairing / L2CAP event bridge |
| `src/swbt/gamepad.py` | modify | connected 判定、wait_connected |
| `src/swbt/diagnostics.py` | modify | pairing / channel / disconnect events |
| `tests/integration/` | modify | fake channel event tests |
| `tests/hardware/` | modify | pairing / L2CAP hardware tests |
| `docs/hardware-test-log.md` | new / modify | 実機観測 |

## 10. 検証

この表は M3 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit tests/integration` | pending | M3 実装後に local automated gate として実行する |
| `uv run pytest -m hardware` | pending-approval | Switch 実機、adapter、command、cleanup plan の明示承認後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | adapter open、HID advertising、Switch pairing、HID control / interrupt channel open、manual close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `docs/hardware-test-log.md`、diagnostics JSON Lines trace |
| cleanup | pairing run 後に advertising 停止、transport close、必要なら Switch 側登録解除手順を記録 |

## 12. 先送り事項

- subcommand reply 不足の補正は M4 で扱う。
- input reflection は M5 で扱う。
- reconnect と key store は M6 で扱う。

## 13. チェックリスト

このチェックリストは M3 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] pairing / L2CAP event の根拠監査を実施し、状態を更新した
- [ ] M3 の local automated gate を実行し、検証欄を結果で更新した
- [ ] 実機検証は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
