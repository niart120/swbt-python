# SwitchGamepad Input API Contract 仕様書

## 1. 概要

### 1.1 目的

`SwitchGamepad` の入力 API を、state update API、action API、complete state API に分けて定義する。利用者が短く書ける API は維持しつつ、接続要求、即時送信、同時性の保証範囲を曖昧にしない。

この unit では、`apply(state)` と `sticks(left=None, right=None)` を採用し、既存の `set_input(state)` は廃止する。互換 alias は残さない。`sticks()` は `Stick` だけを受ける state update API として追加し、tuple や raw int tuple は受け入れない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #28 | input API の責務整理。state update、action、complete state の分類、`apply()` / `sticks()` の判断、macro / sequence を追加しない方針 | https://github.com/niart120/swbt-python/issues/28 |
| user clarification | `set_input()` は廃止し、互換目的の alias は残さない | conversation, 2026-07-04 |
| current implementation | `press()` / `release()` / `neutral()` / `set_input()` / `tap()` の現状。`apply()` と `sticks()` は未実装 | `src/swbt/gamepad/core.py` |
| current implementation | `InputState.with_sticks(left_stick=..., right_stick=...)` と `Stick.normalized()` / `Stick.raw()` は実装済み | `src/swbt/input.py` |
| current implementation | `InputStateStore` は button 更新、complete state replacement、neutral を持つが stick 更新 helper はない | `src/swbt/state_store.py` |
| initial design | 公開 API、入力状態、`set_input()`、`tap()`、`press()` / `release()` の位置付け | `spec/initial/api.md` |
| completed unit | M5 入力操作 API。`tap()`、`press()` / `release()`、`set_input()`、`status()` の既存 contract | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| completed unit | post-M5 入力意味検証。D-pad と left / right stick の実機反映観測 | `spec/complete/unit_013/POST_M5_INPUT_SEMANTIC_CHARACTERIZATION.md` |
| completed unit | API hardening。`tap()` fail-safe、`press()` / `release()` の非即時送信 docstring、top-level export | `spec/complete/unit_017/SWITCH_GAMEPAD_API_HARDENING.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `await pad.press(Button.B)` | local input state に B が追加される | 接続を要求せず、即時送信を保証しない |
| library user | `await pad.sticks(left=Stick.normalized(x=0.0, y=1.0))` | left stick だけが置き換わる | `Stick` を明示し、tuple は受けない |
| library user | `await pad.tap(Button.A)` | 接続済みなら押下 report と release report が即時送信される | 未接続では `ClosedError` |
| library user | `await pad.apply(InputState.neutral().with_buttons([...]))` | 完成済み `InputState` が current state を丸ごと置き換える | 接続を要求せず、即時送信を保証しない |
| library user | button と stick を同一 report に収めたい | `InputState` を作って `apply()` に渡す | 複数 state update 呼び出しの同時性は保証しない |
| maintainer | public docs / agent brief を書く | 未実装の `hold()`、`sequence()`、`send_current_input()` を案内しない | docs は実装済み API と一致させる |

## 2. 対象範囲

- 入力 API を state update API、action API、complete state API に分類する。
- `SwitchGamepad.apply(state: InputState)` を追加する。
- `SwitchGamepad.set_input(state)` は廃止する。互換 alias は残さない。
- `SwitchGamepad.sticks(left: Stick | None = None, right: Stick | None = None)` を追加する。
- `InputStateStore` に stick 更新 helper を追加するか、`SwitchGamepad.sticks()` 内で snapshot から complete state を作るかを実装時に決める。
- `press()`、`release()`、`sticks()`、`neutral()`、`apply()` は接続を要求しない state update API として固定する。
- state update API は即時送信を保証しないことを docstring、`spec/initial/api.md`、後続 docs に明記する。
- `tap()` は action API として、接続済みを要求し、押下と release を即時送信する contract を維持する。
- `tap()` は指定 button だけを release し、既存押下状態を維持する contract を regression test で固定する。
- 完全同時入力には `InputState` + `apply()` を使う方針を文書化する。
- `docs/api.md` / `docs/usage.md` / `docs/agent-brief.md` に渡す API contract を整理する。

## 3. 対象外

- sequence runner、macro scheduler、fluent builder。
- `hold()`、`press_for()`、`tilt_stick()`、`apply_buttons_and_sticks()` など用途特化 helper。
- public `send_current_input()`。
- 高水準 IMU helper。
- `tap()` 以外の duration 付き action API。
- HID report byte layout、button bit、stick packing の変更。
- 実機での stick / button 反映の再検証。既存の unit_013 観測を参照する。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/testing.md`
- `spec/initial/roadmap.md`
- `spec/complete/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/complete/unit_013/POST_M5_INPUT_SEMANTIC_CHARACTERIZATION.md`
- `spec/complete/unit_017/SWITCH_GAMEPAD_API_HARDENING.md`
- `tests/integration/test_switch_gamepad_fake_transport.py`
- `tests/unit/test_public_api_docstrings.py`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | API 契約と state 更新 helper の整理であり、button bit、stick packing、report ID、report length は変更しない |
| Bumble / transport | not applicable | not applicable | 接続、advertising、L2CAP、Bumble 型の public exposure は変更しない |
| OS / driver / adapter | not applicable | not applicable | 実機や adapter に依存する新規観測は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| press state update | `await pad.press(Button.B)` | current button set に B が追加される | 接続不要。即時送信は保証しない |
| release state update | `await pad.release(Button.B)` | current button set から B が取り除かれる | 指定外 button は維持する |
| sticks state update | `await pad.sticks(left=Stick.normalized(...))` | left stick だけが置き換わる | `right=None` なら right stick は維持する |
| sticks type boundary | `left=(0.0, 1.0)` など | 受け入れない | 軸の意味と範囲は `Stick` に閉じ込める |
| neutral state update | `await pad.neutral()` | `InputState.neutral()` 相当へ戻る | 接続中なら後続 periodic report で反映される |
| apply complete state | `await pad.apply(state)` | current input state が `state` に丸ごと置き換わる | 差分適用ではない |
| set_input removal | `SwitchGamepad.set_input` | public method として残さない | pre-alpha の API 整理として扱い、互換 alias は置かない |
| action tap | `await pad.tap(Button.A)` | 押下状態を即時送信し、duration 後に指定 button だけ release して即時送信する | 接続済みを要求する |
| tap preserves held buttons | ZL を press 済みで `tap(Button.A)` | tap 前後で ZL は維持される | Issue #28 の例を固定する |
| simultaneous input | `press()` の直後に `sticks()` | 同一 HID report に収まる保証はない | 完全同時入力は `InputState` + `apply()` |
| docs contract | public docs / agent brief | 未実装 API を案内しない | 後続 unit_022 の前提 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `SwitchGamepad.apply(state)` が snapshot を complete replacement する | new | integration | no | `InputState` 全体の置き換えとして固定する |
| todo | `SwitchGamepad.set_input` が public method として残っていない | breaking cleanup | unit / integration | no | pre-alpha の整理として互換 alias は置かない |
| todo | `sticks(left=...)` は left stick だけを更新し、right stick と button set を維持する | new | integration | no | fake transport の次 periodic report で確認 |
| todo | `sticks(right=...)` は right stick だけを更新し、left stick と button set を維持する | new | integration | no | left / right を分けて固定 |
| todo | `sticks(left=..., right=...)` は左右 stick を同じ committed state に更新する | new | integration | no | helper 内の state replacement を確認 |
| todo | `sticks()` は tuple や raw int tuple を受けず、`Stick` だけを受ける | edge | unit / integration | no | runtime validation が必要なら `InvalidInputError` |
| todo | `press()` / `release()` / `sticks()` / `neutral()` / `apply()` は未接続でも state update できる | regression | integration | no | open 前または fake transport 未接続で確認 |
| todo | state update API は即時 interrupt report を送らない | regression | integration | no | report count が増えないことを確認 |
| todo | `tap(Button.A)` は未接続時に state を残さず `ClosedError` を投げる | regression | integration | no | unit_017 の contract を維持 |
| todo | `tap(Button.A)` は既存押下 button を維持し、A だけ release する | new | integration | no | `press(Button.ZL)` 後の tap で確認 |
| todo | docstring が state update、action、complete state の違いを説明する | regression | unit | no | `tests/unit/test_public_api_docstrings.py` |
| todo | `spec/initial/api.md` が `apply()` / `sticks()` 採用と `set_input()` 廃止に一致する | docs | unit | no | docs drift 防止 |
| deferred | sequence runner / macro API を設計する | deferred | docs | no | この unit では追加しない |

## 8. 設計メモ

- `apply()` は「今すぐ 1 report を送る」API ではなく、complete `InputState` replacement である。
- `set_input()` は残さない。pre-alpha の段階で互換 alias を増やすと、public docs と AI エージェント向け brief に二重の入口が残り、complete state API の推奨名が曖昧になる。
- 既存 README、examples、tests、`spec/initial/api.md` の `set_input()` 記述は `apply()` へ寄せる。
- `sticks()` は `Stick` を受ける。`tuple[float, float]` を受けると軸の単位が normalized なのか raw なのか曖昧になる。
- `press()` + `sticks()` のような複数 state update 呼び出しは、report loop の境界によって別 report になり得る。この挙動は失敗ではなく契約として文書化する。
- `tap()` は action API として例外的に即時送信する。長い入力列や macro はこの API に押し込まない。
- 後続の docs unit は、この unit の採用結果を public API の正本として扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/core.py` | modify | `apply()`、`sticks()`、docstring、state update / action contract |
| `src/swbt/state_store.py` | modify | stick state update helper または replacement helper |
| `src/swbt/input.py` | modify | 必要なら helper naming / docstring を更新。value object の範囲は変えない |
| `spec/initial/api.md` | modify | `apply()` / `sticks()` 採用、`set_input()` 廃止、同時性 contract を反映 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | fake transport integration で API contract を固定 |
| `tests/unit/test_public_api_docstrings.py` | modify | docstring contract を固定 |
| `README.md` | modify | 必要なら最小例の API 名を採用結果へ追従 |
| `examples/*.py` | modify | `set_input()` を使っている例を `apply()` に寄せる |
| `spec/wip/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md` | new / modify | この作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\integration\test_switch_gamepad_fake_transport.py -q` | not run | 実装後に fake transport API contract を確認する |
| `uv run pytest tests\unit\test_public_api_docstrings.py -q` | not run | 実装後に docstring drift を確認する |
| `uv run ruff format --check .` | not run | 実装後の標準 gate |
| `uv run ruff check .` | not run | 実装後の標準 gate |
| `uv run ty check --no-progress` | not run | 実装後の標準 gate |
| `uv run pytest tests\unit` | not run | 実装後の標準 gate |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。この unit は public API と fake transport integration で固定する |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test を追加する場合は、明示承認、対象 adapter、command、cleanup plan を確認する |
| log / artifact | unit / integration test output |
| cleanup | なし |

## 12. 先送り事項

- sequence runner、macro scheduler、fluent builder は初期対象外のままにする。
- `hold()`、`press_for()`、`tilt_stick()`、public `send_current_input()` は追加しない。必要になった場合は別 issue / unit で扱う。
- 高水準 IMU helper は扱わない。IMU は `InputState` の complete state として扱う。
- `set_input()` の互換 alias は先送りしない。この unit で廃止する。

## 13. チェックリスト

このチェックリストは unit_021 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] Issue #28 を起点として対象範囲と対象外を整理した
- [x] TDD Test List の初期案を作成した
- [x] 根拠監査と実機実行条件を記録した
- [ ] `apply()` / `sticks()` を実装し、`set_input()` を廃止した
- [ ] public docs / docstring / initial design を実装結果へ追従した
- [ ] 検証結果を実行結果で更新した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
