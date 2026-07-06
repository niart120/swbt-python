# 04. Runtime / profile / transport details

## Target class responsibilities

### `SwitchGamepad`

`SwitchGamepad` は public abstract interface とする。全 controller が共有する操作 contract だけを定義する。

```python
class SwitchGamepad(ABC):
    @abstractmethod
    async def open(self) -> None: ...

    @abstractmethod
    async def close(self, *, neutral: bool = True) -> None: ...

    @abstractmethod
    async def connect(
        self,
        *,
        timeout: float | None = None,
        allow_pairing: bool = False,
    ) -> None: ...

    @abstractmethod
    async def press(self, *buttons: Button) -> None: ...

    @abstractmethod
    async def release(self, *buttons: Button) -> None: ...

    @abstractmethod
    async def tap(self, *buttons: Button, duration: float = 0.08) -> None: ...

    @abstractmethod
    async def neutral(self) -> None: ...

    @abstractmethod
    async def apply(self, state: InputState) -> None: ...

    @abstractmethod
    def snapshot(self) -> InputState: ...

    @abstractmethod
    def status(self) -> GamepadStatus: ...
```

`__aenter__` / `__aexit__` は共通実装として interface に置いてよい。これらは状態を持たず、抽象メソッドだけに依存する。

### `_RuntimeBackedGamepad`

`_RuntimeBackedGamepad` は private implementation base とする。root export しない。

```python
class _RuntimeBackedGamepad(SwitchGamepad):
    def __init__(self, runtime: ControllerRuntime) -> None:
        self._runtime = runtime

    async def open(self) -> None:
        await self._runtime.open()

    async def close(self, *, neutral: bool = True) -> None:
        await self._runtime.close(neutral=neutral)

    async def connect(
        self,
        *,
        timeout: float | None = None,
        allow_pairing: bool = False,
    ) -> None:
        await self._runtime.connect(timeout=timeout, allow_pairing=allow_pairing)

    async def press(self, *buttons: Button) -> None:
        await self._runtime.press(*buttons)

    async def release(self, *buttons: Button) -> None:
        await self._runtime.release(*buttons)

    async def tap(self, *buttons: Button, duration: float = 0.08) -> None:
        await self._runtime.tap(*buttons, duration=duration)

    async def neutral(self) -> None:
        await self._runtime.neutral()

    async def apply(self, state: InputState) -> None:
        await self._runtime.apply(state)

    def snapshot(self) -> InputState:
        return self._runtime.snapshot()

    def status(self) -> GamepadStatus:
        return self._runtime.status()
```

Test で controller object が必要な場合は、private test helper 経由にする。public docs には載せない。

### `ControllerRuntime`

実行状態は `ControllerRuntime` が持つ。

```text
ControllerRuntime
  owns InputStateStore
  owns DiagnosticsRecorder
  owns OutputReportDispatcher
  owns ConnectionWorkflow
  owns ReportLoop
  owns HidDeviceTransport
  owns ControllerProfile
```

`SwitchGamepad` は runtime を知らない。`_RuntimeBackedGamepad` だけが runtime を知る。

## Runtime behavior preservation

`ControllerRuntime` へ移す際、次の挙動は維持する。

1. `open()` は transport callbacks、metadata、report loop を準備する。pairing は開始しない。
2. `connect()` は bonded reconnect を試し、必要なら optional pairing fallback を行う。
3. `close(neutral=True)` は connected 時に trailing neutral を送り、best-effort disconnect を試みる。
4. `press()`、`release()`、`sticks()`、`apply()`、`tap()` は active profile で validation する。
5. `InputReportBuilder` は profile を受け取り、report packing 前に state を検証する。
6. `SubcommandResponder` は profile を受け取り、device-info / SPI data を profile 由来にする。
7. Default transport は引き続き Bumble import を遅延させる。

## Transport factory design

`transport` は public constructor から消す。内部 factory で生成する。

```python
class _TransportFactory(Protocol):
    def create(
        self,
        *,
        adapter: str,
        device_name: str,
        profile: ControllerProfile,
        diagnostics: DiagnosticsRecorder,
        key_store_path: str | None,
    ) -> HidDeviceTransport: ...
```

Default implementation:

```python
@dataclass(frozen=True)
class _BumbleTransportFactory:
    def create(
        self,
        *,
        adapter: str,
        device_name: str,
        profile: ControllerProfile,
        diagnostics: DiagnosticsRecorder,
        key_store_path: str | None,
    ) -> HidDeviceTransport:
        return create_default_transport(
            adapter=adapter,
            device_name=device_name,
            profile=profile,
            diagnostics=diagnostics,
            key_store_path=key_store_path,
        )
```

Test implementation:

```python
@dataclass(frozen=True)
class _StaticTransportFactory:
    transport: HidDeviceTransport

    def create(
        self,
        *,
        adapter: str,
        device_name: str,
        profile: ControllerProfile,
        diagnostics: DiagnosticsRecorder,
        key_store_path: str | None,
    ) -> HidDeviceTransport:
        _ = (adapter, device_name, profile, diagnostics, key_store_path)
        return self.transport
```

`HidDeviceTransport` protocol は internal に残す。別 backend API を設計するまでは root export しない。

## Test helper design

Fake transport は public controller constructor から消す。

候補:

```text
tests/helpers/fake_transport.py          # unit test だけなら preferred
src/swbt/_testing/fake_transport.py      # repo 外 integration test に必要なら可。ただし root export しない
```

Suggested helper:

```python
def make_test_runtime(
    *,
    spec: _ControllerSpec,
    transport: HidDeviceTransport,
    adapter: str = "test-adapter",
    report_period_us: int | None = None,
) -> ControllerRuntime:
    return _build_runtime(
        spec=spec,
        adapter=adapter,
        key_store_path=None,
        report_period_us=report_period_us,
        controller_colors=None,
        diagnostics=None,
        transport_factory=_StaticTransportFactory(transport),
    )
```

Controller object が必要な test では、private test helper を使う。

```python
def make_test_controller(
    cls: type[_RuntimeBackedGamepad],
    *,
    spec: _ControllerSpec,
    transport: HidDeviceTransport,
) -> _RuntimeBackedGamepad:
    runtime = make_test_runtime(spec=spec, transport=transport)
    return cls._from_runtime_for_tests(runtime)
```

これは user-facing docs に出さない。

## Profile module split

現行 `profile.py` は descriptor、SDP policy、colors、button maps、profile dataclass、identity validation、capability validation を抱えている。次のように分ける。

```text
src/swbt/protocol/
  profiles/
    base.py
    pro_controller.py
    joycon.py
  buttons.py
  descriptors.py
  sdp.py
```

### `profiles/base.py`

```text
ControllerKind
ControllerColors
HidSdpPolicy
ControllerProfile
InputCapabilities, if introduced
```

### `profiles/pro_controller.py`

```text
ProControllerProfile
default_controller_profile()
```

### `profiles/joycon.py`

```text
JoyConLeftProfile
JoyConRightProfile
Joy-Con color defaults
Joy-Con SDP policy helper
```

### `buttons.py`

```text
ButtonBitMap
PRO_CONTROLLER_BUTTON_BITS
JOYCON_LEFT_BUTTON_BITS
JOYCON_RIGHT_BUTTON_BITS
```

### `descriptors.py`

```text
SWITCH_PRO_CONTROLLER_HID_REPORT_DESCRIPTOR
future Joy-Con descriptors, only after source/hardware audit
```

## Input capability refinement

現時点では現行 profile fields で足りる。

```text
button_bits
supports_left_stick
supports_right_stick
```

後続 cleanup で次のようにまとめてもよい。

```python
@dataclass(frozen=True)
class InputCapabilities:
    button_bits: Mapping[Button, tuple[int, int]]
    supports_left_stick: bool
    supports_right_stick: bool
    supports_imu: bool = True
```

これは最初の breaking API PR の blocker ではない。

## Runtime tests

```python
def make_test_runtime(
    *,
    spec: _ControllerSpec,
    transport: HidDeviceTransport,
    adapter: str = "test-adapter",
    report_period_us: int | None = None,
) -> ControllerRuntime:
    return _build_runtime(
        spec=spec,
        adapter=adapter,
        key_store_path=None,
        report_period_us=report_period_us,
        controller_colors=None,
        diagnostics=None,
        transport_factory=_StaticTransportFactory(transport),
    )
```

```python
def test_joycon_l_runtime_uses_left_profile() -> None:
    runtime = make_test_runtime(
        spec=_JOYCON_L_SPEC,
        transport=FakeHidTransport(),
    )

    assert isinstance(runtime._profile, JoyConLeftProfile)
```

internal test では `_profile` を見てよい。public API に runtime profile property を追加しない。

## Architecture guardrails

```python
def test_controller_kind_branching_stays_localized() -> None:
    allowed_fragments = {
        "src/swbt/protocol/profiles/",
        "src/swbt/gamepad/_config.py",
        "src/swbt/gamepad/controllers.py",
        "tests/",
    }

    offenders = []
    for path in Path("src/swbt").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "ControllerKind." in text and not any(fragment in str(path) for fragment in allowed_fragments):
            offenders.append(str(path))

    assert offenders == []
```

```python
def test_public_root_does_not_export_internal_profile_or_transport_types() -> None:
    forbidden = {
        "ControllerProfile",
        "ControllerKind",
        "ProControllerProfile",
        "JoyConLeftProfile",
        "JoyConRightProfile",
        "HidDeviceTransport",
    }

    assert forbidden.isdisjoint(swbt.__all__)
```

## Behavior tests to preserve

- Pro Controller input report の golden test を維持または補強する。
- Joy-Con L/R の unsupported input と button packing の golden test を維持または補強する。
- `InputReportBuilder` は controller-kind branch ではなく profile behavior に依存する。
- Bluetooth hardware なしで unit tests が動く。
- `import swbt` 時に Bumble import が発生しない。
