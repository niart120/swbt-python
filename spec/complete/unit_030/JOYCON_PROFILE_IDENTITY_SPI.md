# Joy-Con Profile Identity SPI 仕様書

## 1. 概要

### 1.1 目的

`ControllerProfile` 境界に Joy-Con (L) / Joy-Con (R) の具体 profile を追加し、Device Info と virtual SPI flash の固定 identity data を profile 由来にする。

この unit では Joy-Con の入力 report mapping と Bumble / SDP descriptor wiring は扱わない。`JoyConLeftProfile` / `JoyConRightProfile` の kind、device name、device type、Device Info core bytes、SPI `0x6012` seed は source-audit 済みの値だけを実装契約にする。calibration seed、Joy-Con 固有 report period、実機 firmware bytes は未検証として残す。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| parent issue | Joy-Con support plan と子 issue の順序 | https://github.com/niart120/swbt-python/issues/48 |
| child issue | Joy-Con L/R profile、Device Info、SPI seed | https://github.com/niart120/swbt-python/issues/50 |
| dependency | `ControllerProfile` 注入の土台 | https://github.com/niart120/swbt-python/issues/49 |
| AGENTS | source-audit 対象と実機安全境界 | `AGENTS.md` |
| source-audit | device type、Device Info、SPI address / data、report period の根拠分類 | `.agents/skills/source-audit/SKILL.md` |
| initial protocol | `0x02` Device Info と `0x10` SPI read の責務 | `spec/initial/protocol.md` |
| unit_028 | Pro Controller device type `0x03`、color SPI seed、device-info tail の既存根拠 | `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` |
| dekuNukem subcommand notes | Device Info の controller type、marker、address、tail | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/bluetooth_hid_subcommands_notes.md |
| dekuNukem SPI notes | SPI `0x6012` device type | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/spi_flash_notes.md |
| joycontrol | Joy-Con enum、device name、`0x02` reply builder | https://github.com/mart1nro/joycontrol |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| protocol core | Joy-Con L profile | Device Info / SPI seed が left profile 由来になる | 未監査 byte は seed しない |
| protocol core | Joy-Con R profile | Device Info / SPI seed が right profile 由来になる | 未監査 byte は seed しない |
| caller | `build_device_info(bluetooth_address)` 相当 | 渡した Bluetooth address が payload に反映される | address は profile 固定値にしない |
| maintainer | calibration 領域 | source fact または hardware observation がない領域は erased byte のまま | 適当な非 `0xFF` 値で埋めない |

## 2. 対象範囲

- `JoyConLeftProfile` / `JoyConRightProfile` の追加。
- `kind = JOYCON_LEFT` / `kind = JOYCON_RIGHT` 相当の profile 識別。
- `device_name = "Joy-Con (L)"` / `"Joy-Con (R)"` 相当の既定表示名。
- profile helper による Device Info payload 生成。
- Bluetooth address を profile 固定値ではなく呼び出し元の session / transport 由来値として扱う境界。
- `VirtualSpiFlash` の初期 seed を `profile.seed_spi_flash()` 相当から注入する構造。
- Pro Controller の `device_type == 0x03` と unit_028 の color SPI seed の維持。
- Joy-Con L/R の device type、Device Info fixed bytes、calibration seed、default report period の source-audit gate。

## 3. 対象外

- Joy-Con button mapping の実装。
- Joy-Con HID report descriptor / SDP record の実装。
- `JoyConPair` の追加。
- 実機から吸い出した calibration 値との完全一致。
- calibration 領域の推測 seed。
- Bumble から Device Info 用 Bluetooth address を取得して渡す transport wiring。
- `0x3F` simple HID report。
- 実機、Bumble adapter、Switch-facing 動作の実行。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- `tests/unit/fixtures/source_audit/switch_protocol_values.toml`
- https://github.com/niart120/swbt-python/issues/48
- https://github.com/niart120/swbt-python/issues/49
- https://github.com/niart120/swbt-python/issues/50

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | Joy-Con device type、Device Info core bytes、SPI `0x6012` は source-audit fixture に記録した。calibration と report period は未検証として seed しない |
| Bumble / transport | not applicable | not applicable | Device Info 用 Bluetooth address の実 transport wiring はこの unit の対象外 |
| OS / driver / adapter | not applicable | not applicable | 仕様作成と protocol unit test では adapter を開かない |

### 5.1 監査対象

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| Pro Controller device type | `0x03` | source fact / implementation fact | `spec/initial/protocol.md`, `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` | existing contract |
| Joy-Con L device type | `0x01` | source fact / implementation fact | dekuNukem `spi_flash_notes.md`, `bluetooth_hid_subcommands_notes.md`, joycontrol `Controller.JOYCON_L` | stable-profile-core |
| Joy-Con R device type | `0x02` | source fact / implementation fact | dekuNukem `spi_flash_notes.md`, `bluetooth_hid_subcommands_notes.md`, joycontrol `Controller.JOYCON_R` | stable-profile-core |
| Joy-Con L Device Info fixed bytes | `04 00 01 02 <addr> 01 01` | implementation fact with source-backed type/tail | dekuNukem `bluetooth_hid_subcommands_notes.md`, joycontrol `report.py` | stable-profile-core; `04 00` は実機 firmware observation ではない |
| Joy-Con R Device Info fixed bytes | `04 00 02 02 <addr> 01 01` | implementation fact with source-backed type/tail | dekuNukem `bluetooth_hid_subcommands_notes.md`, joycontrol `report.py` | stable-profile-core; `04 00` は実機 firmware observation ではない |
| Joy-Con SPI calibration seed | pending | pending | source-audit or hardware observation required | do not invent values |
| Joy-Con default report period | `8000us` fallback | inference | existing configurable default in `report_period_default` source-audit fixture | compatibility fallback; not Joy-Con exact timing |
| Existing color SPI seed | existing unit_028 contract | source fact / hardware observation / inference | `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` | kept; Joy-Con exact color behavior is not hardware-verified |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Pro profile | `ProControllerProfile` | `device_type == 0x03` と既存 SPI seed を維持する | regression |
| Joy-Con L profile identity | `JoyConLeftProfile` | kind、device name、device type が left として識別できる | device type は `0x01` |
| Joy-Con R profile identity | `JoyConRightProfile` | kind、device name、device type が right として識別できる | device type は `0x02` |
| Device Info address | profile helper に address を渡す | 渡した 6 bytes address が reply payload に反映される | transport wiring は別 unit |
| Device Info fixed bytes | Joy-Con profile | source-audit 済みの device type / tail と実装互換 firmware だけを返す | firmware `04 00` は実機観測値ではない |
| SPI device type seed | `0x6012` | source-audit 済みの device type だけを seed する | pending の間は契約にしない |
| calibration seed | stick / IMU calibration 領域 | source fact または hardware observation がない場合は erased byte のまま | 非 `0xFF` 推測 seed を禁止する |
| report period default | Joy-Con profile | source-audit 済み値、または明示した Pro-compatible fallback | fallback は Joy-Con 完全一致と書かない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `ProControllerProfile.device_type == 0x03` が維持される | regression | unit | no | unit_028 互換 |
| green | `JoyConLeftProfile` / `JoyConRightProfile` が distinct kind と device name を持つ | new | unit | no | byte 値は source-audit 済み device type だけ固定 |
| green | Joy-Con device type が source-audit fixture から追える | edge | unit / docs | no | `joycon_spi_device_type_values` |
| green | `build_device_info(bluetooth_address)` 相当が渡された address を payload に反映する | new | unit | no | address は profile 固定値にしない |
| green | Pro Controller の Device Info reply が profile helper 経由になっても既存 bytes を維持する | regression | unit | no | `0x02` regression |
| green | Joy-Con Device Info fixed bytes は source-audit 済みの値だけで test fixture 化する | new | unit | no | firmware `04 00` は implementation-compatible default |
| green | `VirtualSpiFlash` が profile 由来の device type seed を使う | new | unit | no | Joy-Con L/R は `0x01` / `0x02` |
| green | calibration 領域に未監査の非 erased seed を入れていない | edge | unit | no | 適当な seed を禁止 |
| green | Joy-Con profile を `SwitchGamepadConfig.profile` に渡しても Pro 固定値に戻らない | new | integration | no | unit_029 dependency |

## 8. 設計メモ

- `JoyConLeftProfile` / `JoyConRightProfile` の kind と device name は利用者に見える識別子であり、protocol byte とは別に扱う。
- `device_type` と Device Info fixed bytes は byte-level contract なので、source-audit fixture から追える値だけを test に固定する。
- Joy-Con profile shell と byte contract を混同しない。calibration、Joy-Con HID descriptor、入力 mapping はこの unit で固定しない。
- Bluetooth address は transport / session 由来の値である。profile に固定 address を持たせない。
- `VirtualSpiFlash` は profile から seed を受け取る。未監査領域は erased byte を維持し、読まれた事実は diagnostics や source-audit follow-up に残す。
- report period は profile default 候補だが、Joy-Con 固有値は未確認である。この unit では既存 configurable default `8000us` の fallback とし、Joy-Con 完全一致とは書かない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profile.py` | modify | Joy-Con L/R profile、kind、device identity helper |
| `src/swbt/protocol/spi.py` | modify | profile 由来の SPI seed |
| `src/swbt/protocol/subcommand.py` | modify | Device Info を profile helper 経由へ寄せる |
| `src/swbt/gamepad/core.py` | modify | Joy-Con profile が初期化経路で保持されるか確認 |
| `tests/unit/test_protocol_profile.py` | modify | profile identity と audit gate |
| `tests/unit/test_virtual_spi_flash.py` | modify | profile 由来 seed と calibration non-seed |
| `tests/unit/test_subcommand_responder.py` | modify | Device Info address / profile switching |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | fake transport 経由の profile propagation |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | 監査済みになった値だけ追加 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_subcommand_responder.py tests/unit/test_virtual_spi_flash.py tests/unit/test_source_audit_fixtures.py tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_joycon_profile_reaches_device_info_reply -q` | red | `JoyConLeftProfile` import 不在で collection error。unit_030 の未実装を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_subcommand_responder.py tests/unit/test_virtual_spi_flash.py tests/unit/test_source_audit_fixtures.py tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_joycon_profile_reaches_device_info_reply -q` | pass | 64 passed。profile identity、Device Info、SPI seed、source-audit fixture、fake transport profile propagation を確認 |
| `uv sync --dev` | pass | Resolved 53 packages。Checked 41 packages |
| `uv run ruff format --check .` | pass | 77 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 287 passed |
| `uv run pytest tests/integration` | pass | 75 passed |
| `git diff --check` | pass | whitespace error なし |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 仕様作成では不要。protocol unit test でも不要 |
| 承認範囲 | 後続で Joy-Con Device Info / SPI を実機観測する場合は、adapter open、HID advertising、pairing または reconnect、Switch-facing output report / subcommand handling、periodic report loop、cleanup の明示承認が必要 |
| adapter | 仕様作成では使用しない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実機観測時は OS、driver、dongle identity、adapter string、Bumble version、Python version、Switch model / firmware、command、result、cleanup を記録する |
| cleanup | 実機時は neutral、report loop 停止、transport close、adapter release を記録する |

## 12. 先送り事項

- Joy-Con calibration seed は source-audit または hardware observation まで pending。
- Joy-Con 固有 report period は未確認。現時点は既存 configurable default `8000us` fallback であり、Joy-Con 実機 timing guarantee ではない。
- Device Info firmware bytes `04 00` は既存 swbt-python / joycontrol 互換の実装値であり、Joy-Con 実機 firmware observation ではない。
- Bumble から local Bluetooth address を取得して Device Info helper へ渡す wiring は unit_033 または別 follow-up。
- Joy-Con input report mapping は unit_031。
- Joy-Con HID descriptor / SDP record は unit_033。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] Joy-Con device type / Device Info を監査し、calibration / report period を実機確定値として扱っていない
- [x] Pro Controller profile の既存契約を維持した
