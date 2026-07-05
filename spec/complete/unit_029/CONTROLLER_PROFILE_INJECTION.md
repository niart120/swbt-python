# Controller Profile Injection 仕様書

## 1. 概要

### 1.1 目的

Joy-Con 対応の前段として、現在 Pro Controller 固定で生成・参照している controller identity / protocol profile を `ControllerProfile` 注入へ寄せる。

この unit は構造変更だけを扱う。送信される Pro Controller の report、subcommand reply、SPI reply、SDP descriptor、既定 device name、既定 report period は変えない。Joy-Con 固有の protocol constant は追加しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| parent issue | Joy-Con L/R device profile support plan と実装順 | https://github.com/niart120/swbt-python/issues/48 |
| child issue | ControllerProfile 注入の土台。既存 Pro Controller 挙動を維持する | https://github.com/niart120/swbt-python/issues/49 |
| AGENTS | Public API、protocol、Bumble、根拠監査、実機安全境界 | `AGENTS.md` |
| spec-format | WIP 仕様書の構成、TDD Test List、検証、実機条件 | `.agents/skills/spec-format/SKILL.md` |
| source-audit | 新しい Switch protocol byte を確定しない構造変更として扱う | `.agents/skills/source-audit/SKILL.md` |
| hardware-harness | 仕様作成では実機も adapter open も行わない | `.agents/skills/hardware-harness/SKILL.md` |
| initial architecture | profile / protocol / transport の責務分離 | `spec/initial/architecture.md` |
| initial API | `SwitchGamepad` / `SwitchGamepadConfig` の constructor 境界 | `spec/initial/api.md` |
| current profile customization | `ControllerColors` と Pro Controller profile の既存境界 | `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| existing user | `SwitchGamepad(adapter="usb:0", ...)` | 既存と同じ Pro Controller 相当で起動する | 既存 constructor 引数を壊さない |
| protocol core | profile を受け取る `InputReportBuilder` / `SubcommandResponder` / `VirtualSpiFlash` | 同じ profile から report / reply / SPI seed を導出する | Joy-Con 固有 byte は追加しない |
| gamepad stack | `SwitchGamepadConfig` の未指定 profile | Pro Controller profile が既定として使われる | dataclass の共有 mutable default にしない |
| transport boundary | transport factory / `BumbleHidTransport` | profile 由来の descriptor / device name を受け取れる構造になる | この unit では descriptor 内容を変えない |

## 2. 対象範囲

- `ControllerProfile` 境界の明確化。
- `ControllerKind` を追加するかどうかの設計判断。public export はこの unit で確定しない。
- `SwitchGamepadConfig` へ profile を渡せる構造の追加。
- `device_name`、`report_period_us`、`controller_colors` の override 規則の仕様化。
- `InputReportBuilder`、`SubcommandResponder`、`VirtualSpiFlash`、`ReportLoop`、transport factory、`BumbleHidTransport` へ同一 profile を渡す構造。
- `device_name` と `report_period_us` の未指定状態を、現行既定値の literal とは別に表現する構造。
- production code の `ProControllerProfile()` 直接生成箇所を、既定値設定または profile factory へ寄せる。
- Pro Controller の既存 byte fixture を regression として維持する。

## 3. 対象外

- Joy-Con L/R profile の具体値追加。
- Joy-Con device type、Device Info bytes、SPI seed、HID descriptor、button mapping の追加。
- `JoyConPair` または左右同時接続 API。
- Switch protocol bytes の意味付け変更。
- report mode、IMU enable、vibration enable、player lights の mutable session state 実装。
- 実機、Bumble adapter、Switch-facing 動作の実行。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/initial/naming.md`
- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- https://github.com/niart120/swbt-python/issues/48
- https://github.com/niart120/swbt-python/issues/49

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | この unit は新しい Joy-Con protocol constant を追加しない。既存 Pro Controller byte は regression test で変えない |
| Bumble / transport | required | done | profile を transport factory / `BumbleHidTransport` / SDP builder へ渡す構造を unit test で確認した。descriptor や SDP 値は変更していない |
| OS / driver / adapter | not applicable | not applicable | 仕様作成と構造変更では adapter を開かない |

### 5.1 監査方針

- 既存 Pro Controller の byte fixture を移動する場合は、値を変えないことを test で固定する。
- 新しい Joy-Con byte 値が必要になった場合は、この unit では採用せず、#50 / #51 / #53 側で `source-audit` へ回す。
- `ControllerProfile` は fixed identity / protocol profile を表す。接続後に変わる report mode、IMU、vibration、player lights は profile に入れない。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| 既定 profile | `SwitchGamepad(...)` で profile 未指定 | Pro Controller profile を使う | 既存 public API の観測結果を変えない |
| 明示 device name | `device_name="..."` | profile の既定 device name より user value を優先する | `device_name="Pro Controller"` の既定値が常に profile default を上書きしないようにする |
| 明示 report period | `report_period_us=...` | profile の既定 report period より user value を優先する | 未指定時だけ profile default を使う |
| 明示 colors | `controller_colors=...` | profile の既定 colors より user value を優先する | 既存 unit_028 の互換を維持する |
| profile propagation | `SwitchGamepadConfig.profile` | report builder、subcommand responder、SPI、report loop、transport が同一 profile を参照する | report loop は profile-bound builder 注入でもよい。個別に `ProControllerProfile()` を作らない |
| Pro regression | 既存 Pro Controller tests | report / reply / SPI / SDP descriptor が変わらない | この unit の主要 gate |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | profile 未指定の `SwitchGamepad(...)` が既存 Pro Controller profile を使う | regression | unit | no | `tests/unit`, `tests/integration` |
| green | `SwitchGamepadConfig` が profile を受け取り、共有 mutable default を持たない | new | unit | no | `test_switch_gamepad_config_defaults_to_distinct_pro_controller_profiles` |
| green | `device_name` 未指定時は profile default、明示指定時は user value を transport へ渡す | new | unit | no | `test_from_config_uses_profile_device_name_unless_user_overrides` |
| green | `report_period_us` 未指定時は profile default、明示指定時は user value を `ReportLoop` へ渡す | new | unit / integration | no | `test_from_config_uses_profile_report_period_unless_user_overrides` |
| green | `device_name="Pro Controller"` / `report_period_us=8000` の現行既定値と、利用者の明示指定を実装上区別できる | new | unit | no | `None` を未指定として config normalization で解決する |
| green | `controller_colors` 未指定時は profile default、明示指定時は user value を SPI seed へ渡す | regression | unit / integration | no | unit_028 互換。`test_from_config_uses_profile_controller_colors_when_colors_are_unspecified` |
| green | `InputReportBuilder` / `SubcommandResponder` / `VirtualSpiFlash` が同一 profile instance または同一 profile 値を受け取る | new | unit / integration | no | fake transport の periodic report と SPI reply で確認 |
| green | `ReportLoop` が default `InputReportBuilder()` を内部生成せず、profile-bound builder または profile を受け取る | new | unit | no | `test_report_loop_requires_injected_input_report_builder` |
| green | default transport factory が profile を `BumbleHidTransport` へ渡す | new | unit | no | Bumble import を public import 時に解決しない |
| green | Pro Controller の `0x30` report fixture が profile 注入後も変わらない | regression | unit | no | Joy-Con constant は追加していない |
| green | Pro Controller の `0x02` / `0x10` subcommand reply が profile 注入後も変わらない | regression | unit | no | Device Info / SPI regression |
| green | SDP builder に渡される Pro Controller descriptor が profile 注入後も既存 bytes のまま | regression | unit | no | descriptor 内容は unit_033 で扱う |

## 8. 設計メモ

- `ControllerProfile` は fixed identity / protocol profile を表す。`kind`、`device_name`、`device_type`、`hid_report_descriptor`、`default_report_period_us`、`battery_connection`、`vibrator_input`、`controller_colors`、`capabilities` を候補にする。
- public surface はこの unit で急がない。`ControllerKind` や profile class を公開する場合は、docs、`__all__`、import 境界 test を同じ変更に含める。
- `InputState` は Pro Controller / Joy-Con の和集合を表現できる状態として維持する。ただし、非対応入力の検証は unit_031 で扱う。
- `device_name` と `report_period_us` は、公開 API の互換を守りつつ「未指定」と「利用者が現行既定値と同じ値を明示した」を区別する。private sentinel、constructor wrapper、config normalization のいずれかで実現し、`"Pro Controller"` / `8000` という literal を profile default 上書きの根拠にしない。
- `ReportLoop` が profile を持つ目的は、送信周期や report builder の依存を Pro 固定から外すためである。profile-bound `InputReportBuilder` を注入する形でもよい。report mode state を profile に入れない。
- production code で `ProControllerProfile()` を作ってよい場所は、既定 profile factory または `SwitchGamepadConfig` の default に限定する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profile.py` | modify | `ControllerProfile` 境界、既定 Pro profile、必要なら `ControllerKind` |
| `src/swbt/gamepad/core.py` | modify | `SwitchGamepadConfig.profile` と profile propagation |
| `src/swbt/gamepad/transport_factory.py` | modify | default transport へ profile を渡す |
| `src/swbt/report_loop.py` | modify | profile / report builder injection |
| `src/swbt/protocol/input_report.py` | modify | builder の profile 依存を明示する |
| `src/swbt/protocol/subcommand.py` | modify | responder の profile 依存を明示する |
| `src/swbt/protocol/spi.py` | modify | profile 由来の SPI seed を維持する |
| `src/swbt/transport/bumble.py` | modify | transport が profile を受け取る |
| `src/swbt/transport/_bumble_sdp.py` | modify | descriptor / name の入力元を profile に寄せる |
| `tests/unit/` | modify | profile injection と Pro regression |
| `tests/integration/` | modify | fake transport 経由の profile propagation |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_api_boundary.py::test_switch_gamepad_config_defaults_to_distinct_pro_controller_profiles -q` | red | `SwitchGamepadConfig.profile` 未実装の `AttributeError` を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_switch_gamepad_config_defaults_to_distinct_pro_controller_profiles -q` | pass | 1 passed。profile default factory を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_profile_reaches_periodic_input_report_builder -q` | red | custom profile の `battery_connection` が periodic report に反映されない failure を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_profile_reaches_periodic_input_report_builder -q` | pass | 1 passed。config profile が profile-bound builder へ到達 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_uses_profile_controller_colors_when_colors_are_unspecified -q` | red | `controller_colors=None` が fixed default へ正規化され、profile default を使わない failure を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_uses_profile_controller_colors_when_colors_are_unspecified tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_default_controller_colors_when_none tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_output_report_injection_uses_configured_controller_colors -q` | pass | 3 passed。profile default / user override の color 経路を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_from_config_uses_profile_device_name_unless_user_overrides -q` | red | `ProControllerProfile.device_name` 未実装の `TypeError` を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_from_config_uses_profile_device_name_unless_user_overrides -q` | pass | 1 passed。profile default name と user override を確認 |
| `uv run pytest tests/unit/test_gamepad_transport_factory.py::test_default_transport_factory_passes_resource_config_to_bumble_transport -q` | red | default transport factory が `profile` 引数を持たない `TypeError` を確認 |
| `uv run pytest tests/unit/test_gamepad_transport_factory.py::test_default_transport_factory_passes_resource_config_to_bumble_transport -q` | pass | 1 passed。factory から `BumbleHidTransport` へ profile を渡す |
| `uv run pytest tests/unit/test_report_loop.py::test_report_loop_requires_injected_input_report_builder -q` | red | `ReportLoop` が optional builder を持つ failure を確認 |
| `uv run pytest tests/unit/test_report_loop.py` | pass | 3 passed。ReportLoop の builder 注入を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py::test_pro_controller_profile_direct_construction_is_limited_to_profile_factory -q` | red | production code に `ProControllerProfile()` 直接生成が残っていることを確認 |
| `uv run pytest tests/unit/test_protocol_profile.py::test_pro_controller_profile_direct_construction_is_limited_to_profile_factory -q` | pass | 1 passed。既定 profile factory へ集約 |
| `uv run pytest tests/unit/test_bumble_transport.py::test_bumble_initialize_device_configures_json_key_store tests/unit/test_bumble_transport.py::test_bumble_initialize_device_uses_profile_hid_descriptor -q` | pass | 2 passed。Bumble initialize が profile descriptor を使う |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_report_loop.py tests/unit/test_gamepad_transport_factory.py tests/unit/test_public_api_boundary.py tests/unit/test_bumble_transport.py tests/unit/test_bumble_sdp.py tests/unit/test_input_report.py tests/unit/test_subcommand_responder.py tests/unit/test_virtual_spi_flash.py tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 205 passed。profile injection 関連 tests |
| `uv sync --dev` | pass | Resolved 53 packages。Checked 41 packages |
| `uv run ruff format --check .` | pass | 77 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 278 passed |
| `uv run pytest tests/integration` | pass | 74 passed |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 仕様作成では不要。構造変更の自動 test でも不要 |
| 承認範囲 | 後続で Bumble adapter open、HID advertising、pairing、report loop、Switch-facing output report を実行する場合は、対象 adapter、command、Switch-facing 動作、cleanup plan の明示承認が必要 |
| adapter | 仕様作成では使用しない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実機を使う場合は `spec/hardware-test-log.md` に OS、driver、dongle、Bumble version、Python version、Switch model / firmware、command、result、cleanup を記録する |
| cleanup | 仕様作成では不要。実機時は neutral、report loop 停止、transport close、adapter release を記録する |

## 12. 先送り事項

- Joy-Con L/R の device type、Device Info bytes、SPI seed、HID descriptor、button mapping は unit_030 / unit_031 / unit_033 で扱う。
- report mode、IMU enable、vibration enable、player lights の mutable session state は unit_032 で扱う。
- public surface として profile class、`ControllerKind`、factory helper のどれを採用するかは unit_034 の docs までに確定する。この unit では `SwitchGamepad(profile=...)` は追加せず、`SwitchGamepadConfig.profile` と `from_config()` の構造に留めた。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] Pro Controller 既存挙動を維持する regression を実装した
- [x] Joy-Con 固有 protocol constant をこの unit に混ぜていない
