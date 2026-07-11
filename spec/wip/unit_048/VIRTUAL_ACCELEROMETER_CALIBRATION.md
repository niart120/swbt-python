# Virtual Accelerometer Calibration 仕様書

## 1. 概要

### 1.1 目的

仮想 Pro Controller / Joy-Con の factory accelerometer calibration と、G 単位から `IMUFrame` を生成する変換尺度を一元化する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #70 | profile 所有、SPI `0x6020-0x602B`、固定尺度 `1/4096 G/raw`、G API、Pro/Joy-Con 実機回帰 | https://github.com/niart120/swbt-python/issues/70 |
| unit_047 実機観測 | Switch は `0x6020` から 24 bytes を読み、accel 側が全て `FF` の場合はジャイロのカメラ反映を確認できなかった | `spec/wip/unit_047/VIRTUAL_GYRO_CALIBRATION.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | factory SPI `0x6020` から 12 bytes を読む | zero XYZ と reference XYZ を取得する | signed int16 little-endian、軸順 XYZ |
| library user | X/Y/Z の加速度を G で指定する | 同じ校正定義で raw へ変換した `IMUFrame` を得る | `1/4096 G/raw` 固定 |
| diagnostics | raw accel を持つ frame | G 単位の 3 軸値を得る | SPI と同じ zero と尺度 |

## 2. 対象範囲

- `ControllerProfile` が zero `(0,0,0)`、reference `(0x4000,0x4000,0x4000)`、reference acceleration `4.0 G` の校正値を所有する。
- Pro Controller、Joy-Con L、Joy-Con R が同じ既定値を使う。
- `VirtualSpiFlash` が `0x6020-0x602B` を profile から生成し、gyro と合わせて `0x6020-0x6037` を完成させる。
- `IMUFrame.accel_g()`、`with_accel_g()`、`to_accel_g()` を追加する。
- 3 軸、signed int16 境界、非有限値と範囲外、raw/gyro API 回帰を unit test で固定する。
- public docs、docstring、initial design を更新する。
- Pro Controller と Joy-Con の SPI read 実機回帰を記録する。

## 3. 対象外

- 重力方向や姿勢の生成、並進加速度、遠心力、ノイズの模擬。
- user calibration `0x8028-0x803F`、horizontal offset `0x6080-0x6085`。
- 個体別校正と利用者向け校正設定。

## 4. 関連 docs

- `spec/wip/unit_047/VIRTUAL_GYRO_CALIBRATION.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `docs/api.md`
- `docs/usage.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | Issue #70 と source-audit fixture が layout、Int16LE、zero/reference を固定する |
| G conversion scale | required | done | Issue #70 が reference acceleration `4.0 G`、尺度 `1/4096 G/raw` を指定する |
| Bumble / transport | not applicable | not applicable | transport と report packing は変更しない |
| OS / driver / adapter | required | in progress | Pro ControllerはWindows 11 / CSR8510 A10 / WinUSB / `usb:0`で記録済み。Joy-Conは未実行 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile/SPI | 3 種の既定 profile | `00 00` × 3、`00 40` × 3 | `0x6020` から 12 bytes |
| G factory/inverse | X/Y/Z の G 値 | `round(G * 4096)` と逆変換 | zero raw を加減する |
| G replacement | gyro を持つ frame | gyro を維持して accel だけ置換 | immutable copy |
| boundary/error | signed int16 境界、範囲外、NaN、inf | 境界を受理し、範囲外は `InvalidInputError` | clamp しない |
| full calibration | `read(0x6020, 24)` | accel 12 bytes と gyro 12 bytes が連続する | 両 Issue の共存 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | source fixture が layout、軸順、Int16LE、zero/reference、4.0 G、`1/4096 G/raw` を保持する | new | unit | no | fixture は unit_047 で先行追加。Issue #70 の全契約へ更新する |
| refactor-done | 3 profile と SPI が同じ加速度校正値を共有する | new | unit | no | gyroと共通の3軸校正モデルへ集約 |
| refactor-skipped | `accel_g()` と `to_accel_g()` が 3 軸を相互変換する | new | unit | no | 68 input tests pass |
| refactor-skipped | `with_accel_g()` が gyro を維持する | new | unit | no | 反対側sensor保持を確認 |
| refactor-skipped | G API が signed int16 境界を受理し範囲外を統一例外にする | edge | unit | no | NaN/infを含め確認 |
| refactor-skipped | factory 24 bytes と既存 raw/gyro API が共存する | regression | unit | no | 24-byte fixtureと既存API tests pass |
| refactor-skipped | 公開 docs と initial design が G API と固定尺度を説明する | docs | unit | no | public docs tests pass |
| green | Pro Controller と Joy-Con の SPI read を実機で記録する | regression | hardware | yes | Proは`0x6020` 24-byte応答を記録。Joy-Conは未実行 |

## 8. 設計メモ

- G API は校正値を引数に取らず、profile と共有する既定定義を使う。
- raw 変換は `round()` 後に signed int16 を検証し、clamp しない。
- gyro 校正と共通化できる serialize・検証処理は green 後の refactor で判断する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/imu.py` | modify | 加速度校正と G↔raw 変換 |
| `src/swbt/input.py` | modify | 公開 G API |
| `src/swbt/protocol/profiles/base.py` | modify | profile 所有 |
| `src/swbt/protocol/spi.py` | modify | factory accel seed |
| `tests/unit/` | modify | source、profile、SPI、API、回帰 |
| `tests/hardware/` | modify | Pro/Joy-Con SPI read 回帰 |
| `spec/initial/`, `docs/` | modify | 公開契約の追従 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | pass | 26 passed。Issue #70 の尺度記述は次 cycle で追加する |
| standard gate | pass | format、lint、ty、unit 386件、integration 93件。最終差分で再実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | 未承認。Pro/Joy-Con の adapter open、接続、SPI read、close に明示承認が必要 |
| adapter | 実行時に identity と adapter string を確認する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build/hardware/` と `spec/hardware-test-log.md` |
| cleanup | report loop を停止し、transport を close して adapter を解放する |

## 12. 先送り事項

- none

## 13. チェックリスト

- [x] Issue #70 の対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を未承認として記録した
- [x] unit test と実装を完了した
- [x] docs と initial design を更新した
- [ ] Pro/Joy-Con 実機回帰を記録した
- [ ] 標準 gate を記録した
