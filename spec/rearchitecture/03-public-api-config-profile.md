# 03. Public API / config / profile policy

## Target public API

Root import は次を想定する。

```python
from swbt import (
    Button,
    ControllerColors,
    DiagnosticsConfig,
    JoyConL,
    JoyConR,
    ProController,
    Stick,
    SwitchGamepad,
)
```

Controller 作成は concrete class で行う。

```python
pro = ProController(
    adapter="usb:0",
    key_store_path="keys/pro-controller.json",
)

left = JoyConL(
    adapter="usb:0",
    key_store_path="keys/joycon-l.json",
)

right = JoyConR(
    adapter="usb:0",
    key_store_path="keys/joycon-r.json",
)
```

`SwitchGamepad` は直接作成せず、任意 controller を受け取る型として使う。

```python
async def accept_any_controller(pad: SwitchGamepad) -> None:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

## Public constructor policy

すべての concrete controller で同じ public signature を使う。

```python
class ProController(_RuntimeBackedGamepad):
    def __init__(
        self,
        *,
        adapter: str,
        key_store_path: str | os.PathLike[str] | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None: ...


class JoyConL(_RuntimeBackedGamepad):
    def __init__(
        self,
        *,
        adapter: str,
        key_store_path: str | os.PathLike[str] | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None: ...


class JoyConR(_RuntimeBackedGamepad):
    def __init__(
        self,
        *,
        adapter: str,
        key_store_path: str | os.PathLike[str] | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None: ...
```

`adapter` は public layer では required にする。現状 `adapter` を省略できる理由は test transport injection である。`transport=` を public constructor から消すなら、public path では `adapter` を required にした方が整合する。内部 test では private builder に placeholder adapter を渡せばよい。

public API break の初期 PR では、`SwitchGamepadConfig` の代替 public config dataclass を出さない。

```python
pad = ProController(adapter="usb:0", key_store_path="keys/pro.json")
```

Public config object を出すと、「どの class に渡せるのか」「profile を持つのか」「device_name override はあるのか」という問題が再発する。

将来検討するなら、identity を含まない option object に限定する。

```python
@dataclass(frozen=True)
class ControllerOptions:
    key_store_path: str | os.PathLike[str] | None = None
    report_period_us: int | None = None
    controller_colors: ControllerColors | None = None
    diagnostics: DiagnosticsConfig | None = None
```

## Internal runtime config

Concrete class が profile を選んだ後、内部 config で値を正規化する。

```python
@dataclass(frozen=True)
class _RuntimeConfig:
    adapter: str
    key_store_path: str | None
    report_period_us: int
    profile: ControllerProfile
    diagnostics: DiagnosticsConfig | None
    transport_factory: _TransportFactory
```

Runtime / report / transport は profile を必要とする。ただし、それは public constructor の引数ではない。

## Profile ownership policy

### Public class が profile を選ぶ

```python
_PRO_CONTROLLER_SPEC = _ControllerSpec(profile_factory=ProControllerProfile)
_JOYCON_L_SPEC = _ControllerSpec(profile_factory=JoyConLeftProfile)
_JOYCON_R_SPEC = _ControllerSpec(profile_factory=JoyConRightProfile)
```

```python
class ProController(_RuntimeBackedGamepad):
    def __init__(self, *, adapter: str, **options: object) -> None:
        super().__init__(
            _build_runtime(
                spec=_PRO_CONTROLLER_SPEC,
                adapter=adapter,
                **options,
            )
        )
```

Concrete class が public identity で、profile はその内部 protocol definition である。

### Public API では profile を受け取らない

以下は public API として出さない。

```python
ProController(profile=...)
JoyConL(profile=...)
JoyConR(profile=...)
SwitchGamepad.from_config(SwitchGamepadConfig(profile=...))
```

### Deep import は public contract にしない

内部 module や test が `swbt.protocol.profiles.*` から import することは構わない。ただし root export せず、docs でも user-facing customization point として説明しない。

## `ControllerColors` policy

`ControllerColors` は public のまま残す。

理由は、color は controller identity ではなく、SPI profile data 上の presentation option だからである。

```python
left = JoyConL(
    adapter="usb:0",
    controller_colors=ControllerColors(
        body=0x00B2FF,
        buttons=0x323232,
        left_grip=0x00B2FF,
        right_grip=0x00B2FF,
    ),
)
```

Validation は引き続き 24-bit RGB integer として厳格に行う。

## `device_name` policy

Public constructor では `device_name` を受け取らない。

Advertised device name は identity-bearing な値である。`JoyConL(device_name="Pro Controller")` のような組み合わせを許すと、class name と Bluetooth identity が矛盾する。必要なら profile 側で固定する。

## `report_period_us` policy

`report_period_us` は public option として残す。ただし `None` は profile default を使う意味にする。

```python
period = profile.default_report_period_us if report_period_us is None else report_period_us
```

正規化後に validation する。

```python
if not isinstance(period, int) or isinstance(period, bool) or period <= 0:
    raise InvalidInputError("report_period_us must be a positive integer")
```

## `transport` policy

`transport` は public constructor から削除する。

以下は許可しない。

```python
ProController(adapter="usb:0", transport=FakeHidTransport())
JoyConL(transport=FakeHidTransport())
```

内部 factory を使う。

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

Test では internal static factory を使う。詳細は `04-runtime-profile-transport-details.md` に寄せる。

## Public exports

### 残す root export

```text
AdapterDiscoveryError
AdapterInfo
Button
ClosedError
ConnectionFailedError
ConnectionResult
ConnectionTimeoutError
ControllerColors
DiagnosticsConfig
GamepadStatus
IMUFrame
InputState
InvalidInputError
InvalidKeyStoreError
JoyConL
JoyConR
ProController
Stick
SwbtError
SwitchGamepad
TransportOpenError
UnsupportedInputError
list_adapters
```

### 削除する root export

```text
JoyCon
SwitchGamepadConfig
HidDeviceTransport
DisconnectRequestResult
BondedPeer, unless still required by a public result type
```

`ConnectionResult` が public に `BondedPeer` を含むなら、`BondedPeer` を意図的に public に残すか、`ConnectionResult` を plain data に変更する。偶然 root export されている状態は避ける。

## Migration guide

README または docs に migration section を追加する。

```text
Old API                         New API
------------------------------  -------------------------------
SwitchGamepad(.)                ProController(.)
JoyCon("left", .)              JoyConL(.)
JoyCon("right", .)             JoyConR(.)
SwitchGamepadConfig(profile=.)  public replacement なし
transport=FakeHidTransport()    internal tests only
```

### Before / After: Pro Controller

```python
# Before
from swbt import Button, SwitchGamepad

async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

```python
# After
from swbt import Button, ProController

async with ProController(adapter="usb:0", key_store_path="keys/pro-controller.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

### Before / After: Joy-Con L

```python
# Before
from swbt import Button, JoyCon

async with JoyCon("left", adapter="usb:0", key_store_path="left.json") as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.SR, Button.SL)
```

```python
# After
from swbt import Button, JoyConL

async with JoyConL(adapter="usb:0", key_store_path="keys/joycon-l.json") as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.SR, Button.SL)
```

## Public boundary tests

```python
def test_switch_gamepad_is_abstract() -> None:
    assert inspect.isabstract(SwitchGamepad)

    with pytest.raises(TypeError):
        SwitchGamepad()
```

```python
@pytest.mark.parametrize("cls", [ProController, JoyConL, JoyConR])
def test_public_controller_constructors_hide_internal_seams(cls) -> None:
    signature = inspect.signature(cls)

    assert "adapter" in signature.parameters
    assert "key_store_path" in signature.parameters
    assert "report_period_us" in signature.parameters
    assert "controller_colors" in signature.parameters
    assert "diagnostics" in signature.parameters

    assert "profile" not in signature.parameters
    assert "device_name" not in signature.parameters
    assert "transport" not in signature.parameters
```

```python
def test_removed_api_is_not_root_exported() -> None:
    assert "JoyCon" not in swbt.__all__
    assert "SwitchGamepadConfig" not in swbt.__all__
    assert "HidDeviceTransport" not in swbt.__all__
```

```python
def test_concrete_classes_share_interface() -> None:
    assert issubclass(ProController, SwitchGamepad)
    assert issubclass(JoyConL, SwitchGamepad)
    assert issubclass(JoyConR, SwitchGamepad)
```
