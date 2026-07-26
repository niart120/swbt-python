# Python 3.13 最低実行バージョン仕様書

## 1. 概要

### 1.1 目的

Windows上のPython 3.12では、`time.monotonic_ns()`と`asyncio` event loopが
`GetTickCount64()`の15.625 ms分解能に制約され、8 ms周期のquaternion IMU入力に
カクつきが発生した。report生成やevent loopへ個別の時計補正を入れず、最低実行
バージョンをPython 3.13へ引き上げる。CIでは最低バージョンの3.13と次の安定版
3.14を検証する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | 8 ms送信時の周期的なカクつきとHCI credit仮説 | `https://github.com/niart120/swbt-python/issues/152` |
| hardware observation | Python 3.12.10では8 ms区間がカクつき、Python 3.13.5では同条件でカクつきなし | `spec/hardware-test-log.md` |
| local characterization | Python 3.12.10の`monotonic_ns()`は15.625 ms分解能、Python 3.13.5は100 ns分解能 | 2026-07-27のruntime比較 |
| user decision | clock実装を変更せず、最低Pythonを3.13へ引き上げ、CIへ3.14を追加する | 2026-07-27 |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| package利用者 | Python 3.13以上でinstallする | package metadataが対応runtimeを明示する | Python 3.12は対応対象外 |
| contributor | CIを実行する | Python 3.13 / 3.14のunit、integration、buildを検証する | hardware gateは含めない |
| Direct / Periodic利用者 | 8 ms周期の入力を扱う | CPython 3.13以降の高分解能なmonotonic clockを利用する | OS負荷による起床遅延までは保証しない |

## 2. 対象範囲

- `requires-python`を`>=3.13`へ変更する。
- Python classifierを3.13 / 3.14へ揃える。
- RuffとtyのPython対象バージョンを3.13へ変更する。
- CI matrixをPython 3.13 / 3.14へ変更する。
- Bumble canaryを最低対応バージョンのPython 3.13で実行する。
- READMEと実機準備文書の必要Pythonバージョンを3.13へ変更する。
- lockfileのPython要件を更新する。
- package versionを0.6.0へ更新し、互換性変更と実機確認範囲をrelease notesへ記載する。
- Issue #152の実験用HCI / USB probeと実機観測を記録する。

## 3. 対象外

- `ReportSender`、`ReportLoop`、Bumble、`asyncio` event loopのclock変更。
- Python 3.12互換性の維持。
- 8 ms周期やOS scheduler精度の保証。
- HID report layout、IMU packing、既定report周期の変更。
- Bluetooth air capture、別adapter、別OS、別Switch firmwareへの一般化。
- TestPyPI / PyPI publish、tag、GitHub Release作成。

## 4. 関連 docs

- `README.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_049/IMU_SESSION_AND_ENCODING_REDESIGN.md`
- `spec/complete/unit_065/PERIODIC_DEADLINE_SCHEDULER.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not required | done | report生成実装とbyte layoutは変更しない |
| Bumble / transport | required | done | Bumble 0.0.230 / 0.0.233差では症状が変わらず、credit待ち最大0を実測した |
| Python clock | required | done | 対象Windows環境で3.12.10と3.13.5のclock implementationと分解能を取得した |
| OS / driver / adapter | required for observation | done | Windows 11 / CSR8510 A10 / WinUSB / `usb:0`で比較した。別環境へ一般化しない |

### 根拠監査の結果

| 項目 | 値 / 判断 | 根拠分類 | source | status |
|---|---|---|---|---|
| Python 3.12.10 Windows monotonic | `GetTickCount64()`、分解能15.625 ms | runtime fact | `time.get_clock_info("monotonic")` | done |
| Python 3.13.5 Windows monotonic | `QueryPerformanceCounter()`、分解能100 ns | runtime fact | `time.get_clock_info("monotonic")` | done |
| Python / Bumble比較 | 3.12.10ではBumble 0.0.230 / 0.0.233の両方でカクつき、3.13.5 / 0.0.230ではカクつきなし | hardware observation | 実機matrix | done |
| HCI credit | 対象runのBumble queue待機packet最大0 | hardware observation | HCI credit probe | done |
| clock修正案 | `ReportSender`と`ReportLoop`の`perf_counter_ns()`化でPeriodicは滑らかになったが、Directはcaller schedulerの補正も必要だった | experimental observation | 修正後route比較 | done |
| final disposition | clock修正を製品へ採用せず、Python 3.13を最低対応runtimeとする | decision | user decision | done |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| package runtime floor | package metadataを読む | `requires-python`が`>=3.13` | Python 3.12へのinstallを拒否する |
| supported classifiers | PyPI metadataを読む | Python 3.13 / 3.14を列挙し、3.12を列挙しない | 実機互換性の保証ではない |
| CI matrix | GitHub Actions CIを実行する | Ubuntu / macOSの各OSで3.13 / 3.14を検証する | Bumble / hardware testは実行しない |
| static target | Ruff / tyを実行する | 最低対応バージョン3.13を基準に解析する | 新しい構文の採用を要求しない |
| clock implementation | controllerを利用する | 既存の`monotonic_ns()`とclock注入境界を維持する | clockのglobal差し替えを行わない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | package metadataとstatic targetがPython 3.13以上を表す | regression | unit | no | REDは`requires-python >=3.12`で失敗。metadata変更後GREEN |
| refactor-skipped | CIがPython 3.13 / 3.14を実行する | regression | unit | no | REDはmatrix 3.12 / 3.13で失敗。workflow変更後GREEN |
| green | Python 3.13で標準gateが成功する | compatibility | gate | no | Python 3.13.5でstatic、451 unit、165 integration、buildがpass |
| green | Python 3.14でunit / integration / buildが成功する | compatibility | gate | no | Python 3.14.6を明示し、static、451 unit、165 integration、buildがpass |

## 8. 文書検証計画

READMEの対象読者はpackage利用者であり、install前に必要なPythonバージョンを判断できる
ことを確認する。正本は`pyproject.toml`の`requires-python`とする。README以外の公開
文書にはPython 3.12要件がないことを検索し、`docs-quality-review`で正本との一致を
確認する。

## 9. 設計メモ

- Python 3.13の採用理由は、今回のWindows実機で確認したclock分解能と画面観測である。
- Python 3.13でも`asyncio.sleep(0.008)`の正確な起床や125 Hzを保証しない。
- 3.14のCI追加は互換性検査であり、3.14固有機能の採用を意味しない。
- clock注入引数は決定的test用の内部境界として維持する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `pyproject.toml` | modify | version 0.6.0、runtime floor、classifier、Ruff / ty target |
| `uv.lock` | modify | version 0.6.0、runtime floor |
| `.github/workflows/ci.yml` | modify | Python 3.13 / 3.14 matrix |
| `.github/workflows/bumble-canary.yml` | modify | Python 3.13 |
| `tests/unit/test_ci_workflow.py` | modify | CI matrix契約 |
| `tests/unit/test_package_metadata.py` | modify | package / static target契約 |
| `README.md` | modify | 必要Pythonバージョン |
| `docs/hardware.md` | modify | 実機準備の必要Pythonバージョン |
| `docs/release-notes.md` | modify | v0.6.0の互換性変更と実機確認範囲 |
| `tools/hci_credit_gyro_probe.py` | new | Issue #152実験用probe |
| `spec/hardware-test-log.md` | modify | 実験結果と不採用判断 |
| `spec/complete/unit_087/PYTHON_313_RUNTIME_FLOOR.md` | new | 完了した作業仕様 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_ci_workflow.py tests/unit/test_package_metadata.py -q` | red, expected | CI matrixと`requires-python`が旧3.12境界のため2 failed、4 passed |
| 同focused testのGREEN再実行 | passed | 6 passed |
| `uv lock` | passed | 52 packages resolved |
| `uv sync --dev --python 3.13` | passed | Python 3.13.5、40 packages checked |
| Python 3.13.5 `ruff format --check` / `ruff check` / `ty check` | passed | 107 files formatted、lint / type errorなし |
| Python 3.13.5 `pytest tests/unit` | passed | 451 passed |
| Python 3.13.5 `pytest tests/integration` | passed | 165 passed |
| Python 3.13.5 `uv build` | passed | sdist / wheel生成 |
| `uv sync --dev --python 3.14` | passed | CPython 3.14.6を取得し、40 packages installed |
| `uv run --python 3.14 ruff format --check .` / `ruff check .` / `ty check --no-progress` | passed | runtimeを明示し、format / lint / type errorなし |
| `uv run --python 3.14 pytest tests/unit` | passed | Python 3.14.6、451 passed |
| `uv run --python 3.14 pytest tests/integration` | passed | Python 3.14.6、165 passed |
| `uv build --python 3.14` | passed | sdist / wheel生成。0.5.4 wheel metadataは`Requires-Python: >=3.13` |
| runtime指定なしの並列`uv run`による3.14検証 | invalid, rerun | `.python-version`の3.13を再選択したため判定に使用せず、全commandへ`--python 3.14`を明示して再実行 |
| `uv lock --check` | passed | 52 packages resolved |
| `git diff --check` | passed | whitespace errorなし |
| `uv run --python 3.13 --group docs mkdocs build --strict` | passed | 公開docsをstrict modeで生成 |
| v0.6.0 release gate: `uv sync --dev --group docs --python 3.13` | passed | local packageを0.6.0へ更新 |
| v0.6.0 release gate: Ruff / ty / unit / integration / MkDocs | passed | 451 unit、165 integration、static、docs strict build |
| `uv build` | passed | `swbt_python-0.6.0` wheel / sdistを生成 |
| `uvx --from twine twine check --strict dist\swbt_python-0.6.0-py3-none-any.whl dist\swbt_python-0.6.0.tar.gz` | passed | wheel / sdistともにPASSED |

### Docs Quality Review

- audience / task: package利用者がinstallまたは実機準備前に最低Pythonバージョンを判断する。
- documents: `README.md`、`docs/hardware.md`、`docs/release-notes.md`
- sources checked: `pyproject.toml`のversion / `requires-python`、classifiers、CI matrix、`v0.5.4..HEAD`と未コミット差分、`spec/hardware-test-log.md`
- must-fix: なし
- disposition: 利用要件をPython 3.13へ揃え、v0.6.0 release notesの先頭に破壊的変更、移行操作、実装非変更、CI範囲、実機確認と未確認範囲を記載した。
- verification: `uv run --python 3.13 --group docs mkdocs build --strict`がpass。
- remaining risk: Python 3.14の実機互換性は未検証であり、READMEでは保証していない。

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 今回の設定変更後実機検証 | not required |
| 理由 | 製品report / transport実装を変更せず、採用判断の根拠となる実機比較は完了済み |
| 過去の承認範囲 | dedicated `usb:0`、既存profile active reconnect、Direct / Periodic正Z yaw、neutral close、adapter release |
| artifact | `tmp/hardware/issue_152/credit-gyro-20260727/` |

## 13. 先送り事項

- Python 3.14でのSwitch実機検証は未実行。今回のCI追加は実機なしの互換性gateに限る。
- versionを0.6.0へ更新し、release notesを追加した。tag、PyPI / TestPyPI publish、GitHub Releaseはrelease実行時に扱う。
- 別OSにおける8 ms周期の実機表示は未検証。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test Listを更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] docs-quality-reviewを完了した
