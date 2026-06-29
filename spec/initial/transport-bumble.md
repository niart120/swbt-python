# Bumble HID transport

この文書では、Bumble を用いた HID Device transport 層を定義する。この層は Bluetooth 接続、Bumble device、SDP record、HID descriptor、control / interrupt channel を扱う。

## 1. この層の責務

`BumbleHidTransport` の責務は次の通り。

- USB HCI adapter を Bumble transport として開く
- Bumble device を生成する
- Bluetooth Classic を有効化する
- HID Device として SDP record と HID descriptor を設定する
- discoverable / connectable 状態にする
- HID control / interrupt channel の送受信を扱う
- 受信 bytes を上位 callback へ渡す
- 送信 bytes を HID interrupt channel へ流す
- open / close を冪等に近い形で扱う
- adapter、OS、Bumble version などを diagnostics に記録する

この層は Switch のボタン、stick、subcommand の意味を解釈しない。

## 2. `HidDeviceTransport` interface

`HidDeviceTransport` は Bumble に依存しない抽象 interface とする。

```python
class HidDeviceTransport(Protocol):
    async def open(self) -> None: ...
    async def start_advertising(self) -> None: ...
    async def close(self) -> None: ...

    async def send_interrupt(self, payload: bytes) -> None: ...
    async def send_control(self, payload: bytes) -> None: ...

    def on_interrupt_data(
        self,
        callback: Callable[[bytes], Awaitable[None]],
    ) -> None: ...

    def on_control_data(
        self,
        callback: Callable[[bytes], Awaitable[None]],
    ) -> None: ...

    def on_connected(
        self,
        callback: Callable[[], Awaitable[None]],
    ) -> None: ...

    def on_disconnected(
        self,
        callback: Callable[[int | None], Awaitable[None]],
    ) -> None: ...
```

### 2.1 `open`

adapter を開き、Bumble device と HID Device を初期化する。Switch との接続完了までは待たない。

### 2.2 `start_advertising`

discoverable / connectable にする。Bumble 側の API 名と完全一致させる必要はない。上位層から見て「Switch から見つけられる状態に入る」ことを表す。

### 2.3 `send_interrupt`

HID interrupt channel へ bytes を送る。protocol 層から渡される payload は HID report bytes とする。

### 2.4 `send_control`

HID control channel へ bytes を送る。初期実装で使わない場合でも interface には残す。

### 2.5 receive callback

Bumble の callback で受け取った data は、transport 内で最小限の整形だけを行い、上位 callback へ渡す。

## 3. `BumbleHidTransport`

### 3.1 USB HCI adapter 指定

初期実装では、Bumble の USB HCI transport moniker をそのまま `adapter` として受け取る。

例:

```python
SwitchGamepad(adapter="usb:0")
```

OS ごとの adapter discovery は後続の `swbt-probe` CLI で補助する。

### 3.2 Bumble device 生成

`BumbleHidTransport.open()` では次の初期化を行う。

```text
open_transport(adapter)
  ↓
Bumble Device 生成
  ↓
classic_enabled = True
  ↓
HID Device 初期化
  ↓
SDP record 設定
  ↓
HID descriptor 設定
  ↓
power_on
```

Bumble の具体的な設定形式は、Bumble の HID Device example を参照して実装する。

### 3.3 Bluetooth Classic 有効化

Switch との HID Device 接続では Bluetooth Classic を使う。Bumble device の Classic support を有効化する処理を transport に閉じ込める。

### 3.4 HID Device 初期化

Bumble の HID Device helper を利用する。GET_REPORT、SET_REPORT、GET_PROTOCOL、SET_PROTOCOL などの callback が必要な場合は、`BumbleHidTransport` で受け、上位の protocol 層へ必要最小限の event として渡す。

### 3.5 SDP record

Switch が Pro Controller 相当の HID Device として認識できるよう、SDP record を設定する。

SDP record は `swbt.protocol.profile.ProControllerProfile` から descriptor 情報を受け取る形にし、Bumble 固有の record 構築は `BumbleHidTransport` に閉じる。

### 3.6 HID descriptor

HID descriptor は protocol 層の profile として管理する。ただし、Bumble API に渡す具体的な object や bytes 変換は transport 層で行う。

### 3.7 Control channel

HID control channel は transport 層で扱う。上位へ渡す data は bytes とする。control channel 由来か interrupt channel 由来かは event metadata として diagnostics に記録する。

### 3.8 Interrupt channel

periodic `0x30` input report と `0x21` subcommand reply は interrupt channel へ送る。

## 4. OS 別の注意点

### 4.1 Windows

Windows では、専用 USB Bluetooth dongle を WinUSB driver に切り替えて使う前提にする。内蔵 Bluetooth や普段使いの dongle をこの用途に使わない。

README には次を明記する。

- 専用 USB Bluetooth dongle を用意する
- 対象 dongle の driver だけを WinUSB に切り替える
- `adapter="usb:0"` などの指定は環境によって変わる
- OS 標準 Bluetooth stack と併用しない

### 4.2 Linux

Linux では libusb permission、udev rule、既存 Bluetooth service との競合を確認する。

初期 release で Linux 実機接続を保証するかは未決事項とする。adapter open までの検証は早い段階で実施する。

### 4.3 macOS

macOS は初期検証対象外とする。Bumble transport と USB dongle の扱いを調べた上で、後続の hardware matrix に追加する。

## 5. Bumble 依存を閉じ込める方針

`bumble` package を import してよいのは `swbt.transport.bumble` 以下に限定する。

上位層では次を禁止する。

- Bumble device object を保持する
- Bumble callback 型を public API に露出する
- Bumble 固有例外をそのまま外へ投げる
- Bumble の transport moniker 以外の内部型に依存する

Bumble 由来の例外は、`TransportOpenError`、`TransportClosedError`、`TransportSendError` などに変換する。

## 6. 失敗時の扱い

### 6.1 adapter open 失敗

adapter を開けなかった場合、`TransportOpenError` を投げる。diagnostics には adapter string、OS、Python version、Bumble version、元例外型を記録する。

### 6.2 power on 失敗

Bumble device の power on に失敗した場合、可能な範囲で transport を閉じ、`TransportOpenError` を投げる。

### 6.3 send 失敗

接続済みでない状態で `send_interrupt()` が呼ばれた場合は、明確な例外にする。disconnect 中の send 失敗は diagnostics に記録し、`ReportLoop` を停止する。

### 6.4 callback 例外

receive callback 内で例外が発生した場合、例外を握りつぶさず diagnostics に記録する。接続を継続できない場合は lifecycle を `failed` へ遷移させる。

## 7. Adapter bring-up 検証

Bumble transport の最初の実機手前検証は次を完了条件にする。

- `adapter="usb:0"` などで USB HCI transport を開ける
- Bumble device を生成できる
- Bluetooth Classic を有効化できる
- HID Device を初期化できる
- power on できる
- discoverable / connectable にできる
- close を複数回呼んでも破綻しない

Switch との pairing 成功は次の milestone で扱う。

## 8. 参考資料

- Bumble documentation: https://google.github.io/bumble/
- Bumble HID Device example: https://github.com/google/bumble/blob/main/examples/run_hid_device.py
- Bumble USB transport documentation: https://github.com/google/bumble/blob/main/docs/mkdocs/src/transports/usb.md
- Bumble Windows platform documentation: https://github.com/google/bumble/blob/main/docs/mkdocs/src/platforms/windows.md
