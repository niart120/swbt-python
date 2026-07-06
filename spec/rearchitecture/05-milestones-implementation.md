# 05. Milestones / implementation checklist

## M0: Decision freeze and safety tests

目的: 大きく動かす前に、現行挙動と target public boundary を test と docs に固定する。

Work items:

- `spec/rearchitecture/` を追加する。
- 現行 public API の前提を文書化する。
- breaking change を採用することを issue または design note に明記する。
- Target root exports の test を追加する。
- `SwitchGamepad` が abstract である test を追加する。
- Concrete public constructor に `profile`、`device_name`、`transport` がない test を追加する。
- `ProController`、`JoyConL`、`JoyConR` が `SwitchGamepad` subclass である test を追加する。

Gate:

```bash
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run ty check --no-progress
uv run pytest tests/unit
```

M2 まで target tests が失敗する場合は、理由付きで `xfail` にする。Target を暗黙知にしないことを優先する。

Acceptance:

- 文書だけの PR として review できる。
- 実装変更を含めない。
- maintainer が breaking change 方針に同意している。

## M1: Runtime extraction

目的: 現行 public API を一時的に保ったまま、stateful behavior を `ControllerRuntime` へ移す。

Files:

```text
src/swbt/gamepad/runtime.py
src/swbt/gamepad/_config.py
src/swbt/gamepad/core.py
```

Work items:

- `_RuntimeConfig` を追加する。
- `_TransportFactory` / `_BumbleTransportFactory` / `_StaticTransportFactory` を追加する。
- `ControllerRuntime` を追加する。
- lifecycle state、transport instance、report loop、diagnostics、input state store、output report dispatcher、connection workflow を `ControllerRuntime` へ移す。
- private `_RuntimeBackedGamepad` を追加する。
- M2 まで必要なら `SwitchGamepad` を一時的 concrete facade として残す。
- `InputReportBuilder(profile)` と `SubcommandResponder(profile)` が active profile を受け取る状態を維持する。

注意点:

- この PR では `JoyCon`、`SwitchGamepadConfig`、`transport=` を消さない。
- リスクを runtime 移植だけに限定する。

Acceptance:

- public API は変わらない。
- 既存 public examples が引き続き動く。
- Pro Controller path の挙動が変わらない。
- 既存 `JoyCon` を一時的に残す場合、その挙動が変わらない。
- fake transport を使う tests が `_StaticTransportFactory` 経由に寄り始める。
- `import swbt` 時に Bumble import が発生しない。
- `uv run pytest tests/unit` が通る。

## M2: Public controller API break

目的: public class model を最終形に切り替える。

Files:

```text
src/swbt/gamepad/interface.py
src/swbt/gamepad/controllers.py
src/swbt/gamepad/__init__.py
src/swbt/__init__.py
tests/unit/test_public_api_boundary.py
```

Work items:

- `src/swbt/gamepad/interface.py` に abstract `SwitchGamepad` を追加する。
- `src/swbt/gamepad/controllers.py` に `ProController`、`JoyConL`、`JoyConR`、private `_RuntimeBackedGamepad` を追加する。
- Root export から `JoyCon` を削除する。
- Root export から `SwitchGamepadConfig` を削除する。
- Root export から `HidDeviceTransport` を削除する。
- `src/swbt/gamepad/__init__.py` と `src/swbt/__init__.py` を更新する。
- README / docs の `SwitchGamepad(...)` example を `ProController(...)` に変える。
- Joy-Con example を `JoyCon("left" | "right")` から `JoyConL(...)` / `JoyConR(...)` に変える。
- public boundary tests を新 API に差し替える。

Migration:

```text
SwitchGamepad(...)       -> ProController(...)
JoyCon("left", ...)      -> JoyConL(...)
JoyCon("right", ...)     -> JoyConR(...)
SwitchGamepadConfig(...) -> public API では廃止
transport=...            -> internal tests に移動
```

Acceptance:

- `SwitchGamepad()` は `InvalidInputError` ではなく `TypeError` で失敗する。
- `ProController`, `JoyConL`, `JoyConR` が root export される。
- `JoyCon`, `SwitchGamepadConfig`, `HidDeviceTransport` は root export されない。
- README 以外の実装 tests が新 API を使う。

## M3: Config/profile cleanup

目的: public profile injection を消し、controller identity を concrete class owned にする。

Work items:

- `src/swbt/gamepad/_config.py` を追加する。
- `_ControllerSpec` を追加する。
- `_RuntimeConfig` を追加する。
- `_build_runtime()` を実装する。
- Public `SwitchGamepad.from_config()` と `JoyCon.from_config()` を削除する。
- Public path から `profile` argument を削除する。
- Public `device_name` override を削除する。
- `controller_colors` は public option として残す。
- `report_period_us` は `None` なら profile default を使う。

Acceptance:

```python
for cls in (ProController, JoyConL, JoyConR):
    signature = inspect.signature(cls)
    assert "profile" not in signature.parameters
    assert "device_name" not in signature.parameters
```

Internal test では、各 concrete class が正しい profile を選ぶことを検証する。

## M4: Transport seam hiding

目的: Unit-testability は維持しつつ、test transport を user-facing constructor から消す。

Work items:

- Internal `_TransportFactory` protocol を追加する。
- `_BumbleTransportFactory` default implementation を追加する。
- `_StaticTransportFactory` test implementation を追加する。
- `FakeHidTransport` を `tests/helpers/` に移すか、明示的 internal module にする。
- Unit tests は internal helper で runtime を作るように更新する。

Acceptance:

```python
for cls in (ProController, JoyConL, JoyConR):
    assert "transport" not in inspect.signature(cls).parameters

assert "HidDeviceTransport" not in swbt.__all__
```

Bluetooth hardware なしで unit tests が動くこと。

## M5: Profile module split / capabilities cleanup

目的: `profile.py` の肥大化を止め、protocol identity definitions を局所化する。

Work items:

- `src/swbt/protocol/profiles/base.py` を追加する。
- `src/swbt/protocol/profiles/pro_controller.py` を追加する。
- `src/swbt/protocol/profiles/joycon.py` を追加する。
- `src/swbt/protocol/buttons.py` を追加する。
- `src/swbt/protocol/descriptors.py` を追加する。
- 必要なら `src/swbt/protocol/sdp.py` を追加する。
- `InputCapabilities` を追加する場合は、`button_bits`, `supports_left_stick`, `supports_right_stick` を `ControllerProfile.input` に移す。
- `validate_input_state()` と `button_bit()` の挙動は維持する。
- unsupported input tests を維持する。
- `src/swbt/protocol/profile.py` は即削除するか、1 PR 限定の internal-only re-export として残すかを決める。

Acceptance:

- existing profile tests が通る。
- Pro Controller は Pro button map を使う。
- Joy-Con L は left stick だけを許す。
- Joy-Con R は right stick だけを許す。
- unsupported button / stick は `UnsupportedInputError` になる。
- `ControllerKind` references が局所化されている。
- `InputReportBuilder` は controller-kind branch ではなく profile behavior に依存している。
- Public root API は profile class を export していない。

## M6: Docs, examples, hardware verification matrix / release cleanup

目的: user-facing docs を新 API に更新し、未検証 Joy-Con behavior を保証済みのように見せない。breaking change を release 可能な状態にする。

Files:

```text
README.md
docs/api.md
docs/usage.md
docs/agent-brief.md
docs/hardware-guide.md
examples/
spec/hardware-test-log.md
```

Work items:

- README examples を更新する。
- `docs/api.md` を更新する。
- `docs/usage.md` を更新する。
- `docs/agent-brief.md` を更新する。
- examples を更新する。
- 旧 API からの migration note を追加する。
- hardware verification matrix を追加または更新する。
- Joy-Con L/R の検証状態を分けて記録する。
- `JoyConPair` は未実装の上位 API として別扱いにする。
- Pro Controller、Joy-Con L、Joy-Con R は別々の `key_store_path` を使うよう明記する。
- changelog または release note を作る。
- package version を上げる。
- docs site を更新する。
- Rearchitecture docs を公開 docs に載せるなら `mkdocs.yml` を更新する。

Acceptance:

- docs の通常説明に次を含まない。

```text
JoyCon("left"
JoyCon("right"
SwitchGamepad(
SwitchGamepadConfig
transport=FakeHidTransport
```

例外: migration section では旧 API として明確に表示してよい。

- `SwitchGamepad` は型としてのみ説明される。
- agent brief が `ProController`, `JoyConL`, `JoyConR` を案内する。
- `uv run ruff format --check .` が通る。
- `uv run ruff check .` が通る。
- `uv run ty check --no-progress` が通る。
- `uv run pytest tests/unit` が通る。
- `uv run pytest tests/integration` が通る。
- 実機 tests は検証済み構成と未検証構成を分けて記録する。
- Release notes に breaking change を書く。

## Suggested PR sequence

1. Architecture docs and target boundary tests。
2. Runtime extraction with temporary compatibility。
3. Public API break。
4. Hide transport seam。
5. Split profile modules。
6. Hardware matrix and release notes。

この順序の理由は、M1 で挙動変更なしの移植に閉じ、M2 以降で breaking change と docs 更新を扱うためである。M3〜M5 は必要なら PR をさらに小さく分割する。

## Implementation checklist

### 実装前

- `main` を最新化する。
- current README と docs の API 例を確認する。
- public boundary tests を読む。
- profile tests を読む。
- input report tests を読む。
- `BondedPeer` が public return type にまだ必要か確認する。
- `FakeHidTransport` を `tests/helpers` に移すか `swbt._testing` に残すか決める。
- Profile split を public API break の前後どちらで実施するか決める。
- Release version target を決める。

### Runtime extraction PR

- `ControllerRuntime` に移す method を一覧化する。
- lifecycle state を移す。
- connection workflow を移す。
- output dispatcher を移す。
- report loop 作成を移す。
- transport callback 登録を移す。
- diagnostics metadata 記録を移す。

### Public API break PR

- root export を更新する。
- `JoyCon` を削除する。
- `SwitchGamepadConfig` を削除する。
- `HidDeviceTransport` の root export を削除する。
- constructor signature tests を追加する。
- migration docs を追加する。

### Profile split PR

- import cycle を確認する。
- `swbt.protocol.profile` を薄くする。
- root export を増やさない。
- profile identity tests を維持する。
- unsupported input tests を維持する。

### Docs PR

- README を更新する。
- Usage Guide を更新する。
- API Reference を更新する。
- Agent Brief を更新する。
- examples を更新する。
- hardware verification matrix を更新する。

## Reviewer checklist

- public API と internal seam が混ざっていない。
- `profile` が public constructor に出ていない。
- `device_name` が public constructor に出ていない。
- `transport` が public constructor に出ていない。
- concrete controller class と profile の対応が固定されている。
- `ControllerKind` 分岐が runtime に漏れていない。
- `JoyConPair` の実装が対象 PR に混ざっていない。
- compatibility alias が残っていない。
- README と docs の例が新 API に揃っている。
- Hardware / integration tests を run したか、未実施かを PR に書いている。

## Rollback policy

Runtime extraction PR は挙動変更なしなので、問題が出た場合は単純 revert できる。

Public API break PR 以降は breaking change を含む。revert よりも、失敗した変更範囲を小さくして再提出する。互換 layer を追加して埋める判断はしない。

## Risk register

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Runtime extraction で挙動が変わる | High | M1 は behavior-preserving にし、移動ごとに既存 unit tests を回す。 |
| Transport seam を隠すと test が書きづらい | Medium | `_StaticTransportFactory` と `make_test_runtime()` helper を用意する。 |
| Compatibility alias 削除で利用者が驚く | Low/Medium | pre-alpha として breaking cleanup し、migration guide を用意する。 |
| Profile split で import churn が増える | Medium | public API break 後に分割するか、1 PR 限定の internal re-export を使う。 |
| Joy-Con docs が hardware support を過大に見せる | High | verification matrix と unresolved items を明記する。 |
| `BondedPeer` 削除が `ConnectionResult` typing を壊す | Medium | `ConnectionResult` を audit し、必要なら意図的に public に残す。 |

## Open questions

1. `BondedPeer` は `ConnectionResult` の public return type として必要か。それとも plain string / plain data に落とすか。
2. Fake transport は `tests/helpers` に移すか、`src/swbt/_testing` に残すか。推奨は unit test だけなら `tests/helpers`、repo 外 integration test に必要なら `src/swbt/_testing`。
3. `protocol/profile.py` は即削除するか、profile split 中だけ internal re-export として残すか。
4. `report_period_us` は全 concrete public constructor に残すか、advanced option に移すか。現時点の推奨は public に残し、`None` を profile default とする。
5. Rearchitecture docs は MkDocs で公開するか、internal architecture notes として nav には載せないか。現時点の推奨は、利用者向け docs と混ぜず internal architecture note として管理すること。
