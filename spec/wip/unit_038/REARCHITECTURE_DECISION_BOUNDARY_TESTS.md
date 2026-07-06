# Rearchitecture Decision Boundary Tests 仕様書

## 1. 概要

### 1.1 目的

リアーキテクチャの破壊的変更方針を、実装前に review 可能な作業単位へ固定する。対象は target public boundary の test と、現行 public surface からの移行方針の明文化である。

この unit は production code を変更しない。`SwitchGamepad` を abstract interface にする、`ProController` / `JoyConL` / `JoyConR` を public concrete controller にする、public `transport=` と profile injection を消す、という target を test と文書で先に固定する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | リアーキテクチャの中核判断と M0 decision freeze | `spec/rearchitecture/01-design-change-overview.md`, `spec/rearchitecture/05-milestones-implementation.md` |
| implementation fact | 現行 root API は `SwitchGamepad`, `JoyCon`, `SwitchGamepadConfig`, `HidDeviceTransport`, `BondedPeer` を公開している | `src/swbt/__init__.py`, `src/swbt/gamepad/core.py` |
| docs fact | 現行 docs は custom transport を public extension point として説明している | `docs/api.md` |
| repo policy | work unit は `spec/wip/unit_XXX/FEATURE_NAME.md` で管理する | `AGENTS.md`, `.agents/skills/spec-format/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | target public API を review する | breaking change の対象と非対象が test 名と spec に残る | production code はまだ変更しない |
| implementer | 後続 unit に着手する | どの test が target contract で、どれが現行互換 test か分かる | M2 までは target test を `xfail` してよい |
| reviewer | public `transport=` 削除を確認する | custom transport が削除対象の breaking API であることが明示される | 互換 alias を残す判断をしない |

## 2. 対象範囲

- `spec/rearchitecture/` の設計判断を work unit へ分割したことの記録。
- target root exports の boundary test。
- `SwitchGamepad` が直接生成できない abstract interface になることの target test。
- `ProController` / `JoyConL` / `JoyConR` が root export され、`SwitchGamepad` を共有 interface として実装することの target test。
- public constructor に `profile`, `device_name`, `transport` が出ないことの target test。
- 現行 docs が public custom transport を案内している事実の breaking change 記録。

## 3. 対象外

- `SwitchGamepad` の実装変更。
- `JoyCon`, `SwitchGamepadConfig`, `HidDeviceTransport` の削除。
- runtime 抽出。
- profile module 分割。
- README / user docs の全面更新。
- 実機検証。

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
| Switch HID / report bytes | not applicable | not applicable | target boundary test と設計記録だけを扱い、report byte layout は変更しない |
| Bumble / transport | not applicable | not applicable | transport を開かず、Bumble object 型も変更しない。public `transport=` 削除方針だけを記録する |
| OS / driver / adapter | not applicable | not applicable | adapter discovery、driver、実機接続は扱わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| target exports | `swbt.__all__` | `ProController`, `JoyConL`, `JoyConR`, `SwitchGamepad` を含み、`JoyCon`, `SwitchGamepadConfig`, `HidDeviceTransport` を含まない target が test に固定される | M2 まで `xfail` 可 |
| abstract interface | `SwitchGamepad()` | target では `TypeError` になる | 現行では concrete controller のため失敗する target test |
| constructor seam | `inspect.signature(ProController)` など | `adapter`, `key_store_path`, `report_period_us`, `controller_colors`, `diagnostics` だけが user-facing option になる | `profile`, `device_name`, `transport` は出さない |
| current-state note | `docs/api.md` の custom transport 記述 | public extension point 削除が breaking change であることを spec に残す | 互換方針ではない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | root export が target controller API を表す | new | unit | no | `swbt.__all__` の target test。`xfail(strict=True)` で固定し、unit_040 で green にする |
| green | `SwitchGamepad` は abstract で直接生成できない | new | unit | no | `xfail(strict=True)` で固定し、unit_040 で green にする |
| green | public concrete controller が共通 interface を実装する | new | unit | no | `xfail(strict=True)` で固定し、unit_040 で green にする |
| green | public concrete constructor が internal seam を受け取らない | new | unit | no | `xfail(strict=True)` で固定し、unit_040 で green にする |
| green | breaking change 方針が docs / spec に残っている | regression | unit / docs | no | characterization。現行 docs の public extension point と spec の breaking change 方針を同時に固定 |

## 8. 設計メモ

target test は後続実装の失敗を先に可視化するためのものであり、現行 API の互換維持を要求する test ではない。M2 まで `xfail` を使う場合は、理由に `target boundary fixed before implementation` のような意図を残す。

`HidDeviceTransport` は現行 docs で public extension point と説明されている。削除は単なる export 整理ではなく、custom backend API を後続別設計へ送る breaking change として扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tests/unit/test_public_api_boundary.py` | modify | target public boundary tests |
| `tests/unit/test_package_import.py` | modify | root export target tests |
| `spec/rearchitecture/05-milestones-implementation.md` | modify | unit mapping の追記 |
| `spec/wip/unit_038/REARCHITECTURE_DECISION_BOUNDARY_TESTS.md` | add | 作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_package_import.py::test_rearchitecture_target_root_exports_controller_api -q` | red | target API が未実装のため、`ProController` / `JoyConL` / `JoyConR` が `swbt.__all__` に存在しない |
| `uv run pytest tests/unit/test_package_import.py::test_rearchitecture_target_root_exports_controller_api -q` | pass | `1 xfailed`。target boundary fixed before implementation |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_rearchitecture_target_switch_gamepad_is_abstract_interface -q` | red | 現行 `SwitchGamepad` は abstract ではない |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_rearchitecture_target_switch_gamepad_is_abstract_interface -q` | pass | `1 xfailed`。target boundary fixed before implementation |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_rearchitecture_target_public_concrete_controllers_share_interface -q` | red | 現行 `swbt` に `ProController` が存在しない |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_rearchitecture_target_public_concrete_controllers_share_interface -q` | pass | `1 xfailed`。target boundary fixed before implementation |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_internal_seams -q` | red | 現行 `swbt` に `ProController` が存在しない |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_internal_seams -q` | pass | `1 xfailed`。target boundary fixed before implementation |
| `uv run pytest tests/unit/test_public_docs.py::test_rearchitecture_records_transport_removal_as_breaking_change -q` | pass | `1 passed`。現行 docs の public custom transport 記述と rearchitecture spec の breaking change 方針を固定 |
| `uv run ruff format --check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ruff check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ty check --no-progress` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/unit` | not run | 作業仕様作成時点では未実装 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。unit tests と docs/spec 更新だけを扱う |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | なし |
| cleanup | なし |

## 12. 先送り事項

- target test を `xfail` にするか、最初から failure として red を確認するかは実装着手時に決める。
- `HidDeviceTransport` を repo 外 integration test 用に残す必要があるかは unit_042 で扱う。

## 13. チェックリスト

- [ ] 対象範囲と対象外を確認した
- [ ] TDD Test List を更新した
- [ ] 必要な根拠監査を記録した
- [ ] 実機実行条件を記録した
- [ ] 検証結果または未実行理由を記録した
