# Stick Input Shorthand API 仕様書

## 1. 概要

### 1.1 目的

`Stick.normalized(x=..., y=...)` と `SwitchGamepad.sticks(left=..., right=...)` の既存境界を保ったまま、利用者が単一スティック操作を短く書ける公開 API を追加する。

この unit では、`Stick` に正規化座標の利用者向け生成 shortcut を追加し、`SwitchGamepad` に left / right stick だけを更新する `lstick()` / `rstick()` を追加する。tuple や raw tuple を `SwitchGamepad.sticks()` に受け入れる変更は行わない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #34 | `Stick.tilt()`、方向 preset、`SwitchGamepad.lstick()` / `rstick()` の追加提案と受け入れ条件 | https://github.com/niart120/swbt-python/issues/34 |
| completed unit | `sticks()` は `Stick` だけを受ける state update API であり、tuple を受けない。`press()` / `release()` / `sticks()` / `neutral()` / `apply()` は即時送信を保証しない | `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md` |
| current implementation | `Stick.normalized()` と `Stick.raw()`、`InputState.with_sticks()` は実装済み | `src/swbt/input.py` |
| current implementation | `SwitchGamepad.sticks(left=..., right=...)` は `Stick` 型を検証し、state store に委譲する | `src/swbt/gamepad/core.py` |
| public docs | stick 入力例は現在 `Stick.normalized()` と `sticks(left=...)` を案内している | `docs/api.md`, `docs/usage.md`, `docs/agent-brief.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `await pad.lstick(Stick.up())` | left stick だけが上方向の全倒し状態になる | state update API。即時送信を保証しない |
| library user | `await pad.lstick(Stick.up(0.5))` | left stick だけが上方向の半倒し状態になる | `amount` は `0.0..1.0` |
| library user | `await pad.rstick(Stick.right(amount=0.25))` | right stick だけが右方向の 25% 倒し状態になる | right 以外の入力は維持する |
| library user | `await pad.sticks(left=Stick.tilt(0.7, 0.7))` | left stick が指定した正規化座標へ更新される | `tilt()` は `normalized()` と同じ矩形座標モデル |
| library user | 左右 stick を同じ状態更新で変えたい | `await pad.sticks(left=..., right=...)` を使う | `lstick()` / `rstick()` は単一スティック更新 |
| library user | button と stick を完全に同じ report に入れたい | `InputState` を作って `apply()` する | 複数 state update API 呼び出しの同時性は保証しない |

## 2. 対象範囲

- `Stick.tilt(x: float, y: float) -> Stick` を追加する。
- `Stick.up(amount: float = 1.0) -> Stick` を追加する。
- `Stick.down(amount: float = 1.0) -> Stick` を追加する。
- `Stick.left(amount: float = 1.0) -> Stick` を追加する。
- `Stick.right(amount: float = 1.0) -> Stick` を追加する。
- `SwitchGamepad.lstick(stick: Stick) -> None` を追加する。
- `SwitchGamepad.rstick(stick: Stick) -> None` を追加する。
- `lstick()` / `rstick()` は `sticks(left=...)` / `sticks(right=...)` と同じ state update API として扱う。
- `Stick.tilt()`、方向 preset、`lstick()`、`rstick()` の docstring を追加する。
- `docs/api.md`、`docs/usage.md`、`docs/agent-brief.md` に新しい公開 API と利用例を加筆する。
- public docs / docstring の drift を防ぐ unit test を更新する。
- 必要なら `spec/initial/api.md` と `spec/initial/architecture.md` を公開 API 正本として追従する。

## 3. 対象外

- `SwitchGamepad.sticks()` に tuple / list / raw tuple を受けさせない。
- `Stick.up_right()` などの斜め方向 preset は追加しない。斜め入力は `Stick.tilt(x, y)` で表現する。
- `Stick.normalized(x=..., y=...)` は削除しない。
- `Stick.raw(x=..., y=...)` の意味は変えない。
- `lstick()` / `rstick()` を即時送信 API にしない。
- button と stick の完全同時入力用 shortcut は追加しない。
- HID report byte layout、stick packing、report period、Bumble transport は変更しない。
- 新規 hardware run は行わない。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/testing.md`
- `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md`
- `spec/complete/unit_022/PUBLIC_API_USAGE_HARDWARE_DOCS.md`
- `docs/api.md`
- `docs/usage.md`
- `docs/agent-brief.md`
- `tests/unit/test_input_state.py`
- `tests/integration/test_switch_gamepad_fake_transport.py`
- `tests/unit/test_public_api_docstrings.py`
- `tests/unit/test_public_docs.py`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 既存の `Stick.normalized()` と `SwitchGamepad.sticks()` の上に利用者向け helper を追加する。raw 値変換と report packing は変更しない |
| Bumble / transport | not applicable | not applicable | 接続、advertising、L2CAP、Bumble 型の public exposure は変更しない |
| OS / driver / adapter | not applicable | not applicable | 実機、Bluetooth adapter、driver に依存する新規挙動は扱わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| tilt alias | `Stick.tilt(x, y)` | `Stick.normalized(x=x, y=y)` と同じ raw 値を返す | 利用者向けの短い名前。座標系は既存と同じ |
| tilt range validation | `x` または `y` が `-1.0..1.0` の範囲外 | `InvalidInputError` | 既存 `normalized()` と同じ |
| diagonal tilt | `Stick.tilt(1.0, 1.0)` | 許可する | x/y を個別に検証する矩形座標モデルを維持する |
| upward preset | `Stick.up()` | `Stick.tilt(0.0, 1.0)` と同じ raw 値を返す | y 軸正方向を up と扱う |
| downward preset | `Stick.down()` | `Stick.tilt(0.0, -1.0)` と同じ raw 値を返す | y 軸負方向 |
| left preset | `Stick.left()` | `Stick.tilt(-1.0, 0.0)` と同じ raw 値を返す | x 軸負方向 |
| right preset | `Stick.right()` | `Stick.tilt(1.0, 0.0)` と同じ raw 値を返す | x 軸正方向 |
| partial preset | `Stick.up(0.5)` など | 指定方向の半倒しを表す | `amount=0.0` は中央と同じ |
| amount validation | `amount < 0.0` または `amount > 1.0` | `InvalidInputError` | direction preset 専用の入力検証を追加する |
| left stick shorthand | `await pad.lstick(stick)` | left stick だけを置き換える | `await pad.sticks(left=stick)` と同じ state update |
| right stick shorthand | `await pad.rstick(stick)` | right stick だけを置き換える | `await pad.sticks(right=stick)` と同じ state update |
| type boundary | `await pad.lstick((0.0, 1.0))` | `InvalidInputError` | `sticks()` と同じく `Stick` だけを受ける |
| state update timing | `lstick()` / `rstick()` | 接続を要求せず、即時送信を保証しない | 接続中は後続 periodic report で反映される |
| public docs | API docs と usage docs | 新しい short form と既存 `sticks()` / `apply()` の使い分けが分かる | public API 変更のため docs 加筆を完了条件に含める |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `Stick.tilt(x, y)` が `Stick.normalized(x=x, y=y)` と同じ raw 値を返す | new | unit | no | `tests/unit/test_input_state.py` |
| green | `Stick.tilt()` の x/y 範囲外は `InvalidInputError` になる | regression | unit | no | `normalized()` の境界を継承する |
| green | `Stick.tilt(1.0, 1.0)` を許可する | edge | unit | no | 円形制約は追加しない |
| green | `Stick.up()` / `down()` / `left()` / `right()` が全倒し方向を返す | new | unit | no | y 正方向を up として固定する |
| green | `Stick.up(0.5)` などで半倒しを表現できる | new | unit | no | raw 値は `normalized()` の変換に従う |
| green | `amount < 0.0` または `amount > 1.0` は `InvalidInputError` になる | edge | unit | no | preset 共通の validation |
| green | `SwitchGamepad.lstick(stick)` が left stick だけを置き換える | new | integration | no | right stick と button set を維持する |
| green | `SwitchGamepad.rstick(stick)` が right stick だけを置き換える | new | integration | no | left stick と button set を維持する |
| green | `lstick()` / `rstick()` は接続を要求せず、即時 interrupt report を送らない | regression | integration | no | state update API contract |
| green | `lstick()` / `rstick()` は tuple を受けず `InvalidInputError` にする | edge | integration | no | `sticks()` の型境界と同じ |
| green | `SwitchGamepad.sticks()` は引き続き `Stick` だけを受け、tuple は受けない | regression | integration | no | unit_021 の既存 test を維持する |
| green | public docstring が新しい `Stick` factory と `lstick()` / `rstick()` を説明する | docs | unit | no | `tests/unit/test_public_api_docstrings.py` |
| green | `docs/api.md` が `Stick.tilt()`、方向 preset、`lstick()` / `rstick()` を扱う | docs | unit | no | `tests/unit/test_public_docs.py` |
| green | `docs/usage.md` が単一スティック操作の短い例と `sticks()` / `apply()` の使い分けを示す | docs | unit | no | issue #34 の受け入れ条件 |
| green | `docs/agent-brief.md` が `lstick()` / `rstick()` を実装済み API として案内し、tuple 入力を作らせない | docs | unit | no | public API 変更に伴う agent 向け追従 |

## 8. 設計メモ

- `Stick.tilt()` は `Stick.normalized()` の別名として実装する。`normalized()` は座標系を明示する名前として残し、短い利用例では `tilt()` と方向 preset を推奨する。
- 方向 preset の `amount` は `0.0..1.0` とする。負の値で逆方向を表す API にはしない。逆方向は `down()` / `left()` などの別メソッドを使う。
- `Stick.tilt(1.0, 1.0)` は許可する。既存の `normalized()` は x/y を個別に `-1.0..1.0` で検証しており、この unit で円形可動域への丸めを導入しない。
- `lstick()` / `rstick()` は thin wrapper として `sticks(left=...)` / `sticks(right=...)` へ委譲する。これにより、型検証、state store 更新、即時送信しない contract を `sticks()` と揃える。
- `docs/api.md` は公開 API 正本なので、API table、input model、同時入力の注意書きを更新する。
- `docs/usage.md` は issue #34 の利用例を反映し、単一スティック操作では `lstick()` / `rstick()` を示す。左右同時更新は `sticks()`、button と stick の完全同時入力は `InputState` + `apply()` として残す。
- `docs/agent-brief.md` は AI エージェントが tuple や未実装 helper を生成しないよう更新する。
- `spec/initial/api.md` と `spec/initial/architecture.md` は初期設計の正本であり、実装時に公開 API 一覧と利用例を追従する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/input.py` | modify | `Stick.tilt()`、方向 preset、`amount` validation、docstring |
| `src/swbt/gamepad/core.py` | modify | `SwitchGamepad.lstick()` / `rstick()`、docstring |
| `spec/initial/api.md` | modify | `Stick` factory と `lstick()` / `rstick()`、docs examples を追従 |
| `spec/initial/architecture.md` | modify | `SwitchGamepad` の公開入力 API 一覧を追従 |
| `docs/api.md` | modify | public API table、Input Model、stick 入力の使い分けを更新 |
| `docs/usage.md` | modify | `Stick.up()`、`Stick.tilt()`、`lstick()` / `rstick()` の利用例を追加 |
| `docs/agent-brief.md` | modify | 実装済み single-stick API と tuple 禁止を反映 |
| `tests/unit/test_input_state.py` | modify | `Stick` shortcut factory の単体 test |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | `lstick()` / `rstick()` の state update contract |
| `tests/unit/test_public_api_docstrings.py` | modify | 新規 public method / factory の docstring contract |
| `tests/unit/test_public_docs.py` | modify | docs と public API の整合確認 |
| `spec/complete/unit_024/STICK_INPUT_SHORTHAND_API.md` | move / modify | この作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_input_state.py tests\integration\test_switch_gamepad_fake_transport.py::test_lstick_updates_only_left_stick_and_preserves_buttons_and_right_stick tests\integration\test_switch_gamepad_fake_transport.py::test_rstick_updates_only_right_stick_and_preserves_buttons_and_left_stick tests\integration\test_switch_gamepad_fake_transport.py::test_lstick_and_rstick_reject_tuple_inputs tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_require_connection tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_send_immediate_interrupt_reports tests\unit\test_public_api_docstrings.py tests\unit\test_public_docs.py -q` | red | 1 collection error。`Stick.up` 未実装を確認 |
| `uv run pytest tests\unit\test_input_state.py tests\integration\test_switch_gamepad_fake_transport.py::test_lstick_updates_only_left_stick_and_preserves_buttons_and_right_stick tests\integration\test_switch_gamepad_fake_transport.py::test_rstick_updates_only_right_stick_and_preserves_buttons_and_left_stick tests\integration\test_switch_gamepad_fake_transport.py::test_lstick_and_rstick_reject_tuple_inputs tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_require_connection tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_send_immediate_interrupt_reports tests\unit\test_public_api_docstrings.py tests\unit\test_public_docs.py -q` | pass | 48 passed |
| `uv sync --dev` | pass | Resolved 53 packages。docs group 依存 12 件は dev sync 対象外として uninstall された |
| `uv run ruff format --check .` | pass | 71 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 195 passed |
| `uv run pytest tests\integration -q` | pass | 66 passed |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。この unit は public API helper と fake transport integration で固定する |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test を追加する場合は、明示承認、対象 adapter、command、cleanup plan を確認する |
| log / artifact | unit / integration test output、docs diff |
| cleanup | なし |

## 12. 先送り事項

- 斜め方向 preset は追加しない。必要になった場合は別 issue / unit で扱う。
- sequence runner、macro scheduler、fluent builder は初期対象外のままにする。
- `sticks()` の tuple 受け入れは先送りではなく対象外とする。曖昧な座標単位を API 境界へ持ち込まない。
- 実機での新規 stick 反映観測は行わない。raw 値変換と report packing を変えないため、unit / integration test で足りる。

## 13. チェックリスト

このチェックリストは unit_024 の作業完了状態を示す。仕様書の初期作成だけで実装完了扱いにしない。

- [x] Issue #34 を起点として対象範囲と対象外を整理した
- [x] TDD Test List の初期案を作成した
- [x] public API 変更に伴う docs / docstring 更新対象を記録した
- [x] 根拠監査と実機実行条件を記録した
- [x] `Stick` shortcut factory を実装した
- [x] `SwitchGamepad.lstick()` / `rstick()` を実装した
- [x] public docs / docstring / initial design を実装結果へ追従した
- [x] 検証結果を実行結果で更新した
- [x] 完了条件を満たしたため `spec/complete` へ移動する
