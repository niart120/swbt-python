# Controller Config Profile Ownership 仕様書

## 1. 概要

### 1.1 目的

public profile injection を消し、controller identity を concrete controller class の内部所有にする。`SwitchGamepadConfig(profile=...)`, `from_config()`, `device_name` override を public path から削除し、profile は内部 protocol definition として扱う。

`ControllerColors` は controller identity ではなく presentation option なので public に残す。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | config / profile policy と M3 cleanup | `spec/rearchitecture/03-public-api-config-profile.md`, `spec/rearchitecture/05-milestones-implementation.md` |
| current implementation | `SwitchGamepadConfig` が `profile`, `device_name`, `controller_colors` を持ち、`from_config()` が public path にある | `src/swbt/gamepad/core.py` |
| current docs | `SwitchGamepadConfig` と custom transport が public API に出ている | `docs/api.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `ProController(adapter=..., controller_colors=...)` | Pro Controller identity を保ったまま色だけ変えられる | `profile=` は渡せない |
| library user | `JoyConL(adapter=..., device_name="Pro Controller")` | public constructor が `device_name` を受け取らない | identity の矛盾を作れない |
| internal tests | concrete class と profile の対応を検証する | class が正しい profile を選ぶ | profile は root export しない |

## 2. 対象範囲

- `_ControllerSpec` の追加。
- `_RuntimeConfig` / `_build_runtime()` の最終化。
- public `SwitchGamepad.from_config()` と `JoyCon.from_config()` の削除。
- public `SwitchGamepadConfig` の削除。
- public path から `profile` argument と `device_name` override を削除。
- `controller_colors` を public option として維持。
- `report_period_us=None` が profile default を使うこと。
- `BondedPeer` が public return type に必要かの audit。

## 3. 対象外

- `ProController` / `JoyConL` / `JoyConR` class model の導入。これは unit_040 で扱う。
- public `transport=` の最終撤去。これは unit_042 で扱う。
- profile module split。これは unit_043 で扱う。
- controller color SPI byte layout の変更。

## 4. 関連 docs

- `spec/rearchitecture/03-public-api-config-profile.md`
- `spec/rearchitecture/04-runtime-profile-transport-details.md`
- `spec/rearchitecture/05-milestones-implementation.md`
- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- `spec/complete/unit_029/CONTROLLER_PROFILE_INJECTION.md`
- `docs/api.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | profile ownership を変えるが、新しい report byte / SPI address は追加しない |
| Bumble / transport | not applicable | not applicable | transport construction policy は unit_042 で扱う |
| OS / driver / adapter | not applicable | not applicable | adapter open や実機接続は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile injection removal | public constructor / classmethod | `profile` を受け取れない | concrete class が profile を選ぶ |
| device name removal | public constructor | `device_name` を受け取れない | advertised name は profile identity |
| color option | `controller_colors=ControllerColors(...)` | profile default より利用者指定色が優先される | public に残す |
| period default | `report_period_us=None` | profile default period を使う | 正規化後に positive integer validation |
| config removal | `SwitchGamepadConfig` root import | import できない | public replacement は出さない |
| bonded peer audit | `ConnectionResult` 型 | `BondedPeer` を public に残すか plain data に落とすか決める | 偶然 export は避ける |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | concrete controller constructor が `profile` を受け取らない | new | unit | no | signature test |
| green | concrete controller constructor が `device_name` を受け取らない | new | unit | no | signature test |
| green | `SwitchGamepadConfig` が root export されない | new | unit | no | package import test |
| green | `from_config()` が public path に残っていない | new | unit | no | public class attribute は削除し、internal `_from_config()` で regression を維持 |
| green | `controller_colors` override が profile default より優先される | regression | unit / integration | no | unit_028 / unit_037 contract |
| green | `report_period_us=None` が profile default を使う | regression | unit | no | positive integer validation も維持 |
| green | `ConnectionResult` が public 型として必要な値だけを露出する | characterization | unit | no | `BondedPeer` は `HidDeviceTransport` が残る unit_042 まで public transport type として維持 |

## 8. 設計メモ

profile は identity と protocol fact の束であり、public config ではない。public class 名と profile の対応を崩せないようにする。

`ControllerColors` は SPI profile data に現れるが、controller identity そのものではない。利用者が色を変える API は残すが、device name や HID descriptor の差し替えは許可しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/_config.py` | modify | `_ControllerSpec`, `_RuntimeConfig`, `_build_runtime()` |
| `src/swbt/gamepad/core.py` | modify | concrete class が spec を選ぶ |
| `src/swbt/gamepad/__init__.py` | modify | `SwitchGamepadConfig` export removal |
| `src/swbt/__init__.py` | modify | root exports |
| `tests/unit/test_public_api_boundary.py` | modify | config/profile boundary tests |
| `tests/unit/test_package_import.py` | modify | root export tests |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | controller_colors / period regression |
| `docs/api.md` | modify | config/profile migration |
| `spec/complete/unit_041/CONTROLLER_CONFIG_PROFILE_OWNERSHIP.md` | move | 完了した作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_config_identity_seams tests\unit\test_public_api_docstrings.py::test_concrete_controller_docstrings_describe_constructor_arguments -q` | red | `device_name` が public constructor signature と constructor docstring に残っていた |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_config_identity_seams tests\unit\test_public_api_docstrings.py::test_concrete_controller_docstrings_describe_constructor_arguments -q` | pass | `2 passed`。`profile` / `device_name` は public constructor から消え、constructor docstring からも消えた |
| `uv run pytest tests\unit\test_package_import.py::test_package_exports_public_gamepad_surface tests\unit\test_package_import.py::test_rearchitecture_target_root_hides_internal_config_type -q` | red | `SwitchGamepadConfig` が root export に残っていた |
| `uv run pytest tests\unit\test_package_import.py::test_package_exports_public_gamepad_surface tests\unit\test_package_import.py::test_rearchitecture_target_root_hides_internal_config_type -q` | pass | `2 passed`。`SwitchGamepadConfig` は root / gamepad package export から削除済み |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controllers_do_not_expose_from_config -q` | red | `ProController.from_config` / `JoyConL.from_config` / `JoyConR.from_config` が public class attribute として残っていた |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controllers_do_not_expose_from_config tests\unit\test_public_api_boundary.py::test_joycon_from_config_requires_matching_joycon_profile tests\unit\test_public_api_boundary.py::test_joycon_from_config_accepts_matching_joycon_profile tests\unit\test_public_api_docstrings.py::test_concrete_controller_docstrings_describe_constructor_arguments -q` | pass | `4 passed`。public `from_config()` は削除し、internal `_from_config()` の profile validation は維持 |
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py::test_from_config_output_report_injection_uses_configured_controller_colors tests\integration\test_switch_gamepad_fake_transport.py::test_from_config_uses_profile_controller_colors_when_colors_are_unspecified tests\integration\test_switch_gamepad_fake_transport.py::test_from_config_profile_reaches_periodic_input_report_builder tests\integration\test_switch_gamepad_fake_transport.py::test_from_config_joycon_profile_reaches_device_info_reply -q` | pass | `4 passed`。internal `_from_config()` 経由で既存 regression を維持 |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_public_constructor_uses_profile_default_report_period tests\unit\test_public_api_boundary.py::test_switch_gamepad_rejects_non_positive_report_period tests\integration\test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_configured_controller_colors -q` | pass | `4 passed`。public constructor の default period、positive validation、controller color override を確認 |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_connection_result_exposes_plain_reconnect_values_without_bonded_peer -q` | pass | `1 passed`。`ConnectionResult` は `route`, `status`, `peer_address`, `peer_count` の plain fields のみ |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_concrete_controller_classes_own_internal_controller_specs tests\unit\test_public_api_boundary.py::test_rearchitecture_target_public_controller_constructors_hide_config_identity_seams tests\unit\test_public_api_boundary.py::test_public_constructor_uses_profile_default_report_period tests\integration\test_switch_gamepad_fake_transport.py::test_joycon_uses_side_default_controller_colors_when_colors_are_unspecified -q` | pass | `5 passed`。concrete class が `_ControllerSpec` で profile を内部所有することを確認 |
| `uv run pytest tests\unit\test_protocol_profile.py::test_pro_controller_profile_direct_construction_is_limited_to_profile_factory tests\unit\test_public_api_boundary.py::test_concrete_controller_classes_own_internal_controller_specs -q` | pass | `2 passed`。Pro Controller profile は `default_controller_profile()` 経由で spec に渡す |
| `uv sync --dev` | pass | `Resolved 53 packages`, `Checked 41 packages` |
| `uv run ruff format --check .` | pass | `82 files already formatted` |
| `uv run ruff check .` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest tests/unit -q` | pass | `347 passed, 2 xfailed`。残る xfail は unit_042 の transport seam |
| `uv run pytest tests/integration -q` | pass | `93 passed` |
| `uv run pytest tests\unit\test_package_import.py::test_rearchitecture_target_root_hides_internal_transport_type -q` | xfail | `1 xfailed`。理由を unit_042 に更新 |

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

- `BondedPeer` を plain data に落とす場合、docs と typing の migration note を追加する。
- repo 外 integration test 用の fake transport public helper は unit_042 で判断する。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
