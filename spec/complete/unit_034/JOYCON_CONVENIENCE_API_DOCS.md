# Joy-Con Convenience API Docs 仕様書

## 1. 概要

### 1.1 目的

低レイヤーで Joy-Con L/R profile が動くようになった後、利用者が単体 Joy-Con デバイスとして扱いやすい API と docs を追加する。

この unit では単体 Joy-Con の利用面を優先する。採用した public surface は `JoyCon("left", ...)` / `JoyCon("right", ...)` である。低レイヤーの `JoyConLeftProfile` / `JoyConRightProfile` は利用者向けの top-level API に出さない。左右を束ねる `JoyConPair` の実装は対象外であり、実装する場合は別 issue に分ける。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| parent issue | Joy-Con support plan と順序 | https://github.com/niart120/swbt-python/issues/48 |
| child issue | Joy-Con convenience API と docs | https://github.com/niart120/swbt-python/issues/54 |
| dependency | profile injection public surface | https://github.com/niart120/swbt-python/issues/49 |
| dependency | Joy-Con profile identity | https://github.com/niart120/swbt-python/issues/50 |
| dependency | Joy-Con input validation | https://github.com/niart120/swbt-python/issues/51 |
| dependency | profile-aware subcommand state | https://github.com/niart120/swbt-python/issues/52 |
| dependency | Bumble / SDP profile wiring | https://github.com/niart120/swbt-python/issues/53 |
| initial API | `SwitchGamepad` を中心とする public API 方針 | `spec/initial/api.md` |
| docs | current public API / usage / hardware docs | `docs/api.md`, `docs/usage.md`, `docs/hardware.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Python user | Joy-Con L 単体を作る | adopted public surface で作成例がある | profile class 公開を仮定しない |
| Python user | Joy-Con R 単体を作る | adopted public surface で作成例がある | Pro Controller の既存例を壊さない |
| Python user | Joy-Con 非対応入力を呼ぶ | 例外になることが docs で分かる | 黙って無視すると書かない |
| hardware user | 左右 Joy-Con を使い分ける | key store を左右別 / profile 別に分ける理由が分かる | `JoyConPair` 実装は別 issue |
| maintainer | 未実装範囲 | docs が確認済み範囲と未検証範囲を分ける | 実機未検証を確認済みと書かない |

## 2. 対象範囲

- `JoyCon("left", ...)` / `JoyCon("right", ...)` による単体 Joy-Con 作成例。
- `SwitchGamepad` の薄い wrapper としての `JoyCon` public API。
- Joy-Con L/R の非対応入力が例外になることの利用者向け説明。
- key store を仮想デバイスごと、profile ごと、左右ごとに分ける運用説明。
- 未実装範囲と実機未検証範囲の明記。
- README / docs / docstring / example tests の整合。

## 3. 対象外

- Joy-Con profile の低レイヤー実装そのもの。
- 実機検証に基づく Bluetooth / SDP 細部の調整。
- `JoyConPair` の本実装。実装する場合は別 issue で扱う。
- 左右同時 connect / disconnect の failure / cleanup semantics 設計。
- 既存 `SwitchGamepad` 契約の二重定義。
- 仕様作成時の実機、Bumble adapter、Switch-facing 動作。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/naming.md`
- `docs/api.md`
- `docs/usage.md`
- `docs/hardware.md`
- `docs/agent-brief.md`
- `README.md`
- https://github.com/niart120/swbt-python/issues/48
- https://github.com/niart120/swbt-python/issues/49
- https://github.com/niart120/swbt-python/issues/50
- https://github.com/niart120/swbt-python/issues/51
- https://github.com/niart120/swbt-python/issues/52
- https://github.com/niart120/swbt-python/issues/53
- https://github.com/niart120/swbt-python/issues/54

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | done | この unit は docs / convenience API。新しい protocol byte は追加しない |
| Bumble / transport | required | done | `docs/hardware.md` / `docs/api.md` に profile 別 key store、未検証範囲、承認境界を記録。adapter は開いていない |
| OS / driver / adapter | conditional | done | 新しい実機観測は追加していない。Joy-Con profile の OS / dongle / firmware 横断互換は未検証として記録 |

### 5.1 監査方針

- docs 例は採用済み public API だけを使う。利用者向け例は `JoyCon("left", ...)` / `JoyCon("right", ...)` に統一し、`JoyConLeftProfile` / `JoyConRightProfile` は出さない。
- 実機未検証の OS、dongle、firmware、Joy-Con profile 動作は確認済みと書かない。
- key store 分離の理由は、1 つの仮想 Bluetooth HID device が 1 つの profile と pairing identity を持つ前提に基づいて説明する。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Pro docs regression | existing Pro Controller examples | 既存例が維持される | docs 変更で破壊しない |
| Joy-Con L docs | adopted public surface | Joy-Con L 単体の作成例がある | profile class 公開を仮定しない |
| Joy-Con R docs | adopted public surface | Joy-Con R 単体の作成例がある | same |
| unsupported input docs | Joy-Con L/R unsupported inputs | 例外になることを明記する | unit_031 と整合 |
| key store docs | left / right / Pro profiles | key store を分ける運用を説明する | 同じ file を使い回す例を出さない |
| convenience wrapper | optional `JoyCon` class | `SwitchGamepad` の薄い wrapper に留める | connection / close 契約を二重管理しない |
| pair docs | `JoyConPair` | 方針説明まで。実装する場合は別 issue | この unit の実装対象外 |
| unsupported scope docs | `0x3F`, rumble waveform, IMU axis conversion, calibration, pair orchestration, cross-firmware guarantee | 未実装 / 未検証として明記する | 確認済みのように書かない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | Pro Controller の既存 README / docs examples が維持されている | regression | docs / unit | no | `test_public_docs` / `test_readme_docs` |
| done | Joy-Con L 単体の docs example が adopted public surface と一致する | new | docs / unit | no | `JoyCon("left", ...)` |
| done | Joy-Con R 単体の docs example が adopted public surface と一致する | new | docs / unit | no | `JoyCon("right", ...)` |
| done | profile classes が public でない場合、docs example が internal class を import しない | edge | docs / unit | no | `JoyConLeftProfile` / `JoyConRightProfile` を public docs から排除 |
| done | convenience wrapper を追加する場合、`SwitchGamepad` の薄い wrapper として動く | new | unit / integration | no | `JoyCon` を追加 |
| done | docs が Joy-Con 非対応入力の例外を説明する | new | docs / unit | no | `UnsupportedInputError` |
| done | docs が key store を左右別 / profile 別に分ける理由を説明する | new | docs / unit | no | unit_033 と整合 |
| done | docs が `JoyConPair` 実装をこの unit の範囲として扱っていない | regression | docs / unit | no | 別 issue への分割 |
| done | docs が実機未検証範囲を確認済みと書いていない | regression | docs / unit | no | hardware wording |
| done | public API docstrings / `__all__` が adopted public surface と一致する | new / regression | unit | no | `JoyCon` top-level export |

## 8. 設計メモ

- public surface は `JoyCon("left", ...)` / `JoyCon("right", ...)` とした。`SwitchGamepad(profile=JoyConLeftProfile())`、`SwitchGamepad(controller=ControllerKind.JOYCON_LEFT)`、factory helper は利用者向け docs に載せない。
- `JoyCon` は既存 `SwitchGamepad` の constructor / connect / close / input API を薄く包む。独自 lifecycle を持たせない。
- self-review で、`JoyCon` が `SwitchGamepad.from_config()` を継承したままだと Pro profile の `JoyCon` を作れる穴を検出した。`JoyCon.from_config()` は Joy-Con profile 以外を `InvalidInputError` にする。
- `JoyConPair` は 2 つの仮想 HID device を束ねる上位 layer であり、この unit では実装しない。connect / disconnect を束ねる場合の失敗時 cleanup は別設計にする。
- key store は左右別 / profile 別にする。pairing identity と profile が混ざると reconnect や Switch 側表示の診断が難しくなる。
- docs は「未実装」と「実機未検証」を分ける。例えば `0x3F` は未実装、別 firmware の Joy-Con 動作は未検証として扱う。
- self-review で、source-audit fixture の Pro Controller device-info entry が daemon reference tail `01 01` と現行 swbt-python tail `03 02` を混同しやすい文言だったため、reference / current implementation / hardware observation を分けて記録した。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `README.md` | modify | Joy-Con 単体利用の入口と未実装範囲 |
| `docs/api.md` | modify | adopted public surface と examples |
| `docs/usage.md` | modify | Joy-Con L/R 単体の利用例 |
| `docs/hardware.md` | modify | key store 分離、実機未検証範囲、承認境界 |
| `docs/agent-brief.md` | modify | agent 向け Joy-Con scope |
| `spec/initial/api.md` | modify | `JoyCon` public contract |
| `src/swbt/__init__.py` | modify | `JoyCon` top-level export |
| `src/swbt/gamepad/` | modify | `JoyCon` thin wrapper |
| `tests/unit/test_public_docs.py` | modify | docs examples と scope wording |
| `tests/unit/test_readme_docs.py` | modify | README examples |
| `tests/unit/test_package_import.py` | modify | top-level export |
| `tests/unit/test_public_api_boundary.py` | modify | wrapper と public boundary |
| `tests/unit/test_public_api_docstrings.py` | modify | public surface docstring |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | self-review で検出した Pro device-info tail の根拠分類整理 |
| `tests/unit/test_source_audit_fixtures.py` | modify | source-audit fixture の混同防止 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | fake transport で Joy-Con device info reply と invalid side |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | resolved 53 packages / checked 41 packages |
| `uv run ruff format --check .` | pass | 77 files already formatted |
| `uv run ruff check .` | pass | all checks passed |
| `uv run ty check --no-progress` | pass | all checks passed |
| `uv run pytest tests/unit` | pass | 318 passed |
| `uv run pytest tests/integration` | pass | 85 passed |
| `git diff --check` | pass | no whitespace errors |
| `uv run pytest tests/unit/test_public_docs.py tests/unit/test_readme_docs.py tests/unit/test_public_api_docstrings.py tests/unit/test_public_api_boundary.py::test_joycon_public_constructor_is_thin_switch_gamepad_wrapper tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_wrapper_reaches_device_info_reply tests/integration/test_switch_gamepad_fake_transport.py::test_joycon_wrapper_rejects_invalid_side -q` | pass | 21 passed |
| `uv run pytest tests/unit/test_public_api_boundary.py tests/unit/test_public_docs.py tests/unit/test_source_audit_fixtures.py -q` | pass | 46 passed。self-review fixes |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 仕様作成と docs-only checks では不要 |
| 承認範囲 | 後続で docs example を実機実行する場合は、adapter open、HID advertising、pairing または reconnect、periodic report loop、input report、Switch-facing output report / subcommand handling、cleanup の明示承認が必要 |
| adapter | 仕様作成では使用しない。実行時は左右で使う adapter / key store の組み合わせを明示する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実機時は OS、driver、dongle、Bumble version、Python version、Switch model / firmware、profile、key store path、command、result、cleanup を記録する |
| cleanup | neutral、report loop 停止、transport close、adapter release。左右同時実行時は各 device の cleanup を分けて記録する |

## 12. 先送り事項

- `JoyConPair` の実装。必要なら別 issue を作り、2 つの `SwitchGamepad`、左右別 adapter / key store、connect / disconnect failure semantics、cleanup を設計する。
- `0x3F` simple HID report。
- rumble waveform の実処理。
- IMU 軸変換の精密対応。
- 実機完全一致の calibration 値。
- OS / dongle / firmware をまたぐ Joy-Con 実機互換保証。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] docs examples が adopted public surface に一致している
- [x] profile classes が public と決まる前に docs で仮定していない
- [x] `JoyConPair` をこの unit の実装対象にしていない
