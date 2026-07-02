# 公開API設計

この文書では、`swbt-python` の公開 API を定義する。公開 API は `swbt` モジュールルートから import できる形にする。

## 1. API 設計の方針

- 利用者が最初に触る入口は `SwitchGamepad` にする
- Bluetooth や Bumble の詳細は public API に露出させない
- 入力状態は `InputState` として明示的に扱う
- 短い操作には `tap()`、`press()`、`release()` を提供する
- 完全な状態更新には `set_input()` を提供する
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
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.tap(Button.A)

asyncio.run(main())
```

`connect()` は保存済み bond があれば bond reuse reconnect を優先する。初回 pairing まで許可する場合だけ `allow_pairing=True` を指定する。

### 2.2 複数ボタンを押す

```python
import asyncio
from swbt import SwitchGamepad, Button

async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
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
from swbt import SwitchGamepad, InputState, Stick

async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0)

        await pad.set_input(
            InputState.neutral().with_sticks(
                left_stick=Stick.normalized(x=0.0, y=1.0),
                right_stick=Stick.center(),
            )
        )

        await asyncio.sleep(0.2)
        await pad.neutral()

asyncio.run(main())
```

### 2.4 fake transport を使う

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
        adapter: str = "usb:0",
        report_period_us: int = 8000,
        device_name: str = "Pro Controller",
        key_store_path: str | None = None,
        diagnostics: DiagnosticsConfig | None = None,
        transport: HidDeviceTransport | None = None,
    ) -> None: ...
```

引数の意味は次の通り。

| 引数 | 意味 |
|---|---|
| `adapter` | Bumble transport に渡す adapter moniker |
| `report_period_us` | periodic input report の送信周期 |
| `device_name` | HID Device として使う表示名 |
| `key_store_path` | pairing / reconnect 情報の保存先 |
| `diagnostics` | trace と counter の設定 |
| `transport` | テストや別 transport 実装を注入するための引数 |

`transport` が指定された場合、`adapter` はその transport 実装の責務に応じて無視される場合がある。

### 3.2 接続操作

```python
async def open(self) -> None: ...
async def pair(self, timeout: float | None = None) -> ConnectionResult: ...
async def reconnect(self, timeout: float | None = None) -> ConnectionResult: ...
async def connect(
    self,
    *,
    timeout: float | None = None,
    allow_pairing: bool = False,
) -> ConnectionResult: ...
async def wait_connected(self, timeout: float | None = None) -> None: ...
async def close(self, *, neutral: bool = True) -> None: ...
```

`open()` は transport を開き、callback、diagnostics、report loop などの内部 resource を準備する。`open()` だけでは HID advertising、pairing、reconnect を開始しない。

`pair()` は初回 pairing のための入口である。内部では HID advertising と incoming 接続待ちを開始する。

`reconnect()` は保存済み bond を使う再接続だけを試行する。pairing fallback は行わない。

`connect()` は通常利用向けの入口である。保存済み bond があれば `reconnect()` を優先し、bond がない場合は `allow_pairing=True` のときだけ `pair()` へ進む。

`wait_connected()` は低水準の待機 helper であり、接続戦略を開始しない。`close()` は送信 loop と transport を停止する。

接続 API の戻り値は `ConnectionResult` とする。文字列 `Literal` ではなく、接続経路を表す enum と、bond reuse / pairing fallback の有無を持つ小さな値オブジェクトにする。詳細な field は M6 の key store / reconnect 実装時に固定する。

`close()` は冪等にする。複数回呼び出しても例外を出さず、後始末が未完了の箇所だけを処理する。

### 3.3 入力操作

```python
async def set_input(self, state: InputState) -> None: ...
async def neutral(self) -> None: ...

async def press(self, *buttons: Button) -> None: ...
async def release(self, *buttons: Button) -> None: ...
async def tap(self, *buttons: Button, duration: float = 0.08) -> None: ...
```

`set_input()` は現在入力全体を置き換える。`press()` と `release()` は現在入力のボタン集合だけを更新する。`tap()` は `press()`、sleep、`release()` を組み合わせた helper として実装する。

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
async with SwitchGamepad(adapter="usb:0") as pad:
    await pad.connect(timeout=30.0)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` を呼ぶ resource scope である。`__aenter__()` は HID advertising、pairing、reconnect を開始しない。

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
```

### 4.1 immutable にする理由

`ReportLoop` は周期的に状態を読み取る。mutable な状態を直接共有すると、report 生成中に入力状態が変更される可能性がある。`InputState` を immutable に寄せることで、snapshot の意味を明確にする。

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
```

`normalized()` は `-1.0` から `1.0` の値を受け取り、内部 raw 値へ変換する。範囲外の値は例外にする。

## 7. 例外設計

例外型は `swbt.errors` に置く。

```python
class SwbtError(Exception): ...
class TransportOpenError(SwbtError): ...
class ConnectionTimeoutError(SwbtError): ...
class ProtocolError(SwbtError): ...
class ClosedError(SwbtError): ...
class InvalidInputError(SwbtError): ...
```

利用者の入力不正は `InvalidInputError`、transport の open 失敗は `TransportOpenError`、接続待ち timeout は `ConnectionTimeoutError` として分ける。

## 8. 非同期 API の扱い

すべての I/O と時間待ちは `asyncio` coroutine とする。

- `tap()` は内部で `asyncio.sleep(duration)` を使う
- `ReportLoop` は独立した task として動く
- `close()` は `ReportLoop` task を停止し、transport を閉じる
- callback 例外は diagnostics に記録し、必要に応じて接続を failed 状態へ遷移させる

## 9. 初期 API で公開しないもの

初期実装では次を public API に含めない。

- raw HID packet 送信 API
- daemon IPC API
- 高水準 rumble API
- amiibo / NFC API
- IR camera API
- 複数 controller 管理 API

raw HID packet の送受信は diagnostics と内部 test では扱うが、安定 public API にはしない。
