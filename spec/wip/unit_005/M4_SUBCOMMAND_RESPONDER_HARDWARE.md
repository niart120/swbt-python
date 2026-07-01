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
| Bumble / transport | required | done | `bumble_hid_device_api`、`bumble_hidp_output_report_boundary`、`btstack_reference_hid_sdp_policy` を使う。Bumble `0.0.230` の DATA / SET_REPORT callback 境界と参照実装の HID SDP policy は根拠化済み。実機 sequence の callback timing は M4 実行時の hardware observation として別記録にする |
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
| green | HID SDP policy が参照実装と一致する | regression | unit | no | `test_bumble_hid_service_record_matches_reference_sdp_policy` で country code、remote wake、supervision timeout、SSR host max/min を確認 |
| fail | 実機で `0x01` output report を受信できる | new | hardware | yes | 2026-07-01 の M4 post-transport-fix 試行でも L2CAP open 後に `output_report_rx` 未観測のまま Switch 側が reason 19 で切断 |
| fail | 観測された subcommand sequence が trace に残る | new | hardware | yes | `subcommand_rx` 未観測。post-fix failure trace と no-report-window diagnostic は `docs/hardware-test-log.md` に記録 |
| blocked | 主要 subcommand に `0x21` reply を返せる | new | hardware | yes | host output report が未到達のため、実機での reply tx は未検証 |
| observed | 未対応 subcommand があれば docs に反映されている | characterization | hardware | yes | 未対応 subcommand は未観測。未到達状態を hardware log に反映 |

## 8. 設計メモ

- 実機 trace から得た sequence は `hardware observation` であり、別 firmware への一般化はしない。
- `SubcommandResponder` の unit test は source fact または実機 fixture を明示してから green にする。
- fail-safe reply を作る場合でも、未対応 subcommand を diagnostics から消さない。
- M4 は入力 UI 反映の成否を最終判定にしない。反映は M5 の範囲。
- 2026-07-01 の M4 実機試行では、Bumble 0.0.230 / CSR8510 A10 / WinUSB / `usb:0` 条件で HID control / interrupt channel open までは到達したが、Switch から HID output report は来なかった。HIDP DATA header 除去、SET_REPORT callback、control channel output report、HID SDP policy は非実機テストで green。post-fix 実機試行でも `output_report_rx` は未観測で、50,000,000 us の no-report-window diagnostic でも reason 19 で切断された。原因は「早すぎる `0x30`」単独では説明できない。これは hardware observation と inference であり、未確認の一般仕様に昇格しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/subcommand.py` | modify | 実機 sequence に必要な reply |
| `src/swbt/protocol/spi.py` | modify | SPI read data |
| `src/swbt/protocol/output_report.py` | modify | hardware fixture に基づく parser 補強 |
| `src/swbt/report_loop.py` | modify | reply priority の実機 trace 対応 |
| `src/swbt/diagnostics.py` | modify | subcommand rx / reply tx event |
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
| `uv run pytest tests\hardware --collect-only -q` | pass | 3 tests collected。M4 の `test_switch_subcommand_sequence_gets_0x21_replies` を収集できる。実機・adapter open は未実行 |
| `uv run pytest tests\unit\test_bumble_transport.py tests\unit\test_source_audit_fixtures.py -q` | pass | 20 passed。HIDP DATA header、SET_REPORT callback、HID SDP policy、source-audit fixture を確認した |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | 20 passed。interrupt / control 経由の output report と reply queue を fake transport で確認した |
| `uv sync --dev` | pass | Resolved 41 packages / Checked 41 packages |
| `uv run ruff format --check .` | pass | 36 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit` | pass | 91 passed。Bumble import 境界テストは pytest process の import 履歴に依存しない subprocess 検証へ更新済み |
| `uv run pytest tests\integration` | pass | 20 passed。fake transport integration の全件を確認した |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232123 --log-file .pytest_cache\hardware\unit_005\20260701-232123\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | L2CAP open と periodic `0x30` 13 件後、Switch 側 reason 19 で切断。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232352 --log-file .pytest_cache\hardware\unit_005\20260701-232352\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | M4 test だけ temporary `report_period_us=50000` で実行。`0x30` 2 件後に Switch 側 reason 19 で切断。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232634 --log-file .pytest_cache\hardware\unit_005\20260701-232634\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | temporary に Bumble report loop を host output まで遅延。`report_tx` なしでも L2CAP open 後に Switch 側 reason 19 で切断。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-234045 --log-file .pytest_cache\hardware\unit_005\20260701-234045\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | HIDP DATA / SET_REPORT / control channel handling 修正後。SET_REPORT callback 登録、pairing、L2CAP open までは到達。`output_report_rx` は未観測 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-234437 --log-file .pytest_cache\hardware\unit_005\20260701-234437\pytest-debug.log --log-file-level=DEBUG -q -s` | fail | HID SDP policy 参照実装合わせ後。pairing、encryption、L2CAP open までは到達。`output_report_rx` は未観測 |
| `uv run python -` | observed-fail | `.pytest_cache\hardware\unit_005\20260701-234549\subcommand-sequence-no-report-window.jsonl` に記録。50,000,000 us no-report-window で periodic `0x30` を出さずに観測しても `output_report_rx` は来ず、Switch 側 reason 19 で切断 |
| `uv run pytest -m hardware` | fail-partial | unit_005 対象の M4 hardware test は未完了。Bumble adapter と Switch-facing command は承認済みで実行した |

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
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
