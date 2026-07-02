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
| Switch HID / report bytes | required | observed-fail | Button / stick report bytes は M0 の監査済み layout を使う。2026-07-02 M5 run の debug log で A `08 00 00`、L+R `40 00 40`、neutral `00 00 00` を含む `a1 30` 送信を確認したが、Switch UI は反映しなかった |
| Bumble / transport | required | observed-fail | 2026-07-02 M5 run で L2CAP open、`0x01` output report、`0x21` reply、`0x30` input report 送信、clean close を確認したが、semantic input reflection は未達 |
| OS / driver / adapter | required | observed-fail | `docs/hardware-test-log.md` に Windows / CSR8510 A10 / WinUSB / Bumble 0.0.230 / `usb:0` 条件の observed-fail として記録した |
| pairing / bonding path | required | observed-partial | swbt-python M5 trace は `classic_pairing` と L2CAP open を記録したが、pairing complete、authentication、encryption、link key の通過点をまだ記録していなかった。swbt-daemon `local_049` success は `pairing complete, status 00` と full subcommand sequence 後の UI input reflection、`local_073` reconnect success は link-key DB 使用と no new pairing を観測しているため、同等の pairing 経路通過とは扱わない |

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
| observed-fail | 実機で `await pad.tap(Button.A)` が Switch UI に反映される | new | hardware | yes | 2026-07-02 M5 run で A report bytes は送信されたが、ユーザ画面観測ではデバイス登録画面が全く動かなかった |
| observed-partial | 実機で L+R が一定 tick 数以上送信される | new | hardware | yes | 2026-07-02 M5 run で L+R bytes を含む `0x30` が 30 tick 以上送信された。UI 反映は観測されず |
| observed-partial | 実機で `neutral()` 後に入力が残らない | new | hardware | yes | 2026-07-02 M5 run で neutral bytes と clean close は確認。入力反映自体が未達のため UI 残留なしの意味検証は未確定 |
| todo | 実機 trace で pairing complete / authentication / encryption / link key availability を記録する | diagnostic | hardware | yes | swbt-daemon success / reconnect logs との比較用。raw link key は記録しない |
| todo | disconnect 時に内部 state が neutral へ戻る | edge | hardware | yes | wire 上の neutral 送信可否も記録 |

## 8. 設計メモ

- `tap()` の既定 duration は短くしすぎない。Python scheduler jitter の影響を diagnostics で確認する。
- `status()` は control path ではなく監視と検証のための API とする。
- 実機反映が失敗した場合は、report bytes、send timing、subcommand sequence、Switch firmware を分けて原因を記録する。
- pairing 経路は `classic_pairing` と L2CAP open だけで完了扱いにしない。次の実機 run では Bumble diagnostics の `pairing_complete`、`connection_authentication`、`connection_encryption_change`、必要に応じて `link_key_available` を確認し、swbt-daemon `local_049` / `local_073` と比較する。
- swbt-daemon の UI 成功 run は `0x02` / `0x08` だけでなく、`0x10` SPI read、`0x03` report mode、`0x04` trigger buttons elapsed、`0x40` IMU、`0x48` vibration、`0x21` MCU、`0x30` player lights まで応答してから入力反映へ進んでいる。M5 の次回診断では subcommand sequence が repeated `0x08` で止まるか、known sequence へ進むかを分けて記録する。
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
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable --log-file .pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\pytest-debug.log --log-file-level=DEBUG -q -s` | observed-fail | Pytest は 1 passed / 1 warning in 10.08s。trace は L2CAP open、`0x21` reply、A / L+R / neutral checkpoint、56 件の `0x30`、clean close を記録。debug log で A `08 00 00`、L+R `40 00 40`、neutral `00 00 00` の `a1 30` 送信を確認。ユーザ画面観測では Switch のデバイス登録画面が全く動かなかったため、M5 semantic input reflection は fail |
| `uv run pytest tests\unit\test_bumble_transport.py -q` | pass | 18 passed。Bumble connection diagnostics に authentication / encryption / link key availability / mode change の trace を追加 |
| `uv run ruff check src\swbt\transport\bumble.py tests\unit\test_bumble_transport.py` | pass | All checks passed |
| `uv run ruff format --check src\swbt\transport\bumble.py tests\unit\test_bumble_transport.py` | pass | 2 files already formatted |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest -m hardware` | not run | M5 targeted hardware run が semantic input reflection fail のため、全 hardware marker の横展開は実施していない |

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

## 13. swbt-daemon ログ突き合わせ

### 根拠監査

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| daemon UI success sequence | `pairing complete, status 00`、L2CAP open、`0x02/0x08/0x10/0x03/0x04/0x40/0x48/0x21/0x30` replies、L+R / Button A UI reflection | hardware observation | `E:\documents\VSCodeWorkspace\swbt-daemon\docs\hardware-test-log.md` `local_049` | swbt-python M5 run は `0x02` / `0x08` までで未到達 |
| daemon pairing-free reconnect | link-key DB open、link key request response、no `pairing complete`、L2CAP open、Button A smoke | hardware observation | `E:\documents\VSCodeWorkspace\swbt-daemon\docs\hardware-test-log.md` `local_073` | swbt-python は reconnect / key store 対象外。current run では link key availability も未記録 |
| swbt-python M5 pairing evidence | `host_connection`、`classic_pairing`、control / interrupt L2CAP open、`connected` | hardware observation | `docs/hardware-test-log.md` 2026-07-02 M5 run | pairing complete / authentication / encryption / link key は未記録だったため、daemon success と同等に扱わない |
| enhanced Bumble diagnostics | `pairing_complete`、`connection_authentication`、`connection_encryption_change`、`connection_encryption_key_refresh`、`link_key_available`、`classic_mode_change` | implementation fact | `src/swbt/transport/bumble.py`、`tests/unit/test_bumble_transport.py` | 次回 hardware run から比較に使う。raw link key は記録しない |

### 未解決事項

- 次回の実機 run で enhanced diagnostics が `pairing_complete`、authentication、encryption を記録するか確認する。
- `link_key_available` が出るかどうかは Bumble の key store と Switch 側 bonding state に依存する。出ない場合も raw key をログへ出さない。
- Switch が repeated `0x08` から known subcommand sequence へ進まない場合、UI 入力反映失敗の主因は report byte correctness ではなく controller initialization / adoption 側として扱う。

## 14. チェックリスト

このチェックリストは M5 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] input operation API と status の実装を完了した
- [x] M5 の local automated gate を実行し、検証欄を結果で更新した
- [x] 実機入力反映検証は承認、command、cleanup、失敗結果を `docs/hardware-test-log.md` に記録した
- [x] swbt-daemon の success / reconnect logs と突き合わせ、次回の pairing diagnostics に必要な trace events を追加した
- [ ] `tap(Button.A)` の Switch UI 反映と neutral 後の残留なしを確認した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
