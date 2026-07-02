# Device close / graceful disconnect 仕様書

## 1. 概要

### 1.1 目的

`async with SwitchGamepad(...)` を抜ける時と `close(neutral=True)` を呼ぶ時の後始末を、reconnect より先に固定する。接続済みなら trailing neutral を送った後、可能なら HID / L2CAP の close request を出し、closed event または bounded timeout を確認してから transport を閉じる。close request が使えない、失敗する、または closed event が来ない場合でも、`SwitchGamepad` は内部 state を neutral に戻し、report loop と adapter resource を閉じ切る。

この unit は reconnect 成否を扱わない。M6 reconnect / key store は、この unit の close / disconnect contract が決まった後に扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | `with` で開く device は後始末を明確にし、接続済みなら close 通知を入れて閉じる。reconnect の前に詰める | conversation 2026-07-02 |
| lifecycle | `close(neutral=True)` は neutral report、report loop stop、transport close、callback 解除、closed 遷移を行う | `spec/initial/lifecycle.md` |
| transport-bumble | `HidDeviceTransport` は open / advertising / close / send / callback を持つ。unit_014 で内部 cleanup 用の `request_disconnect()` 境界を追加した | `spec/initial/transport-bumble.md`, `src/swbt/transport/base.py` |
| completed M1 | fake transport で `async with`、`close(neutral=True)`、trailing neutral は確認済み。link 接続済みの remote close は対象外 | `spec/complete/unit_002/M1_SWITCH_GAMEPAD_FAKE_TRANSPORT.md` |
| completed M3 | manual close で `transport_close_complete` は観測済み。reconnect と close request ordering は対象外 | `spec/complete/unit_004/M3_PAIRING_L2CAP.md` |
| completed M5 | post-handshake input run の `finally` で `pad.close(neutral=True)` を実行し、final neutral と `transport_close_complete` を記録 | `docs/hardware-test-log.md` |
| swbt-daemon reference | shutdown graceful disconnect は neutral、HID disconnect request、closed event or timeout、HCI power-off を分けて実装済み | `E:/documents/VSCodeWorkspace/swbt-daemon/work-units/complete/local_100/SHUTDOWN_GRACEFUL_DISCONNECT.md` |
| Bumble source | Bumble 0.0.230 の `Device` には channel 別 disconnect helper と channel close callback がある | `.venv/Lib/site-packages/bumble/hid.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `async with SwitchGamepad(...)` を抜ける | `close(neutral=True)` と同じ後始末が走る | exception / cancellation でも実行する |
| library user | connected 状態で `await pad.close(neutral=True)` | neutral、disconnect request、closed or timeout、transport close の順序が diagnostics に残る | close request は最善努力 |
| library user | advertising 中または未接続で `close()` | disconnect request boundary は `unavailable` を返し、transport resource を閉じる | trailing neutral は送れない |
| transport | Switch 側 disconnect callback | 内部 state を neutral にし、report loop と transport を一度だけ閉じる | wire 上 neutral は送れないことがある |
| maintainer | reconnect 実装前 | 前回 close の終端状態と未完了 disconnect が残っていないことを説明できる | M6 の前提条件 |

## 2. 対象範囲

- `SwitchGamepad.__aexit__` と `SwitchGamepad.close(neutral=True)` の close ordering。
- connected 状態での trailing neutral、report loop stop、remote close request、closed event wait、bounded timeout、transport close。
- host disconnect callback と user initiated close の競合処理。
- close request unavailable / failed / timeout / already disconnected の diagnostics。
- `HidDeviceTransport` の remote close request boundary。名前は実装時に `request_disconnect()` などで固定する。
- `BumbleHidTransport` が Bumble の channel disconnect helper を使えるかの source audit と unit test。
- fake transport integration test による close sequence の固定。
- 実機承認が得られた場合の close ordering characterization。

## 3. 対象外

- reconnect、key store、pairing-free reconnect。これは `unit_007`。
- L+R / stick semantic input reflection。これは `unit_013`。
- Switch-facing report bytes、subcommand reply payload、SPI、rumble の変更。
- public API としての明示的な `disconnect()` command 追加。
- daemon IPC 互換。
- 複数 controller、adapter removal recovery、automatic retry。

## 4. 関連 docs

- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/complete/unit_002/M1_SWITCH_GAMEPAD_FAKE_TRANSPORT.md`
- `spec/complete/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/complete/unit_004/M3_PAIRING_L2CAP.md`
- `spec/complete/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `docs/hardware-test-log.md`
- `E:/documents/VSCodeWorkspace/swbt-daemon/work-units/complete/local_100/SHUTDOWN_GRACEFUL_DISCONNECT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done for neutral bytes / no new bytes | trailing neutral は既存 `0x30` input report を使う。新しい report layout は追加しない |
| Bumble / transport | required | done for source, unit tests, and hardware | Bumble 0.0.230 の `disconnect_interrupt_channel()`、`disconnect_control_channel()`、`on_l2cap_channel_close()` を source fact として確認し、`BumbleHidTransport.request_disconnect()` と L2CAP close bridge を unit test で固定した。2026-07-02 の修正前 hardware run では Switch 実機で L2CAP close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed` まで観測したが、`transport_close_complete` が欠落した。race 修正後の rerun では `connected`、neutral `0x30`、L2CAP close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete` を観測した |
| OS / driver / adapter | required | observed | Windows / CSR8510 A10 / WinUSB / `usb:0` で、修正後の connected close ordering を観測した。artifact は `.pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\close-disconnect.jsonl` |

### 5.1 監査済み事実 / 仮説

| 項目 | 分類 | source | status |
|---|---|---|---|
| `SwitchGamepad.close()` は trailing neutral、report loop stop、`request_disconnect()`、closed event wait or 250 ms timeout、transport close の順で処理する | implementation fact | `src/swbt/gamepad.py`, `tests/integration/test_switch_gamepad_fake_transport.py` | current |
| `HidDeviceTransport` は `request_disconnect()` を持ち、`requested` / `unavailable` / `failed` を `DisconnectRequestResult` で返す | implementation fact | `src/swbt/transport/base.py`, `tests/unit/test_public_api_boundary.py` | current |
| `BumbleHidTransport.close()` は runtime close と handle close を行い、`transport_close_complete` を記録する | implementation fact | `src/swbt/transport/bumble.py` | current |
| Bumble 0.0.230 `Device` は control / interrupt channel 別の disconnect helper を持つ | source fact | `.venv/Lib/site-packages/bumble/hid.py:257`, `.venv/Lib/site-packages/bumble/hid.py:264` | local package source |
| Bumble 0.0.230 `Device` は L2CAP channel close callback で control / interrupt channel field を `None` にする | source fact | `.venv/Lib/site-packages/bumble/hid.py:298` | local package source |
| swbt-daemon は shutdown graceful disconnect で neutral、HID disconnect request、closed event or 250 ms timeout、power-off を分けた | implementation fact / hardware observation | `E:/documents/VSCodeWorkspace/swbt-daemon/work-units/complete/local_100/SHUTDOWN_GRACEFUL_DISCONNECT.md` | reference |
| swbt-daemon の 250 ms は正常 close の待機値ではなく、closed event 欠落時の shutdown 継続上限である | implementation fact | `E:/documents/VSCodeWorkspace/swbt-daemon/work-units/complete/local_100/SHUTDOWN_GRACEFUL_DISCONNECT.md:132` | reference |
| swbt-python の close request wait は 250 ms を初期 default とする | implementation fact / inference | `src/swbt/gamepad.py`, swbt-daemon reference | hardware characterization observed-pass |
| Bumble channel disconnect helper を interrupt、control の順で呼ぶ | implementation fact | `src/swbt/transport/bumble.py`, `tests/unit/test_bumble_transport.py` | unit tested |
| Bumble channel disconnect helper を呼べば Switch 側 graceful close と同等に扱える | unverified hypothesis | Bumble local source + daemon reference | hardware characterization required |
| user close 中の disconnected callback が transport final close を先取りすると、`close()` 本体の terminal 記録と callback cleanup の順序が崩れる | implementation fact / hardware observation | `.pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\close-disconnect.jsonl`, `tests/integration/test_switch_gamepad_fake_transport.py` | reproduced and fixed in `0979bd4` |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| context exit | `async with` の正常終了、例外、cancel | `close(neutral=True)` を呼び、後始末を一度だけ実行する | `__aexit__` は例外を握りつぶさない |
| connected close | `connected` で `close(neutral=True)` | state を `disconnecting` にし、trailing neutral を送ってから periodic report loop を止める | neutral 送信失敗は diagnostics に残し close 継続 |
| close request | control / interrupt channel が connected | transport が remote close request を出し、request event を diagnostics に残す | Bumble では interrupt、control の順で channel helper を呼ぶ |
| close confirmation | disconnected callback または channel close が来る | close request の terminal state を `closed` として記録し、transport close へ進む | event の重複は一度だけ扱う |
| close timeout | close request 後に closed event が来ない | bounded timeout を記録し、transport close へ進む | timeout は shutdown を詰まらせない上限 |
| close unavailable | 未接続、helper なし、channel なし | disconnect request は unavailable として記録し、transport close へ進む | failure ではなく分岐 |
| host disconnect | Switch 側または transport 由来 disconnect | reason を記録し、state neutral、report loop stop、transport close を一度だけ行う | trailing neutral は送れない場合がある |
| idempotent close | close 中または closed 後に再度 `close()` | duplicate request や duplicate close を出さない | lifecycle lock で直列化する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | `HidDeviceTransport` に remote close request boundary を追加し、Bumble 型を public API に漏らさない | new | unit | no | `DisconnectRequestResult` と `request_disconnect()` を追加。`test_hid_transport_disconnect_request_boundary_uses_plain_types` |
| done | connected `close(neutral=True)` が trailing neutral、report loop stop、disconnect request、transport close の順で進む | new | integration | no | `test_connected_close_requests_disconnect_after_trailing_neutral` |
| done | `async with` 退出時に close request path が走り、例外は再送出される | regression | integration | no | `test_async_context_exception_requests_disconnect_and_reraises` |
| done | close request closed event で timeout を cancel し、transport close が一度だけ呼ばれる | new | integration | no | `test_close_waits_for_disconnect_request_closed_event_once`。duplicate callback も固定 |
| done | user close 中の disconnected callback は final transport close を横取りせず、`close()` 本体が terminal 記録後に close する | regression | integration | no | `test_close_request_disconnected_callback_leaves_final_close_to_user_close`。修正前 hardware run の `transport_close_complete` 欠落を fake で再現 |
| done | close request timeout でも transport close と final state `closed` へ進む | edge | integration | no | 250 ms default。test では monkeypatch で 1 ms に短縮 |
| done | close request unavailable / failed でも close が完了し、diagnostics に terminal state が残る | edge | integration | no | `test_close_without_connection_records_disconnect_unavailable`, `test_close_request_failure_records_failure_and_closes_transport` |
| done | host disconnect callback と user close が競合しても state neutral、report loop stop、transport close が一度だけになる | edge | integration | no | `test_host_disconnect_racing_user_close_closes_once_and_neutralizes_state` |
| done | Bumble 0.0.230 source に基づき control / interrupt channel disconnect helper の呼び出しを unit test で固定する | new | unit | no | `test_bumble_request_disconnect_calls_interrupt_then_control_helpers`。片側 channel と helper failure も固定 |
| done | diagnostics trace が requested / closed / timeout / unavailable / failed を分ける | new | integration | no | `disconnect_request` と `disconnect_request_terminal` を fake integration で確認 |
| done | hardware run で connected close の neutral、disconnect request or unavailable、closed or timeout、transport close ordering を記録する | characterization | hardware | yes | 明示承認後に実行。修正後 run は `connected`、neutral `0x30`、L2CAP close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete`、`manual_close_checkpoint close_complete` まで観測 |

## 8. 設計メモ

- close request は `SwitchGamepad` の public command ではなく、transport cleanup の内部境界として始める。
- `close(neutral=True)` の主目的は入力安全と resource cleanup である。remote close request の確認は品質向上だが、失敗しても `close()` が戻れない設計にしない。
- daemon reference は BTstack の `hid_device_disconnect(hid_cid)` 由来であり、Bumble では同一 API ではない。事実として再利用するのは「neutral と link close と adapter close を分ける設計」であって、関数名や event 名をそのまま移植しない。
- Bumble の channel 別 disconnect helper は interrupt、control の順で呼ぶ。片側 channel だけ残っている場合は残存 channel だけ requested として扱う。
- `disconnecting` 中の新規 input command は `ReportLoop` 停止後なら `ClosedError`、停止前なら既存の state update として扱う。public API として disconnecting 中の command ordering は保証しない。
- callback 解除 surface は追加していない。host disconnect では callback 側が transport を閉じる。user close 中に disconnected callback が来た場合は、callback 側では neutral / report loop stop まで行い、final transport close は `close()` 本体に残す。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/base.py` | modify | remote close request boundary |
| `src/swbt/transport/fake.py` | modify | disconnect request / closed / timeout simulation |
| `src/swbt/transport/bumble.py` | modify | Bumble channel disconnect helper bridge |
| `src/swbt/gamepad.py` | modify | close ordering、競合、diagnostics |
| `src/swbt/diagnostics.py` | no change | 既存 `DiagnosticsRecorder.record_event()` で close request terminal state を記録 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | close sequence tests |
| `tests/unit/test_bumble_transport.py` | modify | Bumble disconnect helper tests |
| `tests/hardware/test_close_disconnect.py` | add | close ordering characterization test |
| `docs/hardware-test-log.md` | modify | 実機 close ordering observation |
| `spec/wip/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md` | modify | 実装結果、検証、checklist |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | Resolved 41 packages、Checked 41 packages |
| `uv run ruff format --check .` | pass | 39 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed after race fix |
| `uv run pytest tests/unit/test_bumble_transport.py -q` | pass | 22 passed in 0.25s |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_close_request_disconnected_callback_leaves_final_close_to_user_close -q` | red then pass | 修正前は disconnected callback が fake transport close で停止し timeout。`0979bd4` 後は 1 passed in 0.10s |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 31 passed in 0.51s |
| `uv run pytest tests\unit\test_bumble_transport.py tests\unit\test_public_api_boundary.py -q` | pass | 27 passed in 0.43s |
| `uv run pytest tests/unit -q` | pass | 104 passed in 0.56s |
| `uv run pytest tests/integration -q` | pass | 31 passed in 0.49s |
| `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a --log-file .pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | 修正前 run。`connected`、trailing neutral、L2CAP close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed` まで到達したが、`transport_close_complete` 欠落で fail |
| `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix --log-file .pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | 修正後 run。`advertising_start` 後に `host_connection` が来ず、60 秒で `ConnectionTimeoutError` |
| `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry --log-file .pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | 修正後 rerun。1 回目と同じ pre-connection timeout。connected close ordering は未検証 |
| `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity --log-file .pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | 1 passed, 1 warning in 6.80s。`connected`、neutral `0x30`、L2CAP close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete`、`manual_close_checkpoint close_complete` を観測 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for hardware characterization |
| 承認範囲 | adapter open、HID advertising、pairing or existing connection、HID control / interrupt channel open、periodic report loop、trailing neutral、remote close request、closed event wait or timeout、transport close |
| adapter | `usb:0` など、専用 USB Bluetooth dongle の具体的 adapter string |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、pytest log、Bumble debug log、human cleanup observation |
| cleanup | neutral、report loop stop、remote close request terminal state、transport close、adapter release。close request failure 時も adapter release を確認する |

## 12. 先送り事項

- reconnect / key store / pairing-free reconnect は `unit_007`。この unit の close / disconnect contract 完了後に扱う。
- L+R / stick semantic reflection は `unit_013`。
- automatic retry と adapter removal recovery は初期対象外。
- close request timeout 値を 250 ms 以外にする必要が出た場合は、Bumble / Switch 実機観測と理由をこの spec に記録してから変更する。

## 13. チェックリスト

このチェックリストは unit_014 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] reconnect 前に close / disconnect cleanup unit として切り出した
- [x] swbt-daemon の shutdown graceful disconnect reference を source として分離した
- [x] Bumble 0.0.230 の local source 事実と未検証仮説を分けた
- [x] TDD item を red / green / refactor で実装した
- [x] unit / integration gate を実行し、検証欄を結果で更新した
- [x] 実機承認、command、artifact、cleanup、結果を記録した
- [x] `unit_007` reconnect 着手前の前提条件として反映した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
