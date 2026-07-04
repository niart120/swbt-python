# IMU Input Shorthand API 仕様書

## 1. 概要

### 1.1 目的

Issue #39 の提案を受理し、IMU 入力を短く組み立てる公開 API を追加する。

この unit では、`IMUFrame` に accelerometer / gyroscope 用の生成 helper と部分更新 helper を追加し、`InputState` と `SwitchGamepad` から IMU 3 frame を更新できるようにする。既存の `InputState.imu_frames` と `0x30` input report の IMU packing は維持する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #39 | `IMUFrame.raw()`、`gyro()`、`accel()`、`with_gyro()`、`with_accel()`、`InputState.with_imu()`、`with_gyro()`、`with_accel()`、`SwitchGamepad.imu()` の追加提案と受け入れ条件 | https://github.com/niart120/swbt-python/issues/39 |
| completed unit | `press()` / `release()` / `sticks()` / `neutral()` / `apply()` は接続を要求せず、即時送信を保証しない state update API | `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md` |
| completed unit | public API helper 追加時は docs、docstring、initial design、unit/integration test を同じ unit で追従する | `spec/complete/unit_024/STICK_INPUT_SHORTHAND_API.md` |
| work-start implementation | 作業開始時点では `IMUFrame.neutral()` と `InputState.imu_frames` は実装済みで、IMU shorthand と `SwitchGamepad.imu()` は未実装だった | `src/swbt/input.py`, `src/swbt/gamepad/core.py` |
| initial design | 作業開始時点では、IMU frame を値オブジェクトで表す一方、高水準 API として公開するかは未決だった | `spec/initial/protocol.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `IMUFrame.gyro(100, 0, 0)` | gyro だけが指定された `IMUFrame` を得る | 未指定 accel はゼロ |
| library user | `IMUFrame.accel(z=4096).with_gyro(100, 0, 0)` | accel を維持し、gyro だけを後から設定できる | 物理単位や補正は扱わない |
| library user | `InputState.neutral().with_gyro((100, 0, 0))` | 3 frame すべての gyro が更新され、accel は維持される | sample 数は 1 個または 3 個 |
| library user | `await pad.imu(IMUFrame.gyro(100, 0, 0))` | 現在入力の IMU 3 frame が同じ frame に更新される | state update API。即時送信を保証しない |
| library user | button / stick / IMU を同じ complete state にしたい | `InputState` を組み立てて `apply()` に渡す | 複数 state update API 呼び出しの同時性は保証しない |

## 2. 対象範囲

- `IMUFrame.raw(accel=None, gyro=None) -> IMUFrame` を追加する。
- `IMUFrame.gyro(x=0, y=0, z=0) -> IMUFrame` を追加する。
- `IMUFrame.accel(x=0, y=0, z=0) -> IMUFrame` を追加する。
- `IMUFrame.with_gyro(x=0, y=0, z=0) -> IMUFrame` を追加する。
- `IMUFrame.with_accel(x=0, y=0, z=0) -> IMUFrame` を追加する。
- `InputState.with_imu(*frames: IMUFrame) -> InputState` を追加する。
- `InputState.with_gyro(*samples: tuple[int, int, int]) -> InputState` を追加する。
- `InputState.with_accel(*samples: tuple[int, int, int]) -> InputState` を追加する。
- `SwitchGamepad.imu(*frames: IMUFrame) -> None` を state update API として追加する。
- `InputStateStore` に IMU 更新 helper を追加する。
- `docs/api.md`、`docs/usage.md`、`docs/agent-brief.md` に IMU shorthand と利用例を追加する。
- `spec/initial/api.md`、`spec/initial/architecture.md`、`spec/initial/testing.md`、`spec/initial/protocol.md` を公開 API 正本として追従する。
- unit / integration / docs / docstring test を追加する。

## 3. 対象外

- `pad.gyro()` / `pad.accel()` は追加しない。pad 側の入口は `imu()` に絞る。
- `GyroFrame` / `AccelFrame` のような別型は追加しない。
- `IMUFrame.normalized()` は追加しない。
- `IMUFrame.rest()` / `IMUFrame.gravity()` など、物理姿勢や重力方向を意味する API は追加しない。
- 物理単位、センサー補正、重力方向、姿勢推定は扱わない。
- `IMUFrame.neutral()` の意味は変更しない。全軸ゼロの neutral frame として維持する。
- HID report byte layout、IMU frame packing、report period、Bumble transport は変更しない。
- 新規 hardware run は行わない。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_021/SWITCH_GAMEPAD_INPUT_API_CONTRACT.md`
- `spec/complete/unit_024/STICK_INPUT_SHORTHAND_API.md`
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
| Switch HID / report bytes | not applicable | not applicable | 既存の `IMUFrame` 値と `InputState.imu_frames` を public API から組み立てる。`0x30` report の IMU byte layout と packing は変更しない |
| Bumble / transport | not applicable | not applicable | 接続、advertising、L2CAP、Bumble 型の public exposure は変更しない |
| OS / driver / adapter | not applicable | not applicable | 実機、Bluetooth adapter、driver に依存する新規挙動は扱わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| raw neutral | `IMUFrame.raw()` | `IMUFrame.neutral()` と同じ値を返す | 未指定 accel / gyro はゼロ |
| raw accel | `IMUFrame.raw(accel=(0, 0, 4096))` | accel だけを設定し、gyro はゼロ | i16 validation を使う |
| raw gyro | `IMUFrame.raw(gyro=(100, 0, 0))` | gyro だけを設定し、accel はゼロ | i16 validation を使う |
| raw both | `IMUFrame.raw(accel=(...), gyro=(...))` | accel / gyro の両方を設定する | tuple 長 3 以外は `InvalidInputError` |
| gyro factory | `IMUFrame.gyro(x, y, z)` | `IMUFrame.raw(gyro=(x, y, z))` と同じ値を返す | 未指定軸はゼロ |
| accel factory | `IMUFrame.accel(x, y, z)` | `IMUFrame.raw(accel=(x, y, z))` と同じ値を返す | 未指定軸はゼロ |
| frame with gyro | `frame.with_gyro(x, y, z)` | 既存 accel を維持し、gyro だけを置き換える | immutable copy |
| frame with accel | `frame.with_accel(x, y, z)` | 既存 gyro を維持し、accel だけを置き換える | immutable copy |
| imu frame repeat | `state.with_imu(frame)` | `imu_frames=(frame, frame, frame)` の state を返す | 既存 buttons / sticks は維持 |
| imu frame sequence | `state.with_imu(frame1, frame2, frame3)` | 3 frame を順に設定する | 既存 buttons / sticks は維持 |
| imu frame validation | frame 数が 0、2、4 以上、または `IMUFrame` 以外 | `InvalidInputError` | `SwitchGamepad.imu()` も同じ |
| gyro samples repeat | `state.with_gyro((100, 0, 0))` | 3 frame すべての gyro を上書きし、accel は維持する | sample 数は 1 個または 3 個 |
| gyro samples sequence | `state.with_gyro(sample1, sample2, sample3)` | 各 frame の gyro を順に上書きし、accel は維持する | sample tuple は長さ 3 |
| accel samples repeat | `state.with_accel((0, 0, 4096))` | 3 frame すべての accel を上書きし、gyro は維持する | sample 数は 1 個または 3 個 |
| accel samples sequence | `state.with_accel(sample1, sample2, sample3)` | 各 frame の accel を順に上書きし、gyro は維持する | sample tuple は長さ 3 |
| sample validation | sample 数が 0、2、4 以上、tuple 長が 3 以外、範囲外値 | `InvalidInputError` | tuple 以外も `InvalidInputError` |
| gamepad imu repeat | `await pad.imu(frame)` | 現在入力の IMU 3 frame が `(frame, frame, frame)` になる | state update API。即時送信を保証しない |
| gamepad imu sequence | `await pad.imu(frame1, frame2, frame3)` | 現在入力の IMU 3 frame が順に更新される | 既存 buttons / sticks は維持 |
| gamepad timing | `SwitchGamepad.imu()` | 接続を要求せず、即時 interrupt report を送らない | 接続中は後続 periodic report で反映される |
| public docs | API docs と usage docs | IMU shorthand、`InputState` + `apply()`、`pad.imu()` の使い分けが分かる | 物理単位や補正を案内しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `IMUFrame.raw()` が neutral、accel-only、gyro-only、accel+gyro の値を返す | new | unit | no | `tests/unit/test_input_state.py` |
| green | `IMUFrame.raw()` が tuple 長と i16 範囲を検証する | edge | unit | no | `InvalidInputError` |
| green | `IMUFrame.gyro()` / `accel()` が raw shorthand と同じ値を返す | new | unit | no | 未指定軸はゼロ |
| green | `IMUFrame.with_gyro()` / `with_accel()` が反対側の値を維持して置き換える | new | unit | no | immutable copy |
| green | `InputState.with_imu()` が 1 frame repeat と 3 frame sequence を設定し、buttons / sticks を維持する | new | unit | no | frame validation を含む |
| green | `InputState.with_gyro()` / `with_accel()` が 1 sample repeat と 3 sample sequence を設定し、反対側を維持する | new | unit | no | sample 数 validation を含む |
| green | `InputState.with_gyro()` / `with_accel()` が sample shape と i16 範囲を `InvalidInputError` にする | edge | unit | no | tuple 長 3 以外 |
| green | `SwitchGamepad.imu(frame)` が IMU 3 frame を repeat 更新し、buttons / sticks を維持する | new | integration | no | fake transport |
| green | `SwitchGamepad.imu(frame1, frame2, frame3)` が IMU 3 frame を順に更新する | new | integration | no | fake transport |
| green | `SwitchGamepad.imu()` が frame 数と型を `InvalidInputError` にする | edge | integration | no | `InputState.with_imu()` と同じ |
| green | `SwitchGamepad.imu()` は接続不要で即時 interrupt report を送らない | regression | integration | no | state update API contract |
| green | public docstring が IMU helper と `SwitchGamepad.imu()` を説明する | docs | unit | no | `tests/unit/test_public_api_docstrings.py` |
| green | `docs/api.md` と `docs/usage.md` が IMU shorthand の説明と利用例を含む | docs | unit | no | Issue #39 受け入れ条件 |
| green | `docs/agent-brief.md` が `pad.imu()` と `IMUFrame` helper を案内し、未実装 `pad.gyro()` / `pad.accel()` を禁止する | docs | unit | no | 生成 API drift 防止 |

## 8. 設計メモ

- `IMUFrame.raw()`、`gyro()`、`accel()`、`with_gyro()`、`with_accel()` は、直接 dataclass construction と同じ `-32768..32767` の i16 validation を使う。
- `InputState.with_imu()` と `SwitchGamepad.imu()` は、1 個なら 3 frame に複製し、3 個なら順に使う。0、2、4 個以上は受けない。
- `InputState.with_gyro()` / `with_accel()` は、現在の 3 frame を基準に片側だけ置き換える。これは complete state builder であり、`pad.gyro()` / `pad.accel()` の state update API は追加しない。
- sample tuple は `tuple[int, int, int]` として扱う。list、tuple 長 3 以外、範囲外値は `InvalidInputError` に揃える。
- `SwitchGamepad.imu()` は thin wrapper として `InputStateStore.imu()` へ委譲し、`press()` / `sticks()` と同じく接続不要、即時送信なしの state update API にする。
- `spec/initial/protocol.md` の「IMU 高水準 API は未決」は、この unit の完了時に `IMUFrame` と `InputState` helper は公開済みに更新する。ただし wire format は変更しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/input.py` | modify | `IMUFrame` helper、`InputState.with_imu()` / `with_gyro()` / `with_accel()` |
| `src/swbt/state_store.py` | modify | IMU state update helper |
| `src/swbt/gamepad/core.py` | modify | `SwitchGamepad.imu()`、docstring |
| `spec/initial/api.md` | modify | IMU public API と state update contract を追従 |
| `spec/initial/architecture.md` | modify | `SwitchGamepad` と input model の説明を追従 |
| `spec/initial/protocol.md` | modify | IMU API 未決記述を更新 |
| `spec/initial/testing.md` | modify | IMU helper / fake transport test 方針を追従 |
| `docs/api.md` | modify | public API table、Input Model、IMU 入力の使い分けを更新 |
| `docs/usage.md` | modify | gyro / accel / complete state の利用例を追加 |
| `docs/agent-brief.md` | modify | agent 向け IMU helper と禁止事項を追従 |
| `tests/unit/test_input_state.py` | modify | IMUFrame / InputState IMU helper の単体 test |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | `SwitchGamepad.imu()` の state update contract |
| `tests/unit/test_public_api_docstrings.py` | modify | 新規 public method / factory の docstring contract |
| `tests/unit/test_public_docs.py` | modify | docs と public API の整合確認 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_input_state.py tests\integration\test_switch_gamepad_fake_transport.py::test_imu_updates_repeat_frame_and_preserves_buttons_and_sticks tests\integration\test_switch_gamepad_fake_transport.py::test_imu_updates_three_frames_in_order tests\integration\test_switch_gamepad_fake_transport.py::test_imu_rejects_invalid_frame_counts_and_types tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_require_connection tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_send_immediate_interrupt_reports tests\unit\test_public_api_docstrings.py tests\unit\test_public_docs.py -q` | red | 36 failed, 38 passed。`IMUFrame.raw()` / `gyro()` / `accel()`、`InputState.with_imu()` / `with_gyro()` / `with_accel()`、`SwitchGamepad.imu()`、docs 記述が未実装で失敗することを確認 |
| `uv run pytest tests\unit\test_input_state.py tests\integration\test_switch_gamepad_fake_transport.py::test_imu_updates_repeat_frame_and_preserves_buttons_and_sticks tests\integration\test_switch_gamepad_fake_transport.py::test_imu_updates_three_frames_in_order tests\integration\test_switch_gamepad_fake_transport.py::test_imu_rejects_invalid_frame_counts_and_types tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_require_connection tests\integration\test_switch_gamepad_fake_transport.py::test_state_update_apis_do_not_send_immediate_interrupt_reports tests\unit\test_public_api_docstrings.py tests\unit\test_public_docs.py -q` | pass | 74 passed |
| `uv sync --dev` | pass | Resolved 53 packages。Checked 41 packages |
| `uv run ruff format --check .` | pass | 71 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 221 passed |
| `uv run pytest tests\integration -q` | pass | 69 passed |

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

- 物理単位、センサー補正、重力方向、姿勢推定は扱わない。必要になった場合は別 issue / unit で扱う。
- `pad.gyro()` / `pad.accel()` は追加しない。必要性が出た場合も `pad.imu()` との責務重複を先に整理する。
- 実機での新規 IMU 反映観測は行わない。IMU report packing を変えないため、unit / integration test で足りる。

## 13. チェックリスト

このチェックリストは unit_025 の作業完了状態を示す。仕様書の初期作成だけで実装完了扱いにしない。

- [x] Issue #39 を起点として対象範囲と対象外を整理した
- [x] TDD Test List の初期案を作成した
- [x] public API 変更に伴う docs / docstring 更新対象を記録した
- [x] 根拠監査と実機実行条件を記録した
- [x] `IMUFrame` shortcut factory と frame update helper を実装した
- [x] `InputState` の IMU complete state builder を実装した
- [x] `SwitchGamepad.imu()` を実装した
- [x] public docs / docstring / initial design を実装結果へ追従した
- [x] 検証結果を実行結果で更新した
- [x] 完了条件を満たしたため `spec/complete` へ移動する
