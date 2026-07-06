# Controller Runtime Extraction 仕様書

## 1. 概要

### 1.1 目的

現行 public API を一時的に維持したまま、`SwitchGamepad` が抱えている stateful runtime を `ControllerRuntime` へ移す。public surface を壊す前に runtime lifecycle、transport instance、report loop、diagnostics、input state store、output dispatcher、connection workflow の所有者を分ける。

この unit は behavior-preserving refactor とする。`JoyCon`, `SwitchGamepadConfig`, public `transport=` はこの段階では消さない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | M1 runtime extraction と target responsibility split | `spec/rearchitecture/02-as-is-to-be.md`, `spec/rearchitecture/04-runtime-profile-transport-details.md`, `spec/rearchitecture/05-milestones-implementation.md` |
| implementation fact | 現行 `SwitchGamepad` は lifecycle、transport、report loop、diagnostics、input state store、output dispatcher、connection workflow を保持している | `src/swbt/gamepad/core.py` |
| existing tests | fake transport integration tests が現行 behavior を広く固定している | `tests/integration/test_switch_gamepad_fake_transport.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| existing user | `SwitchGamepad(adapter=...)` / `SwitchGamepad(transport=...)` | 現行どおり作成、接続、入力更新、close できる | public API は変えない |
| implementer | runtime owner を移す | `ControllerRuntime` が stateful behavior を持ち、public facade は委譲する | behavior 変更を混ぜない |
| tests | fake transport 経由の接続・report loop | 既存 tests が通る | Bumble import 遅延を維持 |

## 2. 対象範囲

- `ControllerRuntime` の追加。
- `_RuntimeConfig` の追加。
- `_TransportFactory`, `_BumbleTransportFactory`, `_StaticTransportFactory` の最小追加。
- lifecycle state、transport instance、report loop、diagnostics、input state store、output report dispatcher、connection workflow の runtime への移動。
- 既存 `SwitchGamepad` / `JoyCon` の public behavior 維持。
- `InputReportBuilder(profile)` と `SubcommandResponder(profile)` が active profile を受け取る構造の維持。

## 3. 対象外

- `SwitchGamepad` を abstract にすること。
- `ProController` / `JoyConL` / `JoyConR` の public export。
- `JoyCon` / `SwitchGamepadConfig` / public `transport=` の削除。
- profile module 分割。
- hardware behavior の新規主張。

## 4. 関連 docs

- `spec/rearchitecture/02-as-is-to-be.md`
- `spec/rearchitecture/04-runtime-profile-transport-details.md`
- `spec/rearchitecture/05-milestones-implementation.md`
- `spec/initial/architecture.md`
- `spec/complete/unit_020/STRUCTURAL_REFACTOR.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report builder と subcommand responder の byte layout は変えない |
| Bumble / transport | not applicable | not applicable | default transport factory は既存 `create_default_transport()` を呼ぶだけにする。Bumble behavior は変えない |
| OS / driver / adapter | not applicable | not applicable | adapter open や実機接続は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| open lifecycle | `await pad.open()` | callbacks、diagnostics metadata、report loop 準備の現行挙動を維持する | pairing は開始しない |
| connect lifecycle | `await pad.connect(...)` | bonded reconnect 優先、必要時のみ pairing fallback | 現行 behavior 維持 |
| close lifecycle | `await pad.close(neutral=True)` | connected 時の trailing neutral、best-effort disconnect、transport close を維持する | unit_014 contract を壊さない |
| input update | `press`, `release`, `sticks`, `apply`, `tap` | active profile で validation し、state store 更新と immediate report behavior を維持する | existing tests を通す |
| import boundary | `import swbt` | Bumble import が発生しない | factory でも遅延 import を維持 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `SwitchGamepad` の public behavior が runtime 抽出後も変わらない | regression | integration | no | fake transport tests |
| green | `JoyCon("left" / "right")` の profile validation が変わらない | regression | integration | no | existing Joy-Con fake transport tests |
| todo | `open()` が pairing / advertising を開始しない | regression | unit / integration | no | lifecycle contract |
| todo | `close(neutral=True)` が trailing neutral と cleanup を維持する | regression | integration | no | unit_014 contract |
| green | `SwitchGamepad` facade が `ControllerRuntime` を stateful owner として持つ | new | unit | no | public API shape を維持したまま runtime へ委譲 |
| green | `import swbt` が Bumble を import しない | regression | unit | no | existing package import boundary test |
| green | `_StaticTransportFactory` 経由の fake transport 作成で unit test が書ける | new | unit | no | `transport_factory.py` の internal factory として追加 |
| green | `_BumbleTransportFactory` 経由で default transport を作成できる | new | unit | no | 既存 `create_default_transport()` を包む internal factory |

## 8. 設計メモ

M1 は public API break の準備であり、互換 API を消す場所ではない。`_TransportFactory` はこの unit で導入してよいが、public `transport=` を隠す判断は unit_042 に残す。

`ControllerRuntime` には stateful owner を集める。`SwitchGamepad` は一時的に concrete facade のままでよい。M2 で `SwitchGamepad` を abstract interface に変える。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/runtime.py` | add | `ControllerRuntime` |
| `src/swbt/gamepad/_config.py` | add | `_RuntimeConfig` と runtime builder の前段 |
| `src/swbt/gamepad/_transport_factory.py` | add | internal transport factory |
| `src/swbt/gamepad/core.py` | modify | public facade から runtime へ委譲 |
| `tests/unit/test_gamepad_connection_workflow.py` | modify | runtime owner の regression |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | behavior preservation |
| `spec/wip/unit_039/CONTROLLER_RUNTIME_EXTRACTION.md` | add | 作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_gamepad_transport_factory.py::test_static_transport_factory_returns_injected_transport -q` | red | `_StaticTransportFactory` が未実装で import error |
| `uv run pytest tests/unit/test_gamepad_transport_factory.py::test_static_transport_factory_returns_injected_transport -q` | pass | `1 passed` |
| `uv run ruff format src\swbt\gamepad\transport_factory.py tests\unit\test_gamepad_transport_factory.py` | pass | 2 files left unchanged |
| `uv run ruff check src\swbt\gamepad\transport_factory.py tests\unit\test_gamepad_transport_factory.py` | pass | All checks passed |
| `uv run ty check --no-progress src\swbt\gamepad\transport_factory.py tests\unit\test_gamepad_transport_factory.py` | pass | All checks passed |
| `uv run pytest tests/unit/test_gamepad_transport_factory.py::test_bumble_transport_factory_passes_resource_config_to_default_transport -q` | red | `_BumbleTransportFactory` が未実装で import error |
| `uv run pytest tests/unit/test_gamepad_transport_factory.py::test_bumble_transport_factory_passes_resource_config_to_default_transport -q` | pass | `1 passed` |
| `uv run ruff format src\swbt\gamepad\transport_factory.py tests\unit\test_gamepad_transport_factory.py` | pass | 2 files left unchanged |
| `uv run ruff check src\swbt\gamepad\transport_factory.py tests\unit\test_gamepad_transport_factory.py` | pass | All checks passed |
| `uv run ty check --no-progress src\swbt\gamepad\transport_factory.py tests\unit\test_gamepad_transport_factory.py` | pass | All checks passed |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_public_api_import_does_not_import_bumble tests/unit/test_public_api_boundary.py::test_public_api_import_does_not_resolve_bumble -q` | pass | `2 passed`。factory 追加後も public import は Bumble を解決しない |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_switch_gamepad_uses_controller_runtime_owner -q` | red | `ControllerRuntime` が未実装 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_switch_gamepad_uses_controller_runtime_owner -q` | pass | `1 passed`。public API facade が runtime owner へ委譲 |
| `uv run ruff format --check src\swbt\gamepad\core.py tests\unit\test_public_api_boundary.py` | pass | 2 files already formatted |
| `uv run ruff check src\swbt\gamepad\core.py tests\unit\test_public_api_boundary.py` | pass | All checks passed |
| `uv run ty check --no-progress src\swbt\gamepad\core.py tests\unit\test_public_api_boundary.py` | pass | All checks passed |
| `uv run pytest tests\unit\test_public_api_boundary.py tests\unit\test_package_import.py tests\unit\test_gamepad_transport_factory.py -q` | pass | `29 passed, 4 xfailed` |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_async_context_opens_and_closes_fake_transport tests\integration\test_switch_gamepad_fake_transport.py::test_open_only_does_not_start_advertising tests\integration\test_switch_gamepad_fake_transport.py::test_pair_starts_advertising_and_waits_for_fake_connection -q` | pass | `3 passed` |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | `91 passed`。runtime owner 化後も fake transport 経由の `SwitchGamepad` public behavior は既存 regression 範囲で維持 |
| `uv run pytest tests\unit\test_public_api_boundary.py -q` | pass | `25 passed, 3 xfailed`。unit_040 で green にする target boundary xfail は継続 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -k joycon -q` | pass | `15 passed, 76 deselected`。JoyCon wrapper と unsupported input validation は維持 |
| `uv run pytest tests\unit\test_public_api_boundary.py tests\unit\test_input_report.py -k joycon -q` | pass | `11 passed, 50 deselected`。JoyCon public boundary と profile packing / validation は維持 |
| `uv run ruff format --check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ruff check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ty check --no-progress` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/unit` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/integration` | not run | 作業仕様作成時点では未実装 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。fake transport と unit tests で検証する |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | なし |
| cleanup | なし |

## 12. 先送り事項

- `_RuntimeBackedGamepad` を public concrete controllers の private base として最終化する作業は unit_040 で扱う。
- public `transport=` を消す作業は unit_042 で扱う。

## 13. チェックリスト

- [ ] 対象範囲と対象外を確認した
- [ ] TDD Test List を更新した
- [ ] 必要な根拠監査を記録した
- [ ] 実機実行条件を記録した
- [ ] 検証結果または未実行理由を記録した
