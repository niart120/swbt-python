# Public Controller API Model 仕様書

## 1. 概要

### 1.1 目的

public class model を `SwitchGamepad` direct construction から、`SwitchGamepad` abstract interface と `ProController` / `JoyConL` / `JoyConR` concrete controller に切り替える。

この unit は breaking change を含む。`JoyCon(side=...)` と compatibility alias は残さない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | target public inheritance と採用しない代替案 | `spec/rearchitecture/01-design-change-overview.md`, `spec/rearchitecture/03-public-api-config-profile.md` |
| current API | `SwitchGamepad` が直接生成され、`JoyCon(side)` が thin wrapper として存在する | `src/swbt/gamepad/core.py`, `src/swbt/__init__.py` |
| initial API | 初期設計では `SwitchGamepad` を入口にしている | `spec/initial/api.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `ProController(adapter=...)` | Pro Controller identity の仮想 controller が作成される | `SwitchGamepad(...)` は使わない |
| library user | `JoyConL(adapter=...)` / `JoyConR(adapter=...)` | 左右の controller identity が class 名で固定される | `JoyCon("left")` / `JoyCon("right")` は使わない |
| type consumer | `def f(pad: SwitchGamepad)` | Pro / Joy-Con L / Joy-Con R を同じ interface として受け取れる | `SwitchGamepad` は直接生成できない |

## 2. 対象範囲

- `src/swbt/gamepad/interface.py` への abstract `SwitchGamepad` 追加。
- `src/swbt/gamepad/controllers.py` への `ProController`, `JoyConL`, `JoyConR`, private `_RuntimeBackedGamepad` 追加。
- root export の新 API への切り替え。
- `JoyCon` root export の削除。
- README / docs / examples の controller 作成例の新 API への切り替え。
- public boundary tests の新 API への更新。

## 3. 対象外

- `SwitchGamepadConfig` の内部削除。
- public `transport=` の完全撤去。
- profile module split。
- `JoyConPair` の追加。
- 未検証 Joy-Con behavior の保証。

## 4. 関連 docs

- `spec/rearchitecture/README.md`
- `spec/rearchitecture/01-design-change-overview.md`
- `spec/rearchitecture/03-public-api-config-profile.md`
- `spec/rearchitecture/05-milestones-implementation.md`
- `spec/initial/api.md`
- `docs/api.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | public class model の変更であり、report byte layout は変更しない |
| Bumble / transport | not applicable | not applicable | controller class から既存 runtime / transport builder へ渡すだけにし、Bumble behavior は変更しない |
| OS / driver / adapter | not applicable | not applicable | adapter open や実機接続は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| abstract interface | `SwitchGamepad()` | `TypeError` で失敗する | `InvalidInputError` ではない |
| Pro creation | `ProController(adapter="usb:0")` | Pro Controller profile の runtime-backed controller になる | profile は public 引数ではない |
| Joy-Con L creation | `JoyConL(adapter="usb:0")` | Joy-Con L profile の controller になる | invalid side path は存在しない |
| Joy-Con R creation | `JoyConR(adapter="usb:0")` | Joy-Con R profile の controller になる | invalid side path は存在しない |
| root exports | `from swbt import ...` | `ProController`, `JoyConL`, `JoyConR`, `SwitchGamepad` を import でき、`JoyCon` は import できない | compatibility alias は残さない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `SwitchGamepad` は abstract interface として直接生成できない | new | unit | no | unit_038 target test を green にする |
| green | `ProController`, `JoyConL`, `JoyConR` が root export される | new | unit | no | package import test |
| green | `JoyCon` が root export されない | new | unit | no | compatibility alias は残さない |
| green | `JoyConL` / `JoyConR` に invalid side error path がない | new | unit | no | class selection で identity 固定 |
| todo | README / docs の通常例が new API を使う | regression | docs | no | migration section の旧 API 例は例外 |

## 8. 設計メモ

`SwitchGamepad` は受け取る型であり、作る型ではない。これにより concrete controller identity と protocol profile の対応が public class 名で固定される。

`JoyCon = JoyConL` のような alias は残さない。短期的な移行負担より、pre-alpha のうちに public surface の意味を明確にすることを優先する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/interface.py` | add | abstract `SwitchGamepad` |
| `src/swbt/gamepad/controllers.py` | add | `ProController`, `JoyConL`, `JoyConR`, `_RuntimeBackedGamepad` |
| `src/swbt/gamepad/__init__.py` | modify | gamepad package exports |
| `src/swbt/__init__.py` | modify | root exports |
| `tests/unit/test_public_api_boundary.py` | modify | public class model tests |
| `tests/unit/test_package_import.py` | modify | root export tests |
| `README.md` | modify | basic usage examples |
| `docs/api.md` | modify | public API docs |
| `docs/usage.md` | modify | usage guide |
| `examples/` | modify | controller creation examples |
| `spec/wip/unit_040/PUBLIC_CONTROLLER_API_MODEL.md` | add | 作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_switch_gamepad_is_abstract_interface -q` | red | `SwitchGamepad` が concrete class のままで `inspect.isabstract(SwitchGamepad)` が false |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_switch_gamepad_is_abstract_interface -q` | pass | `1 passed`。`SwitchGamepad()` は abstract interface として `TypeError` になる |
| `uv run ty check --no-progress src\swbt\gamepad\interface.py src\swbt\gamepad\core.py tests\unit\test_public_api_boundary.py` | fail | 既存 tests が old concrete `SwitchGamepad` 生成を参照している。後続 concrete controller item で更新する |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_concrete_controllers_share_interface -q` | red | root export に `ProController` がなく AttributeError |
| `uv run pytest tests\unit\test_package_import.py::test_package_exports_public_gamepad_surface -q` | red | `swbt.__all__` が new concrete controllers を含んでいない |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_concrete_controllers_share_interface tests\unit\test_package_import.py::test_package_exports_public_gamepad_surface -q` | pass | `2 passed`。`ProController`, `JoyConL`, `JoyConR` は root export 済み |
| `uv run pytest tests\unit\test_package_import.py::test_package_exports_public_gamepad_surface tests\unit\test_package_import.py::test_rearchitecture_target_root_exports_controller_api -q` | pass | `2 passed`。`JoyCon` は root export から削除済み |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_joycon_concrete_classes_have_no_invalid_side_path -q` | pass | `1 passed`。左右 identity は `JoyConL` / `JoyConR` class selection で固定 |
| `uv run ruff format --check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ruff check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ty check --no-progress` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/unit` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/integration` | not run | 作業仕様作成時点では未実装 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。fake transport と docs tests で検証する |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | なし |
| cleanup | なし |

## 12. 先送り事項

- `SwitchGamepadConfig` と public `transport=` の内部撤去は unit_041 / unit_042 で扱う。
- `BondedPeer` の public return type 整理は unit_041 で扱う。

## 13. チェックリスト

- [ ] 対象範囲と対象外を確認した
- [ ] TDD Test List を更新した
- [ ] 必要な根拠監査を記録した
- [ ] 実機実行条件を記録した
- [ ] 検証結果または未実行理由を記録した
