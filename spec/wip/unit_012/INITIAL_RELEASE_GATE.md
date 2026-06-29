# Initial Release Gate 仕様書

## 1. 概要

### 1.1 目的

初期 release 前に必要な local gate、fake transport integration、Bumble adapter 観測、少なくとも 1 つの Switch 実機構成での pairing と Button A 反映、README / risks 反映を確認する。publish や tag push はこの仕様の範囲外で、実行には別途ユーザの明示確認を必要とする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | release gate の項目 | `spec/initial/roadmap.md` |
| testing | CI 方針、hardware matrix | `spec/initial/testing.md` |
| risks | known risks と README 反映 | `spec/initial/risks.md` |
| naming | package / import / CLI 名の確認 | `spec/initial/naming.md` |
| AGENTS | 標準 gate と実機安全境界 | `AGENTS.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | release 前 | unit tests、fake integration、static check が通っている | 実行結果を記録 |
| maintainer | hardware readiness | Windows + 専用 USB dongle の adapter open が確認済み | hardware log が source |
| maintainer | Switch readiness | 少なくとも 1 構成で pairing と Button A 反映が確認済み | firmware / dongle 条件付き |
| reviewer | README / risks | 対応済み構成、未確認構成、既知リスクが反映済み | 未検証を隠さない |
| maintainer | publish | publish 前に明示確認で停止する | この仕様では実行しない |

## 2. 対象範囲

- unit tests。
- fake transport integration tests。
- static type check、lint、format。
- package build。
- Windows + 専用 USB Bluetooth dongle adapter open 観測。
- 少なくとも 1 つの Switch 実機構成で pairing と Button A 反映観測。
- README の対応済み / 未確認構成。
- `risks.md` の既知リスク反映。
- `docs/hardware-test-log.md` と release checklist の照合。

## 3. 対象外

- production publish。
- tag push。
- PyPI trusted publishing 設定。
- 全 OS / dongle / firmware の保証。
- release automation の作成。
- `pypi-release` skill 作成。

## 4. 関連 docs

- `spec/initial/roadmap.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/initial/naming.md`
- `spec/wip/unit_008/M7_PACKAGING_EXAMPLES_CLI.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | release blocker になる protocol 値は監査済み fixture と unit test で固定されている必要がある |
| Bumble / transport | required | todo | adapter open、pairing、input reflection は Bumble version と trace 付きで確認する |
| OS / driver / adapter | required | todo | README に出す確認済み構成は hardware log からのみ採用する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| local static gate | source tree | format、lint、type check が通る | AGENTS の標準 gate |
| unit gate | tests/unit | protocol core と public import が通る | M0-M1 |
| integration gate | tests/integration | fake transport API / report loop が通る | CI 必須 |
| package gate | build | wheel / sdist が build できる | M7 |
| adapter gate | hardware log | Windows + 専用 USB dongle で adapter open 確認済み | `@pytest.mark.bumble` または manual |
| Switch gate | hardware log | 少なくとも 1 構成で pairing と Button A 反映確認済み | `@pytest.mark.hardware` または manual |
| docs gate | README / risks | 対応済み構成、未確認構成、既知リスクが一致 | documentation drift 対策 |
| publish stop | release ready | publish / tag push 前に停止して確認を求める | この仕様では実行しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `uv run ruff format --check .` が通る | regression | unit | no | local static gate |
| todo | `uv run ruff check .` が通る | regression | unit | no | local static gate |
| todo | `uv run ty check --no-progress` が通る | regression | unit | no | type gate |
| todo | `uv run pytest tests/unit` が通る | regression | unit | no | M0-M1 |
| todo | `uv run pytest tests/integration` が通る | regression | integration | no | fake transport |
| todo | package build が通る | regression | unit | no | M7 |
| todo | Windows + 専用 USB dongle で adapter open が hardware log に記録されている | regression | bumble | yes | release gate |
| todo | 1 つ以上の Switch 実機構成で pairing と Button A 反映が記録されている | regression | hardware | yes | release gate |
| todo | README に対応済み構成と未確認構成が分かれている | regression | unit | no | docs gate |
| todo | `spec/initial/risks.md` に release 時点の既知リスクが反映されている | regression | unit | no | docs gate |

## 8. 設計メモ

- hardware gate は CI 必須にしない。ただし release 判断では evidence として必須にする。
- publish、tag push、PyPI upload はこの spec の作業範囲に含めない。実行前に明示確認で停止する。
- README の確認済み構成は `docs/hardware-test-log.md` の具体的 run からのみ書く。
- `pypi-release` skill は現段階では作らない。packaging と publish 方針が固まった後に別途判断する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `README.md` | modify | release readiness、確認済み / 未確認構成 |
| `spec/initial/risks.md` | modify | release 時点の既知リスク |
| `docs/hardware-test-log.md` | modify | release gate evidence |
| `pyproject.toml` | modify | build / package metadata |
| `tests/unit/` | modify | release blocking unit tests |
| `tests/integration/` | modify | fake transport release gate |

## 10. 検証

この表は initial release 判定時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pending | release 判定時に依存同期として実行する |
| `uv run ruff format --check .` | pending | release 判定時の static gate |
| `uv run ruff check .` | pending | release 判定時の lint gate |
| `uv run ty check --no-progress` | pending | release 判定時の type gate |
| `uv run pytest tests/unit` | pending | release 判定時の unit gate |
| `uv run pytest tests/integration` | pending | release 判定時の fake transport integration gate |
| `uv build` | pending | M7 実装後の package build gate |
| `uv run pytest -m bumble` | pending-approval | adapter 承認後に release hardware evidence として実行する |
| `uv run pytest -m hardware` | pending-approval | Switch 実機承認後に release hardware evidence として実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for release hardware evidence |
| 承認範囲 | adapter open、HID advertising、pairing、subcommand handling、periodic report loop、Button A、neutral、close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | hardware test log、diagnostics trace、test output |
| cleanup | neutral、report loop 停止、transport close、adapter release。Switch 側登録削除が必要なら記録 |

## 12. 先送り事項

- production publish と tag push。
- PyPI trusted publishing 設定。
- release automation。
- Linux / macOS の release guarantee。

## 13. チェックリスト

このチェックリストは initial release gate の完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] release 判定に必要な local / static / build gate を実行し、検証欄を結果で更新した
- [ ] adapter open と Switch 実機の release evidence を `docs/hardware-test-log.md` から確認した
- [ ] README と `spec/initial/risks.md` を release 時点の確認済み / 未確認状態に更新した
- [ ] publish / tag push 前にユーザの明示確認で停止した
