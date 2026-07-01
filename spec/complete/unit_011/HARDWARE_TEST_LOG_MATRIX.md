# Hardware Test Log / Matrix 仕様書

## 1. 概要

### 1.1 目的

Bumble adapter、Switch 実機、OS / driver、dongle、firmware に依存する観測を `docs/hardware-test-log.md` と matrix で管理する。実機観測を別環境へ一般化せず、release gate と README の確認済み構成に使える粒度で残す。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| AGENTS | 実機観測の記録項目と安全境界 | `AGENTS.md` |
| testing | 実機検証マトリクス、hardware test、diagnostics events | `spec/initial/testing.md` |
| transport-bumble | Windows / Linux / macOS の注意点 | `spec/initial/transport-bumble.md` |
| risks | firmware、OS / driver、dongle 差分 | `spec/initial/risks.md` |
| hardware-harness skill | 実行前チェック、記録先、pytest marker | `.agents/skills/hardware-harness/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| developer | Bumble adapter test | OS、driver、dongle、Bumble version、command、result、cleanup が残る | 明示承認が必要 |
| developer | Switch pairing test | Switch model / firmware と pairing / L2CAP 結果が残る | hardware observation として扱う |
| release reviewer | README 更新前 | 確認済み構成と未確認構成を matrix から判定できる | 未確認を保証しない |
| maintainer | failure triage | trace artifact と cleanup result を追える | raw secret は残さない |

## 2. 対象範囲

- `docs/hardware-test-log.md` の作成。
- hardware run entry template。
- OS、driver、dongle、adapter string、Bumble version、Python version、Switch model / firmware、command、result、cleanup の記録。
- matrix の項目定義。
- `@pytest.mark.bumble` と `@pytest.mark.hardware` の結果記録。
- README の確認済み / 未確認構成への反映基準。

## 3. 対象外

- 実機 test の実行そのもの。
- hardware runner の構築。
- 全 dongle / firmware の網羅。
- trace の外部保存サービス。
- secret や link key の記録。

## 4. 関連 docs

- `spec/initial/testing.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/risks.md`
- `spec/wip/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/complete/unit_004/M3_PAIRING_L2CAP.md`
- `spec/complete/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/wip/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `spec/wip/unit_012/INITIAL_RELEASE_GATE.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | future observation only | not run | この作業では report / subcommand / input reflection を観測していない。template に記録欄を用意し、実機観測は後続 run entry に残す |
| Bumble / transport | future observation only | not run | adapter open、Classic、HID advertising、L2CAP は実行していない。Bumble version と command の記録欄を template に含めた |
| OS / driver / adapter | required for log schema | done | OS、driver、dongle、adapter string を run entry と matrix の必須項目として定義した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| log file creation | 初回 hardware run | `docs/hardware-test-log.md` が template 付きで作られる | 実行前に作ってもよい |
| run entry | test / command 実行 | metadata、approval、result、artifact、cleanup が残る | 日付と短い題名 |
| matrix update | run 完了 | Pairing、L2CAP、Subcommands、Input reflected などが更新される | 未検証は未検証のまま |
| failure entry | failure | 失敗位置、trace artifact、cleanup result が残る | 原因断定しない |
| README sync | release 前 | 確認済み / 未確認構成へ反映する | unit_012 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | hardware log template に必要項目が揃っている | new | unit | no | red: `environment` 欄不足。green: docs check で確認 |
| green | matrix に OS、dongle、driver、Switch model、firmware、Pairing、L2CAP、Subcommands、Input reflected がある | new | unit | no | red: `Adapter` / review columns 不足。green: docs check で確認 |
| deferred | `@pytest.mark.bumble` の結果を log に転記できる | characterization | bumble | yes | M2 の adapter run 後に run entry を追加する |
| deferred | pairing / L2CAP run の結果を matrix に反映できる | characterization | hardware | yes | M3 の実機 run 後に run entry と matrix を更新する |
| deferred | subcommand sequence の trace artifact を run entry から辿れる | characterization | hardware | yes | M4 の実機 trace 取得後に artifact path を記録する |
| deferred | Button A 反映結果を matrix に反映できる | characterization | hardware | yes | M5 の入力反映確認後に記録する |
| deferred | reconnect 観測を separate notes として残せる | characterization | hardware | yes | M6 の reconnect 観測後に追記する |

## 8. 設計メモ

- `docs/hardware-test-log.md` は実機観測の正本にする。spec には判断と条件を置き、個別 run の詳細は log に残す。
- run entry には approval を必ず書く。承認がなかった run は実施しない。
- hardware observation は release で「確認済み構成」として使えるが、別構成への保証にはしない。
- cleanup result は成功時も失敗時も書く。入力が残り得る run では neutral と transport close を明記する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `docs/hardware-test-log.md` | new | run entry と matrix |
| `README.md` | modify | 実機検証状態を未記録として明示。release gate 時に確認済み / 未確認構成へ反映する |
| `tests/hardware/README.md` | new | marker 実行結果と `docs/hardware-test-log.md` の対応を明示 |
| `spec/wip/unit_012/INITIAL_RELEASE_GATE.md` | deferred | release gate の証跡照合時に更新する |
| `tests/unit/test_hardware_test_log_docs.py` | new | hardware log template と matrix の docs check |

## 10. 検証

この表は今回の hardware log / matrix 作業で実行または未実行とした gate を示す。

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 41 packages resolved / checked |
| `uv run pytest tests/unit/test_hardware_test_log_docs.py` | pass | 2 passed。run entry template、matrix header、release review 用列を確認した |
| `rg -n "未検証|確認済み|未記録|not run" docs README.md tests\hardware spec` | pass | hardware log、README、hardware test README、関連 spec に未検証 / 未記録 / not run の状態が見えることを確認した |
| `uv run ruff format --check .` | pass | 3 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 3 passed |
| `uv run pytest -m bumble` | not run | この仕様は template / matrix 作成が対象。adapter open は承認対象であり、この作業では実行しない |
| `uv run pytest -m hardware` | not run | 実機 test の実行そのものは対象外。M3 以降の実機 run で記録する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | template 作成では不要。actual entries を作る場合は必要 |
| 承認範囲 | run ごとに adapter open、advertising、pairing、report loop、input 操作、cleanup を明示する |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `docs/hardware-test-log.md`、diagnostics trace |
| cleanup | run entry に実行した cleanup と結果を書く |

## 12. 先送り事項

- `@pytest.mark.bumble` と `@pytest.mark.hardware` の実行結果は、明示承認を受けた M2-M6 の run で `docs/hardware-test-log.md` に追加する。
- README の確認済み / 未確認構成への反映は unit_012 release gate で行う。
- dedicated hardware runner は初期対象外。
- macOS matrix は初期対象外として未検証で残す。
- 複数 firmware の比較は初期 release 後に増やす。

## 13. チェックリスト

このチェックリストは hardware log / matrix 作業の完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] `docs/hardware-test-log.md` の template と matrix を作成した
- [x] docs consistency check を実行し、検証欄を結果で更新した
- [x] hardware run はこの作業では未実行とし、後続 run entry に記録する条件を残した
- [x] 完了条件を満たしたら `spec/complete` へ移動する
