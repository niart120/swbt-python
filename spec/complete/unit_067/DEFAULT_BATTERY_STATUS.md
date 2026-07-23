# 既定バッテリー状態修正仕様書

## 1. 概要

### 1.1 目的

仮想 Pro Controller が Bluetooth 接続中に、充電中または外部給電中と通知しない既定値へ修正する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | 現在の `0x91` を `0x80` へ修正し、Switch 実機の表示も確認する | conversation |
| protocol source | standard input report byte 2 の上位 nibble は battery level と charging、下位 nibble は controller shape と Switch/USB power を表す | dekuNukem `bluetooth_hid_notes.md` |
| implementation | `ControllerProfile.battery_connection` を `0x30` と `0x21` の共通 prefix に使う | `src/swbt/protocol/profiles/base.py`, `src/swbt/protocol/input_report.py`, `src/swbt/protocol/subcommand.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | 仮想 Pro Controller から標準入力レポートまたは subcommand reply を受信する | 満充電、非充電、外部給電なしを表す `0x80` を受信する | 実際の電池残量を動的取得する機能ではない |
| 利用者 | Switch の controller 表示を確認する | 充電中または充電機器接続中として表示されない | UI 文言と表示は Switch firmware に依存するため実機観測として記録する |

## 2. 対象範囲

- `ControllerProfile` の battery / connection 既定値を `0x80` にする。
- 既定 profile の `0x30` input report と `0x21` subcommand reply が `0x80` を送ることを固定する。
- Switch 実機で接続、neutral report loop、表示確認、neutral close を実行する。
- 根拠と実機結果を仕様および `spec/hardware-test-log.md` に記録する。

## 3. 対象外

- 実際の電池残量または給電状態の動的取得。
- battery / connection 状態を変更する public API。
- controller shape ごとの battery / connection 値の分離。
- ボタン、stick、IMU、rumble の振る舞い変更。

## 4. 関連 docs

- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/hardware-test-log.md`
- `tests/unit/fixtures/source_audit/switch_protocol_values.toml`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | dekuNukem の standard input report format では、`0x80` は battery full、charging false、Pro/Charging Grip、Switch/USB powered false を表す |
| Bumble / transport | not applicable | not applicable | transport の packing や接続処理は変更しない |
| OS / driver / adapter | required | done | Windows 11 / CSR8510 A10 / WinUSB / `usb:0` の条件を `spec/hardware-test-log.md` に記録 |

`0x80` のビット意味は source fact とする。Switch UI が期待どおり変わることは実機検証前は未検証仮説であり、検証後も使用した firmware 条件の hardware observation として扱う。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| 周期入力の既定状態 | 既定 Pro Controller profile で `0x30` を生成する | byte 2 が `0x80` | 満充電、非充電、外部給電なし |
| subcommand reply の既定状態 | 既定 Pro Controller profile で `0x21` を生成する | byte 2 が `0x80` | `0x30` と同じ prefix |
| Switch UI 表示 | 実機へ接続して neutral report loop を送る | 充電中または充電機器接続中として表示されない | firmware 条件付きの目視観測 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | 既定 profile の `0x30` と `0x21` が満充電・非充電・外部給電なしを表す `0x80` を通知する | regression | unit | no | `0x91` から `0x80` への最小変更で green。追加の構造変更は不要 |
| green | Switch UI が仮想 Pro Controller を充電中または充電機器接続中として表示しない | characterization | hardware | yes | 利用者が期待どおりの表示を目視確認 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `docs/release-notes.md` | 更新後の表示変更と制約を知りたい利用者 | 実装差分、`spec/initial/protocol.md`、`spec/hardware-test-log.md` | `uv run mkdocs build --strict` | done | none |

`docs-wording` の用語辞書に従い、利用者向け本文では入力レポートの ID、トレースログ、
artifact 名を省いた。`docs-quality-review` では、変更内容、動的な電池状態取得が対象外で
あること、実機観測を別ファームウェアへ一般化しないことを正本と照合した。
未解決の修正必須事項はない。

## 9. 設計メモ

- この変更は既定の wire byte を変える behavior change である。構造変更は混ぜない。
- `0x80` は動的な battery model ではなく固定値である。実際の電池を持たない仮想 controller の既定通知として扱う。
- `battery_connection` は `InputReportBuilder` を経由して `0x30` と `0x21` の双方へ反映される。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profiles/base.py` | modify | battery / connection 既定値を `0x80` に変更 |
| `tests/unit/test_subcommand_responder.py` | modify | `0x30` / `0x21` の既定 byte を固定 |
| `tests/hardware/test_battery_status.py` | new | active reconnect、5秒の neutral report、neutral close を実行 |
| `spec/initial/protocol.md` | modify | 既定値と意味を正本へ記録 |
| `spec/hardware-test-log.md` | modify | 実機条件、結果、cleanup を記録 |
| `docs/release-notes.md` | modify | 利用者向けの修正内容、固定通知、未検証範囲を記録 |
| `spec/complete/unit_067/DEFAULT_BATTERY_STATUS.md` | new | 作業仕様と検証記録 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_subcommand_responder.py::test_default_reports_full_battery_without_charging_or_external_power -q` | red | `report[2]` が `0x91`、期待値が `0x80` で失敗 |
| `uv run pytest tests/unit/test_subcommand_responder.py::test_default_reports_full_battery_without_charging_or_external_power -q` | pass | `0x30` と `0x21` の byte 2 がともに `0x80`。1 passed |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 99 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | environment error | 既存 `tmp/pytest` の削除で `WinError 5`。435 passed、33 setup errors。製品 failure ではない |
| `uv run pytest tests/unit -p no:cacheprovider --basetemp C:\Users\train\AppData\Local\Temp\swbt-unit-067-unit-a` | pass | 468 passed |
| `uv run pytest tests/integration -p no:cacheprovider --basetemp C:\Users\train\AppData\Local\Temp\swbt-unit-067-integration-a` | pass | 137 passed |
| `uv run pytest tests/hardware/test_battery_status.py --collect-only -q` | pass | 1 test collected。adapter は開いていない |
| 承認済み `test_switch_reports_default_battery_status_for_manual_ui_confirmation` | hardware-pass | 1 passed in 6.83s。`0x30` 501件、`0x21` 16件の全 PDU が status `0x80`。利用者目視も pass |
| `uv sync --dev --group docs` | pass | 53 packages resolved、docs group を同期 |
| final `uv run ruff format --check .` | pass | 100 files already formatted |
| final `uv run ruff check .` | pass | All checks passed |
| final `uv run ty check --no-progress` | pass | All checks passed |
| final unit / integration | pass | unit 468件、integration 137件。固有 basetemp で直列実行 |
| `uv run mkdocs build --strict` | pass | strict build 完了 |
| `git diff --check` | pass | whitespace error なし |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | `usb:0` open、Bumble Classic HID 初期化、保存済み key による active reconnect、HID control / interrupt channel、5秒の periodic neutral report、Switch UI 目視確認、neutral close。advertising、新規 pairing、key update、非 neutral 入力は対象外 |
| adapter | `usb:0`。直近 unit_066 で使った専用 CSR8510 A10 / WinUSB adapter と保存済み profile を再利用 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build/hardware/unit_067/battery-status-20260724/` |
| cleanup | button 状態を neutral にし、report loop を停止して controller と transport を閉じる |

実行結果は `spec/hardware-test-log.md` に記録した。終了時の neutral `0x30` は送信済み。
disconnect terminal wait は0.25秒で timeout したが、その後の transport close と adapter
release は完了した。

## 13. 先送り事項

- 実際の電池残量と給電状態を動的に通知する機能は、本修正の範囲外とする。
- 別 Switch firmware での UI 表示は未検証。本 run の観測を一般化しない。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
