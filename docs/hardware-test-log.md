# Hardware Test Log

Bumble adapter と対象機器に依存する観測を記録する正本である。

実機観測は、OS、driver、dongle、adapter string、Bumble version、Python version、Switch model / firmware に依存する。ここに記録した結果は、その条件での観測であり、別構成での保証には使わない。

## Current Status

- Hardware run: 2026-07-01 に CSR8510 A10 / WinUSB / `usb:0` で M2 advertising smoke と M3 pairing / L2CAP pass
- Bumble adapter run: adapter open、Bumble Device 初期化、Classic HID 初期化、SDP / HID descriptor 登録、discoverable / connectable、close を記録済み
- Pairing run: 2026-07-01 に `Pro Controller` / Class of Device `0x002508` で M3 pairing / L2CAP pass。`classic_pairing`、HID control / interrupt channel open、`connected` を記録済み
- Subcommand run: 2026-07-02 に Classic default link policy `0x0005` のみを残した最小実装で M4 subcommand sequence が pass。続く observation window run では Bumble ACL queue drain 後、5 秒以上の実機観測で `0x02` 1 件と `0x08` 8 件を受信し、全件に `0x21` reply を送信した。trace は `classic_link_policy_configured`、Switch からの `0x01` output report、`subcommand_rx`、`subcommand_reply_tx`、`report_tx` reason `subcommand_reply` 9 件を記録し、`unsupported_subcommand` と `error` は 0 件だった。debug log は `packets in flight` backlog 行 0 件だった。link policy 反映前の試行では、HIDP DATA header 除去、SET_REPORT callback、control channel output report、HID SDP policy、service name / language base、daemon-aligned `0x8e` / `0x80` prefix、HID L2CAP local MTU `100` を反映しても `output_report_rx` 未観測のまま Switch 側 reason 19 で切断されていた
- Input reflection run: 2026-07-02 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で M5 input operation sequence を実行した。pytest は `1 passed` だが、これは接続、subcommand reply、`0x30` report 送信、manual checkpoint、clean close を確認するだけで、Switch UI 反映を自動判定しない。初回ユーザ画面観測では Switch のデバイス登録画面が全く動かなかったため、M5 の semantic input reflection は observed-fail。debug log では A button bytes `08 00 00`、L+R button bytes `40 00 40`、neutral bytes `00 00 00` を含む `a1 30` HID interrupt send は確認済み。後続の pairing diagnostics run では `link_key_available` と `connection_encryption_change` は出たが、`pairing_complete` と `connection_authentication` は出ず、Switch は `0x02` と repeated `0x08` から進まなかった。daemon `local_037` の実機履歴では `0x21` reply timer 固定を shared input report timer に直すと repeated `0x08` から `0x10` / `0x03` へ進んだため、swbt-python でも shared timer / reply holdoff を実装した。2026-07-02 shared timer rerun では `0x02`、`0x08`、`0x10`、`0x03`、`0x04`、`0x40`、`0x30`、`0x48`、`0x21`、`0x30` まで進み、ユーザは Switch 側で pairing 完了を目視した。続く post-handshake input run では full observed handshake 後に `tap(Button.A)` を送信し、ユーザは Switch UI への A 反映と neutral 後の入力残りなしを目視した。
- Close disconnect run: 2026-07-02 の unit_014 connected close run は `connected` 後に non-neutral 入力を送らず、trailing neutral、Bumble L2CAP channel close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed` まで観測した。初回は `transport_close_complete` が trace に出ず、user close 中の disconnected callback が final close を先取りする race として fake integration test で再現し、`0979bd4` で修正した。修正後の rerun では `host_connection`、control / interrupt L2CAP open、`connected`、neutral `0x30`、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete`、`manual_close_checkpoint close_complete` まで通過した。後続の visibility 調査で Bumble 0.0.230 の `power_off()` だけでは Classic scan が残ることを確認し、close cleanup に `set_discoverable(False)` / `set_connectable(False)` を追加した。修正後の close disconnect rerun は `1 passed`、final `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0` `SUCCESS` まで確認した。この run は full observed subcommand handshake 後 close ではなく、HID control / interrupt L2CAP `connected` 直後の close ordering を確認する。最後に full observed handshake 後、Button A で登録画面を抜け、neutral、disconnect、post-close UI 確認まで行う path を実行し、ユーザは登録画面脱出と接続解除を目視した。Bumble 0.0.230 の incoming Classic connection handler が deprecated `send_command_sync()` を使う警告は host listener bridge で `AsyncRunner.spawn(host.send_async_command(...))` へ差し替えて解消し、同じ path は `-W error` 付きで `1 passed in 7.85s` になった。
- Subcommand follow-up: 2026-07-02 にユーザが疎通不良を疑ったため、non-neutral 入力なしで subcommand observation window を再実行した。run は `advertising_start` まで進んだが `host_connection` が来ず、60 秒で `ConnectionTimeoutError` になった。この観測は、Switch からの output report / subcommand / `0x21` reply 疎通を確認できていない。
- Problem investigation: 2026-07-02 の L2CAP-only follow-up でも `advertising_start` まで進んだ後、`host_connection` が来ず 60 秒 timeout した。少なくともこの時点の問題は subcommand reply や input report ではなく、Switch が advertised `Pro Controller` へ接続要求を出していない段階にある。
- Problem retry: 2026-07-02 に Switch 側を接続画面へ入り直した想定で L2CAP-only check を再試行したが、再び `advertising_start` 後に `host_connection` が来ず 60 秒 timeout した。HCI debug log にも `HCI_CONNECTION_REQUEST_EVENT` はなかった。
- New pairing attempt: 2026-07-02 にユーザが Switch 側の pairing 情報削除と新規追加画面での探索を確認した状態で L2CAP-only check を再試行した。Bumble 側は `Pro Controller` / Class of Device `0x002508` / extended inquiry response を設定し、最終的な `scan_enable: 3` も成功したが、`host_connection` と HCI `HCI_CONNECTION_REQUEST_EVENT` は来ず 60 秒 timeout した。この run は pairing 失敗ではなく、pairing 開始前の discovery / connection request 未到達として扱う。
- Discovery visibility hold: 2026-07-02 に `usb:0` を `Pro Controller` として 90 秒間 discoverable / connectable に保持した。trace は `advertising_start`、`manual_advertising_hold_start duration_seconds=90`、`manual_advertising_hold_complete`、`transport_close_complete` を記録したが、`host_connection` は記録しなかった。外部 scanner から見えたかどうかはこの artifact だけでは確定できない。
- Close cleanup scan disable: 2026-07-02 に close cleanup を修正後、`usb:0` を 5 秒間だけ `Pro Controller` として advertise し、close で Classic scan を停止する診断を実行した。trace は `host_connection` を記録し、debug log は close path の `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0` が `SUCCESS` で完了したことを記録した。ユーザは iPhone 側で `Pro Controller` 表示が消えたことを目視した。
- Context manager resource scope run: 2026-07-03 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で unit_015 smoke を実行した。`open()` only smoke は `transport_open_complete` と `transport_close_complete` を記録し、`advertising_start` と `host_connection` を記録しなかった。`pair()` close smoke は `advertising_start`、`connection_request`、`host_connection`、`classic_pairing`、HID control / interrupt L2CAP open、`connected`、trailing neutral `0x30`、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete` を記録した。Button A path は full observed handshake 後に `tap(Button.A)`、neutral、close まで到達し、`manual_input_checkpoint post_handshake_tap_a_complete` と `post_handshake_neutral_complete` を記録した。この pytest は on-wire sequence と checkpoint を確認するが、Switch UI 反映は自動判定しない。
- Reconnect key store run: 2026-07-03 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で unit_007 reconnect keystore characterization を実行した。起動条件記録なしの初回 run は active reconnect の条件としては inconclusive。起動条件を trace に残す split run では、初回 pairing を controller search / change grip order screen で行い、`key_store_update status=succeeded` を記録した。2本目の active reconnect は HOME / 通常画面条件で保存済み peer 1 件を選択した。修正前は `Device.connect(..., BR_EDR)` 後に HID control の `L2CAP_CONNECTION_REQUEST` PSM `0x0011` を先に送信し、Switch 側 reason 5 `AUTHENTICATION_FAILURE_ERROR` で切断された。`Connection.authenticate()` と `Connection.encrypt(True)` を HID L2CAP 前に明示した修正後は、`connection_authentication authenticated=true`、`connection_encryption_change encryption=1`、HID control / interrupt L2CAP open、`connected`、`active_reconnect_result status=connected` を記録した。この active reconnect trace では `advertising_start`、`classic_pairing`、`key_store_update` は出ていない。3本目の incoming run は controller search / change grip order screen で `incoming_connection route=incoming` を記録し、active reconnect event を出さなかった。ただし `classic_pairing`、`link_key_available`、`key_store_update status=succeeded` も出たため、pairing-free incoming bond reuse とは扱わない。
- Packaging CLI pair probe: 2026-07-03 に unit_008 の `swbt-probe pair` を承認済み範囲で実行した。初回は `usb:0` を開き、Classic HID Device 初期化、SDP 登録、HID advertising、trace 保存まで到達したが、30 秒間 `host_connection` が来ず `ConnectionTimeoutError` で終了した。ユーザが Switch 側を接続待ちにして再実行した retry では、`connection_request`、`host_connection`、`classic_pairing`、HID control / interrupt L2CAP open、`connected`、key store write、close cleanup まで到達した。retry trace は one neutral `0x30` report と `transport_close_complete` を記録し、non-neutral input は送っていない。
- Unit 019 follow-up smoke: 2026-07-03 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で `test_switch_pairing_l2cap_records_diagnostics` を実行した。Switch を接続待ち画面にした状態で、`connection_request`、`host_connection`、`classic_pairing`、`link_key_available`、`key_store_update status=succeeded`、HID control / interrupt L2CAP open、`connected`、one neutral `0x30`、disconnect request、`transport_close_complete` を記録した。non-neutral input は送っていない。
- Unit 013 input semantics setup: 2026-07-04 に Switch 2 / firmware 22.1.0 / `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で fresh key store setup を実行した。Switch を controller search / change grip order screen に置き、`input-semantics-key-store.json` を作り直した。trace は `key_store_exists=false`、`active_reconnect_result status=no_bond`、`connect_pairing_fallback route=pairing`、`classic_pairing`、`link_key_available`、`key_store_update status=succeeded`、HID control / interrupt L2CAP open、`connected`、full observed subcommand handshake、`manual_input_checkpoint operation=handshake_complete`、close cleanup を記録した。non-neutral input は送っていない。これは unit_013 の後続 active reconnect 入力検証に使う前提 artifact であり、button / D-pad / stick の semantic reflection は後続 run で実行した。
- Unit 013 button check trace: 2026-07-04 に同じ artifact dir の key store を使い、Switch を「ボタンの動作チェック」選択画面直前で待機させて active reconnect button check run を実行した。trace は `key_store_exists=true`、保存済み peer 1 件、`active_reconnect_attempt`、`connection_authentication authenticated=true`、`connection_encryption_change encryption=1`、HID control / interrupt L2CAP open、`active_reconnect_result status=connected`、full observed subcommand handshake、A entry checkpoint、L+R hold checkpoint、neutral checkpoint、`transport_close_complete` を記録した。active reconnect trace には `advertising_start`、`classic_pairing`、`key_store_update` は出ていない。初回のユーザ目視では L ボタンだけが押されているように見え、L+R 同時押し表示は確認できなかった。
- Unit 013 button split diagnosis: 2026-07-04 に同じ button check screen 条件で R-only、L-only、L+R を別 checkpoint として送る再実験を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、`hold_r_only`、`hold_l_only`、`hold_lr_together`、neutral、`transport_close_complete` を記録した。debug log から抽出した `0x30` input report の button bytes は R-only `400000` が 30 件、L-only `000040` が 29 件、L+R `400040` が 30 件だった。ユーザは、Switch のボタンチェック UI は同時押しに対応しておらず片方だけしか UI に反映しないらしい、ひとまず pass 扱いでよい、と判断した。unit_013 のボタン側は、この構成で hardware-pass とする。
- Unit 013 D-pad button check: 2026-07-04 に同じ button check screen 条件で D-pad up、right、down、left を別 checkpoint として送る実験を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、`hold_dpad_up`、`hold_dpad_right`、`hold_dpad_down`、`hold_dpad_left`、各方向後の neutral、`transport_close_complete` を記録した。trace 上の expected button bytes は up `000002`、right `000004`、down `000001`、left `000008` だった。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは UI 側の反映も確認したため、D-pad 側は hardware-pass とする。
- Unit 013 left stick trace: 2026-07-04 に同じ artifact dir の key store を使い、Switch を「スティックの補正」選択画面直前で待機させて active reconnect left stick run を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、left stick hold、16-step circle、neutral、`transport_close_complete` を記録した。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは left stick の目視確認ができたと報告した。ただし、回転が速すぎたか画面遷移を考慮できていなかったため、直ぐに終わってしまったようにも見える、という留保がある。
- Unit 013 right stick trace: 2026-07-04 に同じ artifact dir の key store を使い、Switch を「スティックの補正」選択画面直前で待機させて active reconnect right stick run を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、right stick hold、16-step circle、neutral、`transport_close_complete` を記録した。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは目視完了と報告したが、回転が速すぎて見えなかったとも報告したため、right stick semantic reflection は inconclusive とする。後続再実験では A 後の settle、hold、circle を長くする。
- Unit 013 right stick slow rerun: 2026-07-04 に同じ条件で right stick 再実験を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry 後 `settle_seconds=1.5`、right stick hold `hold_report_count=120`、32-step circle `step_seconds=0.15`、neutral、`transport_close_complete` を記録した。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは right stick の目視確認ができたと報告した。unit_013 の stick 側は、left stick の目視確認と right stick slow rerun の目視確認により hardware-pass とする。

## Run Entry Template

### YYYY-MM-DD: short title

- OS:
- environment:
- adapter:
- dongle:
- driver:
- Python:
- Bumble:
- swbt-python:
- Switch model:
- Switch firmware:
- report period:
- command / test:
- approval:
- result:
- artifact:
- cleanup:
- notes:

## Hardware Matrix

| OS | Bluetooth dongle | Driver | Adapter | Switch model | Firmware | Pairing | L2CAP | Subcommands | Input reflected | Reconnect | Result source | Last updated | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Windows | CSR8510 A10 | WinUSB / libwdi 6.1.7600.16385 | `usb:0` | Switch 2 | 22.1.0 | observed-pass | pass | pass for full observed M5 handshake sequence | observed-pass for Button A / neutral / D-pad / left and right stick | observed-pass for active bond reuse reconnect after explicit Classic authentication/encryption | 2026-07-04 unit_013 input semantics and unit_007 active reconnect runs | 2026-07-04 | Release gate minimum は pairing、L2CAP、subcommand 応答、Button A、neutral。unit_013 で Switch 2 / firmware 22.1.0 の D-pad と left / right stick 反映も確認済み。L+R 同時押し表示は Switch button check UI の表示制約として扱う。incoming run は route 分離と subcommand sequence を記録したが、`classic_pairing` と `key_store_update` も出たため pairing-free incoming bond reuse とは扱わない |
| Linux | 未検証 | libusb 想定 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期保証対象に含めるか未決 |
| macOS | 未検証 | 未検証 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期検証対象外 |

## Run Entries

### 2026-07-04: unit_013 fresh key store setup for active reconnect input checks

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30` reports, `0x21` subcommand replies, and a close-time neutral `0x30`. No non-neutral input operation was sent.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_semantics_pairing_writes_fresh_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect -q -s`
- approval: user approved the first unit_013 hardware run with `OK。まずは1本目から行こう。`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, fresh pairing from the controller search / change grip order screen, key store write, full observed handshake wait, trace save, neutral close cleanup, and adapter release. Scope excluded Button A, L+R, stick input, active reconnect input reflection, extra retry loops, and persistent advertising.
- result: pass, `1 passed in 9.85s`. Trace recorded `key_store_exists=false`, `bonded_peers_discovered peer_count=0`, `active_reconnect_result status=no_bond`, `connect_pairing_fallback route=pairing`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `incoming_connection route=incoming`, `fresh_pairing_connect_result status=connected`, and full observed subcommand handshake through `manual_input_checkpoint operation=handshake_complete`.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\input-semantics-fresh-pairing.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\input-semantics-key-store.json` exists. The file was not opened for logging because it contains link key material.
- cleanup: trace recorded close-time neutral `0x30`, HID interrupt / control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `disconnected`, and `transport_close_complete`.
- notes: An earlier same-scope attempt created the key store but failed the pytest assertion because the test closed immediately after `key_store_update` while the first Switch subcommand reply was in flight. The test was adjusted to wait for the full observed handshake before closing, then rerun passed. This setup run is prerequisite evidence for unit_013 active reconnect input checks only; it does not exercise Button A, L+R, or stick semantic reflection.

### 2026-07-04: unit_013 active reconnect button check trace pass

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, L+R, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect -q -s`
- approval: user approved the second unit_013 hardware run with `ボタンの動作チェック選択画面で待機させている。2本目行こうか`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, L+R hold, neutral, trace save, close cleanup, and adapter release. Scope excluded stick input, new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: superseded by split diagnosis, pytest `1 passed in 9.37s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_enter_with_a_complete`, `hold_lr_reports_sent`, and `button_check_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User observed that only L looked pressed on the Switch button check screen; L+R simultaneous reflection was not confirmed in this first button run.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-button-check.jsonl`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and on-wire input checkpoints. It did not by itself prove L+R semantic reflection. The later split diagnosis captured raw outgoing HID bytes for R-only, L-only, and L+R and supersedes this run for the button result.

### 2026-07-04: unit_013 active reconnect button split diagnosis

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, R-only, L-only, L+R, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_separate_l_r_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-lr-split-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the repeat experiment with `再実験してみよう。待機済みなのでこのまま始めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, R-only hold, L-only hold, L+R hold, neutral between holds, trace save, debug log save, close cleanup, and adapter release. Scope excluded stick input, new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: hardware-pass for unit_013 button check, pytest `1 passed in 10.96s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_lr_split_enter_with_a_complete`, `hold_r_only_reports_sent expected_button_bytes=400000`, `hold_l_only_reports_sent expected_button_bytes=000040`, `hold_lr_together_reports_sent expected_button_bytes=400040`, and `button_check_lr_split_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User judged that the Switch button check UI likely does not display simultaneous button presses and shows only one side, so this is accepted as pass for the button portion.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-button-check-lr-split.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-lr-split-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: Debug log extraction of outgoing `0x30` input reports showed R-only button bytes `400000` 30 times, L-only `000040` 29 times, and L+R `400040` 30 times. This proves that the R bit was sent on-wire in this run. The remaining UI behavior is treated as a limitation of the Switch button check screen rather than a swbt-python input failure for this unit.

### 2026-07-04: unit_013 active reconnect D-pad button check

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, D-pad up, D-pad right, D-pad down, D-pad left, and neutral were sent by the test.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_dpad_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-dpad-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the D-pad run with `待機中。実験を始めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, D-pad up / right / down / left holds, neutral between holds, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, stick input, extra retry loops, and persistent advertising.
- result: hardware-pass. Pytest reported `1 passed in 11.71s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_dpad_enter_with_a_complete`, `hold_dpad_up_reports_sent expected_button_bytes=000002`, `hold_dpad_right_reports_sent expected_button_bytes=000004`, `hold_dpad_down_reports_sent expected_button_bytes=000001`, `hold_dpad_left_reports_sent expected_button_bytes=000008`, and `button_check_after_dpad_left_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that UI reflection was also confirmed.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-button-check-dpad.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-dpad-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route, D-pad direction checkpoints, and human-visible D-pad reflection on the Switch button check screen for this hardware condition.

### 2026-07-04: unit_013 active reconnect left stick trace

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, left stick hold, 16-step left stick circle, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\left-stick-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved continuing verification with `OK。switchセットアップ済み。検証を進めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the stick calibration screen, left stick hold, left stick circle, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded right stick input, new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: hardware-pass with observation caveat. Pytest reported `1 passed in 10.64s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `left_stick_calibration_enter_with_a_complete`, `left_stick_hold_reports_sent`, `left_stick_circle_complete steps=16`, and `left_stick_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that visual confirmation was possible, with the caveat that the circle may have ended quickly because the rotation was fast or screen transition timing was not fully accounted for.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-left-stick.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\left-stick-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and left stick input checkpoints. For a more inspectable operator experience, a later test could hold after entering the calibration screen for longer and slow down the circle input; this unit treats the left stick result as pass because user-visible reflection was observed.

### 2026-07-04: unit_013 active reconnect right stick trace

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, right stick hold, 16-step right stick circle, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested the right side run with `right側でも検証をやろう`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the stick calibration screen, right stick hold, right stick circle, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: trace-pass, visual inconclusive. Pytest reported `1 passed in 10.62s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `right_stick_calibration_enter_with_a_complete`, `right_stick_hold_reports_sent`, `right_stick_circle_complete steps=16`, and `right_stick_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that visual observation was completed, but the circle was too fast to see clearly.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-right-stick-fast.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and right stick input checkpoints. Because the human-visible right stick motion was not inspectable enough, this run is not a semantic pass. The follow-up test timing was changed to wait 1.5 seconds after A, hold for 120 reports, and send a 32-step circle at 0.15 seconds per step.

### 2026-07-04: unit_013 active reconnect right stick slow rerun

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, right stick hold, 32-step right stick circle, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-slow-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the rerun with `再実験もやろう。準備済みなので片方のスティックで実施する形で確認しようか。`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the stick calibration screen, right stick hold, right stick circle, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: hardware-pass. Pytest reported `1 passed in 16.77s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `right_stick_calibration_enter_with_a_complete settle_seconds=1.5`, `right_stick_hold_reports_sent hold_report_count=120`, `right_stick_circle_complete steps=32 step_seconds=0.15`, and `right_stick_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that visual confirmation was possible.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-right-stick.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-slow-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and slower right stick input checkpoints. The slower timing was sufficient for human-visible confirmation.

### 2026-07-03: unit_019 pairing L2CAP smoke after transport contract cleanup

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `main` at `041330b`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one neutral `0x30` input report after `connected`.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_019\20260703-pairing-l2cap-smoke -q -s`
- approval: user explicitly requested the run with `実機検証をやるか。接続画面で待機させているのでテストを始めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch-facing pairing / HID control and interrupt connection wait, trace save, and close cleanup. Scope excluded Button A or other non-neutral input, extra retry loops, and persistent advertising.
- result: pass, `1 passed in 3.09s`. Trace recorded `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `transport_open_complete`, `classic_link_policy_configured settings="0x0005"`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `incoming_connection route=incoming`.
- artifact: `.pytest_cache\hardware\unit_019\20260703-pairing-l2cap-smoke\pairing-l2cap.jsonl`
- cleanup: trace recorded one neutral `0x30` `report_tx`, HID interrupt / control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `disconnected`, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run is a hardware smoke after the unit_019 diagnostics / transport-contract cleanup. It confirms that the current `main` can still pair and open HID control / interrupt L2CAP from the Switch connection screen. It does not exercise active reconnect or Button A input reflection.

### 2026-07-03: unit_008 swbt-probe pair passed after Switch connection wait

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-008-packaging-examples-cli` with uncommitted hardware-log update after `66fd860`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one neutral `0x30` input report after `connected`.
- command / test: `uv run swbt-probe pair --adapter usb:0 --key-store .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\keys.json --trace .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\pair-trace.jsonl --timeout 30`
- approval: user explicitly requested retry after the timeout with `接続待ちにしてないのが原因かも。もっかい頼めるか?`. Scope matched the previous approved hardware test: USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch-facing pairing / HID control and interrupt connection wait, trace save, and close cleanup. Scope excluded Button A or other non-neutral input, extra retry loops, and persistent advertising.
- result: pass, exit 0. The trace recorded `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `transport_open_complete`, `classic_link_policy_configured settings="0x0005"`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `incoming_connection route=incoming`.
- artifact: `.pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\pair-trace.jsonl`
- artifact: `.pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\keys.json`
- cleanup: trace recorded one neutral `0x30` `report_tx`, HID interrupt / control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`. No non-neutral input operation was sent. The key store file exists, but link key material is not logged here.
- notes: The preceding timeout is consistent with the Switch not being in connection-wait state, but this is an inference from the successful retry and the user's operator note, not a controlled A/B proof.

### 2026-07-03: unit_008 swbt-probe pair timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-008-packaging-examples-cli` at `66fd860`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used. Report loop did not start because `connected` was not reached
- command / test: `uv run swbt-probe adapters --json`
- command / test: `uv run swbt-probe pair --adapter usb:0 --key-store .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair\keys.json --trace .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair\pair-trace.jsonl --timeout 30`
- approval: user explicitly approved this hardware test with `実機テストやろうか。承認。`. Scope included USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch-facing pairing / HID control and interrupt connection wait, trace save, and close cleanup. Scope excluded Button A or other non-neutral input, extra retry loops, and persistent advertising.
- result: fail, `ConnectionTimeoutError` after 30 seconds. The no-open adapter command reported candidate `usb:0`, platform `Windows-11-10.0.26200-SP0`, Python 3.13.5, Bumble 0.0.230, and `opens_adapter=false`. The pair trace recorded `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `transport_open_complete`, `classic_link_policy_configured settings="0x0005"`, `advertising_start`, then `connection_timeout state=advertising`. The trace did not record `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`.
- artifact: `.pytest_cache\hardware\unit_008\20260703-swbt-probe-pair\pair-trace.jsonl`
- cleanup: trace recorded recoverable `error`, `disconnect_request status=unavailable` because channels were not connected, and `transport_close_complete`. No key store file was written and no non-neutral input operation was sent.
- notes: This run confirms that `swbt-probe pair --trace` leaves a diagnostic artifact and closes the transport on timeout. It does not prove Switch pairing or HID channel open for the CLI path.

### 2026-07-03: unit_007 active reconnect passed after Classic authentication and encryption

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-007-reconnect-keystore` with uncommitted active reconnect authentication/encryption change after `a4095ce`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Final active reconnect reached `connected`; trace recorded periodic `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports.
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_pairing_writes_reconnect_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\pairing-pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_active_reconnect_with_existing_key_store_records_result -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-close-lock-pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_active_reconnect_with_existing_key_store_records_result -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-auth-encrypt-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved hardware work with `実機承認。一つずつやっていこう`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, initial pairing from controller search / change grip order screen, key store write, active reconnect request from HOME / normal screen, HID control L2CAP open attempt, disconnect handling, and cleanup. Incoming connection evaluation was explicitly left aside.
- 起動条件: initial pairing test recorded `expected_switch_screen=controller_search_or_change_grip_order`. Active reconnect test recorded `expected_switch_screen=home_or_normal_screen_not_change_grip_order`.
- result: pairing prerequisite passed, `1 passed in 7.92s`. Before the authentication/encryption fix, active reconnect reached ACL and sent HID control `L2CAP_CONNECTION_REQUEST` for PSM `0x0011`, then disconnected with `AUTHENTICATION_FAILURE_ERROR` reason 5; the test was still too weak and accepted `status=failed`. After changing the test to require `status=connected` and adding explicit Classic authentication/encryption before HID L2CAP, active reconnect passed, `1 passed in 8.85s`. The trace recorded `key_store_exists=true`, one bonded peer selected, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `active_reconnect_result status=connected`. The final active reconnect trace did not record `advertising_start`, `classic_pairing`, or `key_store_update`. Debug log order was `HCI_AUTHENTICATION_REQUESTED_COMMAND`, `HCI_AUTHENTICATION_COMPLETE_EVENT`, `HCI_SET_CONNECTION_ENCRYPTION_COMMAND`, `HCI_ENCRYPTION_CHANGE_EVENT`, then HID `L2CAP_CONNECTION_REQUEST`.
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\reconnect-initial-pair.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\pairing-pytest-debug.log`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-close-lock-pytest-debug.log`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-auth-encrypt-pytest-debug.log`
- cleanup: final active reconnect trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: The key store file exists in the artifact directory, but link key material is not logged here. The failure before the fix was not evidence of stale key material; it was reproduced as missing explicit Classic authentication/encryption before opening HID L2CAP. Incoming connection behavior is not reclassified by this entry.

### 2026-07-03: unit_007 incoming route from controller screen passed but re-paired

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-007-reconnect-keystore` at `e87ec10`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, and subcommand reply `0x21` reports after incoming connection.
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_incoming_connection_trace_stays_separate_from_active_reconnect -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\incoming-after-setup-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user stated that the previous incoming failure was probably Switch setup, then waited on `持ち方/順番を変える`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, incoming connection from controller search / change grip order screen, pairing/authentication as requested by Switch, HID control / interrupt channel open, Switch-facing output report / subcommand handling, periodic report loop, disconnect request, and cleanup.
- 起動条件: incoming test recorded `expected_switch_screen=controller_search_or_change_grip_order`.
- result: pass, `1 passed in 8.95s`. Trace recorded `key_store_exists=true`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `incoming_connection route=incoming`. It did not record `active_reconnect_attempt` or `active_reconnect_result`. Debug log recorded `HCI_CONNECTION_REQUEST_EVENT`, `HCI_LINK_KEY_NOTIFICATION_EVENT`, `HCI_ENCRYPTION_CHANGE_EVENT`, and HID L2CAP connection request/response. This proves incoming route separation under the listed operator condition, but not pairing-free incoming bond reuse.
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\incoming-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\incoming-after-setup-pytest-debug.log`
- cleanup: trace recorded HID interrupt/control channel close, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, later `transport_close_complete`. A queued post-close send recorded `ClosedError` diagnostics after channel close; cleanup still reached `transport_close_complete`.
- notes: The HCI debug log contains a link key notification. The raw link key value is intentionally not copied into this document. Since this run was started from the controller search / change grip order screen and emitted `classic_pairing` plus `key_store_update`, it must not be used as evidence for Switch-side-operation-free reconnect.

### 2026-07-03: unit_007 reconnect run with unrecorded Switch UI condition

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-007-reconnect-keystore` at `21013fb`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed in previous Bumble debug logs for this adapter
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Initial pairing traces recorded neutral `0x30` on close. Incoming attempt recorded periodic/input `0x30` and `0x21` subcommand replies after HID channel open.
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore --log-file .pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved with `承認`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising for explicit pairing and incoming observation, initial pairing, key store write, active reconnect request, HID control / interrupt channel open wait, Switch-facing output report / subcommand handling when connected, periodic report loop, neutral, disconnect request, closed event wait, and cleanup.
- 起動条件: 未記録。この run だけでは、active reconnect 開始時の Switch が HOME / 通常アプリ画面だったのか、コントローラー探索 / 持ち方・順番を変える画面だったのかを区別できない。
- result: pass, `2 passed in 72.56s`. Initial pairing for active reconnect wrote `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\active-reconnect-key-store.json` and recorded `key_store_update status=succeeded`. The active reconnect attempt opened with `key_store_exists=true`, discovered one bonded peer, recorded `active_reconnect_attempt`, reached `host_connection` for `C8:48:05:F7:B5:21/P`, then disconnected with reason 19 before HID control / interrupt channel open. The final result was `active_reconnect_result status=timeout failure_reason=connection_timeout`; the trace did not record `advertising_start`, `classic_pairing`, or `key_store_update` during active reconnect. Incoming observation opened with `key_store_exists=true`, recorded `advertising_start`, `incoming_connection route=incoming`, HID control / interrupt `l2cap_channel_open`, `connected`, and subcommand receive/reply events. That incoming trace also recorded `classic_pairing` and `key_store_update status=succeeded`, so this run does not prove pairing-free incoming bond reuse.
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\active-reconnect-initial-pair.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\active-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\incoming-reconnect-initial-pair.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\incoming-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\pytest-debug.log`
- cleanup: all test paths closed the gamepad in `finally`. Active reconnect recorded `transport_close_complete` after timeout handling. Incoming attempt recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`.
- notes: Treat this run as inconclusive for active reconnect success or failure under the intended user scenario. The next run must record the operator condition: initial pairing starts from the controller search / change grip order screen; active reconnect starts after returning to HOME or another normal screen, without controller search UI open. Some incoming close paths recorded post-close `ClosedError` diagnostics while queued report work was draining; cleanup still reached `transport_close_complete`.

### 2026-07-03: unit_015 resource open did not advertise, explicit pair and Button A path passed

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `main` at `42837e7` with uncommitted API removal and hardware-test updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed in previous Bumble debug logs for this adapter
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Pair close smoke recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)`. Button A path recorded full observed handshake, `tap(Button.A)`, neutral reports, and close cleanup.
- command / test: `uv run pytest tests/hardware/test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-resource-open-only --log-file .pytest_cache\hardware\unit_015\20260703-004306-resource-open-only\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests/hardware/test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke --log-file .pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests/hardware/test_input_operations.py::test_switch_input_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a --log-file .pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved unit_015 hardware validation. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, resource-only `open()` without HID advertising, explicit `pair()` with discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop after `connected`, full observed subcommand handshake for the Button A path, one `tap(Button.A)`, neutral, trailing neutral, remote close request, closed event wait, and cleanup.
- result: pass. Resource-only smoke: `1 passed in 0.29s`; trace includes `transport_open_complete`, `disconnect_request status=unavailable`, and `transport_close_complete`; trace does not include `advertising_start` or `host_connection`. Pair close smoke: `1 passed in 4.28s`; trace includes `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, HID control / interrupt `l2cap_channel_open`, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_close_checkpoint close_complete`. Button A path: `1 passed in 5.46s`; trace includes full observed handshake through `0x21`, `manual_input_checkpoint handshake_complete`, `post_handshake_tap_a_start`, `post_handshake_tap_a_complete`, `post_handshake_neutral_complete`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`.
- artifact: `.pytest_cache\hardware\unit_015\20260703-004306-resource-open-only\resource-open-only.jsonl`
- artifact: `.pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke\close-disconnect.jsonl`
- artifact: `.pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a\post-handshake-input.jsonl`
- cleanup: all tests closed the gamepad in `finally`. Resource-only smoke never entered advertising. Pair close smoke and Button A path recorded `transport_close_complete` after disconnect request terminal state.
- notes: This validates the unit_015 lifecycle split, explicit `pair()` route, and Button A on-wire path for this hardware condition. It does not validate active bond reuse reconnect, key store behavior, or user-visible input reflection in this run.

### 2026-07-02: unit_014 close request reached closed event but missed final transport close

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch before commit `0979bd4`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed in adjacent Bumble debug logs for this adapter
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)` and no non-neutral input operation
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a --log-file .pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the unit_014 hardware validation. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop, trailing neutral, remote close request, closed event wait or timeout, and cleanup. User explicitly asked not to send A twice or otherwise re-enter the device connection screen; this test sent no A input.
- result: fail. Pytest assertion failed because `transport_close_complete` was missing. Trace includes `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, public `disconnected reason=null`, Bumble `disconnected reason=0`, `disconnect_request_terminal status=closed`, and `manual_close_checkpoint close_complete`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`. Trace reached `manual_close_checkpoint close_complete`, but did not record `transport_close_complete`. The observed failure was reproduced without hardware by `test_close_request_disconnected_callback_leaves_final_close_to_user_close` and fixed in commit `0979bd4`.
- notes: This run proves only that the close request reached L2CAP close and the public closed terminal event on this hardware. It does not validate the fixed final transport close ordering.

### 2026-07-02: unit_014 post-fix close disconnect passed on Switch link

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `c08d4b1` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)` and no non-neutral input operation
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity --log-file .pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user asked to run one more connection check for the same unit_014 hardware scope. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop, trailing neutral, remote close request, closed event wait or timeout, and cleanup. No A input or other non-neutral input operation was sent.
- result: pass, `1 passed, 1 warning in 6.80s`. Trace includes `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, Bumble `disconnected reason=0`, public `disconnected reason=0`, `transport_close_complete`, and `manual_close_checkpoint close_complete`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete` and `manual_close_checkpoint close_complete`. No non-neutral input operation was sent.
- notes: This run validates the post-fix connected close ordering for this hardware configuration. Trace still records separate public disconnection observations for L2CAP close (`reason=null`) and device disconnection (`reason=0`); `close()` remains idempotent and completed.

### 2026-07-02: subcommand observation follow-up timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `918325d` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation --log-file .pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user asked to check communication again because the Switch-side behavior did not look connected. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, subcommand observation and reply if connected, periodic neutral reports, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `l2cap_channel_open`, `connected`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation\subcommand-observation-window.jsonl`, `.pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run did not reach the Switch protocol layer. The observed failure point is before host connection, so it supports the user's observation that this attempt did not look like a live controller communication session.

### 2026-07-02: L2CAP-only follow-up timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `1bd4050` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check --log-file .pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved continuing the problem investigation. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open if connected, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This reproduces the pre-host-connection timeout with the narrower L2CAP diagnostics test. The problem is upstream of Switch output report / subcommand handling in this run.

### 2026-07-02: L2CAP-only retry timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `5e860cb` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry --log-file .pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user asked for one more retry. Scope matched the previous L2CAP-only problem investigation: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open if connected, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`. HCI debug log query found no `HCI_CONNECTION_REQUEST_EVENT`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This repeat strengthens the finding that the current failure mode is pre-host-connection. It does not exercise L2CAP, output reports, subcommands, input reports, or close request ordering.

### 2026-07-02: new pairing L2CAP check timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `ceefe2a` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap --log-file .pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user reported that Switch-side pairing information had been deleted and the Switch was searching from the new controller addition screen, then asked to try a fresh connection. Scope matched the L2CAP-only problem investigation: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing if the Switch initiated it, HID control / interrupt L2CAP open if connected, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`. HCI debug log shows `HCI_WRITE_LOCAL_NAME_COMMAND`, `HCI_WRITE_CLASS_OF_DEVICE_COMMAND`, `HCI_WRITE_EXTENDED_INQUIRY_RESPONSE_COMMAND`, and final `HCI_WRITE_SCAN_ENABLE_COMMAND` with `scan_enable: 3` returning `SUCCESS`; the same log query found no `HCI_CONNECTION_REQUEST_EVENT` or `HCI_CONNECTION_COMPLETE_EVENT`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run was a new-connection attempt from the Switch side, but it did not reach pairing. The current failure point is before Switch host connection. Whether the Switch saw the inquiry response is not established by this artifact; that would need a separate discovery-side observation.

### 2026-07-02: advertising hold recorded no host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `b419cd7` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used. This diagnostic used `BumbleHidTransport` directly and did not create `ReportLoop`
- command / test: one-off `uv run python -` diagnostic script. It opened `BumbleHidTransport(adapter="usb:0")`, called `open()`, `start_advertising()`, recorded `manual_advertising_hold_start duration_seconds=90`, awaited `asyncio.sleep(90)`, recorded `manual_advertising_hold_complete`, and closed the transport in `finally`
- approval: user agreed to continue verification after the pre-host-connection timeout diagnosis. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or HID L2CAP observation only if the Switch initiated a connection, 90 second hold, and cleanup. No report loop, A input, or other non-neutral input operation was used.
- result: observed-timeout/no-host-connection. Trace includes `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `manual_advertising_hold_start`, `manual_advertising_hold_complete`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-215256-advertising-hold\advertising-hold.jsonl`
- cleanup: one-off diagnostic closed the transport in `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run keeps the same failure boundary as the L2CAP-only timeout runs while removing report loop and pytest assertion behavior from the path. It does not prove whether another scanner could see the inquiry response.

### 2026-07-02: close cleanup disabled Classic scan on the dongle

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `16e6039` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used. This diagnostic used `BumbleHidTransport` directly and did not create `ReportLoop`
- command / test: one-off `uv run python -` diagnostic script. It opened `BumbleHidTransport(adapter="usb:0")`, called `open()`, `start_advertising()`, recorded `manual_close_scan_disable_probe_advertising_hold_start duration_seconds=5`, awaited `asyncio.sleep(5)`, recorded `manual_close_scan_disable_probe_close_start`, and closed the transport in `finally`
- approval: user explicitly approved running the close cleanup verification. Scope included USB Bluetooth dongle open, Classic HID Device initialization, short discoverable / connectable advertising, Switch host connection observation if the Switch initiated a connection, close path with `set_discoverable(False)` / `set_connectable(False)`, and cleanup. No report loop, A input, or other non-neutral input operation was used.
- result: observed-pass for close scan disable. Trace includes `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `manual_close_scan_disable_probe_advertising_hold_start`, `host_connection`, `manual_close_scan_disable_probe_close_start`, `disconnected reason=0`, `transport_close_complete`, and `manual_close_scan_disable_probe_close_complete`. Debug log shows close path `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 2` followed by `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0`, both with `status: SUCCESS`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-220455-close-scan-disable\close-scan-disable.jsonl`, `.pytest_cache\hardware\unit_014\20260702-220455-close-scan-disable\close-scan-disable-debug.log`
- cleanup: one-off diagnostic closed the transport in `finally`; trace recorded `transport_close_complete`. Debug log recorded final `scan_enable: 0` with `SUCCESS`. No non-neutral input operation was sent.
- notes: This run confirms the software cleanup fix reaches the controller HCI boundary. It also shows that, at this moment, Switch did send a host connection request during the 5 second window. The user observed that `Pro Controller` disappeared from the iPhone Bluetooth discovery UI after this cleanup, supporting the conclusion that the earlier visible entry was caused by incomplete Classic scan cleanup rather than a still-running Python process.

### 2026-07-02: unit_014 close disconnect passed after Classic scan cleanup fix

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `82ae916` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)` and no non-neutral input operation
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup --log-file .pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved rerunning the original unit_014 close disconnect validation after confirming the close cleanup bug. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop, trailing neutral, remote close request, closed event wait or timeout, Classic scan disable on close, and cleanup. No A input or other non-neutral input operation was sent.
- result: pass, `1 passed, 1 warning in 3.02s`. Trace includes `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, Bumble `disconnected reason=0`, public `disconnected reason=0`, `transport_close_complete`, and `manual_close_checkpoint close_complete`. Debug log includes `HCI_CONNECTION_REQUEST_EVENT`, `HCI_CONNECTION_COMPLETE_EVENT`, and final close path `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0` with `status: SUCCESS`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete` and `manual_close_checkpoint close_complete`. Debug log recorded final `scan_enable: 0` with `SUCCESS`. No non-neutral input operation was sent.
- notes: This run validates unit_014 connected close ordering after the Classic scan cleanup fix. It closes immediately after HID control / interrupt L2CAP `connected`; it does not wait for the full observed Switch subcommand handshake or Switch UI registration completion.

### 2026-07-02: unit_014 post-handshake A exit and close passed without warning

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch with uncommitted warning fix for the first `-W error` run. The prior same-path UI observation run used commit `de8f39d`.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded full observed Switch handshake, Button A input reports, neutral reports, and one trailing neutral `0x30` from `pad.close(neutral=True)`
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-warning-fix-listener --log-file .pytest_cache\hardware\unit_014\20260702-warning-fix-listener\pytest-debug.log --log-file-level=DEBUG -q -s -W error`
- approval: user approved rerunning the same unit_014 hardware path to resolve the pytest warning. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, full observed subcommand handshake, one explicit Button A tap to leave the registration screen, neutral, trailing neutral, remote close request, closed event wait or timeout, Classic scan disable on close, and cleanup.
- result: pass, `1 passed in 7.85s` with `-W error`. Trace includes `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, full observed handshake through `0x21`, `manual_close_checkpoint full_handshake_complete`, `tap_a_exit_pairing_screen_complete`, `neutral_after_a_complete`, `close_start`, trailing neutral `0x30`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, public and Bumble `disconnected reason=0`, `transport_close_complete`, `close_complete`, and `post_close_ui_observation_window_complete`. User confirmed on the prior same-path run that Button A left the Switch registration screen as expected and that disconnect was visible.
- artifact: `.pytest_cache\hardware\unit_014\20260702-warning-fix-listener\post-handshake-a-close.jsonl`, `.pytest_cache\hardware\unit_014\20260702-warning-fix-listener\pytest-debug.log`; prior same-path UI observation artifact: `.pytest_cache\hardware\unit_014\20260702-221752-post-handshake-a-close\post-handshake-a-close.jsonl`, `.pytest_cache\hardware\unit_014\20260702-221752-post-handshake-a-close\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded trailing neutral, close request terminal `closed`, `transport_close_complete`, and post-close UI observation window completion. Debug log recorded final Classic scan disable without any `DeprecationWarning` or `Use utils.AsyncRunner.spawn()` entry.
- notes: The warning source was Bumble 0.0.230's host-registered incoming Classic connection handler calling deprecated `host.send_command_sync()`. swbt-python now replaces that host listener with its diagnostics bridge and runs the upstream handler while mapping `send_command_sync(command)` to `AsyncRunner.spawn(host.send_async_command(command))`.

### 2026-07-02: unit_014 post-fix close disconnect reruns timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `0979bd4`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix --log-file .pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\pytest-debug.log --log-file-level=DEBUG -q -s`; rerun: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry --log-file .pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: same unit_014 hardware validation approval. Scope matched the connected close test, but both post-fix reruns stopped before Switch host connection.
- result: fail for both reruns, `ConnectionTimeoutError` after 60 seconds. Both traces include `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Neither trace includes `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, `connected`, trailing neutral, or close request terminal state.
- artifact: `.pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\pytest-debug.log`, `.pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\pytest-debug.log`
- cleanup: each rerun executed `pad.close(neutral=True)` from `finally`; both traces recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: These reruns do not exercise unit_014 connected close behavior after commit `0979bd4`. The observed failure point is before Switch host connection.

### 2026-07-02: unit_006 post-handshake Button A input reflected on Switch UI

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `6b5ed73` with clean worktree before and after the hardware run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 66 `report_tx` events, 21 `output_report_rx` events, 16 `subcommand_rx` events, and 16 `subcommand_reply_tx` events. Checkpoints recorded `handshake_complete`, `post_handshake_tap_a_start`, `post_handshake_tap_a_complete`, and `post_handshake_neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-post-handshake-input --log-file .pytest_cache\hardware\unit_006\20260702-post-handshake-input\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved this hardware test. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, wait for full observed handshake, `Button.A` tap, neutral input, and cleanup.
- result: pass. Pytest reported `1 passed, 1 warning in 9.45s`. Trace recorded `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, and the full observed M5 handshake subcommand sequence: `0x02`, `0x08`, `0x10` x8, `0x03`, `0x04`, `0x40`, `0x30` x2, `0x48`, `0x21`. `handshake_complete` was recorded at `0x30` report count 4; `post_handshake_tap_a_complete` at count 41; `post_handshake_neutral_complete` at count 49. Bumble debug log showed A button bytes `08 00 00` in `0x30` report counters 20-23 and neutral bytes `00 00 00` from counter 24 onward. The user visually confirmed that A was reflected on the Switch UI and that no residual input was visible after neutral.
- artifact: `.pytest_cache\hardware\unit_006\20260702-post-handshake-input\post-handshake-input.jsonl`, `.pytest_cache\hardware\unit_006\20260702-post-handshake-input\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final `0x30` input report, two public `disconnected reason=0` events, and `transport_close_complete`.
- notes: This run completes the M5 Button A / neutral semantic input reflection condition for this hardware configuration. It does not cover stick semantic reflection, reconnect, or multiple controller behavior.

### 2026-07-02: unit_006 shared timer rerun progressed through Switch handshake

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `4e677f2` with clean worktree before the hardware run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 54 `report_tx` events, including 16 `0x21` subcommand replies and `0x30` periodic / input reports. Checkpoints recorded `tap_a_start`, `tap_a_complete`, `hold_lr_start`, `hold_lr_reports_sent`, and `neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-shared-timer-rerun --log-file .pytest_cache\hardware\unit_006\20260702-shared-timer-rerun\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved this hardware test after shared timer / reply holdoff implementation. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, `Button.A` tap, L+R hold, neutral input, and cleanup.
- result: handshake-progressed, pairing observed-pass, input reflection pending. Pytest reported `1 passed, 1 warning in 8.44s`. Trace recorded `classic_pairing`, `link_key_available`, `connection_encryption_change` with `authenticated=false`, `encryption=1`, `secure_connections=false`, L2CAP control / interrupt open, `connected`, and `classic_mode_change`. Observed subcommands progressed from previous `0x02` / repeated `0x08` to `0x02`, `0x08`, `0x10` x8, `0x03`, `0x04`, `0x40`, `0x30` x2, `0x48`, `0x21`. Each observed subcommand had a `subcommand_reply_tx`. The user visually confirmed that pairing completed on the Switch side. The run also recorded A tap, L+R hold, neutral, clean close. `tap(Button.A)` UI reflection and neutral residual state are not auto-detected by this pytest and remain pending separate user-visible confirmation.
- artifact: `.pytest_cache\hardware\unit_006\20260702-shared-timer-rerun\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-shared-timer-rerun\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded neutral input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run supports the daemon-derived shared timer hypothesis for escaping repeated `0x08` and confirms Switch-side pairing completion under this hardware condition. It does not by itself complete M5 because `tap(Button.A)` UI reflection and neutral residual state require separate user-visible confirmation.

### 2026-07-02: unit_006 pairing diagnostics still stopped at repeated 0x08

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `228d669` with clean worktree before the diagnostic run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded periodic/input `0x30` reports, subcommand reply attempts, `tap_a_start`, `tap_a_complete`, `hold_lr_start`, `hold_lr_reports_sent`, and `neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-pairing-diagnostics --log-file .pytest_cache\hardware\unit_006\20260702-pairing-diagnostics\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved this command after adapter, Switch-facing scope, and cleanup were stated. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, `Button.A` tap, L+R hold, neutral input, and cleanup.
- result: observed-fail for semantic input reflection. Pytest reported `1 passed, 1 warning in 6.51s`, but the user confirmed that the Switch device registration / authentication screen did not move. Trace recorded `classic_pairing`, `link_key_available`, `connection_encryption_change` with `authenticated=false`, `encryption=1`, `secure_connections=false`, L2CAP control / interrupt open, `connected`, `classic_mode_change`, `0x02` once, and repeated `0x08`. It did not record `pairing_complete` or `connection_authentication`, and did not progress to daemon-success subcommands `0x10`, `0x03`, `0x04`, `0x40`, `0x48`, `0x21`, `0x30`.
- artifact: `.pytest_cache\hardware\unit_006\20260702-pairing-diagnostics\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-pairing-diagnostics\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded neutral input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run confirms that link-key availability and encryption change alone are not sufficient evidence that Switch accepted the controller. Based on daemon `local_037`, swbt-python then changed software scheduling so `0x21` replies consume the shared input report timer and hold off following periodic `0x30` reports. That fix has not yet been run on hardware.

### 2026-07-02: unit_006 input operation sequence sent reports but did not move Switch UI

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `79ecbd1` with clean worktree before the observable rerun
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 56 `0x30` reports and 4 `0x21` replies. Checkpoints recorded `tap_a_start`, `tap_a_complete`, `hold_lr_start`, `hold_lr_reports_sent`, and `neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable --log-file .pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved unit_006 hardware verification and requested commit before hardware verification. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, `Button.A` tap, L+R hold, neutral input, and cleanup. Scope excluded reconnect and broader firmware / adapter matrix claims.
- result: observed-fail for semantic input reflection. Pytest reported `1 passed, 1 warning in 10.08s`, but that pass only proves the trace sequence and cleanup assertions. User observed that the Switch device registration screen did not move at all. Debug log confirmed outgoing HID interrupt input reports: A used button bytes `08 00 00` (`a1 30 ... 91 08 00 00 ...`), L+R used `40 00 40` (`a1 30 ... 91 40 00 40 ...`), and neutral used `00 00 00` (`a1 30 ... 91 00 00 00 ...`). Trace recorded no `error` event. The cause is not determined by this run. swbt-daemon `local_049` success observed `pairing complete, status 00`, `0x02` / `0x08` / `0x10` / `0x03` / `0x04` / `0x40` / `0x48` / `0x21` / `0x30` replies, then L+R and Button A UI reflection. swbt-daemon `local_073` pairing-free reconnect pass observed link-key DB use and no new `pairing complete`. This swbt-python run only recorded `classic_pairing`, L2CAP open, and observed `0x02` / `0x08`; it did not record authentication, encryption, link key, or full controller initialization sequence.
- artifact: `.pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final neutral `0x30` input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run proves report transmission through Bumble/L2CAP under the listed conditions, but contradicts M5 completion because Switch UI input reflection was not observed. Next diagnosis should separate report acceptance / controller registration state from report byte correctness. The successful pytest assertion must not be treated as semantic input reflection. After comparison with swbt-daemon logs, the next diagnostic run should require trace evidence for `pairing_complete`, `connection_authentication`, `connection_encryption_change`, optional `link_key_available`, and whether Switch progresses beyond repeated `0x08` into the known daemon subcommand sequence. Raw link key values must not be logged.

### 2026-07-02: unit_005 observation window replied to all observed subcommands

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted observation-window hardware test, post-send `report_tx` diagnostics boundary, and Bumble ACL queue drain implementation.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 135 periodic neutral `0x30` reports, 9 `0x21` subcommand replies, and one neutral input report during cleanup.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain --log-file .pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved continuing unit_005 hardware verification. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, Switch output report receive, `0x21` reply for observed subcommands, 5 second observation window after first subcommand, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: pass, `1 passed, 1 warning in 9.50s`. Trace recorded `output_report_rx` 9 件, `subcommand_rx` 9 件, `subcommand_reply_tx` 9 件, and `report_tx` reason `subcommand_reply` 9 件. Observed subcommands were `0x02` x1 and `0x08` x8, and every observed `(packet_id, subcommand_id)` had a matching reply. `unsupported_subcommand` and `error` were 0 件. Bumble debug log had 0 matches for `packets in flight`, unlike the earlier observation-window experiment without effective ACL drain where controller completed-packet backlog grew.
- artifact: `.pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\subcommand-observation-window.jsonl`, `.pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final neutral `0x30` input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run closes the M4 residual risk that the first successful `0x02` reply did not prove later observed subcommands would receive replies. It does not cover semantic input reflection, reconnect, firmware matrix expansion, or all possible Switch subcommands.

### 2026-07-02: unit_005 link-policy-only run reached subcommand reply

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted minimized link-policy-only implementation, docs, and tests changes. The runtime implementation no longer included HID L2CAP MTU `100` re-registration or the `0x8e` / `0x80` profile prefix change.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Report loop emitted six neutral `0x30` reports before Switch output `0x01`, then sent one `0x21` reply and later neutral reports during cleanup.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-011634-link-policy-only --log-file .pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested real hardware verification. Scope used the established unit_005 M4 hardware test on `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, output report receive wait, `0x21` reply if output arrived, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: pass, `1 passed, 1 warning in 4.27s`. Trace recorded `classic_link_policy_configured` with `settings=0x0005`, `host_connection`, `classic_pairing`, control and interrupt `l2cap_channel_open`, `connected`, `output_report_rx` for report `0x01` / subcommand `0x02`, `subcommand_rx`, `subcommand_reply_tx`, and `report_tx` for `0x21`. The trace did not record `hid_l2cap_mtu`, confirming this was not the MTU-100 server re-registration variant. The debug log confirms `HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND`, `HCI_MODE_CHANGE_EVENT`, incoming HID interrupt PDU `a2 01`, and outgoing reply PDU `a1 21 00 91...`.
- artifact: `.pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded `disconnected reason=0`, the public disconnection event, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run isolates the earlier successful result to the Classic default link policy `0x0005` change. HID L2CAP MTU `100` re-registration and the `0x8e` / `0x80` profile prefix are not needed for this M4 subcommand-sequence pass under the listed adapter / driver / Bumble / Switch state. This is still a hardware observation, not a cross-platform guarantee.

### 2026-07-02: unit_005 link-policy run reached subcommand reply

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted link-policy, MTU-100, `0x8e` / `0x80` prefix, docs, and tests changes.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Report loop emitted six neutral `0x30` reports before Switch output `0x01`, then sent one `0x21` reply and later neutral reports during cleanup.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-010148-link-policy --log-file .pytest_cache\hardware\unit_005\20260702-010148-link-policy\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested real hardware verification. Scope used the established unit_005 M4 hardware test on `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, output report receive wait, `0x21` reply if output arrived, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: pass, `1 passed, 1 warning in 2.92s`. Trace recorded `classic_link_policy_configured` with `settings=0x0005`, `host_connection`, `classic_pairing`, control and interrupt `l2cap_channel_open`, `connected`, `classic_mode_change` with `mode=2` and `interval=24`, `output_report_rx` for report `0x01` / subcommand `0x02`, `subcommand_rx`, `subcommand_reply_tx`, and `report_tx` for `0x21`. The debug log confirms `HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND`, `HCI_MODE_CHANGE_EVENT`, incoming HID interrupt PDU `a2 01`, and outgoing reply PDU `a1 21`.
- artifact: `.pytest_cache\hardware\unit_005\20260702-010148-link-policy\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-010148-link-policy\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded `disconnected reason=0`, the public disconnection event, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run moves M4 past the previous failure point. The smallest observed decisive difference from the MTU-100 failure run is Classic default link policy `0x0005`, followed by a Mode Change before the Switch output report. This run does not prove that HID L2CAP MTU `100` or the `0x8e` / `0x80` report prefix are required together with link policy `0x0005`; the minimized implementation therefore retains link policy `0x0005` and drops the MTU / prefix changes unless a later A/B hardware run proves they are needed. This is still a hardware observation under the listed adapter / driver / Bumble / Switch state, not a cross-platform guarantee.

### 2026-07-02: unit_005 MTU-100 diagnostic still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted MTU-100, `0x8e` / `0x80` prefix, docs, and tests changes.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Report loop started after `connected` and emitted 14 neutral `0x30` reports before Switch-side disconnect.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-004659-mtu100 --log-file .pytest_cache\hardware\unit_005\20260702-004659-mtu100\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested real hardware verification. Scope used the established unit_005 M4 hardware test on `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, output report receive wait, `0x21` reply if output arrived, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: fail before output report. Trace recorded `hid_device_initialized` with `hid_l2cap_mtu=100`, `host_connection`, `classic_pairing`, control and interrupt `l2cap_channel_open`, `connected`, then 14 periodic neutral `0x30` `report_tx` events. It recorded no `HID CONTROL PDU`, no `HID INTERRUPT PDU`, no `output_report_rx`, no `subcommand_rx`, and no `subcommand_reply_tx`. The debug log confirms control and interrupt channels opened as `MTU=100/672`, then `a1 30` reports with `0x8e` / `0x80` prefix were sent, and Switch-side reason 19 disconnected.
- artifact: `.pytest_cache\hardware\unit_005\20260702-004659-mtu100\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-004659-mtu100\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded `disconnected reason=19`, L2CAP channel close events, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run confirms the MTU-100 transport change reached the live L2CAP channels. It did not move the M4 failure point: output report reception is still not reached. The remaining blocker is not explained by HIDP input header absence, status prefix mismatch, or Bumble local MTU alone.

### 2026-07-02: unit_005 single 0x30 and prefix diagnostics still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch at commit `7520925`. Worktree was clean before the initial single-`0x30` runs. The `0x8e` / `0x80` prefix rerun used uncommitted profile changes after unit / integration tests passed.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: all one-off diagnostics used `50,000,000 us` to suppress periodic send. `20260702-003000` waited 300 ms after `connected` before one-shot send; the send was not reached. `20260702-002548` sent one neutral `0x30` immediately after `connected` with the then-current `0x91` / `0x00` status prefix. `20260702-003225` sent one neutral `0x30` immediately after `connected` with the daemon-aligned `0x8e` / `0x80` status prefix.
- command / test: `uv run python .pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\single_0x30_probe.py`; `uv run python .pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\single_0x30_immediate_probe.py`; `uv run python .pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\single_0x30_prefix_probe.py`
- approval: user explicitly approved the immediate single-`0x30` diagnostic and the follow-up prefix-difference diagnostic. Scope included `usb:0` adapter open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, one neutral `0x30` send, 5 s observation, and cleanup. Scope excluded periodic report loop, non-neutral input, Button A input reflection, and reconnect.
- result: fail before output report. The 300 ms delay diagnostic reached `connected` but disconnected with reason 19 before the single `0x30` send; trace recorded no `report_tx`. The `0x91` / `0x00` immediate diagnostic reached `connected`, sent one neutral `0x30` (`report_tx` reason `single_probe_immediate`), recorded no `HID CONTROL PDU`, no `HID INTERRUPT PDU`, no `output_report_rx`, no `subcommand_rx`, and no `subcommand_reply_tx`, then Switch-side reason 19 disconnected. Its debug log shows `>>> HID INTERRUPT SEND DATA, PDU: a130009100...` at line 904 and `REMOTE_USER_TERMINATED_CONNECTION_ERROR` at line 921. The `0x8e` / `0x80` prefix rerun also reached `connected`, sent one neutral `0x30` (`report_tx` reason `single_probe_prefix_8e80`), recorded no output report events, and disconnected with reason 19. Its debug log shows `>>> HID INTERRUPT SEND DATA, PDU: a130008e...80...` at line 431 and `REMOTE_USER_TERMINATED_CONNECTION_ERROR` at line 448.
- artifact: `.pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\single-0x30-delay.jsonl`, `.pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\bumble-debug.log`, `.pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\single-0x30-immediate.jsonl`, `.pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\bumble-debug.log`, `.pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\single-0x30-prefix-8e80.jsonl`, `.pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\bumble-debug.log`
- cleanup: all one-off diagnostics called `pad.close(neutral=False)` after observation or failure. No non-neutral input operation was sent. The immediate diagnostics recorded `transport_close_complete`; final probe cleanup markers reached `probe_cleanup_done`.
- notes: These diagnostics reduce the likelihood that the failure is only caused by continuous 8 ms periodic `0x30` traffic or by the status prefix mismatch alone. They also show that a 300 ms delay is too late for this Switch-side state, because the connection closes before the first send. The remaining difference from swbt-daemon is not simply HIDP input header presence; both immediate diagnostics sent `a1 30` but still did not induce Switch output report `a2 01`. The `0x8e` / `0x80` profile change remains useful as daemon-aligned implementation policy, but this hardware run did not move the M4 failure point.

### 2026-07-02: unit_005 reset-state rerun still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch at commit `0eaaaf4`. User reported that the Switch-side connection state had been reset before this rerun.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: `20260702-001048` used default 8000 us. `20260702-001143` used 50,000,000 us as a no-report-window diagnostic and emitted no periodic input report during the observation window.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-001048 --log-file .pytest_cache\hardware\unit_005\20260702-001048\pytest-debug.log --log-file-level=DEBUG -q -s`; no-report-window diagnostic used a one-off `uv run python -` script and wrote `.pytest_cache\hardware\unit_005\20260702-001143\subcommand-sequence-no-report-window.jsonl`
- approval: user explicitly requested rerunning verification after resetting connection state. Scope followed the existing unit_005 approval: USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for the pytest run, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. The pytest run reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, `connected`, encryption change, and L2CAP open. It recorded no `HID CONTROL PDU`, `HID INTERRUPT PDU`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`, then sent 14 neutral `0x30` reports before Switch-side reason 19 disconnect. The debug log showed direct L2CAP connection requests for HID control PSM `0x0011` and interrupt PSM `0x0013`; no SDP query was observed in the extracted log lines. The no-report-window diagnostic also reached `connected`, recorded no `report_tx` and no output report, then disconnected with reason 19.
- artifact: `.pytest_cache\hardware\unit_005\20260702-001048\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-001048\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260702-001143\subcommand-sequence-no-report-window.jsonl`
- cleanup: pytest run executed `pad.close(neutral=True)` from `finally`; traces recorded `transport_close_complete`. The no-report-window diagnostic closed the pad after observing disconnect. No non-neutral input operation was sent.
- notes: Resetting the connection state did not move the failure point. The current blocker remains before M4 subcommand responder behavior is exercised. The no-report-window diagnostic again shows the disconnect is not explained solely by early neutral `0x30` reports.

### 2026-07-02: unit_005 SDP service-name run still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch at commit `e1ac888`. Runs included HID SDP service name attribute `0x0100` and corrected SDP LanguageBaseAttributeIDList values, in addition to the earlier HIDP DATA, SET_REPORT, control-channel output report, and HID SDP policy fixes.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: `20260702-000120` used default 8000 us. `20260702-000302` used 50,000,000 us as a no-report-window diagnostic and emitted no periodic input report during the observation window.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-000120 --log-file .pytest_cache\hardware\unit_005\20260702-000120\pytest-debug.log --log-file-level=DEBUG -q -s`; no-report-window diagnostic used a one-off `uv run python -` script and wrote `.pytest_cache\hardware\unit_005\20260702-000302\subcommand-sequence-no-report-window.jsonl`
- approval: user explicitly approved unit_005 hardware verification. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for the pytest run, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. The pytest run reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, `connected`, pairing success, encryption change, and L2CAP open. It recorded no `HID CONTROL PDU`, `HID INTERRUPT PDU`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`, then sent 14 neutral `0x30` reports before Switch-side reason 19 disconnect. The no-report-window diagnostic also reached `connected`, recorded no `report_tx` and no output report, then disconnected with reason 19.
- artifact: `.pytest_cache\hardware\unit_005\20260702-000120\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-000120\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260702-000302\subcommand-sequence-no-report-window.jsonl`
- cleanup: pytest run executed `pad.close(neutral=True)` from `finally`; traces recorded `transport_close_complete`. The no-report-window diagnostic closed the pad after observing disconnect. No non-neutral input operation was sent.
- notes: Adding SDP service name and correcting the SDP language base did not move the failure point. The `20260702-000120` debug log showed incoming L2CAP connection requests for HID control PSM `0x0011` and interrupt PSM `0x0013`, with no SDP PSM query observed in the captured log. This means the SDP service name / language base change may not have been re-read by the Switch in this run. Since the no-report-window diagnostic also disconnects before any output report, the current blocker is still before M4 subcommand responder behavior is exercised and is not explained solely by early neutral `0x30` reports.

### 2026-07-01: unit_005 post-transport-fix subcommand run still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch. Runs used committed transport fixes for HIDP DATA output header stripping, SET_REPORT forwarding, control-channel output report handling, and HID SDP policy alignment with the reference implementation.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: `20260701-234045` and `20260701-234437` used default 8000 us. `20260701-234549` used 50,000,000 us as a no-report-window diagnostic and emitted no periodic input report during the observation window.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-234045 --log-file .pytest_cache\hardware\unit_005\20260701-234045\pytest-debug.log --log-file-level=DEBUG -q -s`; repeated after HID SDP policy alignment with artifact dir `.pytest_cache\hardware\unit_005\20260701-234437`. The no-report-window diagnostic used a one-off `uv run python -` script and wrote `.pytest_cache\hardware\unit_005\20260701-234549\subcommand-sequence-no-report-window.jsonl`
- approval: user explicitly approved unit_005 hardware verification. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for pytest runs, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. Runs reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, and `connected`. Debug logs confirmed `SetReport callback registered successfully`; the post-SDP run also showed pairing, link key notification, encryption change, and both L2CAP channels open. No run recorded `HID CONTROL PDU`, `HID INTERRUPT PDU`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`. The pytest runs sent neutral `0x30` reports before Switch-side reason 19 disconnect. The no-report-window diagnostic sent no periodic input report before the same reason 19 disconnect.
- artifact: `.pytest_cache\hardware\unit_005\20260701-234045\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-234045\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-234437\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-234437\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-234549\subcommand-sequence-no-report-window.jsonl`
- cleanup: each pytest run executed `pad.close(neutral=True)` from `finally`; traces recorded `transport_close_complete`. The no-report-window diagnostic closed the pad after observing disconnect. No non-neutral input operation was sent.
- notes: The receive path now handles Bumble HIDP DATA headers, SET_REPORT output reports, control-channel output reports, and the reference HID SDP policy. Current failure remains before M4 subcommand responder behavior is exercised. The no-report-window diagnostic means the disconnect is not explained solely by early neutral `0x30` reports. Remaining candidates are Switch-side HID adoption state, Bumble HID Device behavior, timing, or another transport-level difference; those are not confirmed.

### 2026-07-01: unit_005 subcommand sequence attempts stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch. Attempt 1 ran from a clean worktree at commit `50d552d`. Attempts 2 and 3 used temporary uncommitted experiments that were reverted after the run: slower M4 test report period, then Bumble report-loop deferral.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: attempt 1 used default 8000 us; attempt 2 used temporary 50000 us in the M4 hardware test; attempt 3 deferred periodic report start until host output. Attempt 3 emitted no `report_tx` before disconnect.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232123 --log-file .pytest_cache\hardware\unit_005\20260701-232123\pytest-debug.log --log-file-level=DEBUG -q -s`; repeated with artifact dirs `20260701-232352` and `20260701-232634`
- approval: user explicitly approved unit_005 hardware verification. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for attempts 1 and 2, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. All attempts reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, and `connected`. No attempt recorded `output_report_rx`, `subcommand_rx`, `subcommand_reply_tx`, `unsupported_subcommand`, `HID CONTROL PDU`, or `HID INTERRUPT PDU` from Switch. Attempt 1 sent periodic `0x30` reports before Switch disconnected with reason 19. Attempt 2 sent two slower `0x30` reports before the same disconnect. Attempt 3 sent no input report before Switch disconnected with reason 19. The current failure point is before M4 output report handling.
- artifact: `.pytest_cache\hardware\unit_005\20260701-232123\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-232123\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-232352\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-232352\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-232634\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-232634\pytest-debug.log`
- cleanup: each run executed `pad.close(neutral=True)` from `finally`; trace recorded `transport_close_complete`. Attempts 1 and 2 had already received Switch-side disconnect before cleanup. Attempt 3 had no input report before disconnect.
- notes: Sending no periodic report before host output did not cause Switch to send `0x01`; therefore the earlier disconnect is not explained solely by early `0x30` reports. Existing swbt-daemon design and implementation show that output handler, report scheduler, and send-ready integration are part of the successful BTstack path; Bumble-specific L2CAP/HID readiness remains unverified for M4.

### 2026-07-01: unit_004 pairing / L2CAP pass after discovery identity alignment

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-004-pairing-l2cap` branch with uncommitted unit_004 implementation after aligning discovery identity with the reference production path
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: 8000 us default. Report loop started after `connected`; trace recorded one neutral `0x30` `report_tx`. Semantic input reflection was not tested
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-225624 --log-file .pytest_cache\hardware\unit_004\20260701-225624\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved rerunning the M3 hardware test after applying the discovery identity fix. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing attempt, HID control / interrupt channel open wait, and cleanup. Scope excluded semantic input reflection and reconnect.
- result: pass, `1 passed, 1 warning in 6.81s`. Trace includes `device_name="Pro Controller"`, `class_of_device="0x002508"`, `host_connection`, `classic_pairing`, `l2cap_channel_open` for control PSM `0x0011`, `l2cap_channel_open` for interrupt PSM `0x0013`, `connected`, one neutral `report_tx`, `disconnected reason=0`, and `transport_close_complete`. Debug log confirms `HCI_WRITE_LOCAL_NAME_COMMAND` with `Pro Controller`, `HCI_WRITE_CLASS_OF_DEVICE_COMMAND` with `[002508]`, incoming `HCI_CONNECTION_REQUEST_EVENT`, successful connection complete, successful simple pairing complete, and both L2CAP channels open. `HCI_WRITE_SECURE_CONNECTIONS_HOST_SUPPORT_COMMAND` still returned `UNKNOWN_HCI_COMMAND_ERROR`, but it did not block pairing or L2CAP in this run.
- artifact: `.pytest_cache\hardware\unit_004\20260701-225624\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_004\20260701-225624\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `disconnected reason=0` and `transport_close_complete`. No non-neutral input operation was sent.
- notes: The previous pre-connection-request timeout was no longer reproduced after changing local name from `swbt-python` to `Pro Controller` and Class of Device from `0x000508` to `0x002508`. That causal link is a strong working inference, not a controlled A/B proof, because the run also depended on manual Switch-side operation timing.

### 2026-07-01: unit_004 pairing / L2CAP timeout before connection request

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-004-pairing-l2cap` branch with uncommitted unit_004 implementation
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used; report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-224227 --log-file .pytest_cache\hardware\unit_004\20260701-224227\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved running the M3 hardware experiment from Codex. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing attempt, HID control / interrupt channel open wait, and cleanup. Scope excluded input reflection and reconnect.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `advertising_start`, `connection_timeout state=advertising`, error event, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `pairing_start`, `pairing_complete`, or `l2cap_channel_open`.
- artifact: `.pytest_cache\hardware\unit_004\20260701-224227\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_004\20260701-224227\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. Report loop did not start and no input report was sent.
- notes: HCI debug log shows BD_ADDR `00:1B:DC:F9:9F:7D/P`, local name `swbt-python`, class of device write, `HCI_WRITE_SCAN_ENABLE_COMMAND` success, and extended inquiry response write. `HCI_WRITE_SECURE_CONNECTIONS_HOST_SUPPORT_COMMAND` returned `UNKNOWN_HCI_COMMAND_ERROR`; the run continued to scan enable afterward. This remains a pre-connection-request failure, not an L2CAP failure.

### 2026-07-01: unit_004 pairing / L2CAP timeout before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-004-pairing-l2cap` branch with uncommitted unit_004 implementation
- adapter: `usb:0`
- dongle: not re-recorded in this run. Previous unit_003 inventory associated `usb:0` with CSR8510 A10, `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used; report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-223511 -q -s`
- approval: manual user-run M3 hardware experiment. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing attempt, HID control / interrupt channel open wait, and cleanup. Scope excluded input reflection and reconnect.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `advertising_start`, `connection_timeout state=advertising`, error event, and `transport_close_complete`. Trace does not include `host_connection`, `pairing_start`, `pairing_complete`, or `l2cap_channel_open`.
- artifact: `.pytest_cache\hardware\unit_004\20260701-223511\pairing-l2cap.jsonl`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. Report loop did not start and no input report was sent.
- notes: This is not yet an L2CAP failure. The observed failure point is before Bumble reports a host connection.

### 2026-07-01: unit_003 Bumble HID advertising smoke

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/unit-003-bumble-hardware` branch
- adapter: `usb:0`
- dongle: CSR8510 A10, `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not used
- Switch firmware: not used
- report period: not used
- command / test: `uv run pytest tests\hardware\test_bumble_transport.py -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_003\20260701-022335 -q`
- approval: user approved this M2 hardware smoke. Scope included Bumble adapter open, Bumble Device initialization, Classic enable, HID Device initialization, SDP / HID descriptor registration, discoverable / connectable, and close. Scope excluded Switch pairing, L2CAP channel open, subcommand handling, periodic report loop, and input reflection.
- result: pass, `1 passed in 0.52s`. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered` with `hid_descriptor_size=203`, `hid_device_initialized`, `transport_open_complete`, `advertising_start`, and `transport_close_complete`.
- artifact: `.pytest_cache\hardware\unit_003\20260701-022335\bumble-hid-advertising-smoke.jsonl`
- cleanup: test called `BumbleHidTransport.close()` twice in `finally`; trace recorded one `transport_close_complete`. Post-run PnP status for CSR8510 A10 was `OK`.
- notes: `usb:0` is associated with CSR8510 A10 by the pre-run Windows PnP inventory. This run did not pair with a console, open HID channels, receive subcommands, start the periodic report loop, or send input reports.

### 2026-07-01: unit_003 Bumble adapter open / close smoke

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/unit-003-bumble-hardware` branch
- adapter: `usb:0`
- dongle: CSR8510 A10, `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not used
- Switch firmware: not used
- report period: not used
- command / test: `uv run pytest tests\hardware\test_bumble_transport.py -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_003\20260701-015427 -q`
- approval: user approved Bumble adapter open/close after read-only adapter inventory. Scope excluded Switch pairing, HID advertising, report loop, and input sending.
- result: pass, `1 passed in 0.70s`. Trace includes `transport_open_start`, `transport_open_complete`, and `transport_close_complete`.
- artifact: `.pytest_cache\hardware\unit_003\20260701-015427\bumble-adapter-open-close.jsonl`
- cleanup: test called `BumbleHidTransport.close()` in `finally`; trace recorded `transport_close_complete`.
- notes: `usb:0` is associated with CSR8510 A10 by the pre-run Windows PnP inventory. This run did not initialize Bumble HID Device, enter discoverable / connectable state, pair with a console, or open HID channels.

## Marker Result Mapping

| marker | 記録する結果 | 実行条件 |
|---|---|---|
| `@pytest.mark.bumble` | adapter open、Classic、HID advertising、cleanup | 明示承認、専用 USB Bluetooth dongle、adapter string、cleanup plan が揃った場合だけ実行する |
| `@pytest.mark.hardware` | pairing、L2CAP、subcommand sequence、input reflection、cleanup | 明示承認、対象機器、adapter string、report loop と入力操作の範囲、cleanup plan が揃った場合だけ実行する |

## Recording Rules

- `approval` には、会話上の明示承認、adapter open、HID advertising、pairing、report loop、input operation、cleanup の実行範囲を書く。
- `command / test` には、実行した command を省略せず書く。
- `result` には、成功、失敗、未実行を分けて書く。原因が未確定なら推測を書かない。
- `artifact` には、diagnostics trace、pytest log、手元記録など、後から結果を辿れる場所を書く。
- `cleanup` には、neutral、report loop stop、transport close、adapter release など実施した後始末と結果を書く。
- link key、secret、個人環境に固有の token は記録しない。
