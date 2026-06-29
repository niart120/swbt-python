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
- `spec/wip/unit_009/PORTING_SOURCE_AUDIT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | `0x30` layout、button bit、stick packing、IMU frame、battery / connection info、reply payload、SPI address は既存 `swbt-daemon` spec と実機ログから分類して固定する |
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
| todo | neutral `InputState` が空 button、center stick、neutral IMU を持つ | new | unit | no | M0 最初の red 候補 |
| todo | `Stick.raw()` が `0..4095` 外の値を拒否する | edge | unit | no | 範囲と例外を固定する |
| todo | `Stick.normalized()` が `-1.0`、`0.0`、`1.0` を決定的な raw 値へ変換する | edge | unit | no | 丸めを fixture 化する |
| todo | neutral `0x30` report が report ID を含む 49 bytes になる | new | unit | no | report byte 監査後に期待値を固定する |
| todo | `Button.A` が期待する button bit に反映される | new | unit | no | source-audit 必須 |
| todo | `Button.L` と `Button.R` の同時押しが期待する bytes になる | new | unit | no | source-audit 必須 |
| todo | d-pad 4 方向が個別の bit として反映される | new | unit | no | source-audit 必須 |
| todo | stick center が期待する 12-bit pack になる | new | unit | no | source-audit 必須 |
| todo | `0x01` output report から packet id、rumble、subcommand id、payload を抽出できる | new | unit | no | 不正長 test も追加する |
| todo | `0x10` output report を rumble only として扱う | new | unit | no | subcommand reply を生成しない |
| todo | 対応 subcommand から `0x21` reply を生成できる | new | unit | no | `0x02`、`0x03`、`0x04`、`0x08`、`0x10`、`0x21`、`0x30`、`0x40`、`0x48` |
| todo | `VirtualSpiFlash` が既知 address の読み取りを返す | new | unit | no | address と data は監査対象 |
| todo | protocol package が Bumble を import していない | regression | unit | no | 依存境界の固定 |

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

この表は M0 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit` | pending | M0 実装後に protocol unit gate として実行する |
| `uv run ruff format --check .` | pending | M0 実装後に静的 gate として実行する |

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
- [ ] protocol byte layout と subcommand payload の根拠監査を実施し、状態を更新した
- [ ] M0 の実装と対象 test を実行し、検証欄を結果で更新した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
