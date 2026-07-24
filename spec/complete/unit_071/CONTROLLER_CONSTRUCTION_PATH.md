# Controller 構築経路一本化 仕様書

## 1. 概要

### 1.1 目的

公開 controller から `ControllerRuntime` と transport を構築する内部経路を1本にし、値のコピーだけを行う設定型、factory object、constructor 回避、production package 内の test-only factory を削除する。公開 constructor と観測可能な runtime 挙動は変えない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | controller 構築経路、設定型、runtime constructor、transport 生成、test injection の一本化 | `https://github.com/niart120/swbt-python/issues/116` |
| 親 Issue | 観測可能な公開挙動を維持した不要境界の段階的削除 | `https://github.com/niart120/swbt-python/issues/114` |
| 依存 Issue | 診断履歴と未使用経路の削除 | `https://github.com/niart120/swbt-python/issues/115` |
| 初期設計 | public gamepad、runtime、transport の所有関係 | `spec/initial/architecture.md` |
| 初期設計 | 6 concrete controller の constructor 契約 | `spec/initial/api.md` |
| 初期設計 | fake transport と import boundary の検証方針 | `spec/initial/testing.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| public API 利用者 | 6 concrete controller を既存引数で構築 | constructor 名、parameter、default、例外が変わらない | transport / profile seam を公開しない |
| runtime | 正規化済み controller 設定と optional injected transport を受け取る | 1個の constructor だけで全内部状態を構築する | `__new__()` 回避を使わない |
| default transport 利用者 | injected transport なしで controller を open | `create_default_transport()` を直接使う | adapter 必須、Bumble は遅延 import |
| fake integration test | Fake transport で public controller の lifecycle を検証 | tests 配下の support から公開 constructor 経路を使う | production package に test factory を置かない |
| pairing profile 利用者 | 異なる controller kind の profile path を渡す | adapter preparation / transport 作成前に mismatch を拒否する | profile schema は変更しない |

## 2. 対象範囲

- `_SwitchGamepadConfig` と `_RuntimeConfig` を、正規化済みの内部設定型1個へ統合する。
- `_ControllerSpec` を削除し、各 concrete controller が固定 profile を class 属性で直接所有する。
- profile の `device_name` / `default_report_period_us` と明示値の優先規則を維持する。
- `controller_colors` の明示上書きと profile default を維持する。
- `ControllerRuntime.__init__()` へ初期化を集約し、`_init_from_config()` / `from_config()` / `__new__()` 回避を削除する。
- production から未使用の runtime async context manager を削除する。
- `_TransportFactory`、`_BumbleTransportFactory`、`_StaticTransportFactory` を削除する。
- injected transport はその instance を使い、未指定時は `create_default_transport()` を直接呼ぶ。
- `create_default_transport()` の Bumble 遅延 import を維持する。
- `src/swbt/_testing/gamepad.py` の6 factory と `_RuntimeBackedGamepad._from_config()` を削除する。
- fake transport test を tests 配下の support と公開 constructor 経路へ移す。
- 関連する初期設計とテストを現行構築経路へ更新する。

## 3. 対象外

- `SwitchGamepad` / `PeriodicSwitchGamepad` / `DirectSwitchGamepad` の公開型階層変更。
- `ConnectionWorkflow` の削除や callback 構成変更。
- HID report、subcommand、SPI、SDP、pairing profile schema、CSR identity preparation の変更。
- public constructor への transport / profile 引数追加。
- dependency injection container、registry、manager の追加。
- Issue #117 以降の親 Issue 子項目。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/testing.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/complete/unit_070/DIAGNOSTICS_AND_UNUSED_PATHS_CLEANUP.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | protocol builder、parser、定数、payload を変更しない |
| Bumble / transport | required | done | factory object を削除するが `create_default_transport()` とその関数内の遅延 import、Bumble constructor 引数は維持する。既存 import boundary test と transport factory test を根拠にする |
| OS / driver / adapter | not applicable | not applicable | adapter を開かず、driver / identity preparation の意味を変更しない |

### 5.1 監査結果

| 項目 | 値 / 判断 | 根拠分類 | source | status |
|---|---|---|---|---|
| public import | `import swbt` は Bumble module を import / resolve しない | implementation fact | `tests/unit/test_public_api_boundary.py` | baseline green |
| transport factory import | `import swbt.gamepad.transport_factory` は Bumble module を import しない | implementation fact | `tests/unit/test_gamepad_transport_factory.py` | baseline green |
| default transport | `create_default_transport()` だけが `swbt.transport.bumble` を遅延 import する | implementation fact | `src/swbt/gamepad/transport_factory.py` | 維持 |
| profile kind mismatch | `PairingProfile.require_controller_kind()` が transport 作成前に拒否する | implementation fact | `src/swbt/gamepad/runtime.py`, `tests/unit/test_pairing_profile_runtime.py` | 維持 |
| construction result | concrete controller、`_GamepadConfig`、`ControllerRuntime.__init__()`、`create_default_transport()` の順に一本化した | implementation fact | `src/swbt/gamepad/` と unit / integration gate | done |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| public signature | 6 concrete controller を introspection | parameter 名と default が変更前と一致する | Direct に `report_period_us` を追加しない |
| adapter validation | default transport で adapter を省略 | `InvalidInputError` を constructor で送出する | injected runtime transport は adapter なしを許す |
| profile default | device name / report period の明示値なし | concrete profile の default を正規化済み設定へ入れる | profile object の値をコピーするだけの第2設定型は作らない |
| explicit override | report period / controller colors を指定 | explicit 値を runtime / report builder へ渡す | profile 自体は変更しない |
| profile kind | profile path の kind が concrete controller と不一致 | adapter preparation / transport creation 前に拒否する | 既存例外型を維持 |
| default transport | controller open 時に injected transport なし | `create_default_transport()` を直接1回呼ぶ | factory object を生成しない |
| injected transport | runtime に transport instance を渡す | default transport を作らず、その instance を使用する | tests support から利用 |
| import boundary | public API または transport factory module を import | Bumble を import / resolve しない | `create_default_transport()` 呼び出し時だけ解決 |
| resource ownership | public gamepad の `async with` | gamepad が open / close を所有する | runtime 自体は context manager を公開しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | production package に test-only gamepad factory module が存在しない | regression | unit | no | 削除前の red と削除後の green を確認 |
| done | 6 concrete controller の signature、型階層、adapter validation が維持される | characterization | unit | no | public API boundary test |
| done | profile default と明示 report period / controller colors の優先規則が維持される | characterization | unit / integration | no | `_GamepadConfig` と fake transport test |
| done | profile kind mismatch が transport 作成前に拒否される | characterization | unit | no | pairing profile runtime test |
| done | injected transport と default transport が同じ runtime constructor を使い、default 側だけ factory 関数を呼ぶ | regression | unit / integration | no | factory object を削除 |
| done | public import と transport factory import が Bumble を import / resolve しない | characterization | unit | no | subprocess / guarded import |
| done | fake transport integration が production test factory なしで Periodic / Direct 全経路を維持する | regression | integration | no | tests support は公開 constructor を使用 |

## 8. 文書検証計画

公開 docs site は変更しない。`spec/initial` の内部構築説明と fake transport test 方針を、実装 call graph、import boundary test、constructor signature test と照合する。

## 9. 設計メモ

- 正規化済み設定型は `profile`、adapter / profile path、確定済み device name / report period、optional colors override を保持する。
- concrete controller は `_profile` class 属性を直接持つ。profile 選択用 wrapper object は置かない。
- public constructor は `_profile` から設定を作り、`ControllerRuntime(config, ...)` を1回呼ぶ。
- runtime は optional transport を受け取る。transport が `None` の場合だけ、open 時に `create_default_transport()` を直接呼ぶ。
- tests 配下の support は public controller constructor を呼ぶ際に runtime constructor を差し替え、Fake transport を注入する。production controller に `_from_config()` を戻さない。
- `create_default_transport()` は `transport_factory.py` に残し、Bumble import を関数内に閉じ込める。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/_config.py` | modify | 設定型を正規化済み1個へ統合 |
| `src/swbt/gamepad/core.py` | modify | class profile、public constructor から runtime への単一路 |
| `src/swbt/gamepad/runtime.py` | modify | constructor 一本化、factory object / context manager 削除 |
| `src/swbt/gamepad/transport_factory.py` | modify | factory class を削除し関数だけ維持 |
| `src/swbt/_testing/gamepad.py` | delete | production test factories を削除 |
| `src/swbt/_testing/__init__.py` | delete | 空の test-only package を削除 |
| `tests/gamepad_factory.py` | new | public constructor と runtime injection を使う test support |
| `tests/unit/test_public_api_boundary.py` | modify | 単一設定型、class profile、seam 削除、既存契約 |
| `tests/unit/test_gamepad_transport_factory.py` | modify | 関数と import boundary の検証へ集約 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | production test factory / `_from_config()` を除去 |
| `tests/integration/test_examples.py` | modify | tests support を利用 |
| `spec/initial/architecture.md` | modify | controller 構築経路を記録 |
| `spec/initial/api.md` | modify | production test helper 参照を削除 |
| `spec/initial/testing.md` | modify | tests support と public constructor 経路へ更新 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_package_import.py::test_production_package_has_no_test_gamepad_factory_module -q` | red / green | 削除前は `swbt._testing.gamepad` が見つかり失敗、削除後は unit gate 内で成功 |
| `uv run pytest tests/unit/test_package_import.py tests/unit/test_gamepad_transport_factory.py tests/unit/test_public_api_boundary.py tests/unit/test_pairing_profile_runtime.py -q` | pass | 54 passed |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 102 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 468 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `git diff --check` | pass | whitespace error なし |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | adapter / Switch-facing command を実行しない |
| adapter | none |
| 実行遮断 | 環境変数による遮断は採用しない。`bumble` / `hardware` marker を実行対象から除外する |
| log / artifact | local unit / integration / CI output |
| cleanup | none |

## 13. 先送り事項

- none

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
