# Virtual Gyroscope Calibration 仕様書

## 1. 概要

### 1.1 目的

仮想 Pro Controller が Switch へ返す factory 6-axis calibration のジャイロ部分と、利用者が物理角速度から `IMUFrame` を生成する変換尺度を一元化する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #69 | `ControllerProfile` による校正値所有、SPI `0x602C-0x6037`、固定尺度 `0.070 dps/raw`、物理角速度 API、実機回帰の完了条件 | https://github.com/niart120/swbt-python/issues/69 |
| user follow-up | Joy-Con L/R profile も同じ仮想ジャイロ校正値を SPI に設定する | 2026-07-11 conversation |
| hardware observation | ZL は反映されたが、IMU有効化・gyro PDU送信・静止加速度追加後もスプラトゥーン3のカメラは動かなかった。Switchが一括取得したfactory 6-axis calibrationのaccel側は全て `FF` だった | `build/hardware/issue-69-gyro-calibration-20260712/` |
| upstream reverse-engineering notes | 6-axis factory calibration は 4 組の XYZ Int16LE。後半 2 組が gyro zero / reference で、既定 reference は `0x343B` | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/spi_flash_notes.md |
| upstream IMU notes | saturation-free LSM6DS3 ±2000 dps の尺度は `0.070 dps/raw`。SPI 校正の gyro zero は静止時 offset | https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/imu_sensor_notes.md |
| MissionControl mode dispatch / packing | subcommand `0x40`の`0x01`は標準形式、`0x02-0x05`はquaternion形式。packing mode 2の36 byte layoutと姿勢更新 | https://github.com/ndeadly/MissionControl/tree/d3941d433f15827de8aea116d61ea17bb61d0bcc/mc_mitm/source/controllers |
| completed unit | 既存 `IMUFrame.raw()` / `gyro()` / `with_gyro()` と signed int16 validation | `spec/complete/unit_025/IMU_INPUT_SHORTHAND_API.md` |
| current implementation | SPI は device type、color flag、controller colors のみ profile から seed し、6-axis calibration は erased のまま | `src/swbt/protocol/spi.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | factory SPI `0x602C` から 12 bytes を読む | 仮想ジャイロの zero XYZ と reference XYZ を取得する | signed int16 little-endian、軸順 XYZ |
| library user | 3 軸の角速度を rad/s で指定する | 同じ校正定義で raw へ変換した `IMUFrame` を得る | 単位は rad/s、尺度は `0.070 dps/raw` 固定 |
| diagnostics | raw gyro を持つ `IMUFrame` を逆変換する | 3 軸の角速度を rad/s で得る | SPI と同じ zero と尺度を使う |
| existing user | `IMUFrame.raw()` / `IMUFrame.gyro()` を使う | 従来どおり signed int16 raw 値を設定できる | 既存 API を変更しない |

### 1.4 Intent Delta

当初はIssue #69どおりfactory 6-axis calibrationのgyro部分だけを対象とした。実機ではSwitchが`0x6020`から24 bytesを一括取得し、accel側12 bytesが全て`FF`の状態では、gyro値と静止加速度を正しくpackしてもスプラトゥーン3のカメラ反映を確認できなかった。

6-axis calibrationブロック全体を有効にするため、factory accel calibrationはIssue #70と`spec/complete/unit_048/VIRTUAL_ACCELEROMETER_CALIBRATION.md`で実装する。本 unit はその校正値と共存するgyro側の契約を追跡する。

実機再試験ではSwitch 2 firmware 22.1.0がsubcommand `0x40` payload `0x02`を送り、swbt-pythonは従来の3×6-axis形式を返していた。正負Z rawの閾値的な反応と乱回転を校正値で解消できなかった後、MissionControlがmode `0x02-0x05`をquaternion形式へ切り替える実装を確認した。

このため本unitへhost IMU modeに応じた36 byte packingを追加する。mode `0x01`の従来形式とpublic raw/rad/s APIは維持し、mode `0x02-0x05`だけ状態を持つquaternion packing mode 2へ変換する。Pro Controller、Joy-Con L、Joy-Con Rは同じmode分岐とwire packerを使う。

## 2. 対象範囲

- `ControllerProfile` が仮想ジャイロ校正情報を所有する。
- Pro Controller、Joy-Con L、Joy-Con R の具象 profile が同じ既定校正を共有する。
- 既定校正を全軸 zero raw `0`、reference raw `0x343B`、`0.070 dps/raw` とする。
- `VirtualSpiFlash` が profile の校正情報から `0x602C-0x6037` を生成する。
- `VirtualSpiFlash` が profile の校正情報から accel側 `0x6020-0x602B` も生成し、factory 6-axis calibration 24 bytesを完成させる。
- `IMUFrame.gyro_rate(x_rad_s=..., y_rad_s=..., z_rad_s=...)` を追加する。
- `IMUFrame.with_gyro_rate(...)` と `IMUFrame.to_gyro_rate()` を追加する。
- rad/s と raw の相互変換、3 軸、signed int16 境界、範囲外を unit test で固定する。
- public docs、docstring、initial design を更新する。
- Pro Controller のジャイロ入力を Switch 実機で回帰確認し、結果を記録する。
- subcommand sessionのIMU modeをinput report builderと共有する。
- mode `0x01`では既存の3×6-axis Int16LE形式を維持する。
- Pro Controller、Joy-Con L、Joy-Con Rのmode `0x02-0x05`では、加速度3 sampleと積分済み姿勢をpacking mode 2の36 byteへ格納する。

## 3. 対象外

- 加速度センサーの校正、G単位変換、公開API。Issue #70 / unit_048で扱う。
- `0.070 dps/raw` 以外の尺度を選ぶ設定。
- full-span から尺度を算出する方式。
- `816` / `936` を conversion 定数として使う方式。
- 加速度とジャイロを融合する姿勢推定、ノイズや温度ドリフトの再現。mode `0x02-0x05`に必要な角速度積分だけを行う。
- マウス入力から角速度を生成する処理。
- ユーザー向け校正 GUI。
- Joy-Con の加速度校正、スティック校正、固有の軸反転、実機回帰。Joy-Con L/Rのジャイロ校正seedとPro Controller共通のquaternion wire packingは対象に含む。

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
| factory accel calibration | required | done | dekuNukem `spi_flash_notes.md` は6-axis calibration前半2 groupsをAccel XYZ origin/reference、既定referenceを各軸`0x4000`とする。virtual zeroは各軸`0`とし、物理加速度APIには拡大しない |
| IMU mode `0x02-0x05` packing | required | done | MissionControlはmode `0x01`を標準形式、`0x02-0x05`をQuaternionMotionPackerへ分岐し、packing mode 2のbitfieldを定義する。commit `d3941d433f15827de8aea116d61ea17bb61d0bcc`をsource-audit fixtureへ固定した |
| Bumble / transport | not applicable | not applicable | report packing、transport、advertising、L2CAP は変更しない |
| OS / driver / adapter | required | done | Windows 11 / CSR8510 A10 / WinUSB / Bumble `usb:0` で実行し、環境とcleanupをhardware logへ記録した |

### 5.1 監査値

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| factory 6-axis calibration layout | `0x6020-0x6037`, 4 groups of XYZ Int16LE | source fact | dekuNukem `spi_flash_notes.md` | stable |
| factory accel calibration layout | `0x6020-0x6025` zero XYZ、`0x6026-0x602B` reference XYZ | source fact / implementation policy | dekuNukem `spi_flash_notes.md`, hardware observation | source-audit fixtureとunit testで固定済み |
| factory gyro calibration layout | `0x602C-0x6031` zero XYZ、`0x6032-0x6037` reference XYZ | inference | 上記 layout と「後半 2 groups は Gyro cal」の記述から導出 | source-audit fixture と unit test で固定済み |
| gyro zero raw | `0, 0, 0` | implementation policy | Issue #69 | stable virtual default |
| gyro reference raw | `0x343B, 0x343B, 0x343B` | source fact / implementation policy | dekuNukem `spi_flash_notes.md`, Issue #69 | stable virtual default |
| gyro scale | `0.070 dps/raw` | source fact / implementation policy | dekuNukem `imu_sensor_notes.md`, Issue #69 | stable fixed scale |
| SensorSleep mode dispatch | `0x01` standard、`0x02-0x05` quaternion | implementation fact | MissionControl `emulated_switch_controller.cpp` | source fixtureとunit testで固定済み |
| quaternion packing mode 2 | accel 3×XYZ Int16LE、最大成分を除くsigned 21-bit 3成分、11-bit timestamp、sample count `3` | implementation fact / hardware observation | MissionControl `switch_motion_packing.hpp/.cpp`、Switch 2実機trace | 3 profile共通のwire packingをsource fixtureとunit testで固定。Switch 2 / スプラトゥーン3の正負Zと静止はPro Controllerのみ確認済み |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile ownership | Pro Controller / Joy-Con L / Joy-Con R の既定 profile | zero `(0, 0, 0)`、reference `(13371, 13371, 13371)`、scale `0.070` の校正情報を共有する | profile と SPI の共有元 |
| SPI encoding | 各既定 profile で `read(0x602C, 12)` | `00 00 00 00 00 00 3b 34 3b 34 3b 34` | XYZ zero、XYZ reference、Int16LE |
| rate factory | rad/s の X/Y/Z | `degrees(value) / 0.070` を zero raw へ加え、最も近い整数 raw に丸めた `IMUFrame` | accel はゼロ |
| rate replacement | accel を持つ frame と rad/s の X/Y/Z | accel を維持し gyro raw だけを置換した frame | immutable copy |
| inverse conversion | gyro raw の X/Y/Z | `(raw - zero) * 0.070` を degree/s から rad/s へ変換した tuple | 3 軸同じ定義 |
| signed int16 boundary | raw `-32768` / `32767` に正確に対応する rad/s | 境界 raw を持つ frame | clamp しない |
| out of range | 丸め後 raw が signed int16 外 | `InvalidInputError` | 既存 raw API と同じ例外方針 |
| existing raw API | `raw()` / `gyro()` / `with_gyro()` | 既存の結果と validation を維持する | regression test |

| standard mode packing | session IMU mode `0x01` | 既存の3×(accel XYZ + gyro XYZ) Int16LE | 既存互換 |
| quaternion mode packing | Pro Controller / Joy-Con L / Joy-Con Rのsession IMU mode `0x02-0x05` | 3つのraw gyroをprofile校正でrad/sへ戻し、時系列順にreport間隔の3等分ずつ姿勢へ積分してpacking mode 2へ格納する | 3 acceleration sampleは維持する。Joy-Con軸方向は実機未検証 |
| quaternion sign | 同じ絶対値の正負Z角速度 | packing済みquaternionのZ対応成分が反対符号になる | artificial SPI offsetは使わない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | source-audit fixture が `0x602C-0x6037` の軸順、Int16LE、zero/reference、固定尺度を保持する | new | unit | no | 25 passed。既存 fixture 形式に沿っており追加の構造変更なし |
| refactor-skipped | source-audit fixture が `0x6020-0x602B` のaccel軸順、Int16LE、zero/referenceを保持する | new | unit | no | 26 passed。既存fixture形式に沿っており追加の構造変更なし |
| refactor-skipped | factory accel calibrationとG単位APIを実装する | new | unit | no | Issue #70 / unit_048で実装・検証済み |
| refactor-skipped | `ControllerProfile` が既定の仮想ジャイロ校正情報を所有する | new | unit | no | 39 passed。immutable な共有既定値を field で所有し、追加の構造変更なし |
| refactor-skipped | `VirtualSpiFlash` が profile 由来の factory gyro calibration bytes を返す | new | unit | no | 51 passed。校正値側で Int16LE serialize し、SPI は profile 値を seed。追加の構造変更なし |
| refactor-done | Joy-Con L/R profile も共通の factory gyro calibration bytes を返す | new | unit | no | 52 passed。共有既定値を base profile へ移し、3 profile の重複定義を避けた |
| refactor-skipped | `IMUFrame.gyro_rate()` が rad/s から 3 軸 raw を生成し、`to_gyro_rate()` が逆変換する | new | unit | no | 63 passed。変換を校正値へ集約済みで追加の構造変更なし |
| refactor-skipped | `IMUFrame.with_gyro_rate()` が accel を維持して gyro だけを物理角速度から置換する | new | unit | no | 64 passed。既存 `with_gyro()` へ委譲し追加の構造変更なし |
| refactor-skipped | 物理角速度 API が signed int16 境界を受理し、範囲外を `InvalidInputError` にする | edge | unit | no | 65 passed。finite validation を校正変換へ集約し、追加の構造変更なし |
| refactor-skipped | 既存 `IMUFrame.raw()` / `gyro()` / `with_gyro()` の raw 入力契約を維持する | regression | unit | no | 既存 5 tests が pass。実装変更不要 |
| refactor-skipped | public docstring と docs が rad/s API、固定尺度、範囲外例外、raw API との使い分けを説明する | docs | unit | no | 14 passed。公開 docs と initial design を追従し追加の構造変更なし |
| refactor-skipped | source-audit fixtureがmode `0x01`と`0x02-0x05`のpacking分岐、packing mode 2の主要fieldを保持する | new | unit | no | 27 passed。MissionControl commitを固定し、Switch 2実機観測を追記 |
| refactor-skipped | mode `0x02`のidentity姿勢がaccel 3 sample、packing mode `2`、max index `w`、sample count `3`をpackする | new | unit | no | `test_input_report.py` pass |
| refactor-skipped | 同じ絶対値の正負Z角速度がpacking済みquaternionの反対符号になる | regression | unit | no | deterministic clockでpass |
| refactor-skipped | Pro Controllerのmode `0x02` quaternionがSwitch実機で正負方向へ反映される | regression | hardware | yes | production factory calibrationで左回転、停止、右回転、停止を観測。traceとcleanupをhardware logへ記録済み |
| refactor-skipped | Joy-Con L/Rがmode `0x02-0x05`を受理し、Pro Controllerと同じquaternion packerを使う | regression | unit | no | profile、subcommand、input reportのunit testで固定。Joy-Con実機検証は手段がないため未実行 |
| refactor-skipped | mode `0x02-0x05`で異なる3つのgyro sampleがすべて姿勢更新へ寄与する | regression | unit | no | fake clockで非ゼロsampleの3位置と同一sample時の総積分角を固定 |
| refactor-done | 同じIMU modeの再要求がquaternion姿勢をリセットする | regression | unit | no | revision番号比較を1回消費型のmotion reset要求へ置換 |
| refactor-done | profileのfactory gyro calibrationをSPIへ必ずseedする | regression | unit | no | 非optionalなprofile契約に合わせて到達不能なNone分岐を除去 |


## 8. 設計メモ

- 校正値オブジェクトは zero/reference の XYZ tuple と固定 `0.070 dps/raw` を一つに束ね、`ControllerProfile` と `IMUFrame` conversion が同じ既定定義を参照する。
- base `ControllerProfile` が共通の既定校正 field を所有し、Pro Controller、Joy-Con L、Joy-Con R が同じ immutable 値を継承する。加速度校正はunit_048で3 profileへ適用し、スティック校正はerasedのまま維持する。
- SPI の reference 値から conversion scale を再計算しない。Issue #69 が指定する `0.070 dps/raw` を正本とし、`816` / `936` は実装に置かない。
- rad/s から raw への変換は `round()` で最も近い整数にする。変換後に signed int16 validation を通し、範囲外は clamp せず `InvalidInputError` にする。
- `IMUFrame` の rate API は呼び出し側から校正値や尺度を受け取らない。今回の profile は尺度変更を提供しないため、既定 profile と public conversion は同じ固定定義を共有する。
- Joy-Con の物理軸方向はこの unit では確定しない。Pro Controllerと同じwire packingを使うが、軸反転は追加しない。公開 conversion は report 上の X/Y/Z を変換する。
- `SubcommandSessionState`はresponderと`InputReportBuilder`で同じinstanceを共有する。subcommandはIMU modeとmotion reset要求を記録し、builderがreset要求を一度だけ消費する。profileは固定identity、IMU modeはsession mutable stateという既存境界を維持する。
- quaternion packerはreport生成時のmonotonic clock差分を3等分し、3つのraw gyroを時系列順に積分する。加速度とのfusionは行わず、最大絶対値のquaternion成分を省略した残り3成分だけをfixed point化する。
- 3 profileともmode `0x02-0x05`はpacking mode 2を使う。MissionControlも4つのDscale modeを同じpackerへ分岐し、single orientation sampleのdeltaをゼロにしている。swbt-pythonは公開APIの3 gyro sampleを単一の出力姿勢へ統合する。

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
| `src/swbt/protocol/motion.py` | new | mode `0x02-0x05` quaternion積分とpacking mode 2 |
| `src/swbt/protocol/input_report.py` | modify | session IMU modeに応じた36 byte packing切替 |
| `src/swbt/gamepad/runtime.py` | modify | responderとinput report builderのsession state共有 |
| `tests/unit/test_input_report.py`, `tests/integration/test_switch_gamepad_fake_transport.py` | modify | bitfield、正負符号、runtime mode切替 |
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
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | red | 2 failed, 24 passed。`factory_accelerometer_calibration_layout`がfixtureに未登録であることを確認 |
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | pass | 26 passed。accel layout、axis order、Int16LE、zero/referenceとsource classificationを確認 |
| `uv run pytest tests/unit/test_protocol_profile.py::test_pro_controller_profile_owns_default_virtual_gyro_calibration -q` | red | collection error。`swbt.imu` が未実装であることを確認 |
| `uv run pytest tests/unit/test_protocol_profile.py -q` | pass | 39 passed。profile ownership と既存 profile contract を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py::test_virtual_spi_flash_seeds_factory_gyro_calibration_from_profile -q` | red | 1 failed。`0x602C` が erased byte `ff` のままであることを確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py tests/unit/test_protocol_profile.py -q` | pass | 51 passed。default/custom Pro profile の gyro bytes と当時の既存 profile contract を確認 |
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
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_virtual_spi_flash.py tests/unit/test_input_state.py -q` | pass | 117 passed |
| `uv sync --dev` | pass | Resolved 53 packages |
| `uv run ruff format --check .` | pass | 90 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` | pass | 376 passed |
| `uv run pytest tests/integration -q` | pass | 93 passed |
| `uv run pytest tests/unit/test_input_report.py -q` | red | 2 failed, 33 passed。`InputReportBuilder`がsession stateとclockを受けず、mode `0x02` packing未実装を確認 |
| `uv run pytest tests/unit/test_input_report.py tests/unit/test_report_loop.py -q` | pass | 38 passed。標準形式回帰、identity packing、正負Z quaternionを確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_imu_mode_02_output_switches_periodic_input_to_quaternion_motion -q` | pass | subcommand `0x40 02`後のruntime reportがpacking mode 2へ切り替わることを確認 |
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | pass | 27 passed。MissionControl commit、mode分岐、主要bitfieldを固定 |
| `uv run ruff check ...` / `uv run ty check --no-progress` | pass | 新規protocol実装、runtime配線、testsのlint/typeを確認 |
| `uv run ruff format --check .` | pass | 91 files already formatted |
| `uv run ruff check .` / `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` | pass | 395 passed |
| `uv run pytest tests/integration -q` | pass | 94 passed |
| `uv run pytest tests/hardware/test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection --collect-only -q` | pass | 1 test collected。adapter open、Switch接続、report送信は未実行 |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-quaternion-z-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 17.99s`。Switch 2 / スプラトゥーン3で左回転、停止、右回転、停止を観測。traceはmode `0x02`、正負Z、neutral、transport closeを記録 |
| `uv run pytest tests/unit/test_protocol_profile.py::test_controller_profiles_accept_standard_and_quaternion_imu_modes tests/unit/test_subcommand_responder.py::test_joycon_profiles_accept_quaternion_imu_modes -q` | red | 8 failed, 3 passed。Joy-Con L/Rがmode `0x03-0x05`を拒否する既存profile契約を確認 |
| 同上 | pass | 11 passed。Joy-Con L/Rがmode `0x02-0x05`をACKし、session stateへ保持することを確認 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_subcommand_responder.py tests/unit/test_input_report.py tests/unit/test_source_audit_fixtures.py tests/unit/test_public_docs.py -q` | pass | 161 passed。Joy-Con profile、subcommand、packing、source-audit、公開文書の契約を確認 |
| `uv run ruff format --check .` | pass | 91 files already formatted |
| `uv run ruff check .` / `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` / `uv run pytest tests/integration -q` | pass | 414 passed / 94 passed |
| `uv run pytest tests/unit/test_input_report.py::test_quaternion_mode_integrates_all_three_gyro_samples -q` | red | 1 failed。末尾sampleだけを使う既存実装を確認 |
| `uv run pytest tests/unit/test_input_report.py -q` | pass | 48 passed。3 sampleの各位置、総積分角、既存packing回帰を確認 |
| `uv run pytest tests/unit/test_input_report.py::test_repeated_imu_mode_02_request_resets_quaternion_orientation tests/unit/test_subcommand_responder.py::test_enable_imu_updates_session_state -q` | red | 2 failed。revision依存のsession stateを確認 |
| `uv run pytest tests/unit/test_input_report.py tests/unit/test_subcommand_responder.py -q` | pass | 83 passed。reset要求の記録・一回消費と繰り返しmode requestを確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py -q` | pass | 15 passed。None分岐除去前後でfactory SPI bytes不変 |
| standard gate after mode 2 cleanup | pass | format、lint、ty、unit 418件、integration 94件 |


## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | 2026-07-12に明示承認済み。Bumble adapter open、既存bondによるactive reconnect、periodic report loop、ZL、正負Z gyro report、neutral、closeを実行。意図的なpairing / advertisingは対象外 |
| adapter | `usb:0`。専用 CSR8510 A10 / WinUSBを実行直前に確認済み |
| 実行 command | `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-quaternion-z-pytest-debug.log --log-file-level=DEBUG -q -s` |
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
- [x] rad/s ↔ raw の公開 API と境界方針を実装した
- [x] raw API の回帰を確認した
- [x] docs と initial design を更新した
- [x] Pro Controller 実機回帰を実行して結果を記録した
- [x] 標準 gate の結果を記録した
- [x] IMU mode `0x02-0x05`のquaternion形式を根拠監査した
- [x] session-aware quaternion packingとfake transport回帰を実装した
- [x] Joy-Con L/RにPro Controllerと同じmode `0x02-0x05` quaternion packingを適用する
- [x] production factory calibrationで正負ZのSwitch 2実機回帰を確認する
- [x] mode `0x02-0x05`で3つのgyro sampleを時系列順に積分する
- [x] IMU mode再要求を一回消費型のmotion reset要求として扱う
- [x] factory gyro calibrationの到達不能なNone分岐を除去する
