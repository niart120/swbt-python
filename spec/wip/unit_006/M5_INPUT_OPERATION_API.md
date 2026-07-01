# M5 入力操作 API 仕様書

## 1. 概要

### 1.1 目的

実機接続済みの `SwitchGamepad` で `tap()`、`press()`、`release()`、stick 入力、`neutral()`、`status()` を利用できる状態にする。M5 の完了条件は、少なくとも `tap(Button.A)` が Switch UI に反映され、neutral 後に入力が残らないことを確認することとする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M5 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| api | public input API、status、snapshot | `spec/initial/api.md` |
| lifecycle | neutral fail-safe、disconnect 時の state reset | `spec/initial/lifecycle.md` |
| testing | Button A、L+R、neutral、reconnect 前の hardware tests | `spec/initial/testing.md` |
| risks | scheduler jitter、firmware 差分、scope creep | `spec/initial/risks.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `await pad.tap(Button.A)` | Switch UI に A 入力が反映される | 実機承認が必要 |
| library user | `await pad.press(Button.L, Button.R)` | 一定 tick 数以上 L+R report が送られる | duration は利用者側で sleep |
| library user | `await pad.neutral()` | 以降の report が neutral になり、UI に入力が残らない | Bluetooth link 切断済みなら内部 state のみ保証 |
| library user | `pad.status()` | connection state、report counters、last subcommand、raw rumble を読める | 高頻度 control path では使わない |

## 2. 対象範囲

- 実機での `tap()`。
- 実機での `press()` / `release()`。
- 実機での left / right stick 入力。
- `neutral()`。
- `status()`。
- disconnect 時の内部 state neutral 復帰。
- report counters と last subcommand / raw rumble の status 露出。

## 3. 対象外

- 複雑な macro scheduler。
- 高水準 rumble API。
- 複数 controller。
- reconnect の正式保証。
- GUI。
- daemon IPC。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_001/M0_PROTOCOL_CORE.md`
- `spec/wip/unit_002/M1_SWITCH_GAMEPAD_FAKE_TRANSPORT.md`
- `spec/complete/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/wip/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | Button / stick report bytes は M0 の監査済み layout を使う。実機反映は hardware observation として記録する |
| Bumble / transport | required | todo | report loop timing と send failure が入力反映に影響する |
| OS / driver / adapter | required | todo | 入力反映結果は adapter、driver、Switch firmware 条件付きで扱う |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| tap | `tap(Button.A)` | press report が送られ、duration 後に release report が送られる | 実機で UI 反映を確認 |
| press hold | `press(Button.L, Button.R)` | L+R report が複数 tick 送られる | tick 数を diagnostics で確認 |
| release | `release(Button.L, Button.R)` | 該当 button が clear された report が送られる | 他の入力は保持 |
| stick | normalized stick input | report bytes と実機 UI / game input が一致する範囲で観測される | 反映方法は検証対象による |
| neutral | `neutral()` | store が neutral になり、接続中なら neutral report が送られる | close でも利用 |
| disconnect reset | disconnect callback | store が neutral へ戻る | wire 送信できない場合を明記 |
| status | `status()` | connection state、report counters、last subcommand、raw rumble を返す | diagnostics と整合 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | fake transport で `tap(Button.A)` が press / release の順に report を残す | regression | integration | no | `test_tap_button_a_records_press_and_release_reports` で固定 |
| green | `press(Button.L, Button.R)` が次の periodic reports に反映される | regression | integration | no | `test_press_buttons_are_reflected_in_periodic_report` で固定 |
| green | `release()` が指定 button だけを clear する | new | integration | no | `test_release_only_clears_requested_buttons_in_next_periodic_report` で他入力の保持を固定 |
| green | `set_input()` で left / right stick が report に反映される | new | integration | no | `test_set_input_reflects_left_and_right_sticks_in_next_periodic_report` で normalized stick を固定 |
| green | disconnect callback で内部 state が neutral へ戻る | regression | integration | no | `test_disconnect_callback_neutralizes_state_and_stops_report_loop` で固定 |
| green | `status()` が report counter と last subcommand を返す | new | integration | no | `test_status_returns_report_counters_last_subcommand_and_raw_rumble` で raw rumble も固定 |
| pending-approval | 実機で `await pad.tap(Button.A)` が Switch UI に反映される | new | hardware | yes | `test_switch_input_operation_sequence_for_manual_reflection` と手元 UI 観測を hardware log に記録する |
| pending-approval | 実機で L+R が一定 tick 数以上送信される | new | hardware | yes | 同 hardware test の `hold_lr_reports_sent` checkpoint と画面反映を分けて記録する |
| pending-approval | 実機で `neutral()` 後に入力が残らない | new | hardware | yes | 同 hardware test の `neutral_complete` checkpoint と画面残留なしを記録する |
| todo | disconnect 時に内部 state が neutral へ戻る | edge | hardware | yes | wire 上の neutral 送信可否も記録 |

## 8. 設計メモ

- `tap()` の既定 duration は短くしすぎない。Python scheduler jitter の影響を diagnostics で確認する。
- `status()` は control path ではなく監視と検証のための API とする。
- 実機反映が失敗した場合は、report bytes、send timing、subcommand sequence、Switch firmware を分けて原因を記録する。
- macro scheduler は初期範囲に入れない。複雑な同時操作は後続設計に送る。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | input operation API、status |
| `src/swbt/state_store.py` | modify | button / stick 更新 |
| `src/swbt/report_loop.py` | modify | counters、send timing |
| `src/swbt/diagnostics.py` | modify | status source |
| `src/swbt/__init__.py` | modify | public export |
| `tests/integration/` | modify | fake input operation tests |
| `tests/hardware/` | modify | input reflection tests |
| `docs/hardware-test-log.md` | modify | Button A、L+R、neutral 観測 |

## 10. 検証

この表は M5 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_status_returns_report_counters_last_subcommand_and_raw_rumble -q` | pass | 1 passed。red は `GamepadStatus` に `report_counters` がない `AttributeError`、green で counter、last subcommand、raw rumble を確認 |
| `uv run pytest tests\integration -q` | pass | 23 passed。diagnostics counter / subcommand trace の既存 integration も回帰なし |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_release_only_clears_requested_buttons_in_next_periodic_report -q` | pass | 1 passed。既存実装が条件を満たしていたため red は発生せず、characterization として追加 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_set_input_reflects_left_and_right_sticks_in_next_periodic_report -q` | pass | 1 passed。既存実装が条件を満たしていたため red は発生せず、characterization として追加 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_tap_button_a_records_press_and_release_reports -q` | pass | 1 passed。既存の tap fake transport test を M5 regression item の根拠として確認 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_press_buttons_are_reflected_in_periodic_report -q` | pass | 1 passed。既存の press periodic report test を M5 regression item の根拠として確認 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_disconnect_callback_neutralizes_state_and_stops_report_loop -q` | pass | 1 passed。既存の disconnect neutral reset test を lifecycle item の根拠として確認 |
| `uv run pytest tests\hardware\test_input_operations.py --collect-only -q` | pass | 1 test collected。実機未承認のため hardware test は収集確認のみ |
| `uv sync --dev` | pass | Resolved 41 packages / Checked 41 packages |
| `uv run ruff format --check .` | pass | 37 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 97 passed |
| `uv run pytest tests\integration -q` | pass | 23 passed |
| `uv run pytest tests\unit tests\integration -q` | pass | 120 passed |
| `uv run pytest -m hardware` | pending-approval | periodic input report loop と実機入力反映の明示承認後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | adapter open、HID advertising、pairing、periodic input report loop、Button A / L+R / neutral 入力、close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、hardware test log、必要なら画面観測メモ |
| cleanup | `neutral()`、report loop 停止、transport close、adapter release |

## 12. 先送り事項

- reconnect 成功 / 失敗の正式扱いは M6。
- examples と README への利用例反映は M7。
- macro scheduler は初期 release 後の検討対象。

## 13. チェックリスト

このチェックリストは M5 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] input operation API と status の実装を完了した
- [x] M5 の local automated gate を実行し、検証欄を結果で更新した
- [ ] 実機入力反映は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
