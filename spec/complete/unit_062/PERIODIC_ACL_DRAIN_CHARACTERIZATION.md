# Periodic ACL drain 特性調査 仕様書

## 1. 概要

### 1.1 目的

Issue #93 で観測した ACL completion 待ちが、Periodic controller の実送信周期と入力状態の反映に与える影響を分けて記録する。恒久的な diagnostics API や送信方式の変更は扱わない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | Periodic 経路でも同じ問題が起こり得るかを計測・検証する | conversation, 2026-07-22 |
| implementation fact | `ReportLoop._run()` は sleep 後に `send_next_report()` を await してから次の sleep に進む | `src/swbt/report_loop.py` |
| hardware observation | Direct の ACL drain はこの adapter で約 10 ms であり、enqueue 後から HCI completion 処理までが大半を占めた | `spec/hardware-test-log.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Periodic caller | `apply()` を連続更新 | 呼び出しは transport completion を待たず、遅延中の中間 state は次の report に蓄積されない | public API は変えない |
| ReportLoop / transport | `send_interrupt()` が ACL completion で停止 | 同時送信数は 1 件のまま、完了後の次 report は最新 snapshot を送る | fake transport で先に固定する |
| Switch-facing run | neutral state だけの periodic report | 設定周期、sleep 実測、report 完了間隔、ACL drain を artifact に残す | 明示承認が必要 |

## 2. 対象範囲

- private かつ DEBUG 時だけ有効な periodic report timing probe。
- ACL enqueue / drain 観測と同一 record に、Periodic scheduler の sleep 実測と report completion 間隔を記録する。
- blocking fake transport により、遅い send が重複送信を生まず、次 report が最新 snapshot を送ることを検証する。
- 既存 saved Pro profile による short active reconnect と neutral periodic report の実機特性化。

## 3. 対象外

- `ReportLoop` の cadence 補償、並列送信、default period の変更。
- 公開 diagnostics API、設定フラグ、永続ログ形式。
- pairing、button / stick 入力、local BD_ADDR の変更。
- role-switch-only link policy の再試行。unit_061 の reason 19 stop condition を尊重する。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/testing.md`
- `spec/initial/transport-bumble.md`
- `spec/hardware-test-log.md`
- `spec/complete/unit_060/HCI_ACL_COMPLETION_CORRELATION.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report byte layout は変更しない。既存 builder の出力を state coalescing の観測に使うだけである。 |
| Bumble / transport | required | done | `send_interrupt()` が `drain_bumble_acl_queue()` を await する既存実装と unit_060 の completion 観測を利用する。 |
| OS / driver / adapter | required | done | CSR8510 A10 / WinUSB / `usb:0`、Windows 11、Python 3.13.5、Bumble 0.0.230 を artifact と hardware log に記録し、postflight の HCI / CSR address 一致と `adapter_closed` を確認した。 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| slow periodic send | 1 回目の `send_interrupt()` を fake transport で停止 | scheduler は 2 回目を開始せず、同時に transport へ送らない | 送信を await する現行契約の characterization |
| snapshot coalescing | 1 回目の送信停止中に state を更新 | 解放後の次 `0x30` は更新後の state を含む | 中間 state の送信保証ではない |
| debug disabled | periodic controller を通常実行 | timing logger は record を出さず、既存の report loop 振る舞いを変えない | 一時 probe の非侵入条件 |
| debug enabled | neutral periodic report | report ごとに configured period、sleep 実測、前回 completion からの間隔、transport / ACL timing を JSON DEBUG に出す | private experimental logger のみ |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | blocked first periodic send の間に 2 回目の transport send を開始しない | characterization | unit | no | scheduler の serialize を観測した |
| green | blocked send 中の state 更新は、解放後の次 periodic report に反映される | characterization | unit | no | `apply()` 相当の state store 更新を使う |
| green | DEBUG periodic probe は period / completion interval / transport duration を 1 record に出す | new | unit | no | Bumble なしの fake transport で確認した |
| green | DEBUG 無効時に probe record を出さない | regression | unit | no | 通常経路の output を増やさないことを確認した |
| green | `usb:0` で neutral periodic report の 8 ms / 16 ms 設定を短時間実行し、実間隔と ACL drain を記録する | characterization | hardware | yes | active reconnect と profile cross-mode 再利用を確認した |

## 8. 文書検証計画

not applicable。公開文書を変更しない。

## 9. 設計メモ

- `ReportLoop._run()` は send 完了後に次の sleep を開始する。そのため実測周期は configured period と send duration の和になり得る。これは source fact であり、実機での具体的な値は未検証である。
- Direct probe と ACL observer は task-local context により結び付く。Periodic には別の private context を追加し、共有する sender / Bumble transport から有効な probe を取得する。
- 実機測定は neutral state のみとし、短時間の指定 sample 数で終了する。completion 間隔は Python task における report 完了時刻であり、Switch 側の反映時刻ではない。
- 2026-07-22 の CSR8510 A10 / WinUSB / Bumble 0.0.230 観測では、8 ms 設定の completion interval は p50 20.023 ms、ACL drain は p50 11.386 ms だった。16 ms 設定ではそれぞれ p50 25.116 ms / 8.385 ms だった。両条件とも sleep と transport send の和がおおむね completion interval となり、ACL drain は transport send の大半を占めた。この値を別 adapter / OS / Switch firmware へ一般化しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/_experimental_direct_send_timing.py` | modify | periodic timing context と JSON DEBUG record を追加する |
| `src/swbt/report_loop.py` | modify | periodic loop の scheduler timing を private probe に記録する |
| `src/swbt/transport/bumble.py` | modify | active periodic probe に ACL timing を渡す |
| `tests/unit/test_report_loop.py` | modify | slow transport 時の serial send / latest snapshot を検証する |
| `tests/unit/test_experimental_direct_send_timing.py` | new | private timing probe の DEBUG contract を検証する |
| `tmp/hardware/issue-93/periodic_send_timing_benchmark.py` | new, ignored | 手動 hardware characterization harness |
| `spec/hardware-test-log.md` | modify | 承認済み実機観測を追記する |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_experimental_direct_send_timing.py tests/unit/test_report_loop.py` | passed, 9 | TDD item 1-4 |
| `uv run ruff format --check .` | passed, 103 files | final gate |
| `uv run ruff check .` | passed | final gate |
| `uv run ty check --no-progress` | passed | final gate |
| `uv run pytest tests/unit` | passed, 466 | final gate |
| `uv run pytest tests/integration` | passed, 134 | shared Periodic integration tree |
| `uv run ruff format --check tmp/hardware/issue-93/periodic_send_timing_benchmark.py` | passed | ignored harness の個別確認 |
| `uv run ruff check tmp/hardware/issue-93/periodic_send_timing_benchmark.py` | passed | ignored harness の個別確認 |
| `uv run python tmp/hardware/issue-93/periodic_send_timing_benchmark.py --help` | passed | adapter を開かない CLI 確認 |
| `uv run python tmp/hardware/issue-93/periodic_send_timing_benchmark.py ... --report-period-us 8000 --samples 40` | passed, 40 periodic reports | completion interval p50 20.023 ms、ACL drain p50 11.386 ms |
| `uv run python tmp/hardware/issue-93/periodic_send_timing_benchmark.py ... --report-period-us 16000 --samples 40` | passed, 40 periodic reports | completion interval p50 25.116 ms、ACL drain p50 8.385 ms |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --output tmp/hardware/issue-93/periodic-acl-drain/adapter-identity-postflight.json` | passed | HCI / CSR address `0E:08:71:C0:B4:5C` 一致、`adapter_closed` |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | `usb:0` を Bumble から開き、saved profile の active reconnect、HID advertising / channel open、neutral-only periodic `0x30` report を 8 ms / 16 ms 設定で短時間送信する。pairing と button / stick 操作は行わない。 |
| adapter | dedicated CSR8510 A10, WinUSB, `usb:0`。実行直前と終了後に read-only HCI / CSR identity probe を実施する。 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `tmp/hardware/issue-93/periodic-acl-drain/` の trace、timing JSONL、summary、pre/postflight identity。概要を `spec/hardware-test-log.md` に残す。 |
| cleanup | `close(neutral=True)` により neutral report 後に report loop と transport を停止する。adapter close と postflight identity を確認する。reason 19、unexpected disconnect、identity mismatch、trace error で直ちに停止する。 |

## 13. 先送り事項

- 実機結果を得た後に、8 ms default の見直し、monotonic deadline scheduling、coalescing の利用者向け契約化が必要かを別 unit で判断する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 実機前の検証結果を記録した
- [x] 明示承認後の実機結果を記録した
