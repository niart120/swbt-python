# Joy-Con Default Controller Colors 仕様書

## 1. 概要

### 1.1 目的

Joy-Con L/R profile の `controller_colors` 既定値を side-specific にし、`JoyCon("left")` / `JoyCon("right")` が利用者指定なしでも SPI `0x6050` color block に L/R の識別色を返すようにする。

この unit は正確な工場出荷 Joy-Con color bytes を確定しない。既存 `ControllerColors` 既定値に含まれる青 / 赤を Joy-Con L/R の side identity として profile default に組み込む。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user observation | SDP policy retest 後、Joy-Con L がユーザ目視で Joy-Con として登録された。残る作業として ControllerColor 設定を組み込む | conversation |
| implementation fact | `SwitchGamepadConfig.controller_colors=None` は profile default を使い、明示指定された `ControllerColors` は profile default より優先される | `src/swbt/gamepad/core.py`, `spec/complete/unit_029/CONTROLLER_PROFILE_INJECTION.md` |
| source fact / hardware observation | SPI `0x6050`-`0x605B` は body / buttons / left grip / right grip の 12 bytes color block。Pro profile では実機がこの block を読み、Switch 2 / firmware 22.1.0 で UI 反映を観測済み | `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`, `spec/hardware-test-log.md` |
| implementation fact | 既存 `ControllerColors()` は `body=0x323232`, `buttons=0xFFFFFF`, `left_grip=0x00B2FF`, `right_grip=0xFF3B30` を持つ | `src/swbt/protocol/profile.py` |
| source-audit fixture | Joy-Con L/R 既定 color profile は工場出荷色ではなく swbt-python の profile default policy として記録する | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Joy-Con L user | `JoyCon("left", controller_colors=None)` | SPI `0x6050` が left side default color block を返す | exact factory color とは書かない |
| Joy-Con R user | `JoyCon("right", controller_colors=None)` | SPI `0x6050` が right side default color block を返す | Joy-Con R 実機登録は別検証 |
| library user | `JoyCon("left", controller_colors=ControllerColors(...))` | 利用者指定色が profile default より優先される | 既存 public API を維持 |

## 2. 対象範囲

- `JoyConLeftProfile.controller_colors` の side-specific default。
- `JoyConRightProfile.controller_colors` の side-specific default。
- `VirtualSpiFlash(profile=JoyCon*)` が Joy-Con profile default color block を seed すること。
- `JoyCon(...)` 経由の fake transport SPI reply が profile default color block を返すこと。
- 承認後の Joy-Con L hardware probe で、実機 handshake 中の SPI `0x6050` default color reply と user-visible UI color observation を記録すること。
- 根拠監査 fixture と作業仕様の更新。

## 3. 対象外

- 工場出荷 Joy-Con color bytes の確定。
- 実機から Joy-Con SPI factory data を吸い出すこと。
- 接続後 `set_color()` や profile mutation API の追加。
- Joy-Con R の controller color 実機 UI 反映確認。
- Joy-Con L controller color UI 反映の自動判定。
- 別 firmware / adapter での controller color UI 表示保証。
- Joy-Con R の pairing / input reflection / reconnect 実機検証。

## 4. 関連 docs

- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- `spec/complete/unit_029/CONTROLLER_PROFILE_INJECTION.md`
- `spec/complete/unit_030/JOYCON_PROFILE_IDENTITY_SPI.md`
- `spec/complete/unit_036/JOYCON_SDP_IDENTITY_POLICY.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | SPI color address / byte order は unit_028 で監査済み。今回追加するのは profile default policy であり、新しい SPI address や byte layout は追加しない |
| Bumble / transport | not applicable | not applicable | 色設定は profile / SPI seed の変更で完結し、Bumble object 型や SDP は変更しない |
| OS / driver / adapter | not applicable | not applicable | 自動検証では adapter を開かない。実機 UI 反映を見る場合だけ hardware-harness 承認境界を通す |

### 5.1 監査対象

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| SPI color block | `0x6050`-`0x605B`, body / buttons / left grip / right grip | source fact / hardware observation | `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` | existing contract |
| Joy-Con L default colors | body `0x00B2FF`, buttons `0x323232`, left grip `0x00B2FF`, right grip `0x00B2FF` | implementation fact | `src/swbt/protocol/profile.py`, source-audit fixture | profile-default-policy |
| Joy-Con R default colors | body `0xFF3B30`, buttons `0x323232`, left grip `0xFF3B30`, right grip `0xFF3B30` | implementation fact | `src/swbt/protocol/profile.py`, source-audit fixture | profile-default-policy |
| Joy-Con L hardware observation | SPI `0x6050` bytes `00 b2 ff 32 32 32 00 b2 ff 00 b2 ff`; user observed body blue / light blue and buttons black | hardware observation | `spec/hardware-test-log.md` | 2026-07-06 observed |
| exact factory Joy-Con colors | pending | unverified hypothesis | not audited | do not claim |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Pro default regression | `SwitchGamepad(controller_colors=None)` | 既存 default color block `32 32 32 ff ff ff 00 b2 ff ff 3b 30` を維持する | unit_028 互換 |
| Joy-Con L profile default | `JoyConLeftProfile().controller_colors` | `ControllerColors(body=0x00B2FF, buttons=0x323232, left_grip=0x00B2FF, right_grip=0x00B2FF)` | side identity |
| Joy-Con R profile default | `JoyConRightProfile().controller_colors` | `ControllerColors(body=0xFF3B30, buttons=0x323232, left_grip=0xFF3B30, right_grip=0xFF3B30)` | side identity |
| Joy-Con SPI seed | `VirtualSpiFlash(profile=JoyCon*)` | `0x6050` から profile default color block を返す | 未監査 calibration は引き続き erased |
| public override | `controller_colors=ControllerColors(...)` | 利用者指定色を返す | 既存 API の優先規則を維持 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | Joy-Con L/R profile が side-specific default `ControllerColors` を持つ | new | unit | no | `tests/unit/test_protocol_profile.py` |
| green | `VirtualSpiFlash(profile=JoyCon*)` が side-specific default color block を seed する | new | unit | no | `tests/unit/test_virtual_spi_flash.py` |
| green | `JoyCon(...)` が `controller_colors=None` のとき profile default color block を SPI reply に返す | new | integration | no | fake transport |
| green | source-audit fixture が Joy-Con default color policy を記録する | regression | unit / docs | no | 工場出荷色とは書かない |
| hardware-pass | Joy-Con L 実機 handshake 中に profile default color block を SPI `0x6050` へ返す | new | hardware | yes | `usb:0` / Switch 2 22.1.0。UI 色は user observation として記録し、自動判定しない |

## 8. 設計メモ

`ControllerColors()` の共通既定は Pro profile と `SwitchGamepad(controller_colors=None)` の既存挙動として維持する。Joy-Con では `ControllerProfile.controller_colors` だけを side-specific にし、`SwitchGamepadConfig.controller_colors` の優先規則は変えない。

left / right grip field は単体 Joy-Con UI では未検証だが、SPI color block の既存 field をすべて side color へ揃える。これは side identity を見せるための profile default policy であり、物理 Joy-Con の factory SPI dump ではない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profile.py` | modify | Joy-Con L/R controller color default factory |
| `tests/unit/test_protocol_profile.py` | modify | profile default color test |
| `tests/unit/test_virtual_spi_flash.py` | modify | Joy-Con SPI color seed test |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | JoyCon wrapper 経由の SPI reply test |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | default color policy の根拠分類 |
| `tests/unit/test_source_audit_fixtures.py` | modify | source-audit fixture coverage |
| `tests/hardware/test_joycon_profile.py` | modify | Joy-Con L/R default color SPI reply hardware probe |
| `spec/hardware-test-log.md` | modify | Joy-Con L default color SPI reply と user-visible UI observation の実機記録 |
| `spec/complete/unit_037/JOYCON_DEFAULT_CONTROLLER_COLORS.md` | add / move | 作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_protocol_profile.py::test_joycon_profiles_have_side_specific_default_controller_colors tests/unit/test_virtual_spi_flash.py::test_virtual_spi_flash_seeds_joycon_default_controller_colors_from_profile tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_uses_side_default_controller_colors_when_colors_are_unspecified -q` | red | 4 failed。Joy-Con profile が共通 default color のままだった |
| `uv run pytest tests/unit/test_protocol_profile.py::test_joycon_profiles_have_side_specific_default_controller_colors tests/unit/test_virtual_spi_flash.py::test_virtual_spi_flash_seeds_joycon_default_controller_colors_from_profile tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_uses_side_default_controller_colors_when_colors_are_unspecified -q` | pass | 4 passed |
| `uv run pytest tests/unit/test_protocol_profile.py::test_joycon_profiles_have_side_specific_default_controller_colors tests/unit/test_virtual_spi_flash.py::test_virtual_spi_flash_seeds_joycon_default_controller_colors_from_profile tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_uses_side_default_controller_colors_when_colors_are_unspecified tests/unit/test_source_audit_fixtures.py::test_joycon_default_controller_colors_are_recorded tests/unit/test_public_docs.py tests/unit/test_readme_docs.py tests/unit/test_hardware_test_log_docs.py -q` | pass | 22 passed |
| `uv run ruff format --check .` | pass | 78 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` | pass | 333 passed |
| `uv run pytest tests/integration -q` | pass | 93 passed |
| `uv run ruff format --check tests\hardware\test_joycon_profile.py` | pass | 1 file already formatted |
| `uv run ruff check tests\hardware\test_joycon_profile.py` | pass | All checks passed |
| `uv run ty check --no-progress tests\hardware\test_joycon_profile.py` | pass | All checks passed |
| `uv run pytest tests/hardware/test_joycon_profile.py --collect-only -q` | pass | 4 tests collected。adapter は開いていない |
| `uv run pytest tests\unit\test_hardware_test_log_docs.py -q` | pass | 3 passed |
| `git diff --check` | pass | whitespace error なし |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_reads_default_controller_colors[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-default-colors-20260706 --log-file build\hardware\joycon-left-default-colors-20260706\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-joycon-default-colors -q -s` | pass | `1 passed in 24.39s`。SPI `0x6050` bytes `00b2ff32323200b2ff00b2ff`。ユーザは UI 上で body が青色または水色、buttons が黒色に見えると報告した |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | implementation gate としては not required。2026-07-06 に user approval 後、Joy-Con L default color hardware probe を実行済み |
| 承認範囲 | 実行済み範囲は adapter `usb:0`、USB Bluetooth dongle open、Joy-Con L HID advertising、Switch pairing、HID control / interrupt L2CAP、Device Info reply、SPI `0x6050` controller color read reply、periodic `0x30`、SR+SL hold、neutral cleanup、disconnect request、transport close、adapter release |
| adapter | `usb:0` |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build\hardware\joycon-left-default-colors-20260706\joycon-left-default-controller-colors.jsonl`, `build\hardware\joycon-left-default-colors-20260706\pytest-debug.log`, `build\hardware\joycon-left-default-colors-20260706\joycon-left-colors-key-store.json` |
| cleanup | trace は `disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete`、`manual_joycon_profile_cleanup connection_state=closed` を記録した |

## 12. 先送り事項

- Joy-Con L/R の正確な factory controller color bytes は未監査。実機 SPI dump または信頼できる source が得られるまで profile-default-policy として扱う。
- Joy-Con R default color SPI reply と UI reflection は未検証。
- Joy-Con L default color UI reflection は Windows / CSR8510 A10 / Switch 2 22.1.0 の user observation として記録済みだが、pytest は自動判定しない。別 firmware / adapter での表示保証には使わない。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
