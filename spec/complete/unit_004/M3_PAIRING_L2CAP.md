# M3 Pairing / L2CAP 接続 仕様書

## 1. 概要

### 1.1 目的

M2 の Bumble HID transport を使い、Switch との pairing、HID control channel、HID interrupt channel の open を観測できる状態にする。M3 は入力反映の完全確認を完了条件にしない。接続 sequence と切断 event を diagnostics と hardware log に残す。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M3 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| lifecycle | advertising、pairing、connected、disconnect 状態 | `spec/initial/lifecycle.md` |
| transport-bumble | control / interrupt channel、callback 境界 | `spec/initial/transport-bumble.md` |
| testing | hardware test の pairing / L2CAP 項目 | `spec/initial/testing.md` |
| hardware-harness skill | pairing と channel open の承認境界 | `.agents/skills/hardware-harness/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| developer | Switch の pairing 操作 | `swbt-python` device が Switch 側に見える | 明示承認が必要 |
| transport | HID control channel open | connected 判定に必要な event が diagnostics に残る | channel ready 条件を明確にする |
| transport | HID interrupt channel open | input / reply を送れる channel として記録される | 入力反映は M5 |
| developer | 手動 close または Switch 側 disconnect | disconnect event と cleanup 結果が残る | reconnect は M6 |

## 2. 対象範囲

- Switch pairing 手順の実機確認。
- HID control channel open の検出。
- HID interrupt channel open の検出。
- connected 判定の定義。
- disconnect event と reason の記録。
- pairing 失敗時の raw event / trace 記録。
- hardware test log への OS、driver、dongle、Bumble、Switch model / firmware 記録。

## 3. 対象外

- 入力反映の完全確認。
- `tap(Button.A)` の実機通過。
- subcommand reply 不足の修正全体。
- reconnect。
- 複数 Switch model の互換性保証。
- 複数 controller。

## 4. 関連 docs

- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/complete/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | deferred | M3 では channel open までを扱う。channel open 後に Switch から来る初期 output report の report ID と sequence は M4 の実機 trace で記録する |
| Bumble / transport | required | done | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` の `bumble_l2cap_connection_events` で、Bumble 0.0.230 の HID control / interrupt PSM、channel ready field、connection request、connection / pairing / disconnection event 名を source fact として記録した。実機 trace では Classic HID path の pairing marker として `classic_pairing` が出た |
| discovery identity | required | done | `swbt_daemon_reference_discovery_identity` と `swbt_daemon_reference_discovery_identity_hci` で、リファレンス実装の local name `Pro Controller` と Class of Device `0x002508` を implementation fact / hardware observation として分離して記録した |
| OS / driver / adapter | required | done | `docs/hardware-test-log.md` と `swbt_python_adapter_driver_boundary` に、Windows / CSR8510 A10 / WinUSB / Bumble 0.0.230 / Python 3.13.5 / `usb:0` 条件での M3 pairing / L2CAP pass を hardware observation として記録した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| advertising visible | Switch pairing UI | device が発見可能になる | M2 の advertising が前提 |
| pairing complete | Switch が pairing を進める | pairing complete 相当の event を diagnostics に記録する | Bumble event 名は実装時に確認 |
| control channel open | L2CAP control ready | `l2cap_channel_open` に channel=`control` を記録する | trace schema に従う |
| interrupt channel open | L2CAP interrupt ready | `l2cap_channel_open` に channel=`interrupt` を記録する | 両 channel ready で connected |
| connected state | 両 channel ready | `SwitchGamepad` state が `connected` になる | `wait_connected()` が完了 |
| disconnect | Switch 側または手動 close | reason、cleanup、final state を記録する | reconnect はしない |
| pairing failure | timeout または error | 失敗位置と raw event を残す | 未対応 subcommand は M4 へ |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | fake channel event で control / interrupt 両方が ready になった時だけ `connected` になる | new | integration | no | `test_fake_l2cap_channels_must_both_open_before_wait_connected_completes` |
| green | `wait_connected()` が connected event で完了する | regression | integration | no | `test_wait_connected_completes_after_fake_connected_callback` |
| green | disconnect callback で state が neutral へ戻り report loop が停止する | regression | integration | no | `test_disconnect_callback_neutralizes_state_and_stops_report_loop` |
| green | pairing timeout が diagnostics に失敗位置を残す | new | integration | no | `test_wait_connected_timeout_records_failure_position_in_trace` |
| observed | Switch pairing UI から device が見える | new | hardware | yes | 2026-07-01 pass run では Switch から incoming connection が到達した。UI 表示そのものの人間観測は未記録 |
| green | Switch と Classic pairing complete まで進む | new | hardware | yes | trace は `classic_pairing` を記録。debug log は `HCI_SIMPLE_PAIRING_COMPLETE_EVENT` success を記録 |
| green | HID control channel open が trace に残る | new | hardware | yes | `l2cap_channel_open channel=control psm=0x0011` を確認 |
| green | HID interrupt channel open が trace に残る | new | hardware | yes | `l2cap_channel_open channel=interrupt psm=0x0013` と `connected` を確認 |
| observed | 手動 close で transport が停止し adapter が release される | new | hardware | yes | `pad.close(neutral=True)` が走り、`disconnected reason=0` と `transport_close_complete` を確認した |

## 8. 設計メモ

- connected 判定は「HID control / interrupt channel の両方が利用可能」を基準にする。
- M3 では `0x21` reply の不足を深追いしない。観測された output report と subcommand sequence は M4 の入力にする。
- 実機観測は `hardware observation` として扱い、別 dongle や別 firmware の一般事実にしない。
- `wait_connected(timeout=...)` の timeout 値は test と manual bring-up で明示する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/bumble.py` | modify | pairing / L2CAP event bridge |
| `src/swbt/gamepad.py` | modify | advertising 起動、connected / disconnect、wait_connected timeout |
| `src/swbt/transport/fake.py` | modify | control / interrupt channel ready の fake event |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | fake channel event、disconnect、timeout diagnostics |
| `tests/unit/test_bumble_transport.py` | modify | Bumble L2CAP / pairing / disconnect event bridge |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | Bumble L2CAP / connection event の source fact |
| `tests/hardware/test_pairing_l2cap.py` | new | pairing / L2CAP hardware test skeleton |
| `docs/hardware-test-log.md` | modify | timeout と pass の実機観測を追記 |

## 10. 検証

この表は M3 の非実機実装、timeout 切り分け、discovery identity 修正後の実機 pass を示す。

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 41 packages resolved / checked |
| `uv run pytest tests\unit\test_bumble_transport.py tests\unit\test_source_audit_fixtures.py tests\unit\test_hardware_test_log_docs.py -q` | pass | 17 passed。Bumble event bridge、connection request diagnostics、source audit fixture、hardware log table を確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | 19 passed。fake L2CAP、disconnect fail-safe、timeout diagnostics を確認した |
| `uv run ruff format --check .` | pass | 36 files already formatted |
| `uv run ruff check .` | pass | lint pass |
| `uv run ty check --no-progress` | pass | type check pass |
| `uv run pytest tests\unit -q` | pass | 86 passed |
| `uv run pytest tests\integration -q` | pass | 19 passed |
| `uv run pytest tests\hardware --collect-only -q` | pass | 2 tests collected。実機・adapter open は未実行 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-223511 -q -s` | fail | `ConnectionTimeoutError` after 60s。trace は `advertising_start` 後に `connection_timeout state=advertising`。`host_connection`、pairing、L2CAP は未観測。結果は `docs/hardware-test-log.md` に記録した |
| `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-224227 --log-file .pytest_cache\hardware\unit_004\20260701-224227\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | `ConnectionTimeoutError` after 60s。trace は `advertising_start` 後に `connection_timeout state=advertising`。追加した `connection_request` も未観測。debug log では local name、class of device、scan enable、extended inquiry response write まで確認。結果は `docs/hardware-test-log.md` に記録した |
| `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-225502 --log-file .pytest_cache\hardware\unit_004\20260701-225502\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | connection、Classic pairing、control / interrupt L2CAP open、`connected` までは到達。test oracle が `pairing_start` を期待していたため fail。trace では Classic HID path の marker は `classic_pairing` だった |
| `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-225624 --log-file .pytest_cache\hardware\unit_004\20260701-225624\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | 1 passed, 1 warning in 6.81s。trace は `device_name="Pro Controller"`、`class_of_device="0x002508"`、`host_connection`、`classic_pairing`、control / interrupt `l2cap_channel_open`、`connected`、neutral `report_tx`、`transport_close_complete` を記録 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | adapter open、HID advertising、Switch pairing、HID control / interrupt channel open、manual close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `docs/hardware-test-log.md`、diagnostics JSON Lines trace |
| cleanup | pairing run 後に advertising 停止、transport close、必要なら Switch 側登録解除手順を記録 |

今回実装した hardware test は、承認後に次の範囲で実行できる。

```console
uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\<timestamp> -q
```

この command は USB Bluetooth dongle open、HID advertising、Switch pairing、HID control / interrupt channel open、`pad.close(neutral=True)` による cleanup を含む。2026-07-01 の `20260701-225624` run では pass し、M3 の接続観測は完了した。input reflection、subcommand の意味的処理、reconnect は含まない。

## 12. 先送り事項

- subcommand reply 不足の補正は M4 で扱う。
- input reflection は M5 で扱う。
- reconnect と key store は M6 で扱う。
- discovery identity 変更が timeout 解消の原因だった可能性は高いが、手動操作 timing を含む controlled A/B ではないため、因果は inference として扱う。

## 13. チェックリスト

このチェックリストは M3 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] pairing / L2CAP event の根拠監査を実施し、状態を更新した
- [x] M3 の local automated gate を実行し、検証欄を結果で更新した
- [x] 実機走行できる hardware test command を用意し、実行直前で中断した
- [x] 実機検証は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [x] 完了条件の最終確認後に `spec/complete` へ移動する
