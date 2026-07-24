# 具象 Controller Module 分離 仕様書

## 1. 概要

### 1.1 目的

`src/swbt/gamepad/core.py` に残る6個の具象controllerを
`src/swbt/gamepad/controllers.py`へ移す。正式な公開import、型階層、
constructor signature、実行時の振る舞いを維持し、責務を表さない`core.py`を削除する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #125 | 具象controllerを`controllers.py`へ移す | `https://github.com/niart120/swbt-python/issues/125` |
| user decision | Issue #118と履歴を分け、別issue / specでmodule移動を実施する | conversation |
| Issue #118 / PR #124 | 公開共通実装をinterface側へ統合し、`core.py`を6具象型だけにした | `spec/complete/unit_074/PUBLIC_GAMEPAD_IMPLEMENTATION_OWNERSHIP.md` |
| rearchitecture target | 具象controllerを`controllers.py`に置き、最終状態で`core.py`を残さない | `spec/rearchitecture/02-as-is-to-be.md` |
| test boundary cleanup | 公開契約を検証し、private file配置を恒久契約にしない | `spec/complete/unit_073/TEST_CONTRACT_BOUNDARY_CLEANUP.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library利用者 | `swbt`から6具象型をimportする | 移動前と同じclassを利用できる | 正式な公開経路を維持する |
| package利用者 | `swbt.gamepad`から6具象型をimportする | root exportと同じclassを得る | package exportを維持する |
| maintainer | gamepad packageのsourceを読む | interfaceと具象controllerの責務がfile名から判別できる | 互換用の空moduleを残さない |
| 既存deep import利用者 | `swbt.gamepad.core`をimportする | moduleは存在しない | 文書化された公開APIではない |

## 2. 対象範囲

- `ProController`、`JoyConL`、`JoyConR`を`controllers.py`へ移す。
- `DirectProController`、`DirectJoyConL`、`DirectJoyConR`を`controllers.py`へ移す。
- `swbt.gamepad`の再export元を`controllers.py`へ変更する。
- 現行test fixtureと未完了specの実装path参照を新しいmodule名へ追従させる。
- `core.py`を削除し、互換re-exportを置かない。
- classの`__module__`が`swbt.gamepad.controllers`へ変わることを意図した結果とする。

## 3. 対象外

- `SwitchGamepad`、`PeriodicSwitchGamepad`、`DirectSwitchGamepad`の移動。
- 6具象型の継承、constructor、`create_profile()`、lifecycle、入力、状態、例外の変更。
- runtime、protocol、transportの責務変更。
- `interface.py`のrenameまたは再分割。
- 過去の完了specに記録された当時の`core.py` pathの一括書換え。
- protocol bytes、report timing、Bumble adapter、Switch実機動作の変更。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/testing.md`
- `spec/rearchitecture/02-as-is-to-be.md`
- `spec/rearchitecture/04-runtime-profile-transport-details.md`
- `spec/complete/unit_071/CONTROLLER_CONSTRUCTION_PATH.md`
- `spec/complete/unit_073/TEST_CONTRACT_BOUNDARY_CLEANUP.md`
- `spec/complete/unit_074/PUBLIC_GAMEPAD_IMPLEMENTATION_OWNERSHIP.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | protocol builder、parser、定数を変更しない |
| Bumble / transport | not applicable | not applicable | transport API、factory、Bumble実装を変更しない |
| OS / driver / adapter | not applicable | not applicable | adapterを開かず、driver仮定を追加しない |
| module ownership | required | done | Issue #125、PR #124後のsource、公開API正本、rearchitecture targetを照合した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| root import | `from swbt import ProController`などを実行する | 6具象型をimportできる | class identityを維持する |
| package import | `from swbt.gamepad import ProController`などを実行する | root importと同じclassを得る | `__all__`を維持する |
| concrete module import | `from swbt.gamepad.controllers import ProController`などを実行する | root / package exportと同じclassを得る | 新しい定義元 |
| legacy deep import | `import swbt.gamepad.core`を実行する | `ModuleNotFoundError`になる | 互換moduleを残さない |
| public contract | 6具象型の型階層とsignatureを調べる | 移動前と一致する | `__module__`だけ変更する |
| runtime behavior | fake transportでlifecycleと入力を実行する | 移動前と同じ結果になる | 既存integration testで確認する |
| lazy import | `import swbt`を実行する | Bumble moduleを解決しない | 現行boundary testを維持する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | root / packageの公開export、型階層、signatureを維持する | characterization | unit | no | 変更前後のfocused 73件とfull unit 439件がpass |
| refactor-done | `controllers`から得る6具象型がroot / package exportと同一である | regression | unit | no | 定義moduleとclass identityをone-off commandで確認した |
| refactor-done | lifecycle、profile作成、Periodic / Direct入力契約を維持する | regression | integration | no | 変更前後のfocused 152件とfull integration 154件がpass |
| refactor-done | `core.py`と現行実装参照を残さない | regression | unit / review | no | source scanとarchitecture guardrail pathを更新した |
| refactor-done | 公開importがBumbleを解決しない | regression | unit | no | full unitの既存boundary testがpass |

このunitはgreen済みの振る舞いを保つ構造変更である。存在しない新機能を表すための
人工的なred testは追加せず、baseline green、module移動、同じtestのgreenを確認する。

## 8. 文書検証計画

README、利用者向けdocs、公開API docstring、release notesは変更しない。
公開API正本はroot importを規定しており、この契約も変更しない。
作業仕様と未完了specのpathだけを実装と照合する。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `unit_075` | maintainer / module移動の判断と検証記録 | Issue #125、source、test結果 | diff review | done | none |
| `unit_057` | maintainer / 後続作業の対象path | 移動後source | path scan | done | none |

## 9. 設計メモ

- `swbt`直下を公開APIの正本とし、`swbt.gamepad`の既存再exportも維持する。
- `swbt.gamepad.core`はREADME、`docs/api.md`、`spec/initial/api.md`で案内していない。
  pre-1.0の内部deep importへ互換moduleを追加すると、削除目的と保守対象が残るため採用しない。
- `__module__`変更はrepr、pickle、API文書生成へ影響し得る。現状の公開文書はroot importを
  案内し、pickle互換を保証していないため、`controllers`を新しい定義moduleとして採用する。
- 完了spec内のpathは、そのunit実施時点の根拠である。現在のsourceへ一括変換しない。
- source配置だけを検査する新しい恒久pytestは追加しない。既存の意味あるarchitecture
  guardrailが許可pathを持つ箇所だけ更新し、移動結果はsource scanと公開import確認で検証する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/controllers.py` | new | 6具象controllerの定義 |
| `src/swbt/gamepad/core.py` | delete | 具象controllerを移動しmoduleを削除 |
| `src/swbt/gamepad/__init__.py` | modify | 6具象型のimport元を更新 |
| `tests/unit/test_protocol_profile.py` | modify | controller kind分岐の許可pathを更新 |
| `spec/wip/unit_057/PAIRING_PROFILE_CONTROLLER_KIND.md` | modify | 未完了作業の対象pathを更新 |
| `spec/wip/unit_075/CONCRETE_CONTROLLER_MODULE.md` | new | scope、判断、検証結果を記録 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_api_boundary.py tests/unit/test_protocol_profile.py -q` | pass | 変更前後とも73 passed |
| `uv run pytest tests/integration/test_pairing_profile.py tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 変更前後とも152 passed |
| `uv run python -c "<public import identity and module check>"` | pass | root、package、`controllers`の6型が同一。定義module変更と`core`不在を確認 |
| `uv sync --dev` | pass | dev環境を同期 |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit --basetemp=tmp/pytest-unit-075-full` | pass | 439 passed |
| `uv run pytest tests/integration --basetemp=tmp/pytest-integration-075-full` | pass | 154 passed |
| `uv run --group docs mkdocs build --strict` | pass | strict build成功 |
| `git diff --check` | pass | whitespace errorなし |

最初の標準pytest commandは、先行したfocused runが管理環境内の固定
`--basetemp=tmp/pytest`を再利用不能なACLで残したため、setup時に`WinError 5`になった。
assertionの失敗ではない。未使用のbasetempを明示して同じtest treeを全件実行し、
unit 439件とintegration 154件の成功を確認した。fresh runner上の標準commandはPRのCIで
確認する。

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | adapter、Bumble、Switch-facing commandを実行しない |
| adapter | none |
| 実行遮断 | 環境変数による遮断は採用しない。`bumble` / `hardware` markerを実行対象から除外する |
| log / artifact | local unit / integration / docs build output |
| cleanup | pytestとMkDocsが作成する通常の一時・site出力だけを対象とする |

## 13. 先送り事項

- none

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test Listまたは文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
