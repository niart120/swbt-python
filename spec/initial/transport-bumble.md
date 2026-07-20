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
    async def request_disconnect(self) -> DisconnectRequestResult: ...
    async def list_bonded_peers(self) -> tuple[BondedPeer, ...]:
        """Return current reconnect candidates.

        Implementations must return zero or one peer. Multiple current peers are
        an invalid transport or key-store state and should raise
        InvalidKeyStoreError rather than returning multiple BondedPeer values.
        """
    async def connect_bonded_peer(
        self,
        peer_address: str,
        *,
        connect_timeout: float | None,
    ) -> None: ...

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

### 2.6 reconnect / key store

`list_bonded_peers()` と `connect_bonded_peer()` は、active reconnect のための最小境界である。key store は transport の構築時点で決まる。上位層は injected transport を後から再設定しない。

`list_bonded_peers()` は current reconnect candidate だけを見る。candidate が 0 件なら空 tuple、1 件ならその peer、2 件以上なら unsupported shape として `InvalidKeyStoreError` を投げる。historical / previous peer は返さない。JSON entry の順序や最終更新推定で current peer を選ばない。

## 3. `BumbleHidTransport`

### 3.1 USB HCI adapter 指定

初期実装では、Bumble の USB HCI transport moniker をそのまま `adapter` として受け取る。

例:

```python
SwitchGamepad(adapter="usb:0")
```

OS ごとの adapter discovery は `list_adapters()` と `swbt-probe adapters` で補助する。どちらも USB descriptor の列挙だけを行い、Bumble transport として adapter を開かない。

`BumbleHidTransport` は内部 constructor で `key_store_path` または `profile_path` のどちらか一方を受け取る。両方の同時指定は拒否する。

```python
BumbleHidTransport(
    adapter="usb:0",
    device_name="Pro Controller",
    profile_path="profiles/switch-pro.json",
    expected_local_bluetooth_address=bytes.fromhex("02 12 34 56 78 9A"),
)
```

`key_store_path` の実際の読み書きは Bumble key store が必要とする reconnect / pairing key update のタイミングで行う。`profile_path` は上位 runtime が adapter open 前に検証し、transport は `key_store.namespaces` だけを Bumble KeyStore interface として読み書きする。envelope の identity と controller kind は保持し、更新時はファイル全体を原子的に置き換える。

### 3.1.1 接続情報と local BD_ADDR

`key_store_path` は bond / link key の保存先だけを選び、local Bluetooth identity は変更しない。`ProController` の exp profile 経路では、利用者が管理する `exp_local_address` と pairing key namespace を同じ profile envelope に保存する。

対象は CSR8510 A10 の volatile 操作である。runtime は Bumble transport を作る前に raw CSR session で現在値を読む。現在値が target と異なる場合だけ PSRAM write、warm reset、USB 再列挙、read-back を行う。永続領域は変更しない。現在値が target と一致する場合は write と reset を省略する。

raw session と Bumble transport は同時に adapter を開かない。write 開始後に再列挙または read-back を確定できない場合は `ExpLocalAddressRecoveryRequired` を送出し、pairing を始めない。利用者は専用 USB Bluetooth ドングルを抜き差ししてから再試行する。

`BumbleHidTransport` は `power_on()` 後、discoverable / connectable、pairing、active reconnect の前に public address を target と照合する。不一致なら Switch から見える状態へ進まない。準備結果は `exp_local_identity_prepared` diagnostics event に `already_active` または `rewritten` として記録する。

`close()` は transport と controller resource を閉じるだけで、volatile address を元へ戻さない。CSR8510 A10 / WinUSB / Bumble 0.0.230 の対象個体では通常 close と raw adapter 再 open をまたいで値を保持し、USB power cycle 後に元へ戻ることを観測した。他 adapter、driver、OS へ一般化しない。

2026-07-20 の unit_052 実機 gate では、同じ対象個体で fresh profile の pairing と通常 close 後、同じ profile による active reconnect が pass した。再接続時は `current = target` のため write / reset を省略し、profile bytes を変更せず、advertising / pairing / key update を行わなかった。Switch model / firmware はこの run で記録していない。

`exp_local_address` の生成、重複回避、同時利用管理は利用者の責任とする。swbt は 6 octet、individual、locally administered、予約 inquiry LAP 以外であることを検査する。factory / baseline address は profile に保存せず、公開 read-only probe も提供しない。

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

SDP record は `swbt.protocol.profiles.base.ControllerProfile` から descriptor 情報を受け取る形にし、Bumble 固有の record 構築は `BumbleHidTransport` に閉じる。Joy-Con 固有 HID descriptor は別 unit の source-audit 対象であり、未監査 bytes を SDP fixture にしない。

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

`list_adapters()` の列挙不能は adapter open 失敗ではない。libusb の読み込み、USB context 作成、device iteration の開始に失敗した場合は `AdapterDiscoveryError` として扱う。

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
