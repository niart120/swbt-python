# M1 SwitchGamepad + Fake Transport 仕様書

## 1. 概要

### 1.1 目的

M0 の protocol core を使い、実機なしで `SwitchGamepad` の public API、状態更新、`ReportLoop`、reply queue 優先制御、neutral fail-safe を検証できるようにする。M1 の完了時点では、Bumble を使わずに API と送信順序の contract を固定する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M1 の対象範囲、完了条件 | `spec/initial/roadmap.md` |
| api | public API、利用例、例外 | `spec/initial/api.md` |
| lifecycle | open / close、connected、neutral fail-safe、concurrency | `spec/initial/lifecycle.md` |
| architecture | `SwitchGamepad`、`InputStateStore`、`ReportLoop`、`FakeHidTransport` の責務 | `spec/initial/architecture.md` |
| testing | fake transport integration test 方針 | `spec/initial/testing.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `async with SwitchGamepad(transport=fake)` | open と close が呼ばれ、transport の送信記録を確認できる | 実機と Bumble は使わない |
| library user | `await pad.tap(Button.A)` | fake transport に A 押下 report と release 後 report が記録される | duration は API helper の責務 |
| fake transport test | output report 注入 | `0x21` reply が `0x30` periodic report より先に送られる | M0 の parser / responder を使う |
| close path | `close(neutral=True)` | trailing neutral report と内部 state neutral が観測できる | link 切断済みの実機挙動は扱わない |

## 2. 対象範囲

- `SwitchGamepad` と `SwitchGamepadConfig`。
- `InputStateStore`。
- `ReportLoop`。
- `HidDeviceTransport` 抽象 interface。
- `FakeHidTransport`。
- `DiagnosticsRecorder` の最小実装。
- `open()`、`wait_connected()`、`close()`。
- `set_input()`、`neutral()`、`press()`、`release()`、`tap()`。
- fake transport から output report を注入し、subcommand reply を検証する integration test。

## 3. 対象外

- Bumble transport。
- USB Bluetooth adapter open。
- Switch pairing。
- HID advertising。
- OS 別 driver 処理。
- reconnect の正式保証。
- CLI、examples、package release。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_001/M0_PROTOCOL_CORE.md`
- `spec/wip/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | M1 は M0 の `0x30` / `0x21` bytes を送信順序で使う。新しい byte layout は追加しない |
| Bumble / transport | not applicable | not applicable | fake transport のみを使う |
| OS / driver / adapter | not applicable | not applicable | 実機・adapter を使わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| async context | `async with SwitchGamepad(transport=fake)` | `open()` 後に fake が open 済みになり、退出時に `close(neutral=True)` が走る | `close()` は冪等 |
| wait connected | fake transport が connected callback を発火 | `wait_connected()` が完了する | timeout 時は `ConnectionTimeoutError` |
| state update | `press()` / `release()` | `InputStateStore` の snapshot が変わる | lock で直列化 |
| tap | `tap(Button.A, duration=0.08)` | press、sleep、release の順に state が変わる | protocol に duration を入れない |
| periodic report | connected 状態 | `ReportLoop` が `0x30` を送る | test clock で決定的にする |
| reply priority | reply queue に `0x21` がある | 次送信で `0x21` を `0x30` より先に送る | 初期化 sequence の前提 |
| neutral close | `close(neutral=True)` | 内部 state を neutral にし、可能なら neutral report を送る | 失敗は diagnostics に記録 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `async with SwitchGamepad(transport=fake)` が fake transport を open / close する | new | integration | no | `tests/integration/test_switch_gamepad_fake_transport.py` で固定 |
| green | `wait_connected()` が fake connected callback を待って完了する | new | integration | no | `test_wait_connected_completes_after_fake_connected_callback` で固定 |
| green | `wait_connected(timeout=...)` が timeout 時に `ConnectionTimeoutError` を投げる | edge | integration | no | `test_wait_connected_timeout_raises_connection_timeout_error` で固定 |
| green | `tap(Button.A)` が A 押下 report と release report を fake transport に残す | new | integration | no | `test_tap_button_a_records_press_and_release_reports` で固定 |
| green | `press(Button.L, Button.R)` 後の periodic report が L+R を含む | new | integration | no | `test_press_buttons_are_reflected_in_periodic_report` で固定 |
| green | `release(Button.L, Button.R)` 後の report が該当 button を clear する | new | integration | no | `test_release_buttons_clears_next_periodic_report` で固定 |
| green | output report 注入から `0x21` reply が送信される | new | integration | no | `test_output_report_injection_sends_subcommand_reply` で固定 |
| green | reply queue に `0x21` がある場合、次送信は `0x30` ではなく `0x21` になる | new | integration | no | `test_subcommand_reply_queue_takes_priority_over_periodic_input` で固定 |
| green | `close(neutral=True)` が trailing neutral report を記録する | new | integration | no | `test_close_with_neutral_records_trailing_neutral_report` で固定 |
| green | 複数 task から `press()` / `release()` しても state が破壊されない | edge | integration | no | `test_concurrent_press_and_release_preserve_button_state` で固定 |
| green | callback 例外が diagnostics に記録され、`close()` で後始末できる | edge | integration | no | `test_callback_exception_is_recorded_and_close_cleans_up` で固定 |
| green | public API が Bumble 型を公開していない | regression | unit | no | `tests/unit/test_public_api_boundary.py` で固定 |

## 8. 設計メモ

- `FakeHidTransport` は送信 bytes と event を memory に記録し、test から output report を注入できるようにする。
- `ReportLoop` の test は実時間 sleep に依存しない。fake clock または明示 tick helper を検討する。
- `tap()` は途中で他 task の `set_input()` と競合し得る。M1 では単純な同時更新保護に留め、macro scheduler は対象外にする。
- diagnostics は M1 では最小限にする。ただし event 名は unit_010 の schema に寄せる。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | new | `SwitchGamepad`、設定、async context |
| `src/swbt/state_store.py` | new | `InputStateStore` |
| `src/swbt/report_loop.py` | new | periodic report と reply priority |
| `src/swbt/transport/base.py` | new | `HidDeviceTransport` |
| `src/swbt/transport/fake.py` | new | fake transport |
| `src/swbt/diagnostics.py` | new | 最小 recorder と counter |
| `src/swbt/__init__.py` | modify | public API の再 export |
| `tests/integration/` | new | fake transport integration tests |
| `tests/unit/` | modify | public import と境界 test |

## 10. 検証

この表は M1 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | 1 passed。`async with SwitchGamepad(transport=fake)` の open / close を確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_wait_connected_completes_after_fake_connected_callback -q` | pass | 1 passed。fake connected callback 後に `wait_connected()` が完了することを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_wait_connected_timeout_raises_connection_timeout_error -q` | pass | 1 passed。timeout 時に `ConnectionTimeoutError` を投げることを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_tap_button_a_records_press_and_release_reports -q` | pass | 1 passed。A 押下 report と release report を確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_press_buttons_are_reflected_in_periodic_report -q` | pass | 1 passed。periodic report に L+R が入ることを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_release_buttons_clears_next_periodic_report -q` | pass | 1 passed。release 後の periodic report で L+R が clear されることを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_output_report_injection_sends_subcommand_reply -q` | pass | 1 passed。`0x01` / subcommand `0x02` 注入後に `0x21` reply が送信されることを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_subcommand_reply_queue_takes_priority_over_periodic_input -q` | pass | 1 passed。reply queue の `0x21` が次の `0x30` より先に送られることを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_close_with_neutral_records_trailing_neutral_report -q` | pass | 1 passed。`close(neutral=True)` が trailing neutral report を記録することを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_concurrent_press_and_release_preserve_button_state -q` | pass | 1 passed。複数 task からの press / release 後も report state が壊れないことを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_callback_exception_is_recorded_and_close_cleans_up -q` | pass | 1 passed。callback 例外が status の error event に残り close できることを確認した |
| `uv run pytest tests\unit\test_public_api_boundary.py -q` | pass | 2 passed。public API import / signature に Bumble 型が出ないことを確認した |
| `uv run pytest tests\unit tests\integration -q` | pass | 79 passed。unit と fake transport integration を確認した |
| `uv run ruff format --check .` | pass | 29 files already formatted |
| `uv run ruff check .` | pass | lint pass |
| `uv run ty check --no-progress` | pass | type check pass |
| `uv run pytest tests/unit tests/integration` | pending | M1 実装後に fake transport integration gate として実行する |
| `uv run ty check --no-progress` | pending | M1 実装後に型 gate として実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 不要 |
| 承認範囲 | なし |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | integration test output、diagnostics event fixture |
| cleanup | 不要 |

## 12. 先送り事項

- `BumbleHidTransport` は M2 で扱う。
- Switch pairing と L2CAP の connected 判定は M3 で実機観測に基づいて補う。
- reconnect は M6 まで public guarantee にしない。

## 13. チェックリスト

このチェックリストは M1 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] fake transport と report loop の実装を完了した
- [ ] M1 の対象 test と型 gate を実行し、検証欄を結果で更新した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
