# Experimental Direct Send Timing Probe 仕様書

## 1. 概要

### 1.1 目的

Issue #93 の `DirectProController.send()` 待機を、公開 diagnostics 契約を新設せずに調査する。`logging.DEBUG` を明示的に有効化した実行だけで、Direct の入力操作 lock、sender lock、Bumble の HID enqueue、ACL drain の所要時間を 1 操作単位で出力する。

この作業単位の実装は調査終了後に削除できることを優先する。安定した trace schema、公開設定、queue policy は定義しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub issue | Bumble transport の ACL drain が Direct caller の 8 ms cadence を上回る観測と、待機内訳の要求 | `niart120/swbt-python#93` |
| GitHub issue | Project_Demi の 8 ms 入力評価、frame coalescing、Direct send 待機の関連調査 | `niart120/demi-controller#45` |
| existing implementation | Direct は transport send 成功後にだけ state を commit し、Bumble transport は HID enqueue 後に ACL drain を待つ | `src/swbt/gamepad/runtime.py`, `src/swbt/report_loop.py`, `src/swbt/transport/bumble.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Project_Demi 開発者 | Direct `send()` 中に専用 logger を DEBUG にする | 1 回の `send()` に lock、enqueue、ACL drain の所要時間が対応付く | Console/file handler の設定は呼び出し側が行う |
| swbt 開発者 | Fake transport で Direct `send()` する | hardware なしで operation / sender の計時ログを検証できる | Bumble 固有フィールドは未設定 |
| swbt 開発者 | Bumble fake channel を使う | enqueue 前後と drain 後の ACL pending 値をログに入れられる | 実 adapter を開かない |

## 2. 対象範囲

- private module と `swbt.experimental.direct_send_timing` logger を追加する。
- `DirectSwitchGamepad.send()` に限り、DEBUG 有効時だけ計時 context を作る。
- context 内で input operation lock、`ReportSender` の send lock、transport await の所要時間を収集する。
- Bumble transport で HID `send_data()` の所要時間、ACL pending の enqueue 前後・drain 後、drain 所要時間を収集する。
- 1 操作完了時に JSON object 1 件を logger.debug へ出す。
- Fake transport unit / integration test と Bumble fake channel unit test で確認する。

## 3. 対象外

- `DiagnosticsConfig`、`GamepadStatus`、public API、利用者向け docs の変更。
- 既存 JSON Lines trace event の追加・変更。
- Periodic reporting、Direct の意味的操作、subcommand reply、queue policy の計測。
- ACL drain の削除、bounded enqueue、backpressure、state commit の変更。
- USB Bluetooth adapter の open、Switch pairing、HID advertising、`bumble` / `hardware` marker 実行。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_050/DIRECT_REPORTING_TYPES.md`
- `spec/complete/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report ID や byte layout を変えない。ログには payload を出さない |
| Bumble / transport | required | done | Bumble 0.0.230 の `DataPacketQueue.drain(handle)` は connection の in-flight packet が 0 になるまで待つ。`pending` は host queue 全体の queued-completed であり connection 専用ではない |
| OS / driver / adapter | required | done | Issue #93 の Windows 11 / CSR8510 A10 / WinUSB 測定は hardware observation。設計上の latency guarantee にはしない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| logger 無効 | `swbt.experimental.direct_send_timing` が DEBUG 未満 | timing object、clock read、debug event を作らない | Direct send の既存契約を変えない |
| Fake transport Direct send | logger が DEBUG | `operation=send`、input lock wait、sender lock wait、transport wait を含む JSON object を 1 件出す | Bumble 固有フィールドは `null` |
| Bumble Direct send | logger が DEBUG | HID enqueue と ACL drain の時間、`acl_pending_total_before_enqueue`、`acl_pending_total_after_enqueue`、`acl_pending_total_after_drain` を同じ object に入れる | pending は host 全体の値 |
| send failure | Direct send が transport 例外 | 既存の例外・rollback を維持し、`outcome=error` を記録する | 計測失敗が元の例外を隠さない |

debug event は実験用であり、schema の後方互換を保証しない。時刻値は `perf_counter_ns()` から求める process-local duration で、console/file handler の出力負荷は測定値に含めない。ただし handler 負荷は caller が外側から測る `send()` 時間へ影響するため、比較時は logger 無効の測定も併記する。

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | DEBUG 無効の Direct `send()` は probe event を出さず、指定 state を 1 report で commit する | regression | integration | no | 既存 Direct transaction を守る |
| green | DEBUG 有効の Fake transport Direct `send()` は 1 JSON event に operation と 3 種の lock/transport duration を入れる | new | integration | no | duration は非負だけを確認する |
| green | Bumble fake channel の Direct timing context は HID enqueue と ACL pending / drain fields を同じ event に入れる | characterization | unit | no | pending が connection 専用でないことを field 名で表す |
| green | DEBUG 有効の Direct `send()` が transport error を再送出し、同時に `outcome=error` を記録する | edge | integration | no | probe が rollback / exception 契約を変えないことを確認する |
| deferred | CSR8510 A10 で 8 ms / 16 ms caller を比較し、logger 無効の外側計測と probe event を収集する | characterization | hardware | yes | 明示承認後だけ実行する |

## 8. 文書検証計画

not applicable。実験用 private logger のため利用者向け docs と public API docs は変更しない。

## 9. 設計メモ

計時 context は Direct `send()` の task-local な private state とする。`ReportSender` と `BumbleHidTransport` は context がある場合だけ field を追記するため、`HidDeviceTransport.send_interrupt()` の protocol signature を変更しない。

logger 名は `swbt.experimental.direct_send_timing` とする。出力内容は `json.dumps()` による 1 行の JSON object とし、`operation_id` で 1 Direct send 内の下位計測を結合する。payload bytes、入力値、Bluetooth address、key material は出さない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/_experimental_direct_send_timing.py` | new | task-local context と DEBUG JSON logger |
| `src/swbt/gamepad/runtime.py` | modify | Direct `send()` の operation lock 計時 |
| `src/swbt/report_loop.py` | modify | sender lock と transport await 計時 |
| `src/swbt/transport/_bumble_acl.py` | modify | ACL pending 読み取り helper |
| `src/swbt/transport/bumble.py` | modify | HID enqueue / ACL drain 計時 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | Fake transport Direct probe |
| `tests/unit/test_bumble_transport.py` | modify | Bumble fake channel の enqueue / ACL drain probe |

## 11. 検証

| command | result | notes |
|---|---|---|
| targeted pytest | pass | Fake transport probe、Bumble fake channel probe、ACL drain 回帰、transport error probe を確認 |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 100 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | experimental probe の optional context を確認 |
| `uv run pytest tests/unit` | environment error | 既存 `tmp/pytest` の削除が `WinError 5` で失敗。test assertion / product code failure なし |
| `uv run pytest tests/unit --basetemp=tmp/pytest-unit-issue93 -p no:cacheprovider` | pass | 455 passed。専用 workspace-local temp root を使用 |
| `uv run pytest tests/integration` | environment error | 既存 `tmp/pytest` の削除が `WinError 5` で失敗。test assertion / product code failure なし |
| `uv run pytest tests/integration --basetemp=tmp/pytest-integration-issue93 -p no:cacheprovider` | pass | 134 passed。専用 workspace-local temp root を使用 |
| `git diff --check` | pass | whitespace error なし |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required for implementation; required for characterization |
| 承認範囲 | USB Bluetooth dongle を開く前に、adapter、command、Switch-facing 動作、cleanup を会話で確認する |
| adapter | Issue #93 の `CSR8510 A10 / usb:0` は候補であり未選択 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | caller 外側の duration 集計、DEBUG event、OS、driver、Bumble version、Switch model / firmware を記録する |
| cleanup | logger handler を外し、`close(neutral=True)` 後に adapter を閉じる |

## 13. 先送り事項

- 実験結果を残す必要が生じた場合だけ、stable diagnostics trace schema を別作業単位で設計する。
- bounded enqueue / backpressure / stale report drop policy は、Direct の completion contract を変更し得るため別 Issue とする。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 実装と fake transport 検証を完了した
- [x] 標準 gate の最終結果と Windows tempdir の未解決環境エラーを記録した
