# 公開API設計

この文書では、`swbt-python` の公開 API を定義する。公開 API は `swbt` モジュールルートから import できる形にする。

## 1. API 設計の方針

- 利用者が最初に触る入口は `SwitchGamepad` にする
- Bluetooth や Bumble の詳細は public API に露出させない
- USB Bluetooth adapter 候補の確認は `list_adapters()` に分け、adapter open とは別の no-open API とする
- 入力状態は `InputState` として明示的に扱う
- 短い操作には `tap()`、`press()`、`release()` を提供する
- 完全な状態更新には `apply()` を提供する
- stick だけの状態更新には `lstick()`、`rstick()`、`sticks()` を提供し、axis 値は `Stick` に閉じ込める
- 終了時は `neutral()` または `close(neutral=True)` により入力を戻せるようにする
- API は `asyncio` 前提にする
- duration を伴う操作は protocol ではなく API helper の責務にする

## 2. 基本的な利用例

### 2.1 接続して Button A を押す

```python
import asyncio
from swbt import SwitchGamepad, Button

async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(
            timeout=30.0,
            allow_pairing=True,
        )
        await pad.tap(Button.A)

asyncio.run(main())
```

`connect()` は保存済み bond があれば bond reuse reconnect を優先する。初回 pairing まで許可する場合だけ `allow_pairing=True` を指定する。

### 2.2 複数ボタンを押す

```python
import asyncio
from swbt import SwitchGamepad, Button

async def main() -> None:
    async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
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
from swbt import SwitchGamepad, Stick

async def main() -> None:
    async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
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
from swbt import Button, InputState, Stick, SwitchGamepad

async def main() -> None:
    async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
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
from swbt import SwitchGamepad, Button
from swbt.transport.fake import FakeHidTransport

async def main() -> None:
    transport = FakeHidTransport()

    async with SwitchGamepad(transport=transport) as pad:
        pairing = asyncio.create_task(pad.pair(timeout=1.0))
        await transport.connect()
        await pairing
        await pad.tap(Button.A)

    assert transport.sent_interrupt_reports

asyncio.run(main())
```

fake transport は unit test と integration test 用であり、実機接続には使わない。

## 3. `SwitchGamepad`

### 3.1 初期化

```python
class SwitchGamepad:
    def __init__(
        self,
        *,
        adapter: str | None = None,
        key_store_path: str | None = None,
        report_period_us: int = 8000,
        device_name: str = "Pro Controller",
        controller_colors: ControllerColors | None = None,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> None: ...

    @classmethod
    def from_config(
        cls,
        config: SwitchGamepadConfig,
        *,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> "SwitchGamepad": ...
```

引数の意味は次の通り。

| 引数 | 意味 |
|---|---|
| `adapter` | Bumble transport に渡す adapter moniker |
| `key_store_path` | default Bumble transport が pairing key を保存する JSON key store path |
| `report_period_us` | periodic input report の送信周期 |
| `device_name` | HID Device として使う表示名 |
| `controller_colors` | SPI profile で返す controller body / buttons / left grip / right grip の固定色 |
| `diagnostics` | trace と counter の設定 |
| `transport` | テストや別 transport 実装を注入するための引数 |

default transport を使う場合、`adapter` は必須である。`transport` が指定された場合、`adapter` は省略できる。この場合、diagnostics の adapter metadata は `"custom"` とする。

`key_store_path` は 1 つの仮想 Pro Controller の pairing storage を定義する構成値である。`key_store_path=None` は永続 bond を持たない一時的な仮想 controller を意味する。pairing 自体は可能だが、プロセス終了後の reconnect は期待しない。

`controller_colors=None` は既定の Joy-Con-ish profile `ControllerColors(body=0x323232, buttons=0xFFFFFF, left_grip=0x00B2FF, right_grip=0xFF3B30)` を使う。`body`、`buttons`、`left_grip`、`right_grip` はそれぞれ独立した既定値を持つ。色は作成時に固定し、接続後の `set_color()`、`controller_colors=` setter、profile mutation API は提供しない。

`transport` 注入は public extension point として扱う。`SwitchGamepad` は injected transport を後から再設定しない。key store を必要とする custom transport は、その transport 自身の constructor で設定を受ける。`SwitchGamepadConfig.key_store_path` は default Bumble transport の構築と diagnostics metadata に使う。

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

`open()` は transport を開き、callback、diagnostics、report loop などの内部 resource を準備する。`open()` だけでは HID advertising、pairing、reconnect を開始しない。

`pair()` は初回 pairing のための入口である。内部では HID advertising と incoming 接続待ちを開始する。

`reconnect()` は保存済み bond を使う再接続だけを試行する。pairing fallback は行わない。

`connect()` は通常利用向けの入口である。保存済み bond があれば `reconnect()` を優先し、bond がない場合は `allow_pairing=True` のときだけ `pair()` へ進む。

`close()` は送信 loop と transport を停止する。

`connect()` / `reconnect()` は成功した場合だけ戻る。接続できない場合は `ConnectionFailedError`、timeout は `ConnectionTimeoutError` を投げる。接続失敗の詳細 status が必要な場合は `try_connect()` / `try_reconnect()` を使い、`ConnectionResult` を読む。`pair()` は初回 pairing の明示入口であり、接続戦略の選択結果は返さない。

`ConnectionResult.status` は `"connected"`、`"no_bond"`、`"timeout"`、`"failed"` のいずれかである。current peer が複数ある key store は旧形式または不正形式として扱い、`InvalidKeyStoreError` を投げる。これは接続失敗ではなく永続状態の形式不一致であるため、`try_reconnect()` でも `ConnectionResult` へ畳み込まない。

`close()` は冪等にする。複数回呼び出しても例外を出さず、後始末が未完了の箇所だけを処理する。

### 3.3 入力操作

```python
async def apply(self, state: InputState) -> None: ...
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

`press()`、`release()`、`lstick()`、`rstick()`、`sticks()`、`imu()`、`neutral()`、`apply()` は state update API である。接続は要求せず、即時送信もしない。接続中は次の periodic report で反映される。

`apply()` は完成済みの `InputState` で現在入力全体を置き換える。差分適用ではない。`lstick()` は left stick だけを置き換え、`rstick()` は right stick だけを置き換える。`sticks()` は左右どちらか、または両方の stick だけを置き換える。stick API は `Stick` だけを受け、tuple や raw int tuple は受けない。`imu()` は IMU 3 frame だけを置き換える。1 frame を渡した場合は 3 frame すべてに複製し、3 frame を渡した場合は順に設定する。0 個、2 個、4 個以上、`IMUFrame` 以外は `InvalidInputError` とする。

`tap()` は action API である。接続済みを要求し、押下 report と release report を即時送信する。release 対象は `tap()` に渡した button だけであり、既に押されていた他の button は維持する。

`tap()` の `duration` は秒単位とする。packet protocol へ duration を埋め込まない。

### 3.4 状態取得

```python
def snapshot(self) -> InputSnapshot: ...
def status(self) -> GamepadStatus: ...
```

`snapshot()` は現在入力の snapshot を返す。`status()` は接続状態、送信 report 数、最後に受け取った subcommand、最後の disconnect 理由などを返す。

`status()` は実機検証と利用者側の監視に使う。高頻度 control path では使わない。

### 3.5 context manager

```python
async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` を呼ぶ resource scope である。`__aenter__()` は HID advertising、pairing、reconnect を開始しない。

## 3.6 Adapter discovery

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

`list_adapters()` は `SwitchGamepad(adapter=...)` に渡す USB Bluetooth adapter 候補を返す。Nintendo Switch 本体や周辺 Bluetooth host は列挙しない。

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
    DPAD_UP = auto()
    DPAD_DOWN = auto()
    DPAD_LEFT = auto()
    DPAD_RIGHT = auto()
```

HID report 上の bit 配置は `protocol.md` と `swbt.protocol.input_report` の test で固定する。

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
    def accel(cls, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...

    def with_gyro(self, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...

    def with_accel(self, x: int = 0, y: int = 0, z: int = 0) -> "IMUFrame": ...
```

`IMUFrame.neutral()` は全軸ゼロの frame を返す。`IMUFrame.raw()` は accel / gyro を 3 軸 tuple で指定し、未指定側はゼロにする。`IMUFrame.gyro()` と `IMUFrame.accel()` は片側 sensor だけを指定する short form である。`with_gyro()` と `with_accel()` は既存 frame の反対側 sensor を維持して片側だけを置き換える。

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
class InvalidKeyStoreError(SwbtError): ...
```

no-open adapter 列挙の失敗は `AdapterDiscoveryError` とする。利用者の入力不正は `InvalidInputError`、transport の open 失敗は `TransportOpenError`、接続待ち timeout は `ConnectionTimeoutError`、timeout 以外の接続不成立は `ConnectionFailedError` として分ける。key store の unsupported shape や複数 current peer は `InvalidKeyStoreError` とする。

## 10. 非同期 API の扱い

すべての I/O と時間待ちは `asyncio` coroutine とする。

- `tap()` は内部で `asyncio.sleep(duration)` を使う
- `ReportLoop` は独立した task として動く
- `close()` は `ReportLoop` task を停止し、transport を閉じる
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
