# Diagnostics Trace Schema 仕様書

## 1. 概要

### 1.1 目的

M1 以降の fake transport、Bumble adapter、実機 pairing、subcommand、input reflection、reconnect を同じ粒度で追える diagnostics trace schema を定義する。trace は JSON Lines を基本とし、実機未検証や adapter 依存の観測を後から比較できる形にする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| testing | 診断ログの確認項目と JSON Lines 例 | `spec/initial/testing.md` |
| lifecycle | state transition、close、disconnect、failed | `spec/initial/lifecycle.md` |
| transport-bumble | adapter、OS、Bumble version 記録 | `spec/initial/transport-bumble.md` |
| api | `status()`、diagnostics config | `spec/initial/api.md` |
| risks | documentation drift、scheduler jitter、firmware 差分 | `spec/initial/risks.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| integration test | fake transport event | event 名、state、counter を決定的に assert できる | 実時間に依存しない |
| hardware bring-up | adapter open / pairing / L2CAP | run metadata と event sequence を JSON Lines で残せる | secret は出さない |
| responder debug | subcommand rx / reply tx | packet id、subcommand、report id、reason を対応付けられる | raw bytes の扱いを明示 |
| user monitoring | `status()` | trace と同じ counter / last event に基づく状態を読める | 高頻度 path ではない |

## 2. 対象範囲

- diagnostics event 名。
- JSON Lines trace の必須 field と任意 field。
- run metadata。
- report counters。
- state transition events。
- transport open / close events。
- L2CAP channel open events。
- output report / subcommand / reply / input report events。
- error events。
- `status()` の source。

## 3. 対象外

- 巨大な packet capture file format。
- secret 値の保存。
- 外部 observability backend 連携。
- GUI viewer。
- stable public trace schema としての永続互換保証。

## 4. 関連 docs

- `spec/initial/testing.md`
- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/wip/unit_002/M1_SWITCH_GAMEPAD_FAKE_TRANSPORT.md`
- `spec/wip/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/wip/unit_004/M3_PAIRING_L2CAP.md`
- `spec/wip/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | trace に report ID、subcommand ID、raw bytes を残す場合、意味付けは監査済み値に基づける |
| Bumble / transport | required | todo | event 名と metadata は Bumble callback と version に依存する |
| OS / driver / adapter | required | todo | run metadata と hardware observation の前提として記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| run metadata | diagnostics start | OS、driver、adapter、Python、Bumble、package version、commit を記録できる | 取れない値は `unknown` と理由 |
| state transition | lifecycle change | previous、next、reason を記録する | `closed` など lifecycle と一致 |
| transport event | open / close | start、complete、error を記録する | adapter string を含む |
| channel event | L2CAP ready | channel、direction、metadata を記録する | M3 |
| report tx | `0x21` / `0x30` send | report id、reason、counter、timestamp を記録する | raw bytes は設定で制御 |
| report rx | output report | report id、length、packet id、subcommand id を記録する | raw bytes は必要時 |
| error | exception | error type、message、state、recoverable を記録する | secret を含めない |
| status | `status()` | connection state、counters、last subcommand、last error、raw rumble を返す | trace recorder と同じ source |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | diagnostics event が JSON Lines として 1 行 1 object で出力される | new | unit | no | `tests/unit/test_diagnostics.py` で固定 |
| green | run metadata に OS、Python、package version、adapter が入る | new | unit | no | `test_run_metadata_records_environment_and_adapter` で固定。package version 取得不能時は `unknown` |
| green | lifecycle state transition が previous / next / reason を持つ | new | unit | no | `test_state_transition_records_previous_next_and_reason` で固定 |
| green | report tx counter が `0x21` と `0x30` を区別して増える | new | integration | no | `test_report_tx_counter_distinguishes_0x21_and_0x30` で固定 |
| todo | output report rx と subcommand rx が packet id で対応付く | new | integration | no | fake fixture |
| todo | callback 例外が error event と status に反映される | edge | integration | no | failed state |
| todo | hardware run metadata が hardware log に転記できる粒度で出力される | characterization | hardware | yes | 実機 run 後 |

## 8. 設計メモ

- trace event 名は `transport_open_start`、`transport_open_complete`、`advertising_start`、`connected`、`l2cap_channel_open`、`output_report_rx`、`subcommand_rx`、`subcommand_reply_tx`、`input_report_tx`、`neutral_tx`、`disconnected`、`transport_close_complete`、`error` を初期候補にする。
- raw bytes は diagnostics config で出力可否を制御する。subcommand debug には有用だが、通常ログを肥大化させない。
- `status()` は trace event を全部保持する API ではない。現在状態と最後の観測だけを返す。
- schema を安定させるまでは docs に experimental と書く。release gate では README の記述と実装を合わせる。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/diagnostics.py` | new / modify | recorder、event schema、status source |
| `src/swbt/gamepad.py` | modify | lifecycle event 発火 |
| `src/swbt/report_loop.py` | modify | report counters |
| `src/swbt/transport/bumble.py` | modify | transport / channel metadata |
| `tests/unit/` | modify | schema unit tests |
| `tests/integration/` | modify | fake trace tests |
| `docs/hardware-test-log.md` | modify | trace artifact 参照 |

## 10. 検証

この表は diagnostics schema 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_diagnostics.py::test_diagnostics_event_is_written_as_one_json_object_per_line -q` | pass | 1 passed。`DiagnosticsRecorder` が 1 行 1 JSON object を出力することを確認した |
| `uv run pytest tests\unit\test_diagnostics.py::test_run_metadata_records_environment_and_adapter -q` | pass | 1 passed。run metadata に adapter、OS、Python version、package version が入ることを確認した |
| `uv run pytest tests\unit\test_diagnostics.py::test_state_transition_records_previous_next_and_reason -q` | pass | 1 passed。state transition が previous / next / reason を出力することを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_report_tx_counter_distinguishes_0x21_and_0x30 -q` | pass | 1 passed。`0x30` と `0x21` の report tx counter が別々に増えることを確認した |
| `uv run pytest tests\unit tests\integration -q` | pass | 85 passed |
| `uv run ruff format --check .` | pass | 30 files already formatted |
| `uv run ruff check .` | pass | lint pass |
| `uv run ty check --no-progress` | pass | type check pass |
| `uv run pytest tests/unit tests/integration` | pending | diagnostics schema 実装後に local automated gate として実行する |
| `uv run pytest -m hardware` | pending-approval | hardware metadata は実機承認後に確認する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | schema 実装では不要。hardware metadata validation では必要 |
| 承認範囲 | 実機 run で schema を確認する場合は adapter open、advertising、pairing、report loop、close の範囲を明示する |
| adapter | 例: `usb:0`。実機 run 時のみ必要 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | JSON Lines trace、hardware test log |
| cleanup | 実機 run 時は neutral、transport close、adapter release |

## 12. 先送り事項

- 外部 viewer や可視化は初期対象外。
- 長期互換の stable trace schema は初期 release 後、利用者 feedback と実機観測が増えてから判断する。

## 13. チェックリスト

このチェックリストは diagnostics schema 作業の完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] diagnostics event schema と status source の実装を完了した
- [ ] local automated gate を実行し、検証欄を結果で更新した
- [ ] hardware metadata validation は承認、command、cleanup、結果を記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
