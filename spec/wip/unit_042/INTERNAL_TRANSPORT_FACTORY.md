# Internal Transport Factory 仕様書

## 1. 概要

### 1.1 目的

testability を維持したまま、public constructor から `transport=` を削除する。Bluetooth HID transport は internal runtime seam とし、通常利用者向けの backend extension API にはしない。

現行 docs は `HidDeviceTransport` を custom transport 用 public extension point と説明している。この unit では、その扱いを breaking change として閉じる。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | transport policy と M4 transport seam hiding | `spec/rearchitecture/02-as-is-to-be.md`, `spec/rearchitecture/03-public-api-config-profile.md`, `spec/rearchitecture/04-runtime-profile-transport-details.md` |
| current implementation | `SwitchGamepad(..., transport=...)` と `JoyCon(..., transport=...)` が public constructor にある | `src/swbt/gamepad/core.py` |
| current docs | custom transport を public API として案内している | `docs/api.md` |
| tests | integration tests が fake transport injection に強く依存している | `tests/integration/test_switch_gamepad_fake_transport.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `ProController(adapter="usb:0")` | default Bumble transport が内部 factory から作られる | `transport=` は渡せない |
| unit test | fake transport で runtime を作る | internal helper 経由で test できる | root public API には出さない |
| future backend author | custom backend を作りたい | この rearchitecture では公式 API として扱わない | 別設計へ送る |

## 2. 対象範囲

- `_TransportFactory` protocol の internal 化。
- `_BumbleTransportFactory` default implementation。
- `_StaticTransportFactory` test implementation。
- public constructor から `transport` を削除。
- `HidDeviceTransport` root export の削除。
- fake transport helper の配置決定。
- unit / integration tests の internal helper 化。

## 3. 対象外

- Bumble transport の open / advertising / pairing behavior 変更。
- external backend extension API の設計。
- hardware marker tests の実行。
- profile selection policy。これは unit_041 で扱う。

## 4. 関連 docs

- `spec/rearchitecture/03-public-api-config-profile.md`
- `spec/rearchitecture/04-runtime-profile-transport-details.md`
- `spec/rearchitecture/05-milestones-implementation.md`
- `spec/initial/architecture.md`
- `docs/api.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | transport injection seam の所有者変更であり、report bytes は変更しない |
| Bumble / transport | required | pending | Bumble object 型の public exposure を閉じる。Bumble behavior は変更しないが、transport boundary の公開範囲を audit する |
| OS / driver / adapter | not applicable | not applicable | adapter を開かず、OS / driver behavior は変更しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| public constructor | `ProController(..., transport=...)` | `TypeError` になる | user-facing seam から削除 |
| root exports | `from swbt import HidDeviceTransport` | import できない | internal protocol には残してよい |
| default factory | `ProController(adapter="usb:0")` | default Bumble transport を内部生成する | Bumble import 遅延を維持 |
| test factory | internal helper + fake transport | Bluetooth hardware なしで unit / integration tests が動く | helper は root export しない |
| docs | normal usage docs | custom transport を public API として説明しない | migration section の旧 API 例は例外 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | public controller constructor が `transport` を受け取らない | new | unit | no | signature test。constructor docstring からも public `transport` seam を削除 |
| green | `HidDeviceTransport` が root export されない | new | unit | no | package import test。`BondedPeer` / `DisconnectRequestResult` も root public API から削除 |
| green | internal `_StaticTransportFactory` で fake transport tests が書ける | new | unit / integration | no | `swbt._testing.gamepad` helper 経由で existing fake transport tests を移行 |
| green | default transport factory が Bumble import 遅延を維持する | regression | unit | no | import boundary |
| todo | docs が custom transport を public extension point と説明しない | regression | docs | no | migration section は例外 |

## 8. 設計メモ

`HidDeviceTransport` protocol は runtime 内部契約として残せる。ただし root export しない。repo 外の test helper として必要な場合は `src/swbt/_testing` を検討するが、user-facing docs には出さない。

public backend extension API が必要になった場合は、この unit の互換 layer ではなく別 issue / spec で扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/transport_factory.py` | modify | internal transport factories |
| `src/swbt/gamepad/_config.py` | modify | runtime builder が factory を受け取る |
| `src/swbt/gamepad/core.py` | modify | public constructor から `transport` 削除 |
| `src/swbt/_testing/gamepad.py` | add | fake transport injection 用 internal test helper |
| `src/swbt/__init__.py` | modify | `HidDeviceTransport` export removal |
| `tests/unit/test_public_api_boundary.py` | modify | constructor / root export tests |
| `tests/unit/test_public_api_docstrings.py` | modify | constructor docstring contract |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | internal helper 化 |
| `tests/integration/test_examples.py` | modify | fake transport example integration helper 化 |
| `docs/api.md` | modify | custom transport public docs 削除 |
| `spec/wip/unit_042/INTERNAL_TRANSPORT_FACTORY.md` | add | 作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_transport_seam --runxfail -q` | red | `transport` が public constructor signature に残っていた |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_transport_seam tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_config_identity_seams tests\unit\test_public_api_docstrings.py::test_concrete_controller_docstrings_describe_constructor_arguments -q` | pass | `3 passed`。public concrete controller constructor と Google style docstring から `transport` を削除 |
| `uv run pytest tests/unit -q` | pass | `349 passed`。root `HidDeviceTransport` xfail を解消 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py tests\integration\test_examples.py -q` | pass | `93 passed`。fake transport integration は `swbt._testing.gamepad` helper 経由で実行 |
| `uv run pytest tests\unit\test_package_import.py::test_rearchitecture_target_root_hides_internal_transport_type -q` | red | `HidDeviceTransport` が root public export に残っていた |
| `uv run pytest tests\unit\test_package_import.py tests\unit\test_public_api_docstrings.py::test_public_value_object_docstrings_describe_attributes_and_factory_returns -q` | pass | `5 passed`。transport extension 型を root public API と public docstring contract から削除 |
| `uv run ruff check src\swbt\__init__.py tests\unit\test_package_import.py tests\unit\test_public_api_docstrings.py` | pass | `All checks passed!` |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_public_api_import_does_not_import_bumble tests\unit\test_public_api_boundary.py::test_public_api_import_does_not_resolve_bumble tests\unit\test_public_api_boundary.py::test_only_bumble_transport_module_may_resolve_bumble tests\unit\test_gamepad_transport_factory.py -q` | pass | `6 passed`。public import と default transport factory の Bumble import 遅延を維持 |
| `uv run ruff format --check .` | pass | `84 files already formatted` |
| `uv run ruff check .` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest tests/integration -q` | pass | `93 passed` |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。adapter open、HID advertising、pairing、report loop は実行しない |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | なし |
| cleanup | なし |

## 12. 先送り事項

- external backend extension API は別 spec で扱う。
- fake transport を `tests/helpers` に置くか `src/swbt/_testing` に置くかは実装時に、repo 外 integration test の必要性で決める。

## 13. チェックリスト

- [ ] 対象範囲と対象外を確認した
- [ ] TDD Test List を更新した
- [ ] 必要な根拠監査を記録した
- [ ] 実機実行条件を記録した
- [ ] 検証結果または未実行理由を記録した
