# Virtual Gyroscope Calibration 仕様書

## 1. 概要

### 1.1 目的

仮想 Pro Controller が Switch へ返す factory 6-axis calibration のジャイロ部分と、利用者が物理角速度から `IMUFrame` を生成する変換尺度を一元化する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #69 | `ControllerProfile` による校正値所有、SPI `0x602C-0x6037`、固定尺度 `0.070 dps/raw`、物理角速度 API、実機回帰の完了条件 | https://github.com/niart120/swbt-python/issues/69 |
| user follow-up | Joy-Con L/R profile も同じ仮想ジャイロ校正値を SPI に設定する | 2026-07-11 conversation |
| upstream reverse-engineering notes | 6-axis factory calibration は 4 組の XYZ Int16LE。後半 2 組が gyro zero / reference で、既定 reference は `0x343B` | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/spi_flash_notes.md |
| upstream IMU notes | saturation-free LSM6DS3 ±2000 dps の尺度は `0.070 dps/raw`。SPI 校正の gyro zero は静止時 offset | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/imu_sensor_notes.md |
| completed unit | 既存 `IMUFrame.raw()` / `gyro()` / `with_gyro()` と signed int16 validation | `spec/complete/unit_025/IMU_INPUT_SHORTHAND_API.md` |
| current implementation | SPI は device type、color flag、controller colors のみ profile から seed し、6-axis calibration は erased のまま | `src/swbt/protocol/spi.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | factory SPI `0x602C` から 12 bytes を読む | 仮想ジャイロの zero XYZ と reference XYZ を取得する | signed int16 little-endian、軸順 XYZ |
| library user | 3 軸の角速度を rad/s で指定する | 同じ校正定義で raw へ変換した `IMUFrame` を得る | 単位は rad/s、尺度は `0.070 dps/raw` 固定 |
| diagnostics | raw gyro を持つ `IMUFrame` を逆変換する | 3 軸の角速度を rad/s で得る | SPI と同じ zero と尺度を使う |
| existing user | `IMUFrame.raw()` / `IMUFrame.gyro()` を使う | 従来どおり signed int16 raw 値を設定できる | 既存 API を変更しない |

## 2. 対象範囲

- `ControllerProfile` が仮想ジャイロ校正情報を所有する。
- Pro Controller、Joy-Con L、Joy-Con R の具象 profile が同じ既定校正を共有する。
- 既定校正を全軸 zero raw `0`、reference raw `0x343B`、`0.070 dps/raw` とする。
- `VirtualSpiFlash` が profile の校正情報から `0x602C-0x6037` を生成する。
- `IMUFrame.gyro_rate(x_rad_s=..., y_rad_s=..., z_rad_s=...)` を追加する。
- `IMUFrame.with_gyro_rate(...)` と `IMUFrame.to_gyro_rate()` を追加する。
- rad/s と raw の相互変換、3 軸、signed int16 境界、範囲外を unit test で固定する。
- public docs、docstring、initial design を更新する。
- Pro Controller のジャイロ入力を Switch 実機で回帰確認し、結果を記録する。

## 3. 対象外

- 加速度センサーの物理単位変換。
- `0.070 dps/raw` 以外の尺度を選ぶ設定。
- full-span から尺度を算出する方式。
- `816` / `936` を conversion 定数として使う方式。
- 姿勢推定、センサーフュージョン、ノイズや温度ドリフトの再現。
- マウス入力から角速度を生成する処理。
- ユーザー向け校正 GUI。
- Joy-Con の加速度校正、スティック校正、固有の軸反転、実機回帰。Joy-Con L/R のジャイロ校正 seed は対象に含む。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_025/IMU_INPUT_SHORTHAND_API.md`
- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- `spec/hardware-test-log.md`
- `docs/api.md`
- `docs/usage.md`
- `docs/agent-brief.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | dekuNukem `spi_flash_notes.md` は 6-axis calibration を 4 組の XYZ Int16LE とし、後半 2 組を gyro calibration、reference 既定値を各軸 `0x343B` と記録する。従って gyro 部分は `0x602C-0x6037`、zero XYZ の後に reference XYZ とする |
| gyro conversion scale | required | done | dekuNukem `imu_sensor_notes.md` は saturation-free LSM6DS3 ±2000 dps を `0.070 dps/raw` とする。Issue #69 はこの尺度を固定し、full-span 換算と `816` / `936` の直接利用を明示的に除外する |
| Bumble / transport | not applicable | not applicable | report packing、transport、advertising、L2CAP は変更しない |
| OS / driver / adapter | required | todo | 完了条件の Pro Controller 実機回帰は Windows / CSR8510 A10 / WinUSB / Bumble adapter `usb:0` を候補とする。実行前に明示承認と当日の環境確認が必要 |

### 5.1 監査値

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| factory 6-axis calibration layout | `0x6020-0x6037`, 4 groups of XYZ Int16LE | source fact | dekuNukem `spi_flash_notes.md` | stable |
| factory gyro calibration layout | `0x602C-0x6031` zero XYZ、`0x6032-0x6037` reference XYZ | inference | 上記 layout と「後半 2 groups は Gyro cal」の記述から導出 | fixture で固定予定 |
| gyro zero raw | `0, 0, 0` | implementation policy | Issue #69 | stable virtual default |
| gyro reference raw | `0x343B, 0x343B, 0x343B` | source fact / implementation policy | dekuNukem `spi_flash_notes.md`, Issue #69 | stable virtual default |
| gyro scale | `0.070 dps/raw` | source fact / implementation policy | dekuNukem `imu_sensor_notes.md`, Issue #69 | stable fixed scale |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile ownership | 既定 `ProControllerProfile` | zero `(0, 0, 0)`、reference `(13371, 13371, 13371)`、scale `0.070` の校正情報を持つ | profile と SPI の共有元 |
| SPI encoding | 既定 profile で `read(0x602C, 12)` | `00 00 00 00 00 00 3b 34 3b 34 3b 34` | XYZ zero、XYZ reference、Int16LE |
| rate factory | rad/s の X/Y/Z | `degrees(value) / 0.070` を zero raw へ加え、最も近い整数 raw に丸めた `IMUFrame` | accel はゼロ |
| rate replacement | accel を持つ frame と rad/s の X/Y/Z | accel を維持し gyro raw だけを置換した frame | immutable copy |
| inverse conversion | gyro raw の X/Y/Z | `(raw - zero) * 0.070` を degree/s から rad/s へ変換した tuple | 3 軸同じ定義 |
| signed int16 boundary | raw `-32768` / `32767` に正確に対応する rad/s | 境界 raw を持つ frame | clamp しない |
| out of range | 丸め後 raw が signed int16 外 | `InvalidInputError` | 既存 raw API と同じ例外方針 |
| existing raw API | `raw()` / `gyro()` / `with_gyro()` | 既存の結果と validation を維持する | regression test |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | source-audit fixture が `0x602C-0x6037` の軸順、Int16LE、zero/reference、固定尺度を保持する | new | unit | no | 25 passed。既存 fixture 形式に沿っており追加の構造変更なし |
| refactor-skipped | `ControllerProfile` が既定の仮想ジャイロ校正情報を所有する | new | unit | no | 39 passed。immutable な共有既定値を field で所有し、追加の構造変更なし |
| refactor-skipped | `VirtualSpiFlash` が profile 由来の factory gyro calibration bytes を返す | new | unit | no | 51 passed。校正値側で Int16LE serialize し、SPI は profile 値を seed。追加の構造変更なし |
| refactor-done | Joy-Con L/R profile も共通の factory gyro calibration bytes を返す | new | unit | no | 52 passed。共有既定値を base profile へ移し、3 profile の重複定義を避けた |
| refactor-skipped | `IMUFrame.gyro_rate()` が rad/s から 3 軸 raw を生成し、`to_gyro_rate()` が逆変換する | new | unit | no | 63 passed。変換を校正値へ集約済みで追加の構造変更なし |
| refactor-skipped | `IMUFrame.with_gyro_rate()` が accel を維持して gyro だけを物理角速度から置換する | new | unit | no | 64 passed。既存 `with_gyro()` へ委譲し追加の構造変更なし |
| refactor-skipped | 物理角速度 API が signed int16 境界を受理し、範囲外を `InvalidInputError` にする | edge | unit | no | 65 passed。finite validation を校正変換へ集約し、追加の構造変更なし |
| refactor-skipped | 既存 `IMUFrame.raw()` / `gyro()` / `with_gyro()` の raw 入力契約を維持する | regression | unit | no | 既存 5 tests が pass。実装変更不要 |
| refactor-skipped | public docstring と docs が rad/s API、固定尺度、範囲外例外、raw API との使い分けを説明する | docs | unit | no | 14 passed。公開 docs と initial design を追従し追加の構造変更なし |
| todo | Pro Controller のジャイロ入力が Switch 実機で観測できる | regression | hardware | yes | test 実装・collection 済み。adapter、command、cleanup を承認後に実行 |

## 8. 設計メモ

- 校正値オブジェクトは zero/reference の XYZ tuple と固定 `0.070 dps/raw` を一つに束ね、`ControllerProfile` と `IMUFrame` conversion が同じ既定定義を参照する。
- base `ControllerProfile` が共通の既定校正 field を所有し、Pro Controller、Joy-Con L、Joy-Con R が同じ immutable 値を継承する。Joy-Con の加速度校正とスティック校正は erased のまま維持する。
- SPI の reference 値から conversion scale を再計算しない。Issue #69 が指定する `0.070 dps/raw` を正本とし、`816` / `936` は実装に置かない。
- rad/s から raw への変換は `round()` で最も近い整数にする。変換後に signed int16 validation を通し、範囲外は clamp せず `InvalidInputError` にする。
- `IMUFrame` の rate API は呼び出し側から校正値や尺度を受け取らない。今回の profile は尺度変更を提供しないため、既定 profile と public conversion は同じ固定定義を共有する。
- Joy-Con の物理軸方向はこの unit では確定しない。公開 conversion は report 上の X/Y/Z を変換する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/imu.py` | new | 仮想ジャイロ校正値と rad/s ↔ raw 変換 |
| `src/swbt/input.py` | modify | `IMUFrame` の物理角速度 API |
| `src/swbt/protocol/profiles/base.py` | modify | `ControllerProfile` の校正値所有 |
| `src/swbt/protocol/spi.py` | modify | factory gyro calibration seed |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | layout と尺度の根拠 fixture |
| `tests/unit/test_source_audit_fixtures.py` | modify | source fixture contract |
| `tests/unit/test_protocol_profile.py` | modify | profile ownership |
| `tests/unit/test_virtual_spi_flash.py` | modify | SPI bytes fixture |
| `tests/unit/test_input_state.py` | modify | conversion、境界、raw regression |
| `tests/hardware/test_input_operations.py` | modify | Pro Controller gyro manual reflection |
| `spec/initial/*.md` | modify | API、protocol、testing、architecture の追従 |
| `docs/api.md`, `docs/usage.md`, `docs/agent-brief.md` | modify | public API の説明と例 |
| `spec/hardware-test-log.md` | modify | 承認済み実機回帰結果 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | red | 2 failed, 23 passed。`factory_gyro_calibration_layout` が fixture に未登録であることを確認 |
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | pass | 25 passed。layout、axis order、Int16LE、zero/reference、固定尺度と source classification を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py::test_pro_controller_profile_owns_default_virtual_gyro_calibration -q` | red | collection error。`swbt.imu` が未実装であることを確認 |
| `uv run pytest tests/unit/test_protocol_profile.py -q` | pass | 39 passed。profile ownership と既存 profile contract を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py::test_virtual_spi_flash_seeds_factory_gyro_calibration_from_profile -q` | red | 1 failed。`0x602C` が erased byte `ff` のままであることを確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py tests/unit/test_protocol_profile.py -q` | pass | 51 passed。default/custom Pro profile の gyro bytes と Joy-Con erased calibration の回帰を確認 |
| `uv run pytest tests/unit/test_input_state.py::test_imu_frame_converts_three_axis_gyro_rates_between_rad_s_and_raw -q` | red | 1 failed。`IMUFrame.gyro_rate` が未実装の `AttributeError` を確認 |
| `uv run pytest tests/unit/test_input_state.py -q` | pass | 63 passed。3 軸の rad/s → raw と raw → rad/s、および既存 input model test を確認 |
| `uv run pytest tests/unit/test_input_state.py::test_imu_frame_with_gyro_rate_preserves_accelerometer_axes -q` | red | 1 failed。`with_gyro_rate` が未実装の `AttributeError` を確認 |
| `uv run pytest tests/unit/test_input_state.py -q` | pass | 64 passed。物理角速度による gyro 置換と accel 保持を確認 |
| `uv run pytest tests/unit/test_input_state.py::test_imu_frame_gyro_rate_accepts_i16_boundaries_and_rejects_out_of_range -q` | red | 1 failed。infinity が `OverflowError` になる未統一を確認 |
| `uv run pytest tests/unit/test_input_state.py -q` | pass | 65 passed。signed int16 両端、有限の範囲外、NaN、infinity と `InvalidInputError` 方針を確認 |
| `uv run pytest tests/unit/test_input_state.py::test_imu_frame_raw_defaults_to_neutral_and_sets_accel_and_gyro_axes tests/unit/test_input_state.py::test_imu_frame_raw_rejects_values_outside_i16_range tests/unit/test_input_state.py::test_imu_frame_gyro_and_accel_shorthands_match_raw_construction tests/unit/test_input_state.py::test_imu_frame_update_helpers_preserve_the_opposite_sensor_axes -q` | pass | 5 passed。既存 raw API の生成、範囲、shorthand、部分更新を確認 |
| `uv run pytest tests/unit/test_public_api_docstrings.py tests/unit/test_public_docs.py -q` | red | 4 failed, 10 passed。固定尺度の docstring と API / usage / agent docs が未記載であることを確認 |
| `uv run pytest tests/unit/test_public_api_docstrings.py tests/unit/test_public_docs.py -q` | pass | 14 passed。rad/s API、`0.070 dps/raw`、範囲外例外、raw API の使い分けを確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py::test_virtual_spi_flash_seeds_gyro_calibration_for_joycon_profiles -q` | red | 2 failed。Joy-Con L/R の `gyro_calibration` が `None` であることを確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py tests/unit/test_protocol_profile.py -q` | pass | 52 passed。Pro / Joy-Con L / Joy-Con R の共通校正 seed と既存 profile / SPI contract を確認 |
| `uv run pytest tests/hardware/test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection --collect-only -q` | pass | 1 test collected。adapter open、接続、report loop は未実行 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_virtual_spi_flash.py tests/unit/test_input_state.py` | not run | 各 TDD cycle で対象 test を絞って実行する |
| `uv sync --dev` | not run | 最終 gate |
| `uv run ruff format --check .` | not run | 最終 gate |
| `uv run ruff check .` | not run | 最終 gate |
| `uv run ty check --no-progress` | not run | 最終 gate |
| `uv run pytest tests/unit` | not run | 最終 gate |
| `uv run pytest tests/integration` | not run | 関連 tree の回帰 gate |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | 未承認。Bumble adapter open、Pro Controller advertising / reconnect、periodic report loop、gyro report、neutral、close を対象として明示承認が必要 |
| adapter | 候補 `usb:0`。専用 CSR8510 A10 / WinUSB であることを実行直前に確認する |
| 実行 command | `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260711 --log-file build\hardware\issue-69-gyro-calibration-20260711\gyro-rate-pytest-debug.log --log-file-level=DEBUG -q -s` |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、Switch-facing 動作、cleanup plan で管理する |
| log / artifact | `build/hardware/` 配下の JSONL trace と pytest debug log、`spec/hardware-test-log.md` |
| cleanup | gyro 入力後に neutral frame を送り、report loop を停止し、transport を close して adapter を解放する |

## 12. 先送り事項

- none

## 13. チェックリスト

- [x] Issue #69 の対象範囲と対象外を確認した
- [x] TDD Test List の初期案を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件と未承認状態を記録した
- [x] source-audit fixture を更新した
- [x] profile と SPI の校正共有を実装した
- [ ] rad/s ↔ raw の公開 API と境界方針を実装した
- [x] raw API の回帰を確認した
- [x] docs と initial design を更新した
- [ ] Pro Controller 実機回帰を実行して結果を記録した
- [ ] 標準 gate の結果を記録した
