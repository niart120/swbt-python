# Joy-Con Input Report Mapping 仕様書

## 1. 概要

### 1.1 目的

標準入力 report `0x30` の生成を profile-aware にし、Pro Controller / Joy-Con (L) / Joy-Con (R) で button mapping と stick availability を切り替える。

非対応入力は黙って無視しない。利用者が呼んだ state update API で commit 前に失敗を観測できるようにし、`InputReportBuilder` にも defensive validation を置く。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| parent issue | Joy-Con support plan と順序 | https://github.com/niart120/swbt-python/issues/48 |
| child issue | profile-aware input report mapping と unsupported input validation | https://github.com/niart120/swbt-python/issues/51 |
| dependency | profile injection | https://github.com/niart120/swbt-python/issues/49 |
| dependency | Joy-Con L/R profile identity | https://github.com/niart120/swbt-python/issues/50 |
| AGENTS | button bit、stick packing、IMU frame は source-audit 対象 | `AGENTS.md` |
| initial protocol | `0x30` standard full input report と button / stick / IMU 責務 | `spec/initial/protocol.md` |
| initial API | state update API と `InputState` 境界 | `spec/initial/api.md` |
| initial testing | input report unit test と fake transport integration | `spec/initial/testing.md` |
| dekuNukem HID notes | standard input report button bytes、stick offsets、6-axis data | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/bluetooth_hid_notes.md |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Joy-Con L user | `await pad.press(Button.A)` | commit 前に unsupported input として失敗する | `Button.A` を黙って落とさない |
| Joy-Con R user | D-pad 系入力 | commit 前に unsupported input として失敗する | state store に不正状態を残さない |
| Joy-Con L user | right stick 操作 | commit 前に失敗する | left stick のみ許可 |
| Joy-Con R user | left stick 操作 | commit 前に失敗する | right stick のみ許可 |
| protocol core caller | builder 直接呼び出し | unsupported input を黙って report 化しない | defensive validation |

## 2. 対象範囲

- `Button.SL` / `Button.SR` の追加。
- Pro Controller の既存 button mapping の維持。
- Joy-Con (L) 用 button mapping の追加。
- Joy-Con (R) 用 button mapping の追加。
- profile が `InputReportMapper` 相当を持つ構造。
- Joy-Con L は left stick のみ、Joy-Con R は right stick のみ許可する仕様。
- state update API で unsupported input を commit 前に検証する仕様。
- `InputReportBuilder` の defensive validation。
- `StateStore` が profile を知らないまま維持できること。

## 3. 対象外

- `0x3F` simple HID report の実装。
- IMU 軸変換の精密対応。
- rumble データの左右 routing。
- `StateStore` に profile を持たせること。
- Joy-Con HID descriptor / SDP record。
- 実機、Bumble adapter、Switch-facing 動作の実行。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md`
- `spec/complete/unit_024/STICK_INPUT_SHORTHAND_API.md`
- `spec/complete/unit_025/IMU_INPUT_SHORTHAND_API.md`
- https://github.com/niart120/swbt-python/issues/48
- https://github.com/niart120/swbt-python/issues/49
- https://github.com/niart120/swbt-python/issues/50
- https://github.com/niart120/swbt-python/issues/51

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | Joy-Con standard button mapping と stick offsets を source-audit fixture に記録した。stick availability は profile policy として記録した |
| Bumble / transport | not applicable | not applicable | この unit は protocol core と API validation。transport wiring は unit_033 |
| OS / driver / adapter | not applicable | not applicable | 仕様作成と unit test では adapter を開かない |

### 5.1 監査対象

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| Pro Controller button mapping | existing | implementation fact / source fact | `spec/initial/protocol.md`, existing unit tests | keep |
| Joy-Con L button bit mapping | byte5 left: Down `0x01`, Up `0x02`, Right `0x04`, Left `0x08`, SR `0x10`, SL `0x20`, L `0x40`, ZL `0x80`; byte4 shared: Minus `0x01`, L Stick `0x08`, Capture `0x20` | source fact | dekuNukem `bluetooth_hid_notes.md` | stable-profile-core |
| Joy-Con R button bit mapping | byte3 right: Y `0x01`, X `0x02`, B `0x04`, A `0x08`, SR `0x10`, SL `0x20`, R `0x40`, ZR `0x80`; byte4 shared: Plus `0x02`, R Stick `0x04`, Home `0x10` | source fact | dekuNukem `bluetooth_hid_notes.md` | stable-profile-core |
| `Button.SL` / `Button.SR` placement | profile-dependent: Joy-Con L byte5 `0x20` / `0x10`, Joy-Con R byte3 `0x20` / `0x10` | source fact | dekuNukem `bluetooth_hid_notes.md` | stable-profile-core |
| Joy-Con L stick availability | left stick only; right stick updates rejected before commit, neutral right stick remains representable | inference / profile policy | issue #51, dekuNukem standard stick offsets | profile-policy |
| Joy-Con R stick availability | right stick only; left stick updates rejected before commit, neutral left stick remains representable | inference / profile policy | issue #51, dekuNukem standard stick offsets | profile-policy |
| IMU frame treatment | keep existing unconverted 6-axis packing | source fact / implementation fact | dekuNukem `bluetooth_hid_notes.md`, existing tests | no axis conversion in this unit |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Pro regression | existing Pro buttons and sticks | 既存 `0x30` bytes を維持する | mapping 変更事故を防ぐ |
| Joy-Con L supported buttons | D-pad, `L`, `ZL`, `MINUS`, `CAPTURE`, `LEFT_STICK`, `SL`, `SR` | source-audit 済み bit へ反映される | `00 29 ff` fixture |
| Joy-Con R supported buttons | `A`, `B`, `X`, `Y`, `R`, `ZR`, `PLUS`, `HOME`, `RIGHT_STICK`, `SL`, `SR` | source-audit 済み bit へ反映される | `ff 16 00` fixture |
| unsupported button at API | Joy-Con L に `Button.A`、Joy-Con R に D-pad 系 | state update API が commit 前に例外を出す | state store を変更しない |
| unsupported stick at API | Joy-Con L に right stick、Joy-Con R に left stick | state update API が commit 前に例外を出す | `apply()` も対象 |
| builder defensive validation | unsupported input を含む `InputState` | `InputReportBuilder` が例外を出す | builder 直接利用でも黙って落とさない |
| state store ownership | profile-aware validation 後の state | `StateStore` は profile を持たない | validation owner を別にする |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | Pro Controller の既存 button mapping と stick packing が変わらない | regression | unit | no | existing fixtures |
| green | `Button.SL` / `Button.SR` を public input model に追加する | new | unit | no | Pro profile では unsupported |
| green | Joy-Con L の対応ボタンが source-audit 済み bit に反映される | new | unit | no | `00 29 ff` |
| green | Joy-Con R の対応ボタンが source-audit 済み bit に反映される | new | unit | no | `ff 16 00` |
| green | Joy-Con L profile で `await pad.press(Button.A)` が commit 前に失敗する | edge | integration | no | fake transport で確認 |
| green | Joy-Con R profile で D-pad 入力が commit 前に失敗する | edge | integration | no | fake transport で確認 |
| green | Joy-Con L profile で right stick 操作が commit 前に失敗し、既存 state を保つ | edge | unit / integration | no | `rstick()` |
| green | Joy-Con R profile で left stick 操作が commit 前に失敗し、既存 state を保つ | edge | unit / integration | no | `lstick()` |
| green | `apply(state_with_unsupported_input)` が state を commit せず失敗する | edge | unit / integration | no | complete state replacement |
| green | `InputReportBuilder` 直接呼び出しでも unsupported input を例外にする | edge | unit | no | defensive validation |
| green | `StateStore` が profile を受け取らないまま維持されている | regression | unit | no | validation owner は `SwitchGamepad` / profile |

## 8. 設計メモ

- unsupported input は `UnsupportedInputError(InvalidInputError)` とする。`profile_kind`、`buttons`、`sticks` を持ち、利用者が原因を区別できる。
- validation は commit 前に行う。`press()` / `release()` / `sticks()` / `lstick()` / `rstick()` / `apply()` のいずれも、失敗時に `InputStateStore` を変更しない。
- `InputState` は union model として維持する。profile 固有の状態型を乱立させない。
- `InputReportBuilder` の validation は最後の防衛線である。通常経路では API 側で失敗し、builder は直接利用や内部バグを検出する。
- Joy-Con の IMU 軸変換はこの unit で精密対応しない。source-audit で必要性を整理し、後続へ分ける。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/input.py` | modify | `Button.SL` / `Button.SR` と validation 影響 |
| `src/swbt/errors.py` | modify | unsupported input 用例外を追加する場合 |
| `src/swbt/protocol/profile.py` | modify | profile capabilities / mapper |
| `src/swbt/protocol/input_report.py` | modify | profile-aware mapping と defensive validation |
| `src/swbt/gamepad/core.py` | modify | state update API の commit 前 validation |
| `src/swbt/state_store.py` | inspect / keep | profile を持たせないことを確認 |
| `tests/unit/test_input_report.py` | modify | Pro regression と Joy-Con mapping |
| `tests/unit/test_input_state.py` | modify | `Button.SL` / `Button.SR` |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | API validation と no-commit |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | 監査済み mapping だけ追加 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_input_state.py::test_button_model_includes_single_joycon_sl_and_sr tests/unit/test_input_report.py tests/unit/test_source_audit_fixtures.py tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_left_press_rejects_unsupported_button_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_right_press_rejects_unsupported_button_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_left_rejects_right_stick_update_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_right_rejects_left_stick_update_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_apply_rejects_unsupported_state_before_commit -q` | red | `UnsupportedInputError` import 不在で collection error。unit_031 の未実装を確認 |
| `uv run pytest tests/unit/test_input_state.py::test_button_model_includes_single_joycon_sl_and_sr tests/unit/test_input_report.py tests/unit/test_source_audit_fixtures.py tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_left_press_rejects_unsupported_button_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_right_press_rejects_unsupported_button_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_left_rejects_right_stick_update_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_right_rejects_left_stick_update_before_commit tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_apply_rejects_unsupported_state_before_commit -q` | pass | 52 passed |
| `uv sync --dev` | pass | Resolved 53 packages。Checked 41 packages |
| `uv run pytest tests/unit` | pass | 298 passed |
| `uv run pytest tests/integration` | pass | 80 passed |
| `uv run ruff format --check .` | pass | 77 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 仕様作成では不要。mapping unit test でも不要 |
| 承認範囲 | 後続で input reflection を実機確認する場合は、adapter open、HID advertising、pairing または reconnect、periodic report loop、Switch-facing output report / subcommand handling、入力送信、cleanup の明示承認が必要 |
| adapter | 仕様作成では使用しない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実機時は OS、driver、dongle、Bumble version、Python version、Switch model / firmware、profile、入力、result、cleanup を記録する |
| cleanup | neutral、report loop 停止、transport close、adapter release |

## 12. 先送り事項

- Joy-Con IMU 軸変換と実機反映は pending。この unit は既存 6-axis packing を維持する。
- `0x3F` simple HID report は別 unit。
- IMU 軸変換の精密対応と rumble routing は別 unit。
- Joy-Con descriptor / SDP は unit_033。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] unsupported input を state update API で commit 前に拒否する設計にした
- [x] builder defensive validation を残した
- [x] Joy-Con mapping の未監査 bit を確定していない
