# 周期送信型と Direct 送信型の公開分離 仕様書

## 1. 概要

### 1.1 目的

`0x30` input report の送信契機をライブラリが所有する型と、利用者が所有する型を公開 class で分離する。既存の `ProController` / `JoyConL` / `JoyConR` は周期送信契約を維持し、`DirectProController` / `DirectJoyConL` / `DirectJoyConR` は1操作と1件の送信を対応させる。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #77 | 周期送信型と Direct 送信型を公開型として分離し、送信頻度の所有者を型で固定する | `https://github.com/niart120/swbt-python/issues/77` |
| initial API | 現行の `SwitchGamepad`、状態更新 API、`tap()`、`snapshot()` 契約 | `spec/initial/api.md` |
| input API contract | 状態更新は即時送信を保証せず、`tap()` だけが action API である現行判断 | `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md` |
| current runtime | `ControllerRuntime`、`ReportLoop`、`InputStateStore` による周期送信実装 | `src/swbt/gamepad/runtime.py`, `src/swbt/report_loop.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 周期送信の利用者 | `ProController.apply(state)` または意味的入力操作 | local current state が更新され、後続の周期 report がその時点の状態を送る | 接続と即時送信を要求しない |
| Direct 送信の利用者 | `DirectProController.send(state)` | 指定状態の `0x30` をちょうど1件送り、送信完了後だけ current state を更新する | 接続済みを要求し、周期 task を開始しない |
| Direct 送信の利用者 | `press()` / `release()` / `sticks()` / `imu()` / `neutral()` | last successfully sent state から候補を作り、1件送信して成功後だけ確定する | 同時操作を直列化する |
| Switch host | output report / subcommand | reporting type に関係なく reply を受け取る | input report と同じ送信直列化境界を通す |
| lifecycle | `close(neutral=True/False)` | `True` は trailing neutral を試み、`False` は通常 input report を追加しない | Direct の `True` は利用者所有の送信契機に対する明示的な例外 |

## 2. 対象範囲

- `SwitchGamepad` を lifecycle、connection、status、意味的入力操作の共通抽象型として維持する。
- `PeriodicSwitchGamepad` と `DirectSwitchGamepad` を異なる公開抽象型として追加する。
- `PeriodicSwitchGamepad.apply(state)` と `DirectSwitchGamepad.send(state)` を分離する。
- 既存 `ProController` / `JoyConL` / `JoyConR` を `PeriodicSwitchGamepad` の具象型として維持する。
- `DirectProController` / `DirectJoyConL` / `DirectJoyConR` を追加する。
- input report と subcommand reply に共通する timer、IMU encoding、送信 lock、diagnostics を共通 sender に集約する。
- Direct の完全状態送信と意味的入力操作を、送信成功後 commit のトランザクションとして実装する。
- Direct の input operation を直列化し、`tap()` は押下から解放まで同じ操作 lock を保持する。
- `snapshot()`、`tap()`、`close()` の reporting type ごとの意味を test と公開文書で固定する。
- public root exports、API docs、usage、agent brief、initial design を新しい型境界へ追従させる。

## 3. 対象外

- raw HID bytes の public send API。
- Periodic と Direct の接続中切り替え、または runtime mode object の public API。
- Periodic 型への明示 `0x30` send API。
- Direct の `apply(state); send()`、引数なし `send()`、fire-and-forget queue。
- report period の精度、deadline scheduler、最低送信頻度の補完。
- mouse delta、姿勢モデル、macro / sequence runner、rumble 解釈の追加。
- report byte layout、subcommand payload、SPI data、HID descriptor の変更。
- Bumble adapter、pairing、HID advertising、Switch 実機を使う検証。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md`
- `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md`
- `spec/complete/unit_039/CONTROLLER_RUNTIME_EXTRACTION.md`
- `spec/complete/unit_040/PUBLIC_CONTROLLER_API_MODEL.md`
- `spec/complete/unit_045/INTERNAL_API_BOUNDARY_CLEANUP.md`
- `spec/complete/unit_049/IMU_SESSION_AND_ENCODING_REDESIGN.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 既存 `0x30` builder、`0x21` reply、timer、IMU encoding を再利用し、ID、layout、定数を変更しない |
| Bumble / transport | not applicable | not applicable | `HidDeviceTransport.send_interrupt()` は完了まで待つ既存境界を利用する。Bumble object、SDP、L2CAP、adapter 仮定は追加しない |
| OS / driver / adapter | not applicable | not applicable | fake transport の unit / integration test だけで公開型と送信契約を検証する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| 公開型の分離 | root import と class hierarchy を調べる | Periodic / Direct の抽象型と6具象型が import でき、既存3型は Periodic に属する | mode object は公開しない |
| API の排他性 | method と constructor signature を調べる | Periodic は `apply(state)` を持ち `send(state)` を持たない。Direct は逆で、`report_period_us` を受け取らない | 共通意味操作は両型にある |
| Periodic 状態更新 | 未接続または接続中に状態操作する | local state を commit し、即時送信しない。接続中は後続周期 report が観測する | 現行後方互換 |
| Direct 完全状態送信 | 接続中に `send(state)` を await する | 指定状態の `0x30` を1件送り、transport 完了後に current state を更新する | background queue を作らない |
| Direct 非周期性 | Direct を接続し待機する | 自動 `0x30` を送らない | subcommand reply は自動処理する |
| Direct rollback | 未接続または送信失敗 | `ClosedError` または transport error を返し、report 成功前の current state を維持する | profile validation 失敗も commit しない |
| Direct 意味操作 | press / release / sticks / imu / neutral | last successfully sent state から候補を作り、各正常終了につき1件送り、成功後だけ commit する | `lstick` / `rstick` は `sticks` と同じ規則 |
| Direct 同時操作 | 複数 input operation を同時に開始する | operation lock の取得順に送信と commit が完了し、候補状態が失われない | transport completion の backpressure を返す |
| tap | held input がある状態で `tap()` | 両型とも押下と解放を送り、対象 button だけを解除する。Direct は押下から解放まで操作 lock を保持する | release 失敗時は最後に送信できた押下状態を維持する |
| subcommand 自動応答 | Direct 接続中に host output を注入する | `0x21` を自動送信し、prefix は送信順上の current state を使う | input と共通 sender lock / timer を使う |
| close | Direct で `neutral=True` / `False` | `True` は接続中に neutral 1件を試み、成功後 commit。`False` は input report を追加しない | transport cleanup は両型共通 |
| profile validation | Pro / Joy-Con L / Joy-Con R の Direct 操作 | Periodic と同じ capability を使い、不正候補を送信・commit しない | profile 実装を複製しない |
| snapshot | Periodic / Direct の current state を読む | Periodic は最新 local committed state、Direct は最後に正常送信した state を返す | 新しい接続 session は neutral baseline から始める |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | 公開 root が Periodic / Direct 抽象型と Direct 3具象型を公開し、既存3具象型を Periodic として分類する | new | unit | no | 共通 interface と reporting type 固有 interface を分離し、class hierarchy と `__all__` を固定 |
| refactor-skipped | Periodic だけが `apply(state)` と `report_period_us` を公開し、Direct だけが `send(state)` を公開する | new | unit | no | 公開型分離の実装で expected-green。無効操作を runtime validation へ落とさない signature を固定 |
| refactor-skipped | 既存3具象型の状態操作が即時送信せず、周期 report と snapshot の現行契約を維持する | regression | integration | no | expected-green regression。press / apply / 非即時送信 / tap held input を確認 |
| refactor-done | Direct の `send(state)` が送信完了まで待ち、指定状態の `0x30` をちょうど1件送ってから snapshot を更新する | new | integration | no | 共通 `ReportSender` を抽出し、制御可能な fake transport で完了前後の snapshot と1件送信を確認 |
| refactor-skipped | Direct は接続後に周期 `0x30` を開始せず、host output には自動応答する | new | integration | no | send transaction の runtime 分岐で expected-green。待機中0件と `0x21` reply のみを確認 |
| refactor-skipped | Direct の未接続、送信失敗、profile validation 失敗が current state を変更しない | edge | integration | no | send transaction 実装で expected-green。full send と press の transport error、未接続、Joy-Con L unsupported state を固定 |
| refactor-done | Direct の press / release / sticks / imu / neutral が各1件送信し、成功後だけ状態を確定する | new | integration | no | candidate 生成、profile validation、送信成功後 commit を `_send_direct_update()` に集約 |
| refactor-skipped | Direct の同時入力操作が直列化され、開始順の候補状態と送信順を失わない | edge | integration | no | input operation lock 実装で expected-green。blocking fake transport で2操作目が1操作目完了まで送信開始しないことを固定 |
| refactor-done | `tap()` が両 reporting type で held input を維持し、Direct の押下・解放を直列化する | regression | integration | no | Direct 専用2段 transaction を追加し、押下から解放まで operation lock を保持 |
| refactor-skipped | Direct の tap release 失敗時に押下済み current state を維持し、release 再試行で neutral へ戻せる | edge | integration | no | Direct tap transaction で expected-green。最後に成功送信した押下stateと明示release再試行を固定 |
| refactor-done | Direct input と subcommand reply が共通 timer / send lock を通り、prefix と送信順が一致する | new | unit | no | reply builder 内の state snapshot を共通 sender lock の内側へ移し、timerとprefixを送信順へ一致させた |
| refactor-done | Direct の `close(neutral=True/False)` が trailing neutral の有無、commit、cleanup を契約どおり処理する | new | integration | no | Direct close を operation lock と共通 sender に接続し、`True` だけが送信成功後 neutral を commit |
| refactor-skipped | Direct Pro / Joy-Con L / Joy-Con R が同じ runtime と profile validation を共有する | new | integration | no | `_ControllerSpec` と共通runtime実装で expected-green。3 profile の正常入力と unsupported input を確認 |
| todo | API docs、usage、agent brief、initial design が送信所有者、完了条件、snapshot、close の違いを説明する | new | unit | no | public docs test と placeholder residue check を更新する |

## 8. 設計メモ

### 8.1 公開型

```text
SwitchGamepad
├── PeriodicSwitchGamepad
│   ├── ProController
│   ├── JoyConL
│   └── JoyConR
└── DirectSwitchGamepad
    ├── DirectProController
    ├── DirectJoyConL
    └── DirectJoyConR
```

`SwitchGamepad` の共通意味操作は「現在の論理入力状態を遷移させる」ことを表す。正常終了の意味は、Periodic では local commit、Direct では1件の送信完了と commit である。

### 8.2 共通 sender

`ReportLoop` から次を共通 sender へ抽出する。

- input report / subcommand reply の send lock。
- timer byte と increment。
- connection-scoped IMU encoding。
- `InputReportBuilder` と `transport.send_interrupt()`。
- diagnostics の report counter / reason。

Periodic だけが scheduler と current state snapshot を所有する。Direct は scheduler を生成せず、input operation lock 内で candidate を共通 sender へ渡す。subcommand reply は両型で共通 sender の lock 内に入り、reply prefix の state も送信順の中で取得する。

### 8.3 Direct transaction

```text
input operation lock
  -> last successfully sent state から candidate を構築
  -> profile validation
  -> common sender lock
       -> 0x30 build
       -> transport.send_interrupt() 完了
       -> candidate commit
```

送信失敗では commit しない。`tap()` の release 送信失敗時は、押下 report が最後の成功送信なので押下状態を current state として維持する。

### 8.4 Tidy decision

```text
Tidy decision:
- classification: mixed
- action: split
- reason: 共通 sender 抽出は構造変更、公開型と Direct transaction は振る舞い変更である。sender の既存 wire / timer 回帰を先に固定し、Direct item を順に追加する。
- verification: report sender unit test、public API boundary test、fake transport integration test、標準 gate を順に実行する。
```

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/interface.py` | modify | 共通、Periodic、Direct の公開抽象型 |
| `src/swbt/gamepad/core.py` | modify | reporting type 別 runtime-backed base と6具象型 |
| `src/swbt/gamepad/runtime.py` | modify | reporting type ごとの状態操作、scheduler、close |
| `src/swbt/report_loop.py` | modify | 共通 sender 抽出と Periodic scheduler |
| `src/swbt/state_store.py` | modify | Direct の送信成功後 commit を支える内部境界 |
| `src/swbt/gamepad/output.py` | modify | sender lock 内で current state を使う reply builder |
| `src/swbt/gamepad/__init__.py`, `src/swbt/__init__.py` | modify | public exports |
| `src/swbt/_testing/gamepad.py` | modify | Direct fake transport constructor |
| `tests/unit/test_public_api_boundary.py` | modify | class hierarchy、signature、constructor |
| `tests/unit/test_package_import.py` | modify | root exports |
| `tests/unit/test_report_loop.py` | modify | 共通 sender、timer、送信直列化 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | Direct transaction、非周期性、rollback、tap、close、profile |
| `spec/initial/*.md` | modify | API、architecture、lifecycle、testing の安定契約 |
| `docs/api.md`, `docs/usage.md`, `docs/agent-brief.md` | modify | 公開利用面と生成指針 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_api_boundary.py tests/unit/test_package_import.py -q` | not run | 公開型と signature の TDD |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_reporting_types_and_direct_controllers_are_public_and_classified -q` | red | `PeriodicSwitchGamepad` が root に未公開の `AttributeError` を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_reporting_types_and_direct_controllers_are_public_and_classified -q` | pass | 1 passed。2抽象型、既存 Periodic 3型、Direct 3型の階層と root export を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_reporting_types_expose_only_their_owned_full_state_operation tests/unit/test_package_import.py -q` | pass | 5 passed。`apply` / `send` と `report_period_us` の排他性、root export 一覧を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_press_buttons_are_reflected_in_periodic_report tests/integration/test_switch_gamepad_fake_transport.py::test_apply_updates_snapshot_and_next_periodic_report tests/integration/test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_send_immediate_interrupt_reports tests/integration/test_switch_gamepad_fake_transport.py::test_tap_releases_only_tapped_button_and_preserves_held_buttons -q` | pass | 4 passed。Periodic の周期送信、snapshot、非即時送信、held input を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_waits_for_transport_and_commits_exactly_one_report -q` | red | Direct send が transport へ到達せず、送信開始待ち timeout になる未実装状態を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_waits_for_transport_and_commits_exactly_one_report -q` | pass | 1 passed。transport 完了前は未完了かつ neutral、完了後は指定 `0x30` 1件と state commit を確認 |
| `uv run pytest tests/unit/test_report_loop.py tests/integration/test_switch_gamepad_fake_transport.py::test_press_buttons_are_reflected_in_periodic_report tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_sends_subcommand_reply -q` | red | sender 抽出直後に snapshot が lock 外となり `0x21` が周期 `0x30` より先行する回帰を検出 |
| `uv run pytest tests/unit/test_report_loop.py tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_waits_for_transport_and_commits_exactly_one_report tests/integration/test_switch_gamepad_fake_transport.py::test_press_buttons_are_reflected_in_periodic_report tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_sends_subcommand_reply -q` | pass | 7 passed。snapshot から送信までの周期 lock、Direct commit、subcommand 回帰を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_connection_is_non_periodic_and_still_replies_to_subcommands -q` | pass | 1 passed。接続後60msに自動 `0x30` がなく、Device Info に `0x21` だけを返すことを確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_failures_do_not_change_last_successfully_sent_state tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_rejects_unsupported_profile_state_without_sending -q` | pass | 2 passed。未接続、transport error、profile validation error で last successfully sent state を維持 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_semantic_operations_send_once_and_commit_after_success -q` | red | 未接続 `press()` が `ClosedError` を出さず local state を更新する Periodic 挙動を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_semantic_operations_send_once_and_commit_after_success tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_waits_for_transport_and_commits_exactly_one_report tests/integration/test_switch_gamepad_fake_transport.py::test_direct_send_failures_do_not_change_last_successfully_sent_state -q` | pass | 3 passed。7意味操作の1操作1送信、未接続拒否、full send / press failure rollback を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_concurrent_operations_are_serialized_without_lost_state -q` | pass | 1 passed。A送信完了前はB送信を開始せず、送信列A、A+Bと最終stateを確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_tap_sends_press_and_release_once_while_preserving_held_input -q` | red | Direct tap が押下と解放を各2件送り、合計4件になる既存共通実装を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_tap_sends_press_and_release_once_while_preserving_held_input tests/integration/test_switch_gamepad_fake_transport.py::test_tap_releases_only_tapped_button_and_preserves_held_buttons tests/integration/test_switch_gamepad_fake_transport.py::test_tap_send_failure_releases_pressed_state -q` | pass | 3 passed。Direct 2件送信と held input、Periodic tap 回帰を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_tap_sends_press_and_release_once_while_preserving_held_input tests/integration/test_switch_gamepad_fake_transport.py::test_direct_tap_keeps_pressed_state_when_release_send_fails tests/integration/test_switch_gamepad_fake_transport.py::test_direct_tap_serializes_concurrent_input_until_release -q` | pass | 3 passed。release failure state、release再試行、tap完了前の concurrent press 待機を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_subcommand_reply_uses_state_committed_by_prior_serialized_input -q` | red | input送信後に並ぶ `0x21` prefix が送信前に取得した neutral state のままになる競合を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_subcommand_reply_uses_state_committed_by_prior_serialized_input tests/unit/test_report_loop.py tests/unit/test_gamepad_output_dispatcher.py -q` | pass | 6 passed。送信列 `0x30` timer 0、`0x21` timer 1、reply prefix の Button A と既存sender/dispatcher回帰を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_close_controls_trailing_neutral_report -q` | red | `close(neutral=True)` が local neutral だけを行い trailing `0x30` を追加しない状態を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_close_controls_trailing_neutral_report tests/integration/test_switch_gamepad_fake_transport.py::test_close_with_neutral_records_trailing_neutral_report tests/integration/test_switch_gamepad_fake_transport.py::test_connected_close_requests_disconnect_after_trailing_neutral tests/integration/test_switch_gamepad_fake_transport.py::test_close_treats_trailing_neutral_send_failure_as_best_effort -q` | pass | 4 passed。Direct `True/False` の追加report数とPeriodic close回帰を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_direct_controller_profiles_share_send_and_validation_contract -q` | pass | 3 passed。Pro / Joy-Con L / Joy-Con R の supported 1件送信と unsupported rollback を確認 |
| `uv run pytest tests/unit/test_report_loop.py -q` | not run | 共通 sender の timer / lock 回帰 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q` | not run | Periodic / Direct の fake transport 契約 |
| `uv sync --dev` | not run | 標準 gate |
| `uv run ruff format --check .` | not run | 標準 gate |
| `uv run ruff check .` | not run | 標準 gate |
| `uv run ty check --no-progress` | not run | 標準 gate |
| `uv run pytest tests/unit` | not run | 標準 gate |
| `uv run pytest tests/integration` | not run | 対象 integration tree |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。新しい report byte、Bumble API、adapter 操作を追加せず fake transport で検証する |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。wire fixture 差分または新しい実機仮説が出た場合だけ、明示承認、対象 adapter、command、cleanup plan を確認する |
| log / artifact | unit / integration test output、git diff、PR checks |
| cleanup | なし |

## 12. 先送り事項

- none

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 根拠監査が追加不要である理由を記録した
- [x] 実機実行条件を記録した
- [ ] 公開型と constructor / method の排他性を実装した
- [ ] 共通 sender と Direct transaction を実装した
- [ ] Periodic の後方互換を確認した
- [ ] Direct の rollback、直列化、tap、subcommand、close を確認した
- [ ] 3 controller profile の Direct 型を確認した
- [ ] initial design と public docs を更新した
- [ ] 標準 gate と integration gate の結果を記録した
