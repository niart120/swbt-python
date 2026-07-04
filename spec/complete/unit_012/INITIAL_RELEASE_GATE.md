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
| completed M5 | Windows / CSR8510 A10 / WinUSB / `usb:0` で pairing、full handshake、Button A、neutral を確認済み | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| completed post-M5 | Windows / CSR8510 A10 / WinUSB / `usb:0`、Switch 2 / firmware 22.1.0 で D-pad と left / right stick の反映を確認済み | `spec/complete/unit_013/POST_M5_INPUT_SEMANTIC_CHARACTERIZATION.md` |
| hardware log | release hardware evidence の正本 | `docs/hardware-test-log.md` |

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
- GitHub Actions による pull request / main push の automated gate。
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
- `spec/complete/unit_008/M7_PACKAGING_EXAMPLES_CLI.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | observed-pass for release minimum | `unit_006` post-handshake run で A `08 00 00` と neutral `00 00 00` の `0x30` report が Switch UI 反映まで確認済み。`unit_013` で D-pad と left / right stick の意味反映も確認済み |
| Bumble / transport | required | observed-pass for release minimum | adapter open、HID advertising、pairing / L2CAP、full observed handshake、Button A reflection は `docs/hardware-test-log.md` に記録済み。active bond reuse reconnect は `unit_007` |
| OS / driver / adapter | required | observed-pass for Windows `usb:0` | README に出せる確認済み構成は Windows / CSR8510 A10 / WinUSB / Bumble 0.0.230 / `usb:0` / Switch 2 / firmware 22.1.0 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| local static gate | source tree | format、lint、type check が通る | AGENTS の標準 gate |
| unit gate | tests/unit | protocol core と public import が通る | M0-M1 |
| integration gate | tests/integration | fake transport API / report loop が通る | CI 必須 |
| package gate | build | wheel / sdist が build できる | M7 |
| CI gate | GitHub Actions | static gate、unit tests、fake integration、package build が pull request と main push で実行される | `bumble` / `hardware` marker は対象外 |
| adapter gate | hardware log | Windows + 専用 USB dongle で adapter open 確認済み | `@pytest.mark.bumble` または manual |
| Switch gate | hardware log | 少なくとも 1 構成で pairing と Button A 反映確認済み | `@pytest.mark.hardware` または manual |
| docs gate | README / risks | 対応済み構成、未確認構成、既知リスクが一致 | documentation drift 対策 |
| publish stop | release ready | publish / tag push 前に停止して確認を求める | この仕様では実行しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | `uv run ruff format --check .` が通る | regression | unit | no | 2026-07-04 に 68 files already formatted |
| done | `uv run ruff check .` が通る | regression | unit | no | 2026-07-04 に pass |
| done | `uv run ty check --no-progress` が通る | regression | unit | no | 2026-07-04 に pass |
| done | `uv run pytest tests/unit` が通る | regression | unit | no | 2026-07-04 に 163 passed |
| done | `uv run pytest tests/integration` が通る | regression | integration | no | 2026-07-04 に 55 passed |
| done | package build が通る | regression | unit | no | 2026-07-04 に sdist / wheel build pass |
| done | GitHub Actions CI が pull request / `main` push で local gate 相当を実行する | regression | integration | no | `.github/workflows/ci.yml` で追加。PR check の通過は merge 前に確認する |
| observed-pass | Windows + 専用 USB dongle で adapter open が hardware log に記録されている | regression | bumble | yes | `docs/hardware-test-log.md` の unit_003 / unit_006 entries に `usb:0`、CSR8510 A10、WinUSB、Bumble 0.0.230 を記録済み |
| observed-pass | 1 つ以上の Switch 実機構成で pairing と Button A 反映が記録されている | regression | hardware | yes | 2026-07-02 post-handshake input run で full observed handshake、Button A UI 反映、neutral 後の残留なしを確認 |
| green | README に対応済み構成と未確認構成が分かれている | regression | unit | no | `tests/unit/test_readme_docs.py` で固定 |
| green | `spec/initial/risks.md` に release 時点の既知リスクが反映されている | regression | unit | no | `tests/unit/test_release_gate_docs.py` で固定 |
| green | README の「確認済み構成はまだありません」を unit_006 後の hardware log と整合させる | regression | unit | no | README は確認済み構成を記載し、stale phrase が残っていないことを test で固定 |
| green | Switch model / firmware の記録有無を README / risks / matrix で隠さない | regression | docs | no | 現在の release gate 証拠は Switch 2 / firmware 22.1.0。別構成は未確認として分ける |

## 8. 設計メモ

- hardware gate は CI 必須にしない。ただし release 判断では evidence として必須にする。
- publish、tag push、PyPI upload はこの spec の作業範囲に含めない。実行前に明示確認で停止する。
- README の確認済み構成は `docs/hardware-test-log.md` の具体的 run からのみ書く。
- `pypi-release` skill は現段階では作らない。packaging と publish 方針が固まった後に別途判断する。
- `unit_006` により release minimum の Button A / neutral evidence は揃った。`unit_013` により Switch 2 / firmware 22.1.0 の追加入力意味検証も揃った。
- release text では確認済み構成を Windows / CSR8510 A10 / WinUSB / `usb:0` / Bumble 0.0.230 / Switch 2 / firmware 22.1.0 に限定し、別 firmware と別 dongle は未確認として扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `README.md` | modify | release readiness、確認済み / 未確認構成 |
| `spec/initial/risks.md` | modify | release 時点の既知リスク |
| `docs/hardware-test-log.md` | modify | release gate evidence |
| `.github/workflows/ci.yml` | add | pull request / `main` push の automated gate |
| `pyproject.toml` | modify | build / package metadata |
| `tests/unit/` | modify | release blocking unit tests |
| `tests/integration/` | modify | fake transport release gate |

## 10. 検証

この表は initial release 判定時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 2026-07-04、Windows、Python 3.13.5。41 packages resolved / checked |
| `uv run ruff format --check .` | pass | 2026-07-04。68 files already formatted |
| `uv run ruff check .` | pass | 2026-07-04。All checks passed |
| `uv run ty check --no-progress` | pass | 2026-07-04。All checks passed |
| `uv run pytest tests/unit` | pass | 2026-07-04。163 passed |
| `uv run pytest tests/integration` | pass | 2026-07-04。55 passed |
| `uv build` | pass | 2026-07-04。sandbox では PyPI access 制限で失敗後、network 許可付きで sdist / wheel build pass |
| GitHub Actions `CI` | pending-remote | pull request の required check として merge 前に確認する |
| `uv run pytest -m bumble` | not run | 新規 adapter run はこの unit の最終 docs gate では不要。既存の承認済み adapter / hardware log を release evidence として参照 |
| `uv run pytest -m hardware` | not run | 新規 Switch-facing run はこの unit の最終 docs gate では不要。`unit_006` と `unit_013` の承認済み実機観測を release evidence として参照 |
| GitHub Actions `CI` for PR #13 | pass | Python 3.12 / 3.13 pass。unit_006 merge 前に確認済み |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-post-handshake-input --log-file .pytest_cache\hardware\unit_006\20260702-post-handshake-input\pytest-debug.log --log-file-level=DEBUG -q -s` | observed-pass | 1 passed / 1 warning in 9.45s。full observed handshake、Button A UI 反映、neutral 後の入力残りなしを記録 |
| `uv run pytest tests\unit\test_readme_docs.py tests\unit\test_hardware_test_log_docs.py tests\unit\test_release_gate_docs.py -q` | pass | 2026-07-04。8 passed。README、hardware matrix、risks の release gate 境界を確認 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for release hardware evidence。この unit の最終 docs gate では新規実機 command を実行せず、完了済み log を照合する |
| 承認範囲 | 新規実行なし。根拠として参照する既存 run は adapter open、HID advertising、pairing、subcommand handling、periodic report loop、Button A、neutral、close を含む |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | hardware test log、diagnostics trace、test output |
| cleanup | neutral、report loop 停止、transport close、adapter release。Switch 側登録削除が必要なら記録 |

## 12. 先送り事項

- production publish と tag push。
- PyPI trusted publishing 設定。
- release automation。
- Linux / macOS の release guarantee。
- CSR8510 A10 以外の dongle と Switch 2 / firmware 22.1.0 以外の firmware matrix 拡張。
- pairing-free incoming bond reuse。

## 13. チェックリスト

このチェックリストは initial release gate の完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] GitHub Actions CI で static / unit / fake integration / build gate を自動化した
- [x] release 判定に必要な local / static / build gate を実行し、検証欄を結果で更新した
- [x] adapter open と Switch 実機の release evidence を `docs/hardware-test-log.md` から確認した
- [x] README と `spec/initial/risks.md` を release 時点の確認済み / 未確認状態に更新した
- [x] publish / tag push はこの unit で実行せず、別途ユーザの明示確認が必要な先送り事項として記録した
