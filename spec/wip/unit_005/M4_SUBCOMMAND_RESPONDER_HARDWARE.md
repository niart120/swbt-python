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
| Bumble / transport | required | done | `bumble_hid_device_api` は Bumble `0.0.230` の HID callback 境界だけを示す。実機 sequence の callback timing は M4 実行時の hardware observation として別記録にする |
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
| todo | 観測済み `0x01` fixture から subcommand id と payload を parse できる | characterization | unit | no | 実機 trace 取得後に fixture 化 |
| todo | `0x02` device info reply が監査済み payload を返す | regression | unit | no | M0 の不足補完 |
| todo | `0x10` SPI read reply が address と size に応じた data を返す | regression | unit | no | `spi_flash_boundary_and_seed_map` を期待値 source にする |
| todo | 未対応 subcommand が diagnostics event を生成する | new | unit | no | 隠さないため |
| todo | fake transport 注入時に `0x21` reply が `0x30` より先に送られる | regression | integration | no | M1 の再確認 |
| todo | 実機で `0x01` output report を受信できる | new | hardware | yes | 承認が必要 |
| todo | 観測された subcommand sequence が trace に残る | new | hardware | yes | firmware / adapter 条件付き |
| todo | 主要 subcommand に `0x21` reply を返せる | new | hardware | yes | output と reply tx を trace で対応付ける |
| todo | 未対応 subcommand があれば docs に反映されている | characterization | hardware | yes | 後続 unit の source |

## 8. 設計メモ

- 実機 trace から得た sequence は `hardware observation` であり、別 firmware への一般化はしない。
- `SubcommandResponder` の unit test は source fact または実機 fixture を明示してから green にする。
- fail-safe reply を作る場合でも、未対応 subcommand を diagnostics から消さない。
- M4 は入力 UI 反映の成否を最終判定にしない。反映は M5 の範囲。

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
| `uv run pytest tests/unit tests/integration` | pending | M4 実装後に local automated gate として実行する |
| `uv run pytest -m hardware` | pending-approval | Switch-facing output report / reply 送信の明示承認後に実行する |

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
- [ ] M4 の local automated gate を実行し、検証欄を結果で更新した
- [ ] 実機検証は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
