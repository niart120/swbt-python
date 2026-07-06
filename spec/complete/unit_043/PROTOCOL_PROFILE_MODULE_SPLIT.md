# Protocol Profile Module Split 仕様書

## 1. 概要

### 1.1 目的

`src/swbt/protocol/profile.py` に集まっている descriptor、SDP policy、button maps、profile class、controller colors、device info payload 生成を分割し、controller identity definition の変更理由を局所化する。

この unit は public API を増やさない。profile classes は internal protocol definition として扱い、root export しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | profile module split と `ControllerKind` 分岐局所化 | `spec/rearchitecture/02-as-is-to-be.md`, `spec/rearchitecture/04-runtime-profile-transport-details.md`, `spec/rearchitecture/05-milestones-implementation.md` |
| current implementation | `protocol/profile.py` に Pro / Joy-Con profile、descriptor、button map、colors、SDP policy が混在している | `src/swbt/protocol/profile.py` |
| implementation result | profile 実装を用途別 module に分割し、`protocol/profile.py` は internal compatibility re-export として残した | `src/swbt/protocol/profiles/`, `src/swbt/protocol/buttons.py`, `src/swbt/protocol/descriptors.py`, `src/swbt/protocol/profile.py` |
| existing tests | profile, input report, virtual SPI, source-audit fixtures が profile behavior を固定している | `tests/unit/test_protocol_profile.py`, `tests/unit/test_input_report.py`, `tests/unit/test_virtual_spi_flash.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| protocol maintainer | Joy-Con R button map を直す | Joy-Con profile / button map 近辺だけを変更する | unrelated descriptor / colors に触れない |
| runtime code | `ControllerProfile` を受け取る | controller kind 分岐を増やさず profile behavior に依存する | runtime に `ControllerKind` 分岐を漏らさない |
| public user | `import swbt` | profile class は root export されない | deep import は public contract にしない |

## 2. 対象範囲

- `src/swbt/protocol/profiles/base.py` の追加。
- `src/swbt/protocol/profiles/pro_controller.py` の追加。
- `src/swbt/protocol/profiles/joycon.py` の追加。
- `src/swbt/protocol/buttons.py` の追加。
- `src/swbt/protocol/descriptors.py` の追加。
- 必要な場合の `src/swbt/protocol/sdp.py` 追加。
- `ControllerKind` references の局所化。
- `InputReportBuilder` が controller-kind branch ではなく profile behavior に依存することの維持。
- unsupported input tests の維持。

## 3. 対象外

- 新しい HID descriptor bytes の追加。
- Joy-Con descriptor の source / hardware audit なしの変更。
- public root API への profile class export。
- controller class model の変更。これは unit_040 で扱う。
- public config / transport seam の変更。これは unit_041 / unit_042 で扱う。

## 4. 関連 docs

- `spec/rearchitecture/02-as-is-to-be.md`
- `spec/rearchitecture/04-runtime-profile-transport-details.md`
- `spec/rearchitecture/05-milestones-implementation.md`
- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- `spec/complete/unit_030/JOYCON_PROFILE_IDENTITY_SPI.md`
- `spec/complete/unit_036/JOYCON_SDP_IDENTITY_POLICY.md`
- `spec/complete/unit_037/JOYCON_DEFAULT_CONTROLLER_COLORS.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | 既存 descriptor / button map / device info 値を module 移動した。新しい descriptor / byte layout は追加していない。既存 source-audit fixture と unit tests を維持した |
| Bumble / transport | not applicable | done | SDP policy value の移動はあるが、Bumble transport behavior は変更していない |
| OS / driver / adapter | not applicable | not applicable | adapter open や実機接続は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Pro profile | `ProControllerProfile` | 既存 button map、descriptor、device info、colors、report period を維持する | behavior-preserving |
| Joy-Con L profile | `JoyConLeftProfile` | left stick / left buttons / side default colors を維持する | unsupported input は維持 |
| Joy-Con R profile | `JoyConRightProfile` | right stick / right buttons / side default colors を維持する | unsupported input は維持 |
| kind references | scan `src/swbt` | `ControllerKind` 分岐は profiles / config / controllers / tests に局所化される | runtime に漏らさない |
| public API | `swbt.__all__` | profile classes を含まない | internal deep import は許可 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | profile split 後も Pro input report golden tests が通る | regression | unit | no | `tests/unit/test_input_report.py` |
| done | Joy-Con L/R unsupported button / stick behavior が変わらない | regression | unit | no | `tests/unit/test_input_report.py` |
| done | virtual SPI flash が各 profile の device info / colors を維持する | regression | unit | no | `tests/unit/test_virtual_spi_flash.py` |
| done | `ControllerKind` references が許可範囲に局所化されている | new | unit | no | `tests/unit/test_protocol_profile.py` |
| done | root public API が profile classes を export しない | regression | unit | no | `tests/unit/test_public_api_boundary.py`, `tests/unit/test_package_import.py` |
| done | `protocol/profile.py` を残す場合は internal-only re-export である | characterization | unit | no | production imports は split modules を使う |
| done | public API docstring が Google style で引数名を列挙する | regression | unit | no | `tests/unit/test_public_api_docstrings.py` |

## 8. 設計メモ

この unit は file size を減らすこと自体が目的ではない。HID descriptor、button map、SDP policy、colors、device info payload の変更理由を分けることが目的である。

`src/swbt/protocol/profile.py` は internal compatibility re-export として残す。production code は split modules を import し、root public export には profile classes を戻さない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profiles/base.py` | add | base profile types |
| `src/swbt/protocol/profiles/pro_controller.py` | add | Pro profile |
| `src/swbt/protocol/profiles/joycon.py` | add | Joy-Con L/R profiles |
| `src/swbt/protocol/buttons.py` | add | button maps |
| `src/swbt/protocol/descriptors.py` | add | HID descriptors |
| `src/swbt/protocol/sdp.py` | not added | SDP policy helpers は profile module 内に残した |
| `src/swbt/protocol/profile.py` | modify | internal re-export |
| `tests/unit/test_protocol_profile.py` | modify | profile behavior tests |
| `tests/unit/test_public_api_boundary.py` | existing | root export guardrail |
| `tests/unit/test_public_api_docstrings.py` | modify | public API Google style docstring guardrail |
| `tests/unit/test_input_report.py` | existing | report regression |
| `tests/unit/test_virtual_spi_flash.py` | existing | SPI regression |
| `spec/complete/unit_043/PROTOCOL_PROFILE_MODULE_SPLIT.md` | move | 完了した作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 依存変更なし |
| `uv run ruff format --check .` | pass | 90 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` | pass | 354 passed |
| `uv run pytest tests/integration -q` | pass | 93 passed |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。既存 protocol behavior の unit tests で検証する |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | なし |
| cleanup | なし |

## 12. 先送り事項

- Joy-Con 用の新 HID descriptor を追加する場合は、この unit に混ぜず source-audit 付きの別 unit にする。
- `InputCapabilities` 導入は必須ではない。導入する場合は behavior-preserving で扱う。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
