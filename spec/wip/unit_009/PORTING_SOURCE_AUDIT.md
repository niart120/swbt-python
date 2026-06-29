# Porting Source Audit 仕様書

## 1. 概要

### 1.1 目的

既存 `swbt-daemon`、Switch HID 関連資料、Bumble documentation、実機ログから `swbt-python` に移植する値を分類し、未監査の byte layout や OS / driver 前提を実装へ混入させない。M0、M2、M4、M6、M7 の根拠監査 source として使う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| AGENTS | 根拠監査の対象と分類 | `AGENTS.md` |
| README initial | 参考資料と未決事項 | `spec/initial/README.md` |
| protocol | report / subcommand / SPI / rumble の監査対象 | `spec/initial/protocol.md` |
| transport-bumble | Bumble / SDP / descriptor / OS driver の監査対象 | `spec/initial/transport-bumble.md` |
| risks | driver、firmware、dongle、documentation drift | `spec/initial/risks.md` |
| source-audit skill | 分類と記録形式 | `.agents/skills/source-audit/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| implementer | report ID / byte offset を実装する前 | source fact、implementation fact、hardware observation、inference、unverified hypothesis が分かれている | 未監査値を固定しない |
| implementer | Bumble / SDP / descriptor を実装する前 | 参照元、version、安定度が記録されている | Bumble API は version 付き |
| reviewer | magic number を見る | 値、意味、source、status を追える | 実機観測を一般化しない |
| future milestone | 実機で不足を見つける | 追加監査先と記録先が明確 | 小観測は dev-journal、実機値は hardware log |

## 2. 対象範囲

- `0x30` input report の byte layout。
- `0x01` / `0x10` output report layout。
- button bit、stick packing、IMU frame。
- subcommand ID と `0x21` reply payload。
- SPI flash address と返却 data。
- raw rumble packet layout。
- report period default。
- HID descriptor bytes。
- SDP record。
- Bumble HID Device helper、Classic support、L2CAP callback。
- WinUSB / libusb / OS driver 前提。
- Bluetooth dongle と Switch firmware に依存する観測。

## 3. 対象外

- 実装そのもの。
- 実機コマンドの実行。
- 未確認値を public API の保証にすること。
- 複数 firmware / dongle の網羅。

## 4. 関連 docs

- `spec/initial/protocol.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/wip/unit_001/M0_PROTOCOL_CORE.md`
- `spec/wip/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/wip/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | この仕様自体が監査 inventory。値は各実装 unit に移す前に分類する |
| Bumble / transport | required | todo | Bumble HID Device / SDP / L2CAP 仮定を version 付きで記録する |
| OS / driver / adapter | required | todo | WinUSB、libusb、dongle identity、firmware 観測を一般化しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| value inventory | 監査対象値 | 値、意味、分類、source、status が表になる | 実装前に作る |
| source classification | 参照元 | `source fact` などの分類が付く | 分類を混ぜない |
| stability decision | 監査済み値 | `stable`、`configurable`、`hardware-observed only` を決める | release docs に影響 |
| missing evidence | 根拠不足 | 未解決事項と次の確認先を記録する | 仮説を契約化しない |
| implementation handoff | 実装 unit | 対象 spec の根拠監査欄へ反映する | M0 / M2 / M4 など |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `0x30` neutral report fixture が source と対応付けられている | characterization | unit | no | M0 の fixture source |
| todo | button bit と stick packing の fixture に source 分類がある | characterization | unit | no | 実装前の監査 |
| todo | subcommand reply payload fixture に source 分類がある | characterization | unit | no | M4 で更新 |
| todo | SPI flash address / data fixture に source 分類がある | characterization | unit | no | 未定義領域の扱いを含む |
| todo | HID descriptor / SDP record の source と version が記録されている | characterization | unit | no | M2 の前提 |
| todo | report period default の根拠と configurable 判断が記録されている | characterization | unit | no | scheduler jitter 対策 |
| todo | adapter / driver 前提が hardware log と README に分かれて反映される | regression | hardware | yes | 実機 run 後 |

## 8. 設計メモ

- 監査結果は大きな判断なら該当 `spec/wip/unit_XXX`、安定判断なら `spec/initial`、小さい観測なら `spec/dev-journal.md`、実機値なら `docs/hardware-test-log.md` に置く。
- 実装時に source URL だけではなく commit、version、local fixture 名を残す。
- hardware observation は OS、driver、dongle、Bumble version、Python version、Switch model / firmware を含めて記録する。
- 未監査の値は `unverified hypothesis` と書き、unit test の期待値にしない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `spec/wip/unit_001/M0_PROTOCOL_CORE.md` | modify | protocol value audit status |
| `spec/wip/unit_003/M2_BUMBLE_HID_TRANSPORT.md` | modify | Bumble / descriptor / OS audit status |
| `spec/wip/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md` | modify | observed subcommand audit |
| `spec/dev-journal.md` | new / modify | 小さい未解決観測 |
| `docs/hardware-test-log.md` | new / modify | 実機観測 |
| `tests/unit/fixtures/` | new | 監査済み protocol fixture |

## 10. 検証

この表は source audit 作業時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `rg -n ("TO" + "DO|" + "TB" + "D|" + "x" + "xx") spec src tests README.md` | pending | 監査結果を実装や docs に反映した後、仮テキスト残存確認として実行する |
| `uv run pytest tests/unit` | pending | 監査 fixture 実装後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | source inventory では不要。hardware observation を採る場合は必要 |
| 承認範囲 | 実機観測を行う場合は adapter open、advertising、pairing、report loop、cleanup の範囲を明示する |
| adapter | 例: `usb:0`。実機観測時のみ必要 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | audit table、fixture、hardware log |
| cleanup | 実機観測時は neutral、transport close、adapter release |

## 12. 先送り事項

- release 前にどの監査項目を blocking にするかは unit_012 で判断する。
- Linux / macOS の実機保証は初期 release 範囲が決まった後に拡張する。

## 13. チェックリスト

このチェックリストは source audit 作業の完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] protocol / Bumble / OS driver の監査表を作成し、分類を記録した
- [ ] 監査結果を対象 unit の根拠監査欄または fixture に反映した
- [ ] 監査 fixture と docs residue の検証を実行し、検証欄を結果で更新した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
