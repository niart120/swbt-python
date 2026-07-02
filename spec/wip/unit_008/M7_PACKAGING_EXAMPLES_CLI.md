# M7 Packaging / Examples / CLI 仕様書

## 1. 概要

### 1.1 目的

`swbt-python` を install 可能な package とし、public import、examples、`swbt-probe` CLI、README、開発者向け手順を整える。M7 では常駐 daemon や GUI を提供しない。CLI は adapter と trace の確認を補助する probe として扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M7 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| naming | package 名、module root、CLI 名 | `spec/initial/naming.md` |
| api | public import と利用例 | `spec/initial/api.md` |
| testing | examples fake transport test、hardware bring-up 手順 | `spec/initial/testing.md` |
| risks | documentation drift、OS / driver 差分、scope creep | `spec/initial/risks.md` |
| completed M5 | 実機で Button A / neutral が確認済み。examples はまだ未整備 | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| hardware log | Windows / CSR8510 A10 / WinUSB / `usb:0` の確認済み構成がある | `docs/hardware-test-log.md` |
| user intent | packaging に際して、Google-style で公開 API の引数、返値、属性、例外境界の docstring を拡充する | active goal |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `pip install swbt-python` | package が install できる | release 前は local build で確認 |
| library user | `from swbt import SwitchGamepad, Button` | public API を import できる | Bumble 型を要求しない |
| developer | `examples/tap_a.py` | 最小利用例が読める | 実行には実機承認が必要 |
| developer | fake example | 実機なしで public API の最小例を CI で確認できる | Bumble 型を公開しない |
| developer | `swbt-probe adapters` | adapter 候補と環境情報を確認できる | adapter open を伴う場合は承認条件を分ける |
| developer | `swbt-probe pair --adapter usb:0 --trace trace.jsonl` | pairing probe と trace 保存ができる | Switch-facing 動作の承認が必要 |

## 2. 対象範囲

- `pyproject.toml` の package metadata と build 確認。
- `swbt.__init__` の public export。
- `examples/tap_a.py`。
- `examples/pairing_probe.py`。
- `examples/hardware_bringup.py`。
- `swbt-probe adapters`。
- `swbt-probe pair --adapter usb:0 --trace trace.jsonl`。
- README の Windows / Linux 注意点、確認済み構成、未確認構成、実機安全境界。
- 開発者向け gate 手順。
- `unit_006` の実機確認結果を README / examples / CLI 説明へ反映する。
- `swbt.__all__` から公開される主要 API の Google-style docstring。

## 3. 対象外

- 常駐 daemon。
- GUI。
- 既存 IPC 互換 server。
- production publish と tag push。
- 高水準 macro scheduler。
- 全 OS / dongle の保証。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/api.md`
- `spec/initial/naming.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`
- `spec/wip/unit_012/INITIAL_RELEASE_GATE.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | M7 は package / docs / CLI surface。protocol 値は既存 milestone の成果を参照する |
| Bumble / transport | required | todo | CLI の adapter probe と pairing probe は Bumble API と version に依存する |
| OS / driver / adapter | required | todo | README と `swbt-probe adapters` は Windows WinUSB / Linux libusb の実態を扱う |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| package build | source tree | wheel / sdist が build できる | `uv build` を想定 |
| public import | installed package | `from swbt import SwitchGamepad, Button` が動く | `py.typed` を含む |
| fake example test | examples | fake transport で実機なし test が通る | CI 対象 |
| hardware example | `examples/hardware_bringup.py` | 実行前承認条件が README から辿れる | 自動実行しない |
| adapters CLI | `swbt-probe adapters` | adapter 候補と環境情報を出す | adapter open の有無を明示 |
| pair CLI | `swbt-probe pair --adapter usb:0 --trace trace.jsonl` | pairing probe を行い trace を保存する | 明示承認が必要 |
| README | documentation | 確認済み構成と未確認構成が分かれている | documentation drift 対策 |
| hardware usage example | approved `usb:0` run | 実行前に承認範囲、artifact、cleanup が分かる | 実行は自動化しない |
| public API docstrings | `swbt.__all__` の主要型と `SwitchGamepad` の操作 | Google-style の `Attributes` / `Args` / `Returns` / `Raises` が公開契約を説明する | packaging 前の API surface 固定 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | package build が成功する | new | unit | no | `uv build` |
| refactor-skipped | source distribution metadata が examples を含む | regression | unit | no | `tests/unit/test_package_metadata.py` で `examples/**` を固定 |
| todo | installed package から `SwitchGamepad`、`Button`、`InputState`、`Stick` を import できる | regression | unit | no | public API |
| refactor-skipped | 公開 API docstring が Google-style で引数、返値、属性、例外境界を説明する | new | unit | no | `tests/unit/test_public_api_docstrings.py` で固定。動作変更なし |
| refactor-skipped | `examples/tap_a.py` の fake variant が実機なしで test できる | new | integration | no | `tests/integration/test_examples.py` で fake transport 実行を固定 |
| refactor-skipped | `swbt-probe adapters --help` が動く | new | unit | no | `tests/unit/test_probe_cli.py` で entry point と help を固定。adapter open なし |
| refactor-skipped | `swbt-probe adapters --json` が adapter を開かず候補 adapter と環境情報を表示する | new | unit | no | `tests/unit/test_probe_cli.py` で固定。Bumble import なし |
| refactor-skipped | `swbt-probe pair --help` が承認境界を読める説明を持つ | new | unit | no | `tests/unit/test_probe_cli.py` で固定。実行はしない |
| refactor-skipped | README に Windows 専用 dongle / WinUSB 注意点がある | regression | unit | no | `tests/unit/test_readme_docs.py` で固定 |
| refactor-skipped | README に確認済み構成と未確認構成が分かれている | regression | unit | no | `tests/unit/test_readme_docs.py` で固定 |
| refactor-skipped | README が `unit_006` 後の Button A / neutral observed-pass を stale な「未記録」と矛盾なく説明する | regression | unit | no | `tests/unit/test_readme_docs.py` で固定 |
| refactor-skipped | examples が `tap(Button.A)` / `neutral()` の最小手順と実機承認境界を分けている | new | integration | no | `examples/tap_a.py`、`examples/pairing_probe.py`、`examples/hardware_bringup.py` を `tests/integration/test_examples.py` で固定 |
| todo | `swbt-probe adapters` が developer machine で adapter 情報を表示する | characterization | bumble | yes | adapter open を伴う場合は承認が必要 |
| todo | `swbt-probe pair` が trace を保存する | characterization | hardware | yes | Switch-facing 動作の承認が必要 |

## 8. 設計メモ

- `swbt-probe` は daemon ではなく手動検証と診断の補助 CLI に留める。
- README では「対応済み構成」と「未確認構成」を分けて書く。未検証環境を暗黙に保証しない。
- production publish、tag push、PyPI upload はこの仕様の実装完了だけでは実行しない。release gate とユーザの明示確認が必要。
- examples は実機向けと fake transport 向けを分け、CI では fake transport 側を検証する。
- README は `docs/hardware-test-log.md` から確認済み構成だけを採用する。現時点では Windows / CSR8510 A10 / WinUSB / `usb:0` の Button A / neutral が確認済みで、Linux / macOS、reconnect、stick semantic reflection は未確認として分ける。
- `swbt-probe pair` は便利な wrapper に留め、実機承認を迂回する環境変数 gate は作らない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `pyproject.toml` | modify | CLI entry point、metadata 確認 |
| `src/swbt/__init__.py` | modify | public export |
| `src/swbt/gamepad.py` | modify | public API docstrings |
| `src/swbt/input.py` | modify | public input value docstrings |
| `src/swbt/diagnostics.py` | modify | public diagnostics value docstrings |
| `src/swbt/probe.py` | new | `swbt-probe` CLI |
| `examples/tap_a.py` | new | Button A example |
| `examples/pairing_probe.py` | new | pairing probe example |
| `examples/hardware_bringup.py` | new | hardware bring-up example |
| `README.md` | modify | install、usage、hardware notes、matrix |
| `tests/unit/` | modify | import / CLI help tests |
| `tests/integration/` | modify | examples fake transport tests |
| `docs/hardware-test-log.md` | reference | README に採用する確認済み構成の source |

## 10. 検証

この表は M7 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv build` | pending | M7 実装後に package build gate として実行する |
| `uv run pytest tests\unit\test_public_api_docstrings.py -q` | pass | 2 passed。公開 API docstring が Google-style section と公開契約 token を持つことを確認した |
| `uv run ruff check src\swbt\gamepad.py src\swbt\input.py src\swbt\diagnostics.py tests\unit\test_public_api_docstrings.py` | pass | 今回追加した docstring と test の lint を確認した |
| `uv run pytest tests\unit\test_probe_cli.py -q` | pass | 2 passed。`swbt-probe` entry point と `adapters --help` が adapter open なしで動くことを確認した |
| `uv run ruff check pyproject.toml src\swbt\probe.py tests\unit\test_probe_cli.py` | pass | CLI entry point、probe module、CLI test の lint を確認した |
| `uv run pytest tests\unit\test_probe_cli.py -q` | pass | 3 passed。`pair --help` が adapter、trace、timeout、Switch-facing 承認境界を説明することを確認した |
| `uv run ruff check src\swbt\probe.py tests\unit\test_probe_cli.py` | pass | `pair --help` 追加後の CLI module と test の lint を確認した |
| `uv run pytest tests\unit\test_probe_cli.py -q` | pass | 4 passed。`adapters --json` が adapter open なしで候補 adapter、platform、Python、Bumble version を出すことを確認した |
| `uv run ruff check src\swbt\probe.py tests\unit\test_probe_cli.py` | pass | `adapters --json` 追加後の CLI module と test の lint を確認した |
| `uv run pytest tests\integration\test_examples.py -q` | pass | 1 passed。`examples/tap_a.py` の `tap_a_once()` が fake transport で Button A press / release report を送ることを確認した |
| `uv run ruff check examples\tap_a.py tests\integration\test_examples.py` | pass | tap_a example と integration test の lint を確認した |
| `uv run pytest tests\unit\test_readme_docs.py -q` | pass | 3 passed。README が確認済み / 未確認構成、専用 dongle / WinUSB 注意点、Button A / neutral 観測を hardware log と矛盾なく説明することを確認した |
| `uv run ruff check tests\unit\test_readme_docs.py` | pass | README docs test の lint を確認した |
| `uv run pytest tests\integration\test_examples.py -q` | pass | 2 passed。`tap_a` fake transport 実行と、`pairing_probe.py` / `hardware_bringup.py --help` の承認境界説明を確認した |
| `uv run ruff check examples\tap_a.py examples\pairing_probe.py examples\hardware_bringup.py tests\integration\test_examples.py` | pass | examples 3 件と integration test の lint を確認した |
| `uv run pytest tests\unit\test_package_metadata.py -q` | pass | 1 passed。`source-include` に `examples/**` が含まれることを確認した |
| `uv run ruff check pyproject.toml tests\unit\test_package_metadata.py` | pass | package metadata test の lint を確認した |
| `uv run pytest tests/unit tests/integration` | pending | M7 実装後に local automated gate として実行する |
| `uv run swbt-probe adapters` | pending-approval | adapter open を伴う場合は承認後に実行する |
| `uv run swbt-probe pair --adapter usb:0 --trace trace.jsonl` | pending-approval | Switch-facing 動作の明示承認後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | CLI adapters は adapter 条件次第。pair / hardware examples は required |
| 承認範囲 | adapter open、HID advertising、pairing、report loop、trace 保存、close のどこまで実行するかを command ごとに明示する |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | CLI output、trace JSON Lines、hardware test log |
| cleanup | neutral、transport close、adapter release、必要なら Switch 側登録解除手順 |

## 12. 先送り事項

- production publish と tag push は release gate と明示確認後に扱う。
- 常駐 daemon と IPC 互換 server は初期対象外のままにする。
- GUI は対象外。
- reconnect / key store は `unit_007`。
- L+R / stick semantic characterization は `unit_013`。

## 13. チェックリスト

このチェックリストは M7 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [ ] package metadata、examples、CLI、README の実装を完了した
- [ ] M7 の build と local automated gate を実行し、検証欄を結果で更新した
- [ ] adapter / Switch-facing CLI 検証は承認、command、cleanup、結果を記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
