# Internal API Boundary Cleanup 仕様書

## 1. 概要

### 1.1 目的

controller rearchitecture 後に残っている内部 API 境界を締める。公開 controller class が profile 選択を所有する設計に合わせ、内部 seam から不整合な controller/profile の組み合わせを作れないようにする。

同時に、config class と profile module path の見え方を internal API に揃え、release notes の migration table を GitHub 上で読みやすい Markdown table として固定する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub issue | リアーキ後の内部 API 境界整理。profile mismatch guard、config private rename、profile shim 削除、release notes table 修正を要求 | `https://github.com/niart120/swbt-python/issues/65` |
| current implementation | `ProController._from_config()` が Joy-Con profile を拒否せず、Joy-Con 側だけ重複 guard を持つ | `src/swbt/gamepad/core.py` |
| current implementation | `SwitchGamepadConfig` は root public API から外れているが、class 名は public に見える | `src/swbt/gamepad/_config.py` |
| current implementation | `swbt.protocol.profile` が compatibility re-export として残っている | `src/swbt/protocol/profile.py` |
| release docs | migration table の文言と表構造を release-ready な形に揃える | `docs/release-notes.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| internal test helper | `ProController._from_config(_SwitchGamepadConfig(profile=JoyConLeftProfile()))` | `InvalidInputError` を送出する | public constructor には profile 引数を戻さない |
| internal code | config class を import する | `_SwitchGamepadConfig` を使い、名前から internal API だと分かる | compatibility alias は追加しない |
| protocol maintainer | profile class を import する | `swbt.protocol.profiles.*` から import する | `swbt.protocol.profile` の旧 path を残さない |
| release reviewer | `docs/release-notes.md` を GitHub で読む | migration guide が 3 column table として読める | 内容は 0.2.0 rearchitecture migration に限定する |

## 2. 対象範囲

- `_RuntimeBackedGamepad._from_config()` に controller profile kind の共通 mismatch guard を追加する。
- Joy-Con 固有 `_from_config()` の重複 guard を削除し、共通 guard に寄せる。
- `SwitchGamepadConfig` を `_SwitchGamepadConfig` に rename する。
- 内部 import、internal helper、unit / integration tests を `_SwitchGamepadConfig` に更新する。
- `src/swbt/protocol/profile.py` を削除する。
- production code と tests の profile import を `swbt.protocol.profiles.*`、`swbt.protocol.buttons`、`swbt.protocol.descriptors` へ一元化する。
- `docs/release-notes.md` の migration guide table を Markdown table として整形し、対応する release gate docs test を更新する。
- `spec/initial/architecture.md` の package/module 表記が旧 `protocol/profile.py` を案内しないように更新する。

## 3. 対象外

- 新しい controller profile、HID descriptor、button bit、SPI address の追加。
- public constructor への `profile` / `transport` / `device_name` 引数の再追加。
- `SwitchGamepadConfig` の互換 alias 追加。
- `swbt.protocol.profile` の deprecation period 追加。
- Bumble adapter open、Switch pairing、HID advertising、periodic report loop の実行。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/naming.md`
- `spec/initial/testing.md`
- `spec/complete/unit_040/PUBLIC_CONTROLLER_API_MODEL.md`
- `spec/complete/unit_041/CONTROLLER_CONFIG_PROFILE_OWNERSHIP.md`
- `spec/complete/unit_043/PROTOCOL_PROFILE_MODULE_SPLIT.md`
- `spec/complete/unit_044/REARCHITECTURE_DOCS_RELEASE_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | profile module import path と controller/config 境界の整理であり、新しい report byte、descriptor、SPI address は追加しない |
| Bumble / transport | not applicable | not applicable | transport 実装や Bumble API の仮定は変更しない |
| OS / driver / adapter | not applicable | not applicable | adapter open や OS driver 操作を行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile mismatch guard | concrete controller class と config profile kind が一致しない | `InvalidInputError` | Pro / Joy-Con L / Joy-Con R で共通 |
| matching profile | concrete controller class と config profile kind が一致する | `_from_config()` が controller を返す | fake transport で検証する |
| private config | `swbt.gamepad._config` | `_SwitchGamepadConfig` が存在し、`SwitchGamepadConfig` は存在しない | internal API の名前を揃える |
| profile import path | `swbt.protocol.profile` | module が存在しない | split modules が唯一の import path |
| release notes table | migration guide | `Old API / New API / Notes` の 3 column table として読める | issue #65 の推奨表に合わせる |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `_from_config()` が concrete controller と一致しない profile kind を拒否する | regression | unit | no | Pro Controller に Joy-Con profile を渡す case を含める |
| todo | internal config class が `_SwitchGamepadConfig` としてだけ import できる | new | unit | no | root public API には既に出ていないため internal module boundary を固定する |
| todo | `swbt.protocol.profile` が削除され、profile imports が split modules に一元化されている | regression | unit | no | production code と tests の旧 import path を拒否する |
| todo | release notes の migration guide が期待する Markdown table rows を持つ | regression | unit | no | 表示崩れを内容と行単位で固定する |

## 8. 設計メモ

`_RuntimeBackedGamepad._from_config()` は public API ではないが、tests と internal helper が使う construction seam である。この seam でも concrete class が profile 選択を所有するという設計ルールを破れないようにする。

`_SwitchGamepadConfig` は runtime/test setup 専用の値であり、利用者向け extension point ではない。pre-release の boundary cleanup なので互換 alias は追加しない。

`swbt.protocol.profile` は unit_043 では internal compatibility re-export として残したが、issue #65 では release-ready 前の曖昧さとして扱う。今回削除し、旧 path の案内や test import を残さない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/_config.py` | modify | `_SwitchGamepadConfig` rename |
| `src/swbt/gamepad/core.py` | modify | 共通 profile mismatch guard |
| `src/swbt/gamepad/runtime.py` | modify | `_SwitchGamepadConfig` import 更新 |
| `src/swbt/_testing/gamepad.py` | modify | internal config import 更新 |
| `src/swbt/protocol/profile.py` | delete | compatibility shim 削除 |
| `tests/unit/` | modify | new regression tests と import path 更新 |
| `tests/integration/` | modify | `_SwitchGamepadConfig` と split profile import へ更新 |
| `docs/release-notes.md` | modify | migration table 整形 |
| `spec/initial/architecture.md` | modify | protocol profile module layout 更新 |
| `spec/wip/unit_045/INTERNAL_API_BOUNDARY_CLEANUP.md` | add / modify | 作業仕様と検証結果 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | not run | 実装後に標準 gate として実行する |
| `uv run ruff format --check .` | not run | 実装後に標準 gate として実行する |
| `uv run ruff check .` | not run | 実装後に標準 gate として実行する |
| `uv run ty check --no-progress` | not run | 実装後に標準 gate として実行する |
| `uv run pytest tests/unit -q` | not run | 実装後に標準 gate として実行する |
| `uv run pytest tests/integration -q` | not run | profile import と internal config rename が integration tests に影響するため実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。unit / integration tests と docs tests で検証する |
| adapter | なし |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | なし |
| cleanup | なし |

## 12. 先送り事項

- none

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [ ] 検証結果または未実行理由を記録した
