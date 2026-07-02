# Hardware Test Log

この文書は、Bumble adapter と対象機器に依存する観測を記録する正本である。

実機観測は、OS、driver、dongle、adapter string、Bumble version、Python version、Switch model / firmware に依存する。ここに記録した結果は、その条件での観測であり、別構成での保証には使わない。

## Current Status

- Hardware run: 2026-07-01 に CSR8510 A10 / WinUSB / `usb:0` で M2 advertising smoke と M3 pairing / L2CAP pass
- Bumble adapter run: adapter open、Bumble Device 初期化、Classic HID 初期化、SDP / HID descriptor 登録、discoverable / connectable、close を記録済み
- Pairing run: 2026-07-01 に `Pro Controller` / Class of Device `0x002508` で M3 pairing / L2CAP pass。`classic_pairing`、HID control / interrupt channel open、`connected` を記録済み
- Subcommand run: 2026-07-02 に Classic default link policy `0x0005` のみを残した最小実装で M4 subcommand sequence が pass。続く observation window run では Bumble ACL queue drain 後、5 秒以上の実機観測で `0x02` 1 件と `0x08` 8 件を受信し、全件に `0x21` reply を送信した。trace は `classic_link_policy_configured`、Switch からの `0x01` output report、`subcommand_rx`、`subcommand_reply_tx`、`report_tx` reason `subcommand_reply` 9 件を記録し、`unsupported_subcommand` と `error` は 0 件だった。debug log は `packets in flight` backlog 行 0 件だった。link policy 反映前の試行では、HIDP DATA header 除去、SET_REPORT callback、control channel output report、HID SDP policy、service name / language base、daemon-aligned `0x8e` / `0x80` prefix、HID L2CAP local MTU `100` を反映しても `output_report_rx` 未観測のまま Switch 側 reason 19 で切断されていた
- Input reflection run: 2026-07-02 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で M5 input operation sequence を実行した。pytest は `1 passed` だが、これは接続、subcommand reply、`0x30` report 送信、manual checkpoint、clean close を確認するだけで、Switch UI 反映を自動判定しない。ユーザ画面観測では Switch のデバイス登録画面が全く動かなかったため、M5 の semantic input reflection は observed-fail。debug log では A button bytes `08 00 00`、L+R button bytes `40 00 40`、neutral bytes `00 00 00` を含む `a1 30` HID interrupt send は確認済み

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

| OS | Bluetooth dongle | Driver | Adapter | Switch model | Firmware | Pairing | L2CAP | Subcommands | Input reflected | Result source | Last updated | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Windows | CSR8510 A10 | WinUSB / libwdi 6.1.7600.16385 | `usb:0` | 未記録 | 未記録 | pass | pass | pass for observed `0x02` / `0x08` sequence | observed-fail | 2026-07-02 M5 input operation sequence | 2026-07-02 | `Pro Controller` / Class of Device `0x002508` で L2CAP open 後、Classic default link policy `0x0005` と Bumble ACL queue drain を含む実装で Switch output report `a2 01`、`0x02` と `0x08`、`0x21` reply tx まで到達。M5 run では A / L+R / neutral の `a1 30` HID interrupt send と clean close を確認したが、ユーザ画面観測では Switch のデバイス登録画面が全く動かなかった。semantic input reflection は未達 |
| Linux | 未検証 | libusb 想定 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期保証対象に含めるか未決 |
| macOS | 未検証 | 未検証 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期検証対象外 |

## Run Entries

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
- result: observed-fail for semantic input reflection. Pytest reported `1 passed, 1 warning in 10.08s`, but that pass only proves the trace sequence and cleanup assertions. User observed that the Switch device registration screen did not move at all. Debug log confirmed outgoing HID interrupt input reports: A used button bytes `08 00 00` (`a1 30 ... 91 08 00 00 ...`), L+R used `40 00 40` (`a1 30 ... 91 40 00 40 ...`), and neutral used `00 00 00` (`a1 30 ... 91 00 00 00 ...`). Trace recorded no `error` event. The cause is not determined by this run.
- artifact: `.pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final neutral `0x30` input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run proves report transmission through Bumble/L2CAP under the listed conditions, but contradicts M5 completion because Switch UI input reflection was not observed. Next diagnosis should separate report acceptance / controller registration state from report byte correctness. The successful pytest assertion must not be treated as semantic input reflection.

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
