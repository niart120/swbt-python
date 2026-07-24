# Public Gamepad 実装所有者統合 仕様書

## 1. 概要

### 1.1 目的

`SwitchGamepad`、`PeriodicSwitchGamepad`、`DirectSwitchGamepad` の公開型階層と
6具象コントローラーの公開契約を維持したまま、lifecycle、connection、意味的入力、
status、snapshot の実装と `ControllerRuntime` への委譲を `SwitchGamepad` に集約する。
公開ABCとprivate runtime-backed基底に重複しているmethod定義、docstring、薄い中間階層を
削除する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #118 | 公開gamepad実装の所有者を一か所にする | `https://github.com/niart120/swbt-python/issues/118` |
| 親 Issue #114 | 不要な抽象化と未使用経路を段階的に削除する | `https://github.com/niart120/swbt-python/issues/114` |
| user decision | `SwitchGamepad` は第三者が独自実装する拡張点ではなく、library提供controllerを受け取る公開共通型とする | conversation |
| user decision | 6具象クラスの `controllers.py` 移動は Issue #118 完了後の別specへ分離する | conversation |
| 依存 Issue #117 | connection workflowをruntimeへ統合済み | `spec/complete/unit_072/CONNECTION_RUNTIME_INTEGRATION.md` |
| test boundary cleanup | private owner typeを恒久テストで固定しない | `spec/complete/unit_073/TEST_CONTRACT_BOUNDARY_CLEANUP.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| type consumer | `SwitchGamepad`、`PeriodicSwitchGamepad`、`DirectSwitchGamepad` を型注釈に使う | 既存の公開継承関係とabstract性を維持する | 第三者実装用のruntime非依存ABCにはしない |
| Periodic利用者 | 3周期送信型を生成し、`apply()`と意味的入力を呼ぶ | constructor signature、local commit、周期送信契約を維持する | `report_period_us`を受け取る |
| Direct利用者 | 3直接送信型を生成し、`send()`と意味的入力を呼ぶ | constructor signature、送信成功後commitを維持する | `report_period_us`を受け取らない |
| maintainer | 公開methodの実装とdocstringを確認する | 共通methodの実装所有者が`SwitchGamepad`だけである | private owner identityをpytest契約にしない |
| import利用者 | `swbt`、`swbt.gamepad`、既存submoduleから公開型をimportする | Issue #118ではmodule pathとroot exportを維持する | module移動は後続spec |

## 2. 対象範囲

- `SwitchGamepad` が `ControllerRuntime` への参照と共通public methodの実装を所有する。
- `SwitchGamepad` のasync context manager実装を1か所に維持する。
- `PeriodicSwitchGamepad.apply()` と `DirectSwitchGamepad.send()` の実装を各公開型へ置く。
- `create_profile()` のプロファイル作成、pair、失敗時cleanupを共通処理へ集約する。
- PeriodicとDirectで異なる公開constructor / `create_profile()` signatureを明示的に維持する。
- 6具象クラスをcontroller identityと公開signatureへ集中させる。
- `_RuntimeBackedGamepad`、`_PeriodicRuntimeBackedGamepad`、
  `_DirectRuntimeBackedGamepad`を削除する。
- 公開APIの現行説明と実装所有関係を`spec/initial`へ反映する。

## 3. 対象外

- 6具象クラスの`src/swbt/gamepad/controllers.py`への移動。
- `src/swbt/gamepad/core.py`または`interface.py`の削除、rename、互換re-export判断。
- `swbt` root、`swbt.gamepad`、`swbt.gamepad.interface`、
  `swbt.gamepad.core`の公開import経路変更。
- Periodic / Directの型統合、Direct controllerの削除。
- public method名、引数、例外、入力確定タイミングの変更。
- `ControllerRuntime`の再分割。
- protocol、transport、HID report、subcommand、SPI、SDP、report period既定値の変更。
- Bumble adapter、Switch pairing、advertising、実機testの実行。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/testing.md`
- `spec/rearchitecture/02-as-is-to-be.md`
- `spec/rearchitecture/04-runtime-profile-transport-details.md`
- `spec/complete/unit_040/PUBLIC_CONTROLLER_API_MODEL.md`
- `spec/complete/unit_050/DIRECT_REPORTING_TYPES.md`
- `spec/complete/unit_071/CONTROLLER_CONSTRUCTION_PATH.md`
- `spec/complete/unit_072/CONNECTION_RUNTIME_INTEGRATION.md`
- `spec/complete/unit_073/TEST_CONTRACT_BOUNDARY_CLEANUP.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | protocol builder、parser、report bytesを変更しない |
| Bumble / transport | not applicable | not applicable | transport APIとBumble実装を変更しない |
| OS / driver / adapter | not applicable | not applicable | adapterを開かず、driver仮定を追加しない |
| public API ownership | required | done | Issue #118、現行`interface.py` / `core.py`、公開boundary testを照合した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| abstract type | `SwitchGamepad`、Periodic、Directを直接生成する | `TypeError`になる | 具象型が公開constructorとidentityを定義する |
| public hierarchy | 6具象型を分類する | Periodic 3型とDirect 3型の継承関係を維持する | root exportも維持 |
| constructor | 6具象型のsignatureを調べる | Periodicだけ`report_period_us`を持つ | profile、device name、transportは露出しない |
| full-state operation | Periodic / Direct型を調べる | Periodicだけ`apply()`、Directだけ`send()`を持つ | method名を統合しない |
| lifecycle | `async with`、open、connect、closeをfake transportで実行する | open / close順序、例外、cleanupを維持する | common implementationは`SwitchGamepad`が所有 |
| input commit | Periodic / Directで入力操作を実行する | Periodicはlocal commit、Directは送信成功後commit | 既存integration testで観測 |
| profile creation | 6具象型で`create_profile()`を実行する | profile kind、pair、失敗時cleanupを維持する | Periodic / Directの公開signatureは別 |
| module compatibility | 公開型を既存pathからimportする | Issue #118前後で同じclassを得る | `controllers.py`移動まで維持 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | 公開型階層、abstract性、root exportを維持する | characterization | unit | no | baselineと変更後のboundary testがgreen |
| refactor-done | Periodic / Directのconstructor signatureと`apply()` / `send()`分離を維持する | characterization | unit | no | `create_profile()`の送信所有者別signatureも確認し、private MROは固定しない |
| refactor-done | 6具象型の`create_profile()` signature、profile kind、失敗時cleanupを維持する | regression | unit / integration | no | 共通処理への統合後も同じ観測結果 |
| refactor-done | lifecycle、connection、意味的入力、status、snapshotのfake transport挙動を維持する | regression | integration | no | integration 154件がgreen |
| refactor-done | `swbt`、`swbt.gamepad`、既存submoduleの公開importを維持する | regression | unit | no | import identityをone-off commandで確認。module移動は後続spec |

## 8. 文書検証計画

公開API docstringを変更するため、実装後に`docs-quality-review`を使う。自然言語の特定語句を
pytestで固定せず、Issue #118、`spec/initial`、実装、公開boundary testを照合する。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| public API docstring | library利用者 / lifecycle、入力、例外の確認 | `spec/initial/api.md`、既存behavior test | Ruff、MkDocs strict | done | none |
| `spec/initial/api.md` | maintainer / 公開型とsignature | Issue #118、public boundary test | link / diff review | done | none |
| `spec/initial/architecture.md` | maintainer / public ownerとruntime ownerの区別 | Issue #118、`ControllerRuntime`実装 | link / diff review | done | none |
| `spec/rearchitecture/*` | maintainer / 旧runtime非依存判断の扱い | Issue #118、user decision | diff review | done | 初回移行の履歴と現行方針の優先順位をREADMEに明記 |

## 9. 設計メモ

- `SwitchGamepad`は利用側の共通型であり、第三者が独自runtime実装を差し込むextension pointとは
  扱わない。
- `SwitchGamepad`は公開APIの実装と`ControllerRuntime`への参照を所有する。
  lifecycle state、transport、protocol session、report loopのstateful ownerは
  `ControllerRuntime`のままとする。
- abstract性の維持だけを目的としたdummy methodは追加しない。具象型ごとに異なる可能性がある
  公開constructorを抽象契約とし、6具象型がconstructorとcontroller identityを定義する。
- private class名、method owner type、source file配置は恒久pytest契約にしない。共通実装が
  1か所であることはdiff reviewと作業仕様の完了確認で検証する。
- metaclass、動的signature生成、decoratorによるconstructor合成は使わない。
- `controllers.py`移動はIssue #118を完了した後、`unit_075`として新規作業仕様を作る。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/interface.py` | modify | runtime参照、共通public method、mode固有operation、profile作成共通処理 |
| `src/swbt/gamepad/core.py` | modify | private中間基底を削除し、6具象型をidentityと公開signatureへ限定 |
| `tests/gamepad_factory.py` | modify | fake transport注入先を共通実装所有者へ合わせる |
| `tests/unit/test_public_api_boundary.py` | modify | 公開階層、signature、既存submodule importの回帰確認 |
| `tests/unit/test_pairing_profile_runtime.py` | modify if needed | profile作成の共通処理を公開観測で検証 |
| `tests/integration/test_pairing_profile.py` | modify if needed | pair失敗時cleanupとprofile kindを維持 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify if needed | lifecycleと入力確定の回帰確認 |
| `spec/initial/api.md` | modify | 公開型と実装所有者の現行判断 |
| `spec/initial/architecture.md` | modify | public API ownerとstateful runtime ownerの境界 |
| `spec/rearchitecture/README.md` | modify | 初回移行文書とIssue #118の上書き関係 |
| `spec/rearchitecture/01-design-change-overview.md` | modify | 現行public継承図 |
| `spec/rearchitecture/02-as-is-to-be.md` | modify | runtime非依存ABCの旧判断を現行方針へ更新 |
| `spec/rearchitecture/03-public-api-config-profile.md` | modify | private基底を前提にしない継承例 |
| `spec/rearchitecture/04-runtime-profile-transport-details.md` | modify | public ownerとruntime delegationの現行構造 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_public_api_boundary.py tests/unit/test_pairing_profile_runtime.py -q` | pass | 変更前baselineと変更後がともに38 passed |
| `uv run pytest tests/integration/test_pairing_profile.py tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 変更前152 passed、変更後152 passed |
| `uv run pytest tests/unit/test_public_api_boundary.py -q` | pass | `create_profile()` signature assertion追加後28 passed |
| `uv run python -c "<public import identity check>"` | pass | root、`swbt.gamepad`、`core`、`interface`のclass identityを維持 |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 439 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `uv run --group docs mkdocs build --strict` | pass | strict build成功 |
| `git diff --check` | pass | whitespace errorなし |

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

- 6具象クラスを`src/swbt/gamepad/controllers.py`へ移す。Issue #118完了後に
  `unit_075`を作り、`core.py`の削除または互換re-export、class `__module__`、
  direct submodule importへの影響を独立して判断する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test Listまたは文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
