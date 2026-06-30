# M0 Protocol Core 仕様書

## 1. 概要

### 1.1 目的

実機、Bumble、Bluetooth adapter に依存しない Switch HID protocol core を作る。M0 では入力状態、`0x30` input report、`0x01` / `0x10` output report parse、主要 subcommand reply、virtual SPI flash、raw rumble state を unit test で固定する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M0 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| architecture | protocol 層の責務と Bumble 非依存境界 | `spec/initial/architecture.md` |
| protocol | report 生成、output report parse、subcommand reply の設計 | `spec/initial/protocol.md` |
| testing | unit test の分類と最低検証項目 | `spec/initial/testing.md` |
| source-audit skill | byte layout と subcommand payload の根拠分類 | `.agents/skills/source-audit/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| protocol unit test | neutral `InputState` | report ID `0x30`、49 bytes の input report が生成される | Bumble と実機を使わない |
| protocol unit test | `Button.A`、`Button.L` + `Button.R`、d-pad、stick center | report bytes に入力状態が反映される | bit layout は根拠監査後に fixture 化する |
| protocol unit test | `0x01` output report | packet id、raw rumble、subcommand id、payload が parse される | 不正長は `ProtocolError` |
| protocol unit test | 主要 subcommand | `0x21` reply bytes が生成される | payload は監査済み根拠から固定する |

## 2. 対象範囲

- `Button`、`Stick`、`IMUFrame`、`InputState`。
- `InputReportBuilder` による `0x30` standard full input report 生成。
- `OutputReportParser` による `0x01` と `0x10` の parse。
- `SubcommandResponder` による `0x02`、`0x03`、`0x04`、`0x08`、`0x10`、`0x21`、`0x30`、`0x40`、`0x48` の最小 reply。
- `VirtualSpiFlash` の初期内容と read 境界。
- `RumbleState` による raw rumble bytes の保持。
- protocol 層が Bumble、transport、実機接続を import しないことの確認。

## 3. 対象外

- Bumble transport。
- USB Bluetooth adapter open。
- Switch pairing。
- L2CAP channel。
- periodic report loop。
- public `SwitchGamepad` API。
- packaging。
- 高水準 rumble API、NFC、IR camera、amiibo の意味処理。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/initial/roadmap.md`
- `spec/initial/risks.md`
- `spec/complete/unit_009/PORTING_SOURCE_AUDIT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` の `input_report_0x30_layout`、`button_bit_and_stick_pack`、`output_report_parser_layout`、`subcommand_reply_0x21_layout`、`spi_flash_boundary_and_seed_map` を M0 実装前の根拠 source とする |
| Bumble / transport | not applicable | not applicable | M0 は protocol core のみで Bumble を import しない |
| OS / driver / adapter | not applicable | not applicable | M0 は USB Bluetooth adapter を使わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| neutral state | `InputState.neutral()` | button 集合は空、左右 stick は center、IMU は neutral frame | immutable な値として扱う |
| stick raw validation | `Stick.raw(x, y)` | `0..4095` の範囲外を拒否する | 例外型は `InvalidInputError` または protocol 層の入力例外として決める |
| stick normalized conversion | `Stick.normalized(x, y)` | `-1.0..1.0` を 12-bit raw に変換する | 丸め規則を test で固定する |
| input report | `InputState` | report ID `0x30` を含む 49 bytes を返す | byte offset は監査済み fixture に従う |
| output report parse | `0x01` bytes | packet id、rumble、subcommand id、payload を返す | parse 結果は値オブジェクト |
| rumble only parse | `0x10` bytes | raw rumble を更新し、subcommand reply は作らない | 高水準 rumble 解釈はしない |
| subcommand reply | 対応 subcommand | `0x21` reply bytes を返す | 送信順序は M1 の `ReportLoop` |
| unsupported subcommand | 未対応 subcommand | diagnostics へ記録できる情報を返す | 実機で隠さず観測するため |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | neutral `InputState` が空 button、center stick、neutral IMU を持つ | new | unit | no | `tests/unit/test_input_state.py` で固定 |
| green | `Stick.raw()` が `0..4095` 外の値を拒否する | edge | unit | no | `InvalidInputError` を固定 |
| green | `Stick.normalized()` が `-1.0`、`0.0`、`1.0` を決定的な raw 値へ変換する | edge | unit | no | 端点変換を固定 |
| green | neutral `0x30` report が report ID を含む 49 bytes になる | new | unit | no | `tests/unit/test_input_report.py` で固定 |
| green | `Button.A` が期待する button bit に反映される | new | unit | no | 代表 bit と全公開 button mapping を固定 |
| green | `Button.L` と `Button.R` の同時押しが期待する bytes になる | new | unit | no | byte 3 / 5 の bit を固定 |
| green | d-pad 4 方向が個別の bit として反映される | new | unit | no | byte 5 の low nibble を固定 |
| green | stick center が期待する 12-bit pack になる | new | unit | no | center と custom stick pack を固定 |
| green | `0x01` output report から packet id、rumble、subcommand id、payload を抽出できる | new | unit | no | 不正長は `ProtocolError` |
| green | `0x10` output report を rumble only として扱う | new | unit | no | subcommand id は `None` |
| green | 対応 subcommand から `0x21` reply を生成できる | new | unit | no | `0x02`、`0x03`、`0x04`、`0x08`、`0x10`、`0x21`、`0x30`、`0x40`、`0x48` |
| green | 未対応 subcommand が diagnostics 用の id と payload を保持する | edge | unit | no | `UnsupportedSubcommandError` で固定 |
| green | `VirtualSpiFlash` が既知 address の読み取りを返す | new | unit | no | `0x6012` の device type と read 境界を固定 |
| green | `RumbleState` が raw rumble bytes を保持する | new | unit | no | 高水準 rumble 解釈はしない |
| green | protocol package が Bumble を import していない | regression | unit | no | `tests/unit/test_protocol_boundary.py` で固定 |

## 8. 設計メモ

- report byte、subcommand payload、SPI 初期内容は未監査の値を実装へ直書きしない。
- `InputState` と `Stick` は標準ライブラリだけに依存させる。
- `SubcommandResponder` は送信しない。reply bytes を返し、送信優先順位は M1 の `ReportLoop` が扱う。
- 高水準 rumble、NFC、IR camera の意味処理は public API に出さない。必要な raw bytes と ack だけを扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/input.py` | new | `Button`、`Stick`、`IMUFrame`、`InputState` |
| `src/swbt/protocol/input_report.py` | new | `0x30` input report builder |
| `src/swbt/protocol/output_report.py` | new | `0x01` / `0x10` output report parser |
| `src/swbt/protocol/subcommand.py` | new | subcommand reply generation |
| `src/swbt/protocol/spi.py` | new | `VirtualSpiFlash` |
| `src/swbt/protocol/rumble.py` | new | `RumbleState` |
| `src/swbt/protocol/profile.py` | new | Pro Controller 相当の固定 profile |
| `src/swbt/errors.py` | new | protocol と入力値の例外 |
| `tests/unit/` | new / modify | protocol core unit tests |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 2026-07-01 実行。Resolved 41 packages / Checked 41 packages |
| `uv run ruff format --check .` | pass | 2026-07-01 実行。20 files already formatted |
| `uv run ruff check .` | pass | 2026-07-01 実行。All checks passed |
| `uv run ty check --no-progress` | pass | 2026-07-01 実行。All checks passed |
| `uv run pytest tests/unit` | pass | 2026-07-01 実行。66 passed |
| `uv run pytest tests/integration` | not run | M0 は protocol unit のみで、fake transport integration は M1 の対象 |
| `bumble` / `hardware` marker tests | not run | M0 は Bumble、adapter open、Switch-facing 動作を対象外とする |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 不要 |
| 承認範囲 | なし |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | unit test output |
| cleanup | 不要 |

## 12. 先送り事項

- `HID descriptor` と `SDP record` は M2 で扱う。
- `reply queue` の優先送信は M1 で扱う。
- 実機で観測された追加 subcommand は M4 で仕様へ戻す。

## 13. チェックリスト

このチェックリストは M0 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] protocol byte layout と subcommand payload の根拠監査を実施し、状態を更新した
- [x] M0 の実装と対象 test を実行し、検証欄を結果で更新した
- [x] 完了条件を満たしたら `spec/complete` へ移動する
