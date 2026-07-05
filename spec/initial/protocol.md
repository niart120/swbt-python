# Switch HID protocol

この文書では、`swbt-python` の Switch HID protocol 層を定義する。この層は bytes 列の生成と解釈を担当し、Bluetooth 接続や Bumble の実装詳細を扱わない。

## 1. この層の責務

Switch HID protocol 層の責務は次の通り。

- `InputState` から `0x30` standard full input report を生成する
- Switch から受け取った output report を parse する
- `0x01` rumble + subcommand report を扱う
- `0x10` rumble only report を扱う
- subcommand に対する `0x21` reply を生成する
- raw rumble bytes を保持する
- virtual SPI flash を提供する
- protocol unit test で packet layout を固定する

## 2. この層が扱わないもの

この層では次を扱わない。

- Bluetooth adapter の open / close
- pairing
- L2CAP channel
- HCI transport
- Bumble callback
- OS ごとの driver 設定
- report の実送信時刻
- reconnect

これらは `transport-bumble.md`、`lifecycle.md`、`report_loop.py` 側の責務とする。

## 3. Input report

### 3.1 `0x30` standard full input report

初期実装では、periodic input report として `0x30` standard full input report を生成する。

設計上の contract は次の通り。

- report ID は `0x30`
- report ID を含む bytes 長は 49 bytes とする
- ボタン状態を report 内の button bytes に pack する
- 左右 stick は 12-bit raw 値として pack する
- IMU は int16 little-endian の 6 軸値を 3 frame 分持つ
- battery / connection info の初期既定値は protocol fixture として固定する
- vibrator report field の初期既定値は protocol fixture として固定する

具体的な byte offset と bit layout は unit test により固定する。実装時は既存 `swbt-daemon` の Switch HID core spec と実機ログを参照する。

### 3.2 ボタン bit 配置

`Button` から report bytes への変換は `InputReportBuilder` が担当する。

```python
report = InputReportBuilder().build_0x30(input_state)
```

初期 test では少なくとも次を固定する。

- neutral state では全 button bit が clear される
- `Button.A` が期待する bit に反映される
- `Button.L` と `Button.R` の同時押しが反映される
- d-pad 4 方向が個別に反映される
- `PLUS`、`MINUS`、`HOME`、`CAPTURE` が個別に反映される

### 3.3 stick 値の pack

`Stick` は `x` と `y` の 12-bit raw 値を持つ。report へ詰める処理は `InputReportBuilder` 内に閉じ込める。

```python
left = Stick.raw(x=2048, y=2048)
right = Stick.raw(x=2048, y=2048)
```

初期実装では、`Stick.center()` を neutral 値として使う。

### 3.4 battery / connection info

battery / connection info は初期値を固定する。実機検証で必要が出るまで public API には出さない。

この値は `ProControllerProfile` に置き、test fixture として扱う。

### 3.5 IMU frame

初期実装では、IMU frame は `InputState.imu_frames` の 3 frame をそのまま送る。IMU frame の byte layout は int16 little-endian の 6 軸値であり、公開 API helper はこの値オブジェクトを組み立てるだけに留める。

IMU frame の構造は次の値オブジェクトで表す。

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
```

`IMUFrame.raw()`、`gyro()`、`accel()`、`with_gyro()`、`with_accel()` は raw int16 値を扱う。物理単位、センサー補正、重力方向、姿勢推定は protocol core の責務に含めない。

## 4. Output report

### 4.1 `0x01` rumble + subcommand

Switch から `0x01` output report を受け取った場合、次の処理を行う。

1. packet id を読む
2. raw rumble bytes を抽出する
3. subcommand id を読む
4. subcommand payload を抽出する
5. `SubcommandResponder` へ渡す
6. `0x21` reply を reply queue へ投入する

`OutputReportParser` は parse 結果を値オブジェクトで返す。

```python
@dataclass(frozen=True)
class OutputReport:
    report_id: int
    packet_id: int | None
    rumble: bytes | None
    subcommand_id: int | None
    subcommand_payload: bytes
```

### 4.2 `0x10` rumble only

`0x10` は rumble only report として扱う。raw rumble bytes を更新し、subcommand reply は生成しない。

初期実装では、高水準 rumble 解釈を行わない。受信した raw bytes は diagnostics と `status()` で読めるようにする。

## 5. Subcommand reply

### 5.1 `0x21` subcommand reply

Switch からの subcommand に対しては、`0x21` subcommand reply を生成する。

`0x21` reply は、periodic `0x30` input report より優先して送る。優先制御は `ReportLoop` が担当し、reply payload の生成は `SubcommandResponder` が担当する。

### 5.2 reply queue

`SubcommandResponder` は送信を行わず、reply bytes を返す。送信順序は `ReportLoop` が管理する。

```text
output report received
  ↓
OutputReportParser
  ↓
SubcommandResponder
  ↓
reply queue
  ↓
ReportLoop
  ↓
HidDeviceTransport.send_interrupt()
```

### 5.3 reply 優先の理由

Switch の初期化 sequence では、subcommand reply が遅れると接続処理が進まない可能性がある。periodic input report を継続しながら、reply queue に積まれた `0x21` を次 tick で優先送信する。

## 6. 初期対応 subcommand

初期対応対象は次の subcommand とする。

| Subcommand | 用途 | 初期実装の扱い |
|---|---|---|
| `0x02` | request device info | Pro Controller 相当の device info を返す |
| `0x03` | set report mode | 指定された mode を記録し ack を返す |
| `0x04` | trigger buttons elapsed time | 最小 reply を返す |
| `0x08` | shipment / pairing related | 既存実装の観測に合わせた最小 reply を返す |
| `0x10` | SPI flash read | virtual SPI flash から指定範囲を返す |
| `0x21` | NFC/IR MCU config | 最小 reply を返す |
| `0x30` | set player lights | 指定値を記録し ack を返す |
| `0x40` | enable IMU | enable 状態を記録し ack を返す |
| `0x48` | enable vibration | enable 状態を記録し ack を返す |

未対応 subcommand を受け取った場合は、diagnostics に記録し、既存の実機挙動に近い fail-safe reply を検討する。初期実装では未対応を隠さず test と trace で見えるようにする。

## 7. Virtual SPI flash

`0x10` SPI flash read に応答するため、protocol 層に `VirtualSpiFlash` を置く。

```python
class VirtualSpiFlash:
    def read(self, address: int, size: int) -> bytes: ...
```

初期内容は `ProControllerProfile` として固定する。未定義領域は既存実装の挙動を確認した上で値を決める。未定義領域を読む場合は diagnostics に記録する。

既定 seed は少なくとも次を含む。

| Address | Data | 意味 |
|---:|---|---|
| `0x6012` | `03` | Pro Controller device type |
| `0x601B` | `01` | color info exists |
| `0x6050`-`0x605B` | `ControllerColors.to_spi_bytes()` | body、buttons、left grip、right grip を各 3 bytes の RGB color |

`SubcommandResponder` は configured `ProControllerProfile` から `VirtualSpiFlash` を作る。`0x10` SPI read は request prefix 5 bytes に `VirtualSpiFlash.read(address, size)` を続けて返す。`0x02` request device info reply は Pro Controller profile bytes `04 00 03 02 <6 byte address> 03 02` を返す。現行 swbt-python は Bluetooth address customization を持たないため address は `00 00 00 00 00 00` とする。色 bytes 自体は device info reply に埋め込まない。2026-07-05 の Windows / Switch 2 / firmware 22.1.0 実機検証では、tail `01 01` だと grip が body 色に寄り、tail `03 02` で SPI `0x6056`-`0x605B` の左右 grip 色が UI に反映された。

## 8. Rumble raw state

rumble は初期実装では意味処理しない。Switch から受け取った raw 8 bytes を保持する。

```python
@dataclass(frozen=True)
class RumbleState:
    raw: bytes
    updated_at_ns: int
```

public API として高水準 rumble を提供しない。`status()` と diagnostics では最後に受け取った raw bytes を参照できるようにする。

## 9. Protocol unit test 方針

protocol 層は Bumble なしで test できるようにする。

最低限の test は次の通り。

- neutral `InputState` から `0x30` report を生成できる
- `0x30` report の長さが 49 bytes である
- `Button.A` が期待する bit に反映される
- `Button.L` と `Button.R` が同時に反映される
- stick center が期待する 12-bit pack になる
- `0x01` output report から packet id、rumble、subcommand を抽出できる
- `0x10` output report が rumble only として処理される
- `0x02` device info reply を生成できる
- `0x10` SPI flash read reply を生成できる
- reply queue に積まれた `0x21` が periodic `0x30` より先に送られる

## 10. 参考資料

- Switch HID core spec: https://github.com/niart120/swbt-daemon/blob/main/spec/protocols/switch-hid-core.md
- Hardware test log: https://github.com/niart120/swbt-daemon/blob/main/docs/hardware-test-log.md
- Current state and support matrix: https://github.com/niart120/swbt-daemon/blob/main/docs/status.md
