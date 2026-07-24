# 診断履歴と未使用経路の削除 仕様書

## 1. 概要

### 1.1 目的

公開 API、HID report、送信順序を変えずに、無制限に増える診断 event 履歴と本番から使われない内部経路を削除する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | 診断履歴、test-only reply queue、状態更新 helper、未使用 control 送信経路の削除 | `https://github.com/niart120/swbt-python/issues/115` |
| 親 Issue | 観測可能な公開挙動を維持した内部境界の整理 | `https://github.com/niart120/swbt-python/issues/114` |
| 初期設計 | sender、report loop、transport、diagnostics の責務 | `spec/initial/architecture.md` |
| 初期設計 | output report と subcommand reply の送信経路 | `spec/initial/protocol.md` |
| 初期設計 | transport interface と Bumble 実装境界 | `spec/initial/transport-bumble.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 長時間動作する gamepad | trace writer なしで周期 `0x30` を送信する | report counter は増えるが、送信回数に比例した event 履歴を保持しない | `GamepadStatus` の集計値は維持する |
| diagnostics 利用者 | trace writer ありで lifecycle、report、subcommand、error を記録する | 既存 schema の JSON Lines を受け取る | event 名と field を変えない |
| Switch output report 処理 | subcommand を含む `0x01` を受信する | reply と periodic input が同じ sender lock と timer を使い、reply 後の holdoff が働く | reply bytes と送信順序を変えない |
| public gamepad API | button、stick、IMU、neutral を更新する | 従来と同じ `InputState` が確定する | `InputStateStore.update()` / `apply()` に集約する |
| transport 上位層 | host から control channel data を受信する | `on_control_data()` callback が従来どおり呼ばれる | 未使用の device-to-host `send_control()` は削除する |

## 2. 対象範囲

- `DiagnosticsRecorder` の全 event 履歴と `events` property を削除する。
- report counter、last subcommand ID、last raw rumble、last error を有界な状態として保持する。
- trace writer への JSON Lines 出力を維持する。
- 本番 call site がない `record_state_transition()` を削除する。
- `ReportLoop` の test-only reply queue と専用送信経路を削除する。
- 実際の `send_subcommand_reply()`、共通 sender lock、timer、reply 後 holdoff を維持する。
- `InputStateStore` の個別 helper を削除し、production call site を `update()` / `apply()` へ移す。
- 本番 call site がない `HidDeviceTransport.send_control()` と Fake / Bumble 実装を削除する。
- `on_control_data()` を維持する。
- 関連する初期設計とテストを現行経路へ合わせる。

## 3. 対象外

- `GamepadStatus` の公開フィールド変更。
- public gamepad の `press()`、`release()`、`sticks()`、`imu()`、`neutral()` の変更。
- input report、output report、subcommand reply、SPI、rumble の byte layout 変更。
- report period、reply holdoff 時間、timer の進め方の変更。
- Direct の transport 受理後 commit 条件の変更。
- Bumble adapter、Switch 実機を使う検証。
- 親 Issue #114 の他の子 Issue。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/roadmap.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | `ReportSender.send_subcommand_reply()` と既存 unit / integration test を維持し、report builder、parser、定数、payload は変更しない |
| Bumble / transport | required | done | `rg` で `send_control()` の production call site は定義以外 0 件。host-to-device の `on_control_data()` は `ControllerRuntime` が登録しているため維持する |
| OS / driver / adapter | not applicable | not applicable | adapter を開かず、driver や OS 依存挙動を変更しない |

### 5.1 監査結果

| 項目 | 値 / 判断 | 根拠分類 | source | status |
|---|---|---|---|---|
| subcommand reply 経路 | `OutputReportDispatcher` から `send_subcommand_reply()` を呼び、`ReportSender` の lock 内で reply を生成・送信する | implementation fact | `src/swbt/gamepad/output.py`, `src/swbt/gamepad/runtime.py`, `src/swbt/report_loop.py` | confirmed |
| reply と input の直列化 | `0x21` と `0x30` は同じ `ReportSender._send_lock` と timer を使う | implementation fact | `src/swbt/report_loop.py`, `tests/unit/test_report_loop.py` | confirmed |
| outbound control 送信 | `send_control()` は protocol 定義、Fake、Bumble 実装と test にだけ存在し、本番 call site はない | implementation fact | `rg -n "send_control" src tests` | confirmed |
| inbound control 受信 | `ControllerRuntime` が `on_control_data()` を登録し、integration test が reply まで確認する | implementation fact | `src/swbt/gamepad/runtime.py`, `tests/integration/test_switch_gamepad_fake_transport.py` | confirmed |
| protocol bytes | builder、parser、profile、定数を変更しない | implementation fact | 対象差分と既存 unit / integration test | unit 475 件、integration 154 件で確認 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| diagnostics の有界保持 | trace writer なしで多数の report event を記録 | recorder が通常 event を履歴として保持せず、counter だけが増える | last error 1 件の保持は許容する |
| status 集計 | report、subcommand、rumble、error を記録 | 従来と同じ counter、last ID、raw bytes、last error を返す | dict / bytes は防御的に返す |
| trace 出力 | trace writer ありで event を記録 | 既存 event schema の JSON Lines を逐次出力する | flush を維持する |
| reply 送信 | periodic input と subcommand reply が競合する | 同じ lock と timer で直列化し、reply 後は periodic を holdoff する | test-only queue は使わない |
| state 更新 | public API から IMU または neutral を更新 | `update()` / `apply()` 経由で従来と同じ state になる | Direct commit 条件は不変 |
| control channel 受信 | Fake transport へ control data を注入 | output dispatcher を通って `0x21` reply を送る | `on_control_data()` を維持する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | trace writer なしで report event を繰り返しても過去 event object を保持せず、counter は正しく増える | regression | unit | no | `_events` 保持による red 後に有界集計へ変更して green |
| refactor-done | trace writer が既存 schema を維持し、last error を含む集計値を返す | characterization | unit / integration | no | `events` property の検査を trace または集計値へ置換 |
| refactor-done | subcommand reply と input report が共通 timer / lock を使い、reply 後 holdoff を維持する | characterization | unit / integration | no | 実際の `send_subcommand_reply()` 経路で検証し、reply queue 専用 test を削除 |
| refactor-done | state store helper 削除後も public IMU / neutral / concurrent state update と Direct commit が維持される | regression | unit / integration | no | `update()` / `apply()` へ集約 |
| refactor-done | outbound `send_control()` 削除後も inbound control data が subcommand reply へ到達する | regression | integration | no | Bumble adapter を開かず fake transport で確認 |

## 8. 文書検証計画

公開文書は変更しない。`spec/initial` と本作業仕様は、実装の call graph、検索結果、unit / integration test と照合する。

## 9. 設計メモ

- diagnostics event は trace writer へ同期出力した後に破棄する。`last_error` だけは `GamepadStatus` のため 1 件保持する。
- reply は queue へ積まず、output report callback から共有 sender へ直接渡す。共有 lock 内で reply を構築するため、session state 変更と ACK の順序を維持できる。
- Periodic holdoff は `ReportLoop.send_subcommand_reply()` の完了後に設定する。
- `InputStateStore` は complete state の `apply()` と atomic read-modify-write の `update()` に絞る。
- HID control channel は host-to-device 受信に必要である。device-to-host の未使用送信 method を削除しても control channel 自体は削除しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/diagnostics.py` | modify | event 履歴、`events`、未使用 transition helper を削除 |
| `src/swbt/report_loop.py` | modify | reply queue と既成 reply 送信経路を削除 |
| `src/swbt/state_store.py` | modify | 個別 state helper を削除 |
| `src/swbt/gamepad/runtime.py` | modify | IMU / neutral 更新を `update()` / `apply()` へ移行 |
| `src/swbt/gamepad/output.py` | modify | reply 経路の説明を現行実装へ合わせる |
| `src/swbt/transport/base.py` | modify | `send_control()` を protocol から削除 |
| `src/swbt/transport/fake.py` | modify | outbound control report の保持と送信を削除 |
| `src/swbt/transport/bumble.py` | modify | outbound control 送信実装を削除 |
| `tests/unit/test_diagnostics.py` | modify | 無制限保持と集計値を検証 |
| `tests/unit/test_report_loop.py` | modify | 実際の reply 経路で timer / holdoff を検証 |
| `tests/unit/test_bumble_transport.py` | modify | `events` / `send_control()` 専用検査を trace / interrupt 検査へ置換 |
| `tests/unit/test_public_api_boundary.py` | modify | test transport から未使用 method を削除 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | reply queue 用語を実際の送信順序へ置換 |
| `spec/initial/protocol.md` | modify | direct reply + shared sender 経路へ更新 |
| `spec/initial/transport-bumble.md` | modify | outbound control method を interface から削除 |
| `spec/initial/roadmap.md` | modify | M1 の完了表現を現行 reply 経路へ更新 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_diagnostics.py::test_report_events_are_not_retained_without_a_trace_writer -q` | red | `_events` が最初の `report_tx` event を保持して `1 failed` |
| 同上 | pass | 履歴削除後に `1 passed` |
| `uv run pytest tests/unit/test_diagnostics.py tests/unit/test_report_loop.py::test_imu_mode_transition_and_ack_share_periodic_send_lock ... -q` | pass | 変更前 characterization と診断変更後の対象検査 `10 passed` |
| `uv run pytest tests/unit/test_report_loop.py tests/integration/test_switch_gamepad_fake_transport.py::test_subcommand_reply_precedes_the_next_periodic_input tests/integration/test_switch_gamepad_fake_transport.py::test_imu_mode_ack_precedes_first_periodic_input_in_the_new_format -q` | pass | queue 削除後の timer / lock / holdoff `10 passed` |
| state store 対象 integration 4 件 | pass | IMU、neutral、disconnect、Direct commit を変更前後とも `4 passed` |
| `uv run pytest tests/unit/test_bumble_transport.py::test_bumble_interrupt_send_fails_until_l2cap_channel_is_connected tests/integration/test_switch_gamepad_fake_transport.py::test_control_output_report_injection_sends_subcommand_reply -q` | pass | outbound method 削除と inbound control 維持 `2 passed` |
| `uv sync --dev` | pass | `Resolved 53 packages` |
| `uv run ruff format --check .` | pass | `100 files already formatted` |
| `uv run ruff check .` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest tests/unit` | pass | `475 passed in 2.23s` |
| `uv run pytest tests/integration` | pass | `154 passed in 8.27s` |
| `git diff --check` | pass | whitespace error なし |
| `uv run mkdocs build --strict` | not run | `mkdocs` が project の開発依存に含まれず program not found。Issue #115 の指定 gate ではないため依存を追加せず、正本との手動照合を実施 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | adapter / Switch-facing command を実行しない |
| adapter | none |
| 実行遮断 | 環境変数による遮断は採用しない。`bumble` / `hardware` marker を実行対象から除外する |
| log / artifact | local unit / integration test output |
| cleanup | none |

## 13. 先送り事項

- none

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
