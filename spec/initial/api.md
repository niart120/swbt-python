# 公開API設計

この文書では、`swbt-python` の公開 API を定義する。公開 API は `swbt` モジュールルートから import できる形にする。

## 1. API 設計の方針

- lifecycle と意味的入力操作の共通型は `SwitchGamepad` にする
- 周期送信の共通型は `PeriodicSwitchGamepad`、具象型は `ProController` / `JoyConL` / `JoyConR` にする
- 利用者所有の Direct 送信の共通型は `DirectSwitchGamepad`、具象型は `DirectProController` / `DirectJoyConL` / `DirectJoyConR` にする
- Bluetooth や Bumble の詳細は public API に露出させない
- USB Bluetooth adapter 候補の確認は `list_adapters()` に分け、adapter open とは別の no-open API とする
- 入力状態は `InputState` として明示的に扱う
- 短い操作には `tap()`、`press()`、`release()` を提供する
- 完全な状態更新には Periodic の `apply()` と Direct の `send()` を提供する
- stick だけの状態更新には `lstick()`、`rstick()`、`sticks()` を提供し、axis 値は `Stick` に閉じ込める
- 終了時は `neutral()` または `close(neutral=True)` により入力を戻せるようにする
- API は `asyncio` 前提にする
- duration を伴う操作は protocol ではなく API helper の責務にする

## 2. 基本的な利用例

### 2.1 接続して Button A を押す

```python
import asyncio
from swbt import Button, ProController

async def main() -> None:
    pad = await ProController.create_profile(
        adapter="usb:0",
        profile_path="profiles/switch-pro.json",
        exp_local_address="02:12:34:56:78:9A",
        pair_timeout=60.0,
    )
    try:
        await pad.tap(Button.A)
    finally:
        await pad.close()

asyncio.run(main())
```

`create_profile()` は新規プロファイルを保存して初回ペアリングを行う。`exp_local_address` の生成と重複回避は利用者が担う。以降の例はこのプロファイルが存在する前提とし、`connect()` は保存済みペアリング情報があれば再接続を優先する。ペアリングの再試行まで許可する場合だけ `allow_pairing=True` を指定する。

### 2.2 複数ボタンを押す

```python
import asyncio
from swbt import Button, ProController

async def main() -> None:
    async with ProController(adapter="usb:0", profile_path="profiles/switch-pro.json") as pad:
        await pad.connect(timeout=30.0)

        await pad.press(Button.L, Button.R)
        await asyncio.sleep(0.5)
        await pad.release(Button.L, Button.R)
        await pad.neutral()

asyncio.run(main())
```

### 2.3 スティック入力を送る

```python
import asyncio
from swbt import ProController, Stick

async def main() -> None:
    async with ProController(adapter="usb:0", profile_path="profiles/switch-pro.json") as pad:
        await pad.connect(timeout=30.0)

        await pad.lstick(Stick.up())
        await pad.rstick(Stick.right(0.5))

        await asyncio.sleep(0.2)
        await pad.neutral()

asyncio.run(main())
```

### 2.4 ボタンとスティックを同じ状態として反映する

```python
import asyncio
from swbt import Button, InputState, ProController, Stick

async def main() -> None:
    async with ProController(adapter="usb:0", profile_path="profiles/switch-pro.json") as pad:
        await pad.connect(timeout=30.0)

        state = InputState.neutral().with_buttons([Button.L, Button.R]).with_sticks(
            left_stick=Stick.up(),
        )
        await pad.apply(state)

        await asyncio.sleep(0.2)
        await pad.neutral()

asyncio.run(main())
```

`press()` と `sticks()` のような複数の state update API 呼び出しは、同じ HID report に入ることを保証しない。完全に同じ状態として反映したい入力は `InputState` を作って `apply()` に渡す。

### 2.5 fake transport を使う

```python
import asyncio
from swbt import Button
from swbt._testing.gamepad import make_pro_controller
from swbt.transport.fake import FakeHidTransport

async def main() -> None:
    transport = FakeHidTransport()

    async with make_pro_controller(transport=transport) as pad:
        pairing = asyncio.create_task(pad.pair(timeout=1.0))
        await transport.connect()
        await pairing
        await pad.tap(Button.A)

    assert transport.sent_interrupt_reports

asyncio.run(main())
```

fake transport は unit test と integration test 用であり、実機接続には使わない。

## 3. controller 型

`SwitchGamepad` は lifecycle、connection、status、意味的入力操作を共有する抽象型であり、直接生成しない。`PeriodicSwitchGamepad` と `DirectSwitchGamepad` が入力レポートの送信所有者を型として固定する。

```text
SwitchGamepad
├── PeriodicSwitchGamepad
│   ├── ProController
│   ├── JoyConL
│   └── JoyConR
└── DirectSwitchGamepad
    ├── DirectProController
    ├── DirectJoyConL
    └── DirectJoyConR
```

Periodic の入力操作は local state の確定で正常終了し、レポートループが後続の入力レポートを送る。Direct の入力操作は入力レポート1件の送信完了後に state を確定して正常終了する。Direct の transport 送信が失敗した場合は、最後に正常送信した state を維持する。

### 3.1 初期化

```python
class ProController(PeriodicSwitchGamepad):
    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None: ...

    @classmethod
    async def create_profile(
        cls,
        *,
        adapter: str,
        profile_path: str,
        exp_local_address: str,
        pair_timeout: float | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> Self: ...

class JoyConL(PeriodicSwitchGamepad):
    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        report_period_us: int | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None: ...

    @classmethod
    async def create_profile(...) -> Self: ...

class JoyConR(PeriodicSwitchGamepad): ...

class DirectProController(DirectSwitchGamepad):
    def __init__(
        self,
        *,
        adapter: str | None = None,
        profile_path: str | None = None,
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
    ) -> None: ...

    @classmethod
    async def create_profile(...) -> Self: ...
```

全 concrete controller は `profile_path` と `create_profile()` を持つ。profile は exp local identity と pairing key を同じ envelope に保存する。

| 引数 | 意味 |
|---|---|
| `adapter` | Bumble transport に渡す adapter moniker |
| `profile_path` | concrete controller が exp local identity と pairing key を読み書きする swbt profile JSON path |
| `report_period_us` | Periodic だけが受け取る入力レポートの送信周期。`None` は profile の既定値 |
| `controller_colors` | SPI profile で返す controller body / buttons / left grip / right grip の固定色 |
| `diagnostics` | trace と counter の設定 |

公開 constructor では `adapter` は必須である。transport 注入と profile 差し替えは内部 test helper に限定し、公開 extension point としない。

concrete controller の `profile_path` は、利用者が選んだ `exp_local_address` と pairing key を同じ swbt profile JSON に保存する。新規 path は具象 class の `create_profile()` で作成し、既存 path は同じ controller kind の constructor に渡して再利用する。異なる kind の profile は `ProfileControllerMismatchError` とし、adapter open 前に拒否する。

`profile_path` は全 concrete controller の pairing storage を定義する。controller kind または対象機器が異なる場合は保存先を分ける。`profile_path=None` は永続 bond を持たない一時的な仮想 controller を意味する。

`create_profile()` は path が存在する場合に上書きせず `FileExistsError` を送出する。address は 6 octet の individual / locally administered address だけを受理し、予約 inquiry LAP を拒否する。pairing に失敗した場合も profile は残り、同じ `profile_path` を通常 constructor に渡して再試行できる。

Periodic の `report_period_us=None` は profile が持つ既定周期を使う。Pro Controller の既定 profile では `8000us` になる。Direct はレポートループを持たず、`report_period_us` を受け取らない。

`controller_colors=None` は既定の Joy-Con-ish profile `ControllerColors(body=0x323232, buttons=0xFFFFFF, left_grip=0x00B2FF, right_grip=0xFF3B30)` を使う。`body`、`buttons`、`left_grip`、`right_grip` はそれぞれ独立した既定値を持つ。色は作成時に固定し、接続後の `set_color()`、`controller_colors=` setter、profile mutation API は提供しない。

### 3.2 接続操作

```python
async def open(self) -> None: ...
async def pair(self, timeout: float | None = None) -> None: ...
async def reconnect(self, timeout: float | None = None) -> None: ...
async def try_reconnect(self, timeout: float | None = None) -> ConnectionResult: ...
async def connect(
    self,
    *,
    timeout: float | None = None,
    allow_pairing: bool = False,
) -> None: ...
async def try_connect(
    self,
    *,
    timeout: float | None = None,
    allow_pairing: bool = False,
) -> ConnectionResult: ...
async def close(self, *, neutral: bool = True) -> None: ...
```

`open()` は transport、callback、diagnostics、共通 sender を準備する。Periodic だけが report loop を準備し、Direct は周期 task を作らない。`open()` だけでは HID advertising、pairing、reconnect を開始しない。

`pair()` は初回 pairing のための入口である。内部では HID advertising と incoming 接続待ちを開始する。

`reconnect()` は保存済み bond を使う再接続だけを試行する。pairing fallback は行わない。

`connect()` は通常利用向けの入口である。保存済み bond があれば `reconnect()` を優先し、bond がない場合は `allow_pairing=True` のときだけ `pair()` へ進む。

`close()` は Periodic の送信 loop と共通 transport を停止する。`neutral=True` かつ接続中の場合、Direct でも終了処理の例外としてニュートラル入力を1件送信し、成功後に state を確定する。`neutral=False` は終了用入力レポートを追加しない。

`connect()` / `reconnect()` は成功した場合だけ戻る。接続できない場合は `ConnectionFailedError`、timeout は `ConnectionTimeoutError` を投げる。接続失敗の詳細 status が必要な場合は `try_connect()` / `try_reconnect()` を使い、`ConnectionResult` を読む。`pair()` は初回 pairing の明示入口であり、接続戦略の選択結果は返さない。

`ConnectionResult.status` は `"connected"`、`"no_bond"`、`"timeout"`、`"failed"` のいずれかである。current peer が複数ある key store は旧形式または不正形式として扱い、`InvalidKeyStoreError` を投げる。これは接続失敗ではなく永続状態の形式不一致であるため、`try_reconnect()` でも `ConnectionResult` へ畳み込まない。

`close()` は冪等にする。複数回呼び出しても例外を出さず、後始末が未完了の箇所だけを処理する。

### 3.3 入力操作

```python
async def apply(self, state: InputState) -> None: ...
async def send(self, state: InputState) -> None: ...
async def sticks(
    self,
    *,
    left: Stick | None = None,
    right: Stick | None = None,
) -> None: ...
async def lstick(self, stick: Stick) -> None: ...
async def rstick(self, stick: Stick) -> None: ...
async def imu(self, *frames: IMUFrame) -> None: ...
async def neutral(self) -> None: ...

async def press(self, *buttons: Button) -> None: ...
async def release(self, *buttons: Button) -> None: ...
async def tap(self, *buttons: Button, duration: float = 0.08) -> None: ...
```

`apply()` は Periodic だけ、`send()` は Direct だけが提供する。Periodic の `press()`、`release()`、`lstick()`、`rstick()`、`sticks()`、`imu()`、`neutral()`、`apply()` は接続を要求せず、即時送信もしない。接続中は次の periodic report で反映される。

`apply()` と `send()` は完成済みの `InputState` で現在入力全体を置き換える。差分適用ではない。Direct の `send()` と意味的入力操作は接続済みを要求し、1操作につき入力レポートを1件送ってから state を確定する。未接続、profile validation、transport 送信失敗では state を変更しない。Direct の input operation は直列化し、候補 state の更新を失わない。

`lstick()` は left stick だけを置き換え、`rstick()` は right stick だけを置き換える。`sticks()` は左右どちらか、または両方の stick だけを置き換える。stick API は `Stick` だけを受け、tuple や raw int tuple は受けない。profile が対応しない button / stick update は state store へ commit する前に `UnsupportedInputError` とする。`imu()` は IMU 3 frame だけを置き換える。1 frame を渡した場合は 3 frame すべてに複製し、3 frame を渡した場合は順に設定する。0 個、2 個、4 個以上、`IMUFrame` 以外は `InvalidInputError` とする。

`tap()` は action API である。接続済みを要求し、押下 report と release report を即時送信する。release 対象は `tap()` に渡した button だけであり、既に押されていた他の button は維持する。Direct は押下から解放まで同じ input operation lock を保持する。解放送信に失敗した場合は、最後に正常送信した押下 state を維持する。

`tap()` の `duration` は秒単位とする。packet protocol へ duration を埋め込まない。

### 3.4 状態取得

```python
def snapshot(self) -> InputSnapshot: ...
def status(self) -> GamepadStatus: ...
```

`snapshot()` は現在入力の snapshot を返す。Periodic は最新の local state、Direct は最後に正常送信した state を返す。新しい接続 session は neutral baseline から始める。`status()` は接続状態、送信 report 数、最後に受け取った subcommand、最後の disconnect 理由などを返す。

`status()` は実機検証と利用者側の監視に使う。高頻度 control path では使わない。

### 3.5 context manager

```python
async with ProController(adapter="usb:0", profile_path="profiles/switch-pro.json") as pad:
    await pad.connect(timeout=30.0)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` を呼ぶ resource scope である。`__aenter__()` は HID advertising、pairing、reconnect を開始しない。

## 3.6 Joy-Con L / R

```python
left = JoyConL(adapter="usb:0", profile_path="profiles/switch-left-joycon.json")
right = JoyConR(adapter="usb:0", profile_path="profiles/switch-right-joycon.json")

direct_left = DirectJoyConL(
    adapter="usb:0",
    profile_path="switch-direct-left-joycon-bond.json",
)
direct_right = DirectJoyConR(
    adapter="usb:0",
    profile_path="switch-direct-right-joycon-bond.json",
)
```

`JoyConL` / `DirectJoyConL` は Joy-Con L profile、`JoyConR` / `DirectJoyConR` は Joy-Con R profile を固定する。side string を受け取る wrapper は公開しない。接続、入力、diagnostics、`close(neutral=True)` の lifecycle は共通にする。

```python
async with JoyConL(
    adapter="usb:0",
    profile_path="profiles/switch-left-joycon.json",
) as left:
    await left.connect(timeout=30.0, allow_pairing=True)
    await left.tap(Button.L)
```

片側 Joy-Con が持たない button / stick は `UnsupportedInputError` とする。左 Joy-Con は A/B/X/Y、right stick などを扱わない。右 Joy-Con は D-pad、left stick などを扱わない。`InputState` を `apply()` または `send()` する場合も同じ検査を行い、不正 state は送信・commit しない。

全 concrete controller は `profile_path` を使える。各 profile envelope は `pro` / `joycon_l` / `joycon_r` / `direct_pro` / `direct_joycon_l` / `direct_joycon_r` の kind を持ち、別 kind の constructor では開けない。同じ対象機器でも controller kind ごとに別の保存 path と `exp_local_address` を管理する。Direct と Periodic 間で profile を共有しない。

`JoyConPair` は初期 API に含めない。左右を 1 つの controller として束ねる API は、左右別 device の connect / disconnect failure semantics と cleanup を別途設計してから追加する。

Joy-Con profile は Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で限定観測がある。docs は Joy-Con L/R の SR+SL 登録、利用者指定色、Joy-Con L の D-pad、Joy-Con R の ABXY、左右スティックの hold / circle 送信を確認済み範囲として書き、SDP 完全一致、OS / dongle / firmware をまたぐ互換性、横持ち Joy-Con のスティック補正 UI 完了は保証しない。

## 3.7 Adapter discovery

```python
@dataclass(frozen=True, slots=True)
class AdapterInfo:
    name: str
    aliases: tuple[str, ...]
    vendor_id: int | None
    product_id: int | None
    manufacturer: str | None
    product: str | None
    serial_number: str | None
    bus_number: int | None
    device_address: int | None
    port_numbers: tuple[int, ...]
    is_bluetooth_hci: bool


def list_adapters() -> tuple[AdapterInfo, ...]: ...
```

`list_adapters()` は `ProController(adapter=...)` などの公開具象型に渡す USB Bluetooth adapter 候補を返す。Nintendo Switch 本体や周辺 Bluetooth host は列挙しない。

この API は libusb の USB device enumeration と descriptor 読み取りを行うが、Bumble transport として adapter を開かない。Bluetooth controller power on、HID advertising、pairing、report loop も開始しない。

候補が 0 件の場合は空 tuple を返す。USB 列挙処理自体を開始できない場合は `AdapterDiscoveryError` を投げる。候補が返っても adapter open や対象機器との接続成功は保証しない。

## 4. `InputState`

`InputState` は入力状態を表す値オブジェクトである。

```python
@dataclass(frozen=True)
class InputState:
    buttons: frozenset[Button]
    left_stick: Stick
    right_stick: Stick
    imu_frames: tuple[IMUFrame, IMUFrame, IMUFrame]

    @classmethod
    def neutral(cls) -> "InputState": ...

    def with_buttons(self, buttons: Iterable[Button]) -> "InputState": ...
    def with_sticks(
        self,
        *,
        left_stick: Stick | None = None,
        right_stick: Stick | None = None,
    ) -> "InputState": ...
    def with_imu(self, *frames: IMUFrame) -> "InputState": ...
    def with_gyro(self, *samples: tuple[int, int, int]) -> "InputState": ...
    def with_accel(self, *samples: tuple[int, int, int]) -> "InputState": ...
```

### 4.1 immutable にする理由

`ReportLoop` は周期的に状態を読み取る。mutable な状態を直接共有すると、report 生成中に入力状態が変更される可能性がある。`InputState` を immutable に寄せることで、snapshot の意味を明確にする。

`with_imu(frame)` は 1 frame を 3 frame すべてに複製する。`with_imu(frame1, frame2, frame3)` は 3 frame を順に設定する。`with_gyro((x, y, z))` と `with_accel((x, y, z))` は 1 sample を 3 frame に複製し、3 sample を渡した場合は各 frame の gyro または accel を順に置き換える。sample 数が 0 個、2 個、4 個以上、tuple 長が 3 でない値、範囲外値は `InvalidInputError` とする。

## 5. `Button`

初期実装では、次のボタンを扱う。

```python
class Button(Enum):
    A = auto()
    B = auto()
    X = auto()
    Y = auto()
    L = auto()
    R = auto()
    ZL = auto()
    ZR = auto()
    PLUS = auto()
    MINUS = auto()
    HOME = auto()
    CAPTURE = auto()
    LEFT_STICK = auto()
    RIGHT_STICK = auto()
    SL = auto()
    SR = auto()
    DPAD_UP = auto()
    DPAD_DOWN = auto()
    DPAD_LEFT = auto()
    DPAD_RIGHT = auto()
```

HID report 上の bit 配置は `protocol.md` と `swbt.protocol.input_report` の test で固定する。`SL` / `SR` は単体 Joy-Con profile で使う button であり、Pro Controller profile では unsupported input として扱う。

## 6. `Stick`

`Stick` は 12-bit raw 値を保持する。

```python
@dataclass(frozen=True)
class Stick:
    x: int
    y: int

    MIN: ClassVar[int] = 0
    CENTER: ClassVar[int] = 2048
    MAX: ClassVar[int] = 4095

    @classmethod
    def center(cls) -> "Stick": ...

    @classmethod
    def raw(cls, *, x: int, y: int) -> "Stick": ...

    @classmethod
    def normalized(cls, *, x: float, y: float) -> "Stick": ...

    @classmethod
    def tilt(cls, x: float, y: float) -> "Stick": ...

    @classmethod
    def up(cls, amount: float = 1.0) -> "Stick": ...

    @classmethod
    def down(cls, amount: float = 1.0) -> "Stick": ...

    @classmethod
    def left(cls, amount: float = 1.0) -> "Stick": ...

    @classmethod
    def right(cls, amount: float = 1.0) -> "Stick": ...
```

`normalized()` は `-1.0` から `1.0` の値を受け取り、内部 raw 値へ変換する。範囲外の値は例外にする。

`tilt(x, y)` は `normalized(x=x, y=y)` と同じ正規化座標を使う短い生成 API である。`up()`、`down()`、`left()`、`right()` は単一方向の倒し込み量を `amount=0.0..1.0` で受ける。`Stick.tilt(1.0, 1.0)` は x/y を個別に検証する既存の矩形座標モデルとして許可する。

## 7. `IMUFrame`

`IMUFrame` は accelerometer 3 軸と gyroscope 3 軸の raw int16 値を保持する。

```python
@dataclass(frozen=True)
class IMUFrame:
    accel_x: int
    accel_y: int
    accel_z: int
    gyro_x: int
    gyro_y: int
    gyro_z: int

    @classmethod
    def neutral(cls) -> "IMUFrame": ...

    @classmethod
    def raw(
        cls,
        *,
        accel: tuple[int, int, int] | None = None,
        gyro: tuple[int, int, int] | None = None,
    ) -> "IMUFrame": ...

    @classmethod
    def gyro(cls, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...

    @classmethod
    def gyro_rate(
        cls,
        *,
        x_rad_s: float = 0.0,
        y_rad_s: float = 0.0,
        z_rad_s: float = 0.0,
    ) -> "IMUFrame": ...

    @classmethod
    def accel(cls, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...

    def with_gyro(self, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...

    def with_gyro_rate(
        self,
        *,
        x_rad_s: float = 0.0,
        y_rad_s: float = 0.0,
        z_rad_s: float = 0.0,
    ) -> "IMUFrame": ...

    def with_accel(self, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...

    def to_gyro_rate(self) -> tuple[float, float, float]: ...

    @classmethod
    def accel_g(
        cls,
        *,
        x_g: float = 0.0,
        y_g: float = 0.0,
        z_g: float = 0.0,
    ) -> "IMUFrame": ...

    def with_accel_g(
        self,
        *,
        x_g: float = 0.0,
        y_g: float = 0.0,
        z_g: float = 0.0,
    ) -> "IMUFrame": ...

    def to_accel_g(self) -> tuple[float, float, float]: ...
```

`IMUFrame.neutral()` は全軸ゼロの frame を返す。`IMUFrame.raw()` は accel / gyro を 3 軸 tuple で指定し、未指定側はゼロにする。`IMUFrame.gyro()` と `IMUFrame.accel()` は片側 sensor だけを raw 値で指定する short form である。`with_gyro()` と `with_accel()` は既存 frame の反対側 sensor を維持して片側だけを置き換える。

`IMUFrame.gyro_rate()` と `with_gyro_rate()` は rad/s の 3 軸角速度を固定尺度 `0.070 dps/raw` で raw 値へ変換する。`to_gyro_rate()` は raw 値を rad/s の 3 軸 tuple へ戻す。呼び出し側から校正値や尺度は渡さない。変換後の raw 値が signed int16 の範囲外、または角速度が非有限値の場合は clamp せず `InvalidInputError` とする。

`IMUFrame.accel_g()` と `with_accel_g()` は G 単位の 3 軸加速度を固定尺度 `1/4096 G/raw` で raw 値へ変換する。`to_accel_g()` は raw 値を G の 3 軸 tuple へ戻す。呼び出し側から校正値や尺度は渡さない。変換後の raw 値が signed int16 の範囲外、または加速度が非有限値の場合は clamp せず `InvalidInputError` とする。

## 8. `ControllerColors`

`ControllerColors` は Pro Controller profile の body / buttons / left grip / right grip 色を表す値オブジェクトである。

```python
@dataclass(frozen=True)
class ControllerColors:
    body: int = 0x323232
    buttons: int = 0xFFFFFF
    left_grip: int = 0x00B2FF
    right_grip: int = 0xFF3B30

    def to_spi_bytes(self) -> bytes: ...
```

`body`、`buttons`、`left_grip`、`right_grip` は 24-bit RGB integer として扱う。省略した field はそれぞれの既定値を使い、grip を body 色へ正規化しない。`ControllerColors(body=0x112233, buttons=0x445566, left_grip=0x778899, right_grip=0xAABBCC)` は SPI `0x6050` から `11 22 33 44 55 66 77 88 99 aa bb cc` として返る。範囲外値、文字列、bytes、tuple は `InvalidInputError` とする。

この値は入力状態ではなく controller identity / profile に属する。`InputState`、`press()`、`release()`、`apply()`、`neutral()` は色設定を扱わない。

## 9. 例外設計

例外型は `swbt.errors` に置く。

```python
class SwbtError(Exception): ...
class AdapterDiscoveryError(SwbtError): ...
class TransportOpenError(SwbtError): ...
class ConnectionTimeoutError(SwbtError): ...
class ConnectionFailedError(SwbtError): ...
class ProtocolError(SwbtError): ...
class ClosedError(SwbtError): ...
class InvalidInputError(SwbtError): ...
class UnsupportedInputError(InvalidInputError): ...
class InvalidKeyStoreError(SwbtError): ...
```

no-open adapter 列挙の失敗は `AdapterDiscoveryError` とする。利用者の入力不正は `InvalidInputError`、profile が対応しない入力は `UnsupportedInputError`、transport の open 失敗は `TransportOpenError`、接続待ち timeout は `ConnectionTimeoutError`、timeout 以外の接続不成立は `ConnectionFailedError` として分ける。key store の unsupported shape や複数 current peer は `InvalidKeyStoreError` とする。

## 10. 非同期 API の扱い

すべての I/O と時間待ちは `asyncio` coroutine とする。

- `tap()` は内部で `asyncio.sleep(duration)` を使う
- Periodic の `ReportLoop` は独立した task として動く
- `close()` は Periodic の `ReportLoop` task を停止し、transport を閉じる
- callback 例外は diagnostics に記録し、必要に応じて接続を failed 状態へ遷移させる

## 11. 初期 API で公開しないもの

初期実装では次を public API に含めない。

- raw HID packet 送信 API
- `set_input()` の互換 alias
- daemon IPC API
- 高水準 rumble API
- amiibo / NFC API
- IR camera API
- 複数 controller 管理 API

raw HID packet の送受信は diagnostics と内部 test では扱うが、安定 public API にはしない。
