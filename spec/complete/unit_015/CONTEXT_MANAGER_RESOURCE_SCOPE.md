# Context Manager Resource Scope 仕様書

## 1. 概要

### 1.1 目的

`SwitchGamepad` の `async with` / `open()` / 接続開始 API の責務を整理する。破壊的変更を許容し、`async with` は adapter、transport、内部 task の resource scope を作るだけに寄せる。Bluetooth 上で外部から見える動作である HID advertising、pairing、active bond reuse reconnect は、明示的な接続 API から開始する。

現状の `async with SwitchGamepad(...)` は `__aenter__()` から `open()` を呼び、`open()` が `transport.start_advertising()` まで実行する。これは M1-M5 の bring-up には使いやすいが、M6 以降の外部 API では、初回 pairing 経路が暗黙の主経路に見える。実際の利用では保存済み bond を使った接続の方が高頻度になるため、resource lifetime と接続戦略を分ける。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | `async with` は resource scope に寄せ、互換性を無視した破壊的変更も許容する | conversation 2026-07-02 |
| api | target API は `async with` を resource scope とし、利用例では `connect()` / `pair()` を明示する | `spec/initial/api.md` |
| lifecycle | target lifecycle は `opened` 状態を追加し、`open()` では HID advertising を開始しない | `spec/initial/lifecycle.md` |
| M1 fake transport | `async with SwitchGamepad(transport=fake)` と `open()` が fake transport の `start_advertising` を記録する | `spec/complete/unit_002/M1_SWITCH_GAMEPAD_FAKE_TRANSPORT.md`, `tests/integration/test_switch_gamepad_fake_transport.py` |
| M6 reconnect | bond reuse reconnect では active / incoming / advertising recovery を分ける。`async with` の暗黙 advertising は M6 の主経路設計と衝突する | `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `async with SwitchGamepad(...) as pad:` | adapter / transport resource が開き、退出時に必ず close される | `__aenter__` だけでは advertising しない |
| library user | 初回接続を明示する | `await pad.pair(timeout=...)` が discoverable / connectable / HID advertising を開始し、incoming 接続を待つ | Switch 側の pairing 操作が必要 |
| library user | 通常接続を明示する | M6 の `connect()` が bond 優先で接続戦略を選べる | active bond reuse は unit_007 |
| developer | fake transport integration | `async with` だけでは fake transport に `start_advertising` が残らない | 既存テストは破壊的に更新する |
| lifecycle | block 退出、例外、cancel | neutral、report loop stop、disconnect request、transport close の cleanup が走る | unit_014 の close contract を維持する |

## 2. 対象範囲

- `async with` / `__aenter__` の責務を resource scope に限定する。
- `open()` を transport resource open と protocol/report-loop 準備に限定し、HID advertising を開始しない。
- 初回 pairing / incoming 接続待ちを明示 API へ移す。
- `close(neutral=True)` / `__aexit__` の cleanup contract は維持する。
- fake transport integration tests の期待順序を更新する。
- `spec/initial/api.md` と `spec/initial/lifecycle.md` の context manager / open / pairing 記述を更新する。
- M6 の bond reuse reconnect は、この unit 完了後に高水準 `connect()` / `reconnect()` として扱う。

## 3. 対象外

- active bond reuse reconnect の実装。これは `unit_007`。
- key store の保存、読み込み、peer 選択。これは `unit_007`。
- 自動 advertising recovery と retry loop。
- `connected session scope` 型の別 context manager 追加。
- daemon mode。
- 実機 reconnect 観測。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/architecture.md`
- `spec/initial/roadmap.md`
- `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report layout は変更しない |
| Bumble / transport | required | done | implementation fact。`HidDeviceTransport.open()` は host connection を待たない resource open、`start_advertising()` は host-discoverable state として定義済み。`BumbleHidTransport.open()` は adapter open、device / HID callback 初期化、SDP / HID device 初期化までを行い、`BumbleHidTransport.start_advertising()` が `_default_start_advertising()` 経由で power on、Classic link policy、connectable / discoverable を行う |
| OS / driver / adapter | not applicable | not applicable | adapter open の可否や driver 挙動は変えない。実機 run は不要 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| resource scope enter | `async with SwitchGamepad(...)` | transport は open 済み、diagnostics metadata は記録済み、HID advertising は未開始 | state 名は `opened` とする |
| explicit pairing entry | `await pad.pair(timeout=...)` | `transport.start_advertising()` を呼び、incoming 接続完了まで待つ | 既存の `open()` 暗黙 advertising 経路を移す |
| explicit low-level advertising | 必要な場合のみ内部 helper または transport-level API | public API では `start_advertising()` を直接露出しない | 利用者には `pair()` / M6 `connect()` を見せる |
| resource close | `__aexit__` / `close(neutral=True)` | unit_014 の ordering に従い cleanup する | connected でなければ disconnect request は unavailable |
| no implicit pairing | `async with` のみ | `advertising_start` trace は出ない | 破壊的変更として固定する |
| M6 handoff | `connect()` / `reconnect()` | bond reuse reconnect の高水準 API は unit_007 で実装する | この unit では API 形だけを邪魔しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | `async with SwitchGamepad(transport=fake)` は transport を open するが `start_advertising` を呼ばない | breaking | integration | no | red で `start_advertising` が残って失敗し、green で `open()` を resource open に限定した。追加 refactor は不要 |
| refactor-skipped | `await pad.open()` は transport open と report loop 準備だけを行い advertising しない | breaking | integration | no | `test_open_only_does_not_start_advertising` で `opened` state と event `("open",)` を固定 |
| refactor-skipped | `await pad.pair(timeout=...)` は advertising を開始し、fake connected callback で完了する | new | integration | no | `test_pair_starts_advertising_and_waits_for_fake_connection` で `start_advertising` と connected 完了を確認 |
| refactor-skipped | `pair()` timeout は `connection_timeout` diagnostics を残す | regression | integration | no | `pair()` timeout は `advertising` として記録する |
| refactor-skipped | `close(neutral=True)` の connected cleanup ordering は維持される | regression | integration | no | close request / timeout / host-disconnect race tests を resource-scope event order に更新し、integration 全体で確認 |
| refactor-skipped | public API import は Bumble を import しない | regression | unit | no | `test_public_api_import_does_not_import_bumble` を含む boundary tests で確認 |
| done | 明示 `pair()` 後の full handshake から Button A path へ進める | regression | hardware | yes | `test_switch_input_after_full_handshake_for_manual_reflection` で on-wire sequence と checkpoint を確認。UI 反映は自動判定しない |
| done | docs examples は `async with` 後に `connect()` または `pair()` を明示する | docs | docs | no | `spec/initial/api.md` の利用例を更新済み |

## 8. 設計メモ

- `async with` は「接続済み session」ではなく「安全に閉じるための resource scope」とする。
- `connected session scope` が必要になった場合は、後続で `SwitchGamepad.connected(...)` のような classmethod を検討する。M6 前には入れない。
- `pair()` は初回 pairing のための明示 API とする。内部では HID advertising を開始するが、利用者に `start_advertising()` を直接呼ばせない。
- M6 の `connect()` は bond 優先の便利 API として設計する。bond がなければ `allow_pairing=True` の場合だけ `pair()` に進む。
- `wait_connected()` は public API と private helper のどちらにも残さない。接続待ちと timeout diagnostics は `pair()` / M6 `connect()` / `reconnect()` の内部責務に寄せる。
- 互換性は維持しない。既存 examples / tests は破壊的に更新する。
- `open()` 後の state 名は `opened` とする。`advertising` は `pair()` が始まってからの state とする。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | `__aenter__` / `open()` / `pair()` / lifecycle state |
| `src/swbt/transport/base.py` | no change | `open()` / `start_advertising()` の既存 docstring が今回の責務分離と一致しているため変更なし |
| `src/swbt/transport/fake.py` | no change | fake lifecycle event は既存の `open` / `start_advertising` / `connected` を利用 |
| `src/swbt/diagnostics.py` | no change | 既存 `connection_timeout` event の state field で `advertising` を記録 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | `async with` / `open()` / `pair()` の breaking tests |
| `tests/unit/test_public_api_boundary.py` | no change | public API boundary の回帰確認だけを実行 |
| `spec/initial/api.md` | modify | 利用例、context manager、接続 API。仕様整理として更新済み |
| `spec/initial/lifecycle.md` | modify | `open()` と `pair()` / `connect()` の状態遷移。仕様整理として更新済み |
| `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` | modify | この unit を M6 の prerequisite として参照 |

## 10. 検証

実装後の automated gate と unit_015 smoke 結果を記録する。

| command | result | notes |
|---|---|---|
| `uv run ruff format --check .` | pass | 40 files already formatted |
| `uv run ruff check .` | pass | `pair(timeout=...)` は public timeout API として `ASYNC109` を明示抑制 |
| `uv run ty check --no-progress` | pass | all checks passed |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 32 passed |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_async_context_opens_and_closes_fake_transport -q` | pass | first TDD item。red は `start_advertising` が残って失敗、green 後 pass |
| `uv run pytest tests/unit/test_public_api_boundary.py -q` | pass | 5 passed。Bumble import boundary |
| `uv run pytest tests/unit tests/integration -q` | pass | 138 passed |
| `uv run pytest tests/hardware/test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-resource-open-only --log-file .pytest_cache\hardware\unit_015\20260703-004306-resource-open-only\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 0.29s`。`open()` は `transport_open_complete` を記録し、`advertising_start` / `host_connection` を記録しなかった |
| `uv run pytest tests/hardware/test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke --log-file .pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 4.28s`。`pair()` が `advertising_start`、HID L2CAP `connected`、trailing neutral、disconnect terminal、`transport_close_complete` まで到達 |
| `uv run pytest tests/hardware/test_input_operations.py::test_switch_input_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a --log-file .pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 5.46s`。full observed handshake 後に `tap(Button.A)`、neutral、close checkpoint まで到達。Switch UI 反映は自動判定しない |
| `git diff --check -- spec/initial/api.md spec/initial/lifecycle.md spec/complete/unit_015/CONTEXT_MANAGER_RESOURCE_SCOPE.md` | pass | docs whitespace check |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | done。public lifecycle の破壊的変更について、resource-only `open()` smoke、explicit `pair()` close smoke、full handshake 後の Button A path を実行済み |
| 承認範囲 | user approved。実行範囲は adapter open、Classic HID Device initialization、resource-only `open()` without advertising、explicit `pair()` の discoverable / connectable / HID advertising、Switch pairing or existing connection、HID control / interrupt L2CAP open、periodic report loop after `connected`、full observed subcommand handshake、`tap(Button.A)`、neutral、trailing neutral、remote close request、closed event wait、cleanup |
| adapter | `usb:0` |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `.pytest_cache\hardware\unit_015\20260703-004306-resource-open-only\resource-open-only.jsonl`, `.pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a\post-handshake-input.jsonl`, `docs/hardware-test-log.md` |
| cleanup | `pad.close(neutral=True)`。resource-only smoke は advertising に入らず close。pair close smoke と Button A path は disconnect request terminal、transport close complete を記録 |

## 12. 先送り事項

- `connect()` の bond 優先 strategy、`reconnect()`、key store、peer selection は `unit_007` で扱う。
- `SwitchGamepad.connected(...)` のような connected session scope は、利用例が必要になった段階で別 unit に送る。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 実装後に検証結果を記録した
- [x] 完了条件を満たしたら `spec/complete` へ移動する
