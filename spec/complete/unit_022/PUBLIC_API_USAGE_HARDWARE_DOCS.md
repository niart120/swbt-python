# Public API / Usage / Hardware / Agent Brief Docs 仕様書

## 1. 概要

### 1.1 目的

README に詰め込んでいる公開 API、目的別の使い方、実機依存情報、AI エージェント向けの短縮仕様を `docs/` 配下へ分ける。利用者と AI エージェントが実装済み public API だけを見て、存在しない helper や未保証の接続手順を作らない状態にする。

この unit は GitHub Issue #29 に対応する。API 名の最終判断は `unit_021` の input API contract を前提にし、docs は実装済みの public surface と `swbt.__all__` に合わせる。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #29 | `docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` の追加要件 | https://github.com/niart120/swbt-python/issues/29 |
| prerequisite unit | `apply()` / `sticks()`、`set_input()` 廃止、state update / action / complete state の最終 contract | `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md` |
| current public exports | top-level import surface | `src/swbt/__init__.py` |
| current API implementation | `SwitchGamepad`、connection methods、input methods、status / snapshot | `src/swbt/gamepad/core.py` |
| initial design | 公開 API、入力状態、例外、transport extension point | `spec/initial/api.md` |
| hardware source | 確認済み構成、未確認構成、実機観測の正本 | `docs/hardware-test-log.md` |
| release gate | README / risks に出してよい確認済み / 未確認境界 | `spec/complete/unit_012/INITIAL_RELEASE_GATE.md` |
| risks | OS、driver、dongle、firmware、documentation drift の扱い | `spec/initial/risks.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | public API を調べる | `from swbt import ...` で使う型と method contract が分かる | deep import を通常利用として案内しない |
| library user | 初回接続例を書く | `connect(timeout=..., allow_pairing=True)` と `key_store_path` の意味が分かる | 実機と dongle が必要なことを隠さない |
| library user | button と stick を同時に扱う | complete `InputState` を使うべき場面が分かる | state update API の同時性を過大に書かない |
| hardware user | adapter / driver 問題を切り分ける | 確認済み構成、未確認構成、troubleshooting を辿れる | 未検証構成を保証済みと書かない |
| AI agent | 利用例を生成する | 未実装 API を作らず、public import と最小接続 pattern を使う | agent brief は短く、禁止事項を明示する |

## 2. 対象範囲

- `docs/api.md` を public API の仕様正本として追加する。
- `docs/usage.md` を目的別の利用例として追加する。
- `docs/hardware.md` を実機、Bluetooth adapter、driver、pairing / reconnect、troubleshooting の正本として追加する。
- `docs/agent-brief.md` を AI エージェント向けの短い仕様として追加する。
- README は最小導線に保ち、詳細 docs へのリンクを追加する。
- docs の API 名と import は `src/swbt/__init__.py`、`SwitchGamepad` 実装、`unit_021` の採用結果と一致させる。
- docs は確認済み構成と未確認構成を分け、実機観測は `docs/hardware-test-log.md` 由来に限定する。
- docs に未実装 helper、未保証の reconnect、未確認 OS / dongle の保証を書かない。
- docs drift を防ぐため、必要に応じて unit tests で docs の主要文言と `swbt.__all__` の整合を確認する。

## 3. 対象外

- MkDocs 構成、`mkdocs.yml`、docs site navigation。これは `unit_023`。
- GitHub Pages 公開。
- 自動 API reference 生成。
- `SwitchGamepad` API の実装変更。これは `unit_021`。
- hardware test の新規実行。
- versioned docs。
- Material for MkDocs などの追加 theme。

## 4. 関連 docs

- `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md`
- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_012/INITIAL_RELEASE_GATE.md`
- `docs/hardware-test-log.md`
- `README.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | docs は public API と実機条件を説明する。report byte layout は変更しない |
| Bumble / transport | required | source-from-existing-docs | Bumble version、adapter、driver、pairing / reconnect の説明は既存の hardware log と completed specs から引用し、新規仮説は保証として書かない |
| OS / driver / adapter | required | source-from-existing-docs | 確認済み構成は `docs/hardware-test-log.md` と release gate から転記する。新規実機観測は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| api import policy | `docs/api.md` | public API は `swbt` module root から import すると書く | custom transport 実装者向けに `HidDeviceTransport` を extension point として扱う |
| api connection docs | `connect()` / `pair()` / `reconnect()` / `try_*()` | 成功必須 API と結果返却 APIの違いが分かる | `InvalidKeyStoreError` の扱いも書く |
| api input docs | `press()` / `release()` / `sticks()` / `neutral()` / `tap()` / `apply()` | state update、action、complete state の違いが分かる | `set_input()` は public docs に残さない |
| api value objects | `Button` / `Stick` / `IMUFrame` / `InputState` | factory、範囲、immutable state の意味が分かる | docstring と矛盾させない |
| api diagnostics docs | `DiagnosticsConfig` / `GamepadStatus` | trace writer と status の読み方が分かる | secret material を記録しない |
| usage minimal example | `docs/usage.md` | `async with SwitchGamepad(...): await pad.connect(...); await pad.tap(Button.A)` の最小例がある | adapter open と実機依存を隠さない |
| usage connection examples | 初回 pairing / reconnect / try_* | どの API をどの状態で使うか分かる | `key_store_path` の分離例を含める |
| usage input examples | button / stick / neutral | `tap()` と held button、complete state の使い分けが分かる | 同時性保証を過大にしない |
| hardware confirmed scope | `docs/hardware.md` | Windows / CSR8510 A10 / WinUSB / Bumble 0.0.230 / Switch 2 / firmware 22.1.0 を確認済みとして書く | 別構成へ一般化しない |
| hardware unconfirmed scope | `docs/hardware.md` | Linux、macOS、別 dongle、別 firmware、pairing-free incoming bond reuse を未確認として分ける | 未検証を「できるはず」と書かない |
| hardware troubleshooting | adapter open / pairing timeout / no bond / multiple current peers / input not reflected | 失敗点ごとの切り分けができる | 実装済み diagnostics に合わせる |
| agent brief | `docs/agent-brief.md` | public import、最小接続 pattern、禁止 API が短く分かる | 未実装 API を作らせない |
| README link | README | 詳細 docs へ辿れる | README は入口に留める |
| README size reduction | README | key store 詳細、hardware table、driver troubleshooting を README に戻さず、詳細 docs へ誘導する | `tests/unit/test_readme_docs.py` で固定 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| red then green | `docs/api.md` が `swbt.__all__` と主要 public methods を過不足なく扱う | new | unit | no | `tests/unit/test_public_docs.py` で public export と主要 method token を固定 |
| green | `docs/api.md` が state update / action / complete state の違いを明記する | new | unit | no | `unit_021` の `apply()` / `sticks()` contract に合わせた |
| green | `docs/usage.md` に初回接続、pairing のみ、reconnect のみ、`try_*()` の例がある | new | unit | no | examples は実装済み API だけを使う |
| green | `docs/usage.md` に button、stick、neutral、complete state の例がある | new | unit | no | 同時入力は `InputState` + `apply()` を使う |
| green | `docs/hardware.md` が確認済み構成と未確認構成を分ける | regression | unit | no | README / risks と同じ事実境界を `tests/unit/test_public_docs.py` で固定 |
| green | `docs/hardware.md` が `key_store_path`、no bond、multiple current peers、再 pairing 手順を説明する | new | unit | no | reconnect / key store unit と整合 |
| green | `docs/agent-brief.md` が未実装 API の禁止事項を含む | new | unit | no | `hold()`、`sequence()`、`send_current_input()` など。旧 complete state API 名はユーザ指示により本文へ出さず、absence test で固定 |
| green | README から `docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` へ辿れる | regression | unit | no | `tests/unit/test_readme_docs.py::test_readme_links_public_docs` で固定 |
| green | README に hardware table、driver troubleshooting、key store 復旧手順を戻さない | regression | unit | no | `test_readme_keeps_detailed_hardware_and_key_store_guidance_in_docs` で固定 |
| green | public docs と agent brief に旧 complete state API 名を利用可能 API として残さない | breaking cleanup | unit | no | public docs 全体の absence test で固定し、complete state API は `apply()` に統一する |
| green | docs 内に Poetry 前提、未実装 helper、確認済みでない構成の保証が残っていない | regression | unit | no | `tests/unit/test_public_docs.py::test_public_docs_do_not_carry_stale_or_placeholder_wording` で固定 |
| deferred | MkDocs navigation で docs を閲覧する | deferred | docs | no | `unit_023` で扱う |

## 8. 設計メモ

- `docs/api.md` は public API の正本にする。実装詳細の deep import を通常利用として案内しない。
- `HidDeviceTransport` は Bumble 型ではなく repo-local extension point なので、custom transport 実装者向けに説明してよい。
- `docs/usage.md` は使い方中心にする。API の全引数説明を重複させすぎない。
- `docs/hardware.md` は `docs/hardware-test-log.md` の要約であり、実機ログそのものではない。観測日、構成、未確認範囲を分ける。
- `docs/agent-brief.md` は短く保つ。AI エージェントが未実装 API を作りがちな箇所だけを明示する。
- `unit_021` は完了済みである。docs は `apply()` / `sticks()` / `set_input()` 廃止を現在の public API contract として扱う。
- 2026-07-04 のユーザ指示により、public docs では旧 complete state API 名を明示的に説明しない。利用可能 API として残っていないことは docs absence test で確認する。
- 2026-07-04 のユーザ指示により、追加した docs の見出しは英語に統一する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `docs/api.md` | new | public API 仕様正本 |
| `docs/usage.md` | new | 目的別利用例 |
| `docs/hardware.md` | new | 実機、Bluetooth adapter、driver、pairing / reconnect、troubleshooting |
| `docs/agent-brief.md` | new | AI エージェント向け短縮仕様 |
| `README.md` | modify | 詳細 docs への導線 |
| `tests/unit/test_readme_docs.py` | modify | README から docs への link と stale wording を確認 |
| `tests/unit/test_public_docs.py` | new | public docs と public surface / hardware 境界 / stale wording の整合確認 |
| `tests/unit/test_public_api_docstrings.py` | inspect | docstring contract の既存 gate を局所検証で実行 |
| `tests/unit/test_release_gate_docs.py` | inspect | release gate 境界の既存 gate を局所検証で実行 |
| `spec/complete/unit_022/PUBLIC_API_USAGE_HARDWARE_DOCS.md` | move / modify | この作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_public_docs.py -q` | red | 5 failed。`docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` が未作成であることを確認 |
| `uv run pytest tests\unit\test_public_docs.py tests\unit\test_readme_docs.py -q` | pass | 12 passed。docs 4 本追加、README 導線、README 縮小境界を確認 |
| `uv run pytest tests\unit\test_readme_docs.py tests\unit\test_release_gate_docs.py tests\unit\test_public_api_docstrings.py tests\unit\test_public_docs.py -q` | pass | 15 passed。README、release gate、docstring、public docs drift を確認 |
| `uv sync --dev` | pass | Resolved 41 packages / Checked 41 packages |
| `uv run ruff format --check .` | pass | 69 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 171 passed |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。docs は既存 hardware log と completed specs を根拠にする |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。新規 hardware run が必要になった場合は別 unit または明示承認で扱う |
| log / artifact | unit test output、docs diff |
| cleanup | なし |

## 12. 先送り事項

- MkDocs site 構成、`mkdocs.yml`、`docs/index.md` は `unit_023`。
- GitHub Pages 公開、versioned docs、自動 API reference 生成は対象外。
- 未確認 OS / dongle / firmware の検証は別 unit。
- API 実装変更は `unit_021`。
- 新規 hardware run は行わない。確認済み構成は既存 `docs/hardware-test-log.md` と completed specs の観測から要約した。

## 13. チェックリスト

このチェックリストは unit_022 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] Issue #29 を起点として対象範囲と対象外を整理した
- [x] TDD Test List の初期案を作成した
- [x] 根拠監査と実機実行条件を記録した
- [x] `docs/api.md` / `docs/usage.md` / `docs/hardware.md` / `docs/agent-brief.md` を追加した
- [x] README から各 docs へ辿れるようにした
- [x] docs と `swbt.__all__` / public method contract の整合を確認した
- [x] 検証結果を実行結果で更新した
- [x] 完了条件を満たしたら `spec/complete` へ移動する
