# M4 Subcommand Responder 実機通過 仕様書

## 1. 概要

### 1.1 目的

Switch から受け取る output report と subcommand sequence を実機 trace で観測し、M0 の `SubcommandResponder` を不足分込みで更新する。M4 の完了条件は、主要 subcommand に `0x21` reply を返し、初期化 sequence が入力反映手前まで進むこととする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M4 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| protocol | output report parse、subcommand reply、reply priority | `spec/initial/protocol.md` |
| testing | hardware test の subcommand sequence 項目 | `spec/initial/testing.md` |
| risks | subcommand 応答不足と firmware 差分 | `spec/initial/risks.md` |
| source-audit skill | subcommand ID、reply payload、SPI data の根拠分類 | `.agents/skills/source-audit/SKILL.md` |
| hardware-harness skill | Switch-facing output report / subcommand handling の承認境界 | `.agents/skills/hardware-harness/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch | `0x01` output report | report ID、packet id、subcommand id、payload が diagnostics に残る | 実機承認が必要 |
| protocol | 観測済み subcommand | `0x21` reply が生成される | payload は根拠監査済み |
| report loop | reply queue と periodic report | `0x21` が `0x30` より優先送信される | M1 の優先制御を実機 trace で確認 |
| developer | 未対応 subcommand | raw bytes、payload、sequence position が文書化される | 隠さず M0/M4 に戻す |

## 2. 対象範囲

- 実機からの `0x01` output report 受信。
- subcommand id と payload の diagnostics 記録。
- 観測済み subcommand sequence の hardware log 反映。
- `SubcommandResponder` の不足補完。
- `0x21` reply の priority queue 投入。
- periodic `0x30` と reply の送信順序確認。
- 未対応 subcommand の文書化。

## 3. 対象外

- 高水準 NFC / IR 意味処理。
- 高水準 rumble API。
- reconnect。
- Button A 反映の完了判定。
- firmware 差分の網羅。

## 4. 関連 docs

- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_001/M0_PROTOCOL_CORE.md`
- `spec/wip/unit_002/M1_SWITCH_GAMEPAD_FAKE_TRANSPORT.md`
- `spec/complete/unit_004/M3_PAIRING_L2CAP.md`
- `spec/wip/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` の `output_report_parser_layout`、`subcommand_reply_0x21_layout`、`subcommand_reply_payloads`、`spi_flash_boundary_and_seed_map`、`raw_rumble_payload` を source fact / implementation fact として使う |
| Bumble / transport | required | done | `bumble_hid_device_api`、`bumble_hidp_output_report_boundary`、`btstack_reference_hid_sdp_policy`、`bumble_reference_classic_link_policy`、`bumble_acl_packet_queue_drain_boundary` を使う。Bumble `0.0.230` の DATA / SET_REPORT callback 境界、参照実装の HID SDP policy、service name / language base 属性、daemon production の default link policy `ROLE_SWITCH|SNIFF_MODE` = `0x0005`、ACL queue の投入・drain 境界は根拠化済み。通常送信をenqueue受理、明示切断をdrain境界とする現行方針は unit_064 で更新した。実機 sequence の callback timing は M4 実行時の hardware observation として別記録にする |
| OS / driver / adapter | required | done | `swbt_daemon_csr8510_winusb_observation` は既存 daemon の条件付き観測であり、Bumble / 別 firmware へ一般化しない。M4 実機 trace は adapter、driver、Bumble version、Switch firmware 付きで `docs/hardware-test-log.md` に記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| output report trace | Switch から `0x01` | raw bytes、packet id、subcommand id、payload を記録する | privacy 不要な raw HID のみ |
| responder lookup | 対応 subcommand | `0x21` reply bytes を生成する | M0 unit test に反映 |
| SPI read | `0x10` subcommand | `VirtualSpiFlash` の指定範囲を返す | address と data は監査対象 |
| unsupported subcommand | 未対応 id | diagnostics に `unsupported_subcommand` を残す | fail-safe reply の要否を判断 |
| reply queue | reply generated | `ReportLoop` の priority queue に入る | 送信は `send_interrupt()` |
| send order | reply queue 非空 | `0x21` reply が次 tick で送られる | `0x30` より前 |
| initialization progress | pairing 後の sequence | 入力反映手前まで進む | 反映判定は M5 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `0x01` fixture から subcommand id と payload を parse できる | characterization | unit | no | `test_0x01_output_report_extracts_packet_rumble_subcommand_and_payload` で packet id、rumble、subcommand id、payload を確認。実機 trace fixture 化は hardware run 後に扱う |
| green | `0x02` device info reply が監査済み payload を返す | regression | unit | no | `test_device_info_subcommand_builds_profile_reply` で ACK と payload を確認 |
| green | `0x10` SPI read reply が address と size に応じた data を返す | regression | unit | no | `test_spi_flash_read_subcommand_returns_request_prefix_and_seed_data` と `test_virtual_spi_flash_*` で seed data と範囲条件を確認 |
| green | 未対応 subcommand が diagnostics event を生成する | new | integration | no | `test_callback_exception_is_recorded_in_trace_and_status` で `unsupported_subcommand` と `error` event を確認 |
| green | fake transport 注入時に `0x21` reply が `0x30` より先に送られる | regression | integration | no | `test_subcommand_reply_queue_takes_priority_over_periodic_input` と `test_output_report_rx_and_subcommand_rx_share_packet_id` で送信順序と reply trace 対応付けを確認 |
| green | Bumble HIDP DATA の output header を除去して上位へ渡す | regression | unit | no | `test_bumble_hid_data_callbacks_strip_hidp_output_data_header` で DATA PDU の HIDP header を transport 境界で剥がすことを確認 |
| green | Bumble SET_REPORT callback の output report を上位へ渡す | regression | unit | no | `test_bumble_set_report_callback_forwards_output_report` で `report_id + report_data` と handshake status を確認 |
| green | control channel の output report でも `0x21` reply を返す | regression | integration | no | `test_control_output_report_injection_sends_subcommand_reply` で control 経由の output report が responder と reply queue に到達することを確認 |
| green | HID SDP policy が参照実装と一致する | regression | unit | no | `test_bumble_hid_service_record_matches_reference_sdp_policy` で service name、LanguageBaseAttributeIDList、HID language base、country code、remote wake、supervision timeout、SSR host max/min を確認 |
| green | Classic default link policy を daemon production と同じ `0x0005` に合わせる | regression | unit | no | `test_bumble_start_advertising_configures_reference_classic_link_policy` で `HCI_Write_Default_Link_Policy_Settings_Command(0x0005)` が connectable / discoverable 前に送られることを確認。BTstack の `allow_role_switch=true` は outgoing ACL 向け記述のため incoming Switch 接続の修正根拠にはしない |
| green | 実機で `0x01` output report を受信できる | new | hardware | yes | 2026-07-02 の link-policy-only run と observation window run で `output_report_rx` report `0x01` を観測 |
| green | 観測された subcommand sequence が trace に残る | new | hardware | yes | 2026-07-02 の observation window run で `0x02` x1、`0x08` x8、`subcommand_rx`、`subcommand_reply_tx`、`report_tx` reason `subcommand_reply` を記録 |
| green | 観測 subcommand に `0x21` reply を返せる | new | hardware | yes | 2026-07-02 の observation window run で `0x02` x1 と `0x08` x8 を観測し、全件に `0x21` reply を送信した。全 subcommand / 全 firmware の網羅ではない |
| green | 未対応 subcommand があれば docs に反映されている | characterization | hardware | yes | 2026-07-02 の observation window run で `unsupported_subcommand` は 0 件。未対応 subcommand が出た場合は diagnostics と hardware log に残す方針を維持する |

## 8. 設計メモ

- 実機 trace から得た sequence は `hardware observation` であり、別 firmware への一般化はしない。
- `SubcommandResponder` の unit test は source fact または実機 fixture を明示してから green にする。
- fail-safe reply を作る場合でも、未対応 subcommand を diagnostics から消さない。
- M4 は入力 UI 反映の成否を最終判定にしない。反映は M5 の範囲。
- 2026-07-01 から 2026-07-02 の M4 実機試行では、Bumble 0.0.230 / CSR8510 A10 / WinUSB / `usb:0` 条件で HID control / interrupt channel open までは到達したが、Switch から HID output report は来なかった。HIDP DATA header 除去、SET_REPORT callback、control channel output report、HID SDP service name / language base / policy は非実機テストで green。service name と language base を参照実装へ合わせた後、ユーザが Switch 側接続状態をリセットしても `output_report_rx` は未観測で、50,000,000 us の no-report-window diagnostic でも reason 19 で切断された。追加の single-`0x30` diagnostic では、接続後 300 ms 待機版は `0x30` 送信前に reason 19 で切断され、接続直後 1 件版は `0x91` / `0x00` prefix と daemon-aligned `0x8e` / `0x80` prefix の両方で `a1 30` を 1 件送信した後も `output_report_rx` 未観測のまま reason 19 で切断された。`20260702-001048` の debug log では HID control PSM `0x0011` と interrupt PSM `0x0013` への直接 L2CAP connection request は見えるが、SDP PSM query は観測していない。原因は「早すぎる `0x30`」または「status prefix mismatch」単独では説明できない。これは hardware observation と inference であり、未確認の一般仕様に昇格しない。
- swbt-daemon の成功 dump は HID control / interrupt の L2CAP server を `mtu 100` で登録し、channel open 後の `local_mtu` も `100` だった。Bumble 0.0.230 の `ClassicChannelSpec` 既定 MTU は `2048` で、`bumble.hid.HID` は既定値のまま PSM `0x0011` / `0x0013` server を作る。2026-07-02 の `20260702-004659-mtu100` run は control / interrupt とも `MTU=100/672` で open したことを確認したが、`output_report_rx` は未観測のまま Switch 側 reason 19 で切断された。したがって、現在の失敗は Bumble local MTU mismatch 単独では説明できない。MTU `100` 再登録は最小実装から外した。
- swbt-daemon production は Classic discovery 設定で default link policy を `ROLE_SWITCH|SNIFF_MODE` = `0x0005` にする。daemon 成功 dump では L2CAP open 後、最初の Switch output report 付近で `HCI_EVENT_MODE_CHANGE, mode 2` が見える一方、2026-07-02 の Bumble MTU-100 run では Mode Change が観測されず、送信側に HCI completed-packet backlog も残っていた。swbt-python では Bumble `power_on` 後、connectable / discoverable 化の前に `HCI_Write_Default_Link_Policy_Settings_Command(0x0005)` を送る。2026-07-02 の `20260702-011634-link-policy-only` run では `classic_link_policy_configured`、Switch input PDU `a2 01`、reply PDU `a1 21` を観測し、M4 hardware test が pass した。この run では MTU `100` 再登録も `0x8e` / `0x80` prefix 変更も含めていないため、現時点の最小 runtime 変更は Classic default link policy `0x0005`。BTstack の `allow_role_switch=true` は outgoing classic ACL 向けの API 説明なので、incoming Switch 接続の修正根拠としては扱わない。
- 2026-07-02 の最初の observation-window 試行では、`subcommand_reply_tx` と `report_tx` は出ていたが Bumble debug log に `10 packets in flight` と大きな queue backlog が残った。`report_tx` は transport enqueue 前の記録ではなく、`send_interrupt()` が戻った後の記録に変更した。Bumble `0.0.230` の `hid.HID.send_data()` は L2CAP channel `write()` までで、controller 完了は `host.DataPacketQueue.pending` / `drain()` が持つため、Bumble transport は HID interrupt send 後に該当 connection の ACL queue を drain する。2026-07-02 の `20260702-obs-window-host-queue-drain` run では `0x02` x1 と `0x08` x8 の全件に `0x21` reply を送り、debug log の `packets in flight` backlog 行は 0 件だった。これは Bumble 0.0.230 / CSR8510 A10 / WinUSB / `usb:0` 条件の実装境界であり、別 adapter での latency guarantee にはしない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/subcommand.py` | modify | 実機 sequence に必要な reply |
| `src/swbt/protocol/spi.py` | modify | SPI read data |
| `src/swbt/protocol/output_report.py` | modify | hardware fixture に基づく parser 補強 |
| `src/swbt/report_loop.py` | modify | reply priority の実機 trace 対応 |
| `src/swbt/diagnostics.py` | modify | subcommand rx / reply tx event |
| `src/swbt/transport/bumble.py` | modify | HIDP DATA / SET_REPORT / control channel 境界、Classic link policy |
| `tests/unit/` | modify | subcommand reply fixture tests |
| `tests/integration/` | modify | fake injection priority tests |
| `tests/hardware/` | modify | subcommand sequence hardware tests |
| `docs/hardware-test-log.md` | modify | 実機 trace summary |

## 10. 検証

この表は M4 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_output_report.py::test_0x01_output_report_extracts_packet_rumble_subcommand_and_payload -q` | pass | 1 passed。`0x01` output report から packet id、rumble、subcommand id、payload を parse できる |
| `uv run pytest tests\unit\test_subcommand_responder.py::test_device_info_subcommand_builds_profile_reply -q` | pass | 1 passed。`0x02` device info reply の ACK / payload を確認した |
| `uv run pytest tests\unit\test_subcommand_responder.py::test_spi_flash_read_subcommand_returns_request_prefix_and_seed_data tests\unit\test_virtual_spi_flash.py -q` | pass | 6 passed。`0x10` SPI read reply と virtual SPI flash の seed / range 条件を確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_callback_exception_is_recorded_in_trace_and_status -q` | pass | 1 passed。未対応 subcommand の packet id、payload、subcommand id が `unsupported_subcommand` event に残り、既存の failed/error path も維持される |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_output_report_rx_and_subcommand_rx_share_packet_id -q` | pass | 1 passed。`output_report_rx`、`subcommand_rx`、`subcommand_reply_tx` が同じ packet id / subcommand id で対応付くことを確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_subcommand_reply_queue_takes_priority_over_periodic_input -q` | pass | 1 passed。reply queue の `0x21` が次送信で periodic `0x30` より先に送られる |
| `uv run pytest tests\hardware --collect-only -q` | pass | 4 tests collected。M4 の `test_switch_subcommand_sequence_gets_0x21_replies` と `test_switch_subcommand_observation_window_replies_to_all_observed_commands` を収集できる。実機・adapter open は未実行 |
| `uv run pytest tests\unit\test_bumble_transport.py tests\unit\test_source_audit_fixtures.py -q` | pass | 27 passed。Classic default link policy `0x0005`、Bumble ACL queue drain、HIDP DATA header、SET_REPORT callback、HID SDP service name / language base / policy、source-audit fixture を確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | 20 passed。interrupt / control 経由の output report と reply queue を fake transport で確認した |
| `uv sync --dev` | pass | Resolved 41 packages / Checked 41 packages |
| `uv run ruff format --check .` | pass | 36 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 97 passed。最小実装へ戻した後、profile default は元の `0x91` / `0x00`、Bumble transport 変更は Classic default link policy `0x0005` と ACL queue drain に整理して確認した |
| `uv run pytest tests\integration` | pass | 20 passed。fake transport integration の全件を確認した |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232123 --log-file .pytest_cache\hardware\unit_005\20260701-232123\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | L2CAP open と periodic `0x30` 13 件後、Switch 側 reason 19 で切断。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232352 --log-file .pytest_cache\hardware\unit_005\20260701-232352\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | M4 test だけ temporary `report_period_us=50000` で実行。`0x30` 2 件後に Switch 側 reason 19 で切断。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232634 --log-file .pytest_cache\hardware\unit_005\20260701-232634\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | temporary に Bumble report loop を host output まで遅延。`report_tx` なしでも L2CAP open 後に Switch 側 reason 19 で切断。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-234045 --log-file .pytest_cache\hardware\unit_005\20260701-234045\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | HIDP DATA / SET_REPORT / control channel handling 修正後。SET_REPORT callback 登録、pairing、L2CAP open までは到達。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-234437 --log-file .pytest_cache\hardware\unit_005\20260701-234437\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | HID SDP policy 参照実装合わせ後。pairing、encryption、L2CAP open までは到達。`output_report_rx` は未観測 |
| `uv run python -` | observed-fail | `.pytest_cache\hardware\unit_005\20260701-234549\subcommand-sequence-no-report-window.jsonl` に記録。50,000,000 us no-report-window で periodic `0x30` を出さずに観測しても `output_report_rx` は来ず、Switch 側 reason 19 で切断 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-000120 --log-file .pytest_cache\hardware\unit_005\20260702-000120\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | HID SDP service name / language base 参照実装合わせ後。pairing、encryption、L2CAP open までは到達。`output_report_rx` は未観測。debug log では HID PSM `0x0011` / `0x0013` への直接 connection request は見えるが、SDP PSM query は未観測 |
| `uv run python -` | observed-fail | `.pytest_cache\hardware\unit_005\20260702-000302\subcommand-sequence-no-report-window.jsonl` に記録。HID SDP service name / language base 反映後、50,000,000 us no-report-window で periodic `0x30` を出さずに観測しても `output_report_rx` は来ず、Switch 側 reason 19 で切断 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-001048 --log-file .pytest_cache\hardware\unit_005\20260702-001048\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | Switch 側接続状態リセット後。pairing、encryption、L2CAP open までは到達。`output_report_rx` は未観測。debug log では HID PSM `0x0011` / `0x0013` への直接 connection request は見えるが、SDP PSM query は未観測 |
| `uv run python -` | observed-fail | `.pytest_cache\hardware\unit_005\20260702-001143\subcommand-sequence-no-report-window.jsonl` に記録。Switch 側接続状態リセット後、50,000,000 us no-report-window で periodic `0x30` を出さずに観測しても `output_report_rx` は来ず、Switch 側 reason 19 で切断 |
| `uv run python .pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\single_0x30_probe.py` | observed-fail | 50,000,000 us で periodic を抑制し、接続後 300 ms 待って neutral `0x30` を 1 件送る診断。`connected` までは到達したが、`report_tx` 前に Switch 側 reason 19 で切断 |
| `uv run python .pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\single_0x30_immediate_probe.py` | observed-fail | 50,000,000 us で periodic を抑制し、接続直後に neutral `0x30` を 1 件だけ送る診断。`report_tx` reason `single_probe_immediate` 1 件、debug log の PDU は `a1 30 ...`。`output_report_rx` は未観測で Switch 側 reason 19 で切断 |
| `uv run python .pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\single_0x30_prefix_probe.py` | observed-fail | 50,000,000 us で periodic を抑制し、接続直後に daemon-aligned `0x8e` / `0x80` prefix の neutral `0x30` を 1 件だけ送る診断。debug log の PDU は `a1 30 00 8e ... 80 ...`。`output_report_rx` は未観測で Switch 側 reason 19 で切断 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-004659-mtu100 --log-file .pytest_cache\hardware\unit_005\20260702-004659-mtu100\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | MTU-100 反映後。trace は `hid_l2cap_mtu=100`、control / interrupt L2CAP open、`connected`、periodic `0x30` 14 件後に Switch 側 reason 19 で切断。debug log は両 channel が `MTU=100/672` で open したことを示す。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-010148-link-policy --log-file .pytest_cache\hardware\unit_005\20260702-010148-link-policy\pytest-debug.log --log-file-level=DEBUG -q -s` | pass-before-cleanup | 1 passed, 1 warning in 2.92s。trace は `classic_link_policy_configured` `0x0005`、`classic_mode_change` mode `2` interval `24`、`output_report_rx` report `0x01` / subcommand `0x02`、`subcommand_rx`、`subcommand_reply_tx`、`report_tx` reason `subcommand_reply` を記録。debug log は `HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND`、`HCI_MODE_CHANGE_EVENT`、input PDU `a2 01`、reply PDU `a1 21` を示す。この run は cleanup 前の MTU / prefix 変更も含むため、link-policy-only 実装の実機再検証は未実行 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-011634-link-policy-only --log-file .pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | 1 passed, 1 warning in 4.27s。trace は `classic_link_policy_configured` `0x0005`、`output_report_rx` report `0x01` / subcommand `0x02`、`subcommand_rx`、`subcommand_reply_tx`、`report_tx` reason `subcommand_reply` を記録。debug log は `HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND`、`HCI_MODE_CHANGE_EVENT`、input PDU `a2 01`、reply PDU `a1 21 00 91...` を示す。trace に `hid_l2cap_mtu` はなく、MTU `100` 再登録なしの最小実装で pass |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain --log-file .pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\pytest-debug.log --log-file-level=DEBUG -q -s` | pass | 1 passed, 1 warning in 9.50s。trace は `output_report_rx` 9 件、`subcommand_rx` 9 件、`subcommand_reply_tx` 9 件、`report_tx` reason `subcommand_reply` 9 件を記録。観測 subcommand は `0x02` x1 と `0x08` x8。`unsupported_subcommand` と `error` は 0 件。Bumble debug log の `packets in flight` backlog match は 0 件 |
| `uv run pytest -m hardware` | not-run | 全 hardware marker は未実行。unit_005 対象の M4 hardware test は pass |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | adapter open、HID advertising、pairing、output report 受信、`0x21` reply 送信、periodic report loop、close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics JSON Lines trace、`docs/hardware-test-log.md`、subcommand fixture |
| cleanup | neutral state へ戻し、report loop 停止、transport close、adapter release |

## 12. 先送り事項

- Button A など入力反映の UI 確認は M5 で扱う。
- reconnect 中の subcommand sequence は M6 で扱う。
- 未対応 subcommand が release blocker かどうかは release gate で判断する。

## 13. チェックリスト

このチェックリストは M4 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] subcommand ID、reply payload、SPI data の根拠監査を実施し、状態を更新した
- [x] M4 の local automated gate を実行し、検証欄を結果で更新した
- [x] 実機検証は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [x] 完了条件を満たしたら `spec/complete` へ移動する
