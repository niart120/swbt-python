# Hardware

`swbt-python` の実機接続では、PC の標準 Bluetooth 機能ではなく、Bumble から直接開く専用 USB Bluetooth dongle を使います。
最初に driver と adapter 名を確認し、その後に対象機器側で controller pairing / search 画面を開いて接続します。

## Setup

### General Requirements

| 項目 | 内容 |
|---|---|
| Python | Python 3.12 以降 |
| USB Bluetooth dongle | PC の通常 Bluetooth 機能と共有しない専用 dongle |
| 対象機器 | controller pairing / search 画面へ手動で移動できること |

### Driver / USB Access

Bumble の `usb:` adapter は USB HCI transport を libusb 経由で使用します。
ここでの driver 準備は、OS の Bluetooth 機能で使う driver ではなく、専用 dongle を Bumble から直接開くための OS 側設定を指します。

| OS | status | 準備 |
|---|---|---|
| Windows | supported | Zadig などで専用 dongle に WinUSB / libwdi driver を導入する |
| Linux | experimental | `libusb-1.0` が使えること、USB デバイスにアクセスできること、kernel / BlueZ が対象 dongle を使用中でないことを確認する |
| macOS | experimental | `libusb-1.0` が使えること、macOS Bluetooth stack が外付け HCI を使用しない設定になっていること、必要に応じて libusb の library path を指定する |

#### Bumble USB transport で必要なこと

Bumble の `usb:` adapter は USB HCI transport を libusb 経由で扱います。Bumble の USB transport documentation では、`usb:` moniker、`libusb-1.0`、`usb_probe` / `lsusb` による列挙確認が示されています。

`swbt-python` の lock file では Bumble 0.0.230 と `libusb1` / `libusb-package` dependency を固定しています。

#### Linux の手順

Linux の手順はこの Hardware Guide に整備されていますが、動作検証されていないことに留意してください。

Linux では、Bumble 同梱の `libusb_package` で `libusb-1.0` が見つからない場合、OS 側で `apt install libusb-1.0-0` が必要になることがあります。USB デバイスへのアクセス権を付け、kernel / BlueZ が dongle を使用中の場合は `hciconfig hciX down` などで解放する必要があります。

#### macOS の手順

macOS では、macOS Bluetooth stack が外付け HCI を使用しないように `sudo nvram bluetoothHostControllerSwitchBehavior="never"` の設定が必要になる場合があります。実行前に現在の値を確認します。

```console
nvram bluetoothHostControllerSwitchBehavior
```

`libusb-1.0.dylib` が見つからない場合は、Homebrew で `libusb` を入れます。

```console
brew install libusb
```

Intel Mac の Homebrew 環境では、`libusb1` が `/usr/local/opt/libusb/lib` を自動探索しない場合があります。その場合は、実行時に `DYLD_LIBRARY_PATH` を指定します。

```console
DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib uv run swbt-probe adapters --json
```

`swbt-python` を source checkout から動かす場合、依存 package の build で `pkgconf` と `openssl@3` が必要になることがあります。

```console
brew install pkgconf openssl@3
```

2026-07-05 の実機観測では、macOS 15.7.7、CSR8510 A10、Homebrew `libusb` 1.0.30、Bumble 0.0.230、Python 3.12.13、adapter `usb:0` で、pairing、HID control / interrupt L2CAP、保存済み bond を使う active reconnect、button 入力、neutral cleanup を確認しています。

#### Linux / macOS の未確認範囲

Linux / macOS は experimental です。ここに書いた内容は、Bumble から専用 adapter を使う前に確認する項目です。接続成功を保証するものではありません。

Linux 上の adapter listing、adapter open、HID advertising、pairing、reconnect、input reflection はまだ確認していません。macOS CI で確認するのは、依存関係のインストール、単体テスト、fake transport を使った結合テスト、パッケージ作成までです。USB Bluetooth dongle は使いません。

#### Windows Driver Setup

Windows では、Zadig などで専用 USB Bluetooth dongle に WinUSB / libwdi driver を導入する必要があります。

[Zadig](https://zadig.akeo.ie/) は、Windows 上で WinUSB などの汎用 USB driver を対象デバイスへ入れるためのツールです。

Zadig では次の順に進めます。

- 専用 USB Bluetooth dongle を接続し、Zadig を管理者権限で起動する。
- 対象の dongle を選択する。
- 一覧に出ない場合は `Options > List All Devices` を使う。
- 選択した USB デバイスの VID / PID が対象 dongle と一致することを確認する。
- driver は `WinUSB` を選ぶ。
- `Install Driver` を実行する。

Zadig の操作画面と詳細: [Zadig 2.x User Guide](https://github.com/pbatard/libwdi/wiki/Zadig)。

### Adapter Name

driver 準備後、Bumble から見える adapter 名を確認します。

```powershell
swbt-probe adapters --json
```

このコマンドは adapter 一覧確認用です。Switch に向けた pairing、HID advertising、report loop は開始しません。

`adapter` には `usb:0` のような Bumble adapter 名を指定します。adapter 名は PC の接続状態で変わるため、コード例の `usb:0` を固定値として扱わないでください。

## Pairing And Reconnect

`key_store_path` は pairing 情報を保存する JSON key store path です。保存済み bond を使う場合は `SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json")` のように指定します。

`connect(timeout=..., allow_pairing=True)` は保存済み bond があれば reconnect を優先し、bond がない場合だけ pairing fallback へ進みます。初回 pairing では対象機器を controller pairing / search 画面に置いてください。

`reconnect(timeout=...)` は key store に current bonded peer が 1 件ある場合だけ active reconnect を試します。pairing fallback はしません。

1 つの key store に複数の current peers を混ぜないでください。複数 current peers は `multiple current peers` の不正状態として扱い、どの peer を使うかを推測しません。別対象機器には別の `key_store_path` を使ってください。

## Confirmed Behavior

2026-07-04 時点では、Windows 11、CSR8510 A10、WinUSB / libwdi、Switch 2 firmware 22.1.0 の組み合わせで次を確認済みです。

- 初回 pairing。
- 保存済み pairing 情報を使う reconnect。
- Button A、D-pad、left / right stick の入力反映。
- neutral 後に入力が残らないこと。

2026-07-05 時点では、macOS 15.7.7、CSR8510 A10、Homebrew `libusb`、Switch 2、adapter `usb:0` の組み合わせで次を確認済みです。

- 初回 pairing。
- 保存済み pairing 情報を使う active reconnect。
- 主要 subcommand への応答を含む初期化 sequence。
- Button 入力の反映。
- neutral 後に入力が残らないこと。

確認済み条件の trace、Bumble version、Python version、driver version は repository 内の `spec/hardware-test-log.md` にあります。

## Notes

Linux / macOS で必要になる OS 側設定は、Bumble から専用 adapter を使うためのものです。PC の通常 Bluetooth 機能と同じ adapter は使わないでください。

## Troubleshooting

### Adapter Does Not Open

- 専用 USB Bluetooth dongle を使っているか確認します。
- Windows では WinUSB / libwdi に切り替わっているか確認します。
- 専用 dongle の adapter 名を指定しているか確認します。
- `swbt-probe adapters --json` で adapter 名を確認します。

### Pairing Timeout

- 対象機器が controller pairing / search 画面にいるか確認します。
- `pair()` または `connect(..., allow_pairing=True)` を使っているか確認します。
- trace に `advertising_start`、`connection_request`、`host_connection` があるか確認します。

### No Bond

- `reconnect()` / `try_reconnect()` は保存済み bond がない場合、`no bond` として失敗します。
- 初回接続では `connect(..., allow_pairing=True)` か `pair()` を使います。
- `key_store_path` が別ファイルを指していないか確認します。

### Multiple Current Peers

- 1 つの key store に複数の current peers がある状態です。
- 対象機器ごとに key store を分けます。
- 復旧する場合は該当 key store を削除し、pairing をやり直します。

### Input Is Not Reflected In The UI

- pairing / reconnect 直後の初期通信が終わってから入力を送っているか確認します。
- `tap()` は即時 report を送ります。`press()` / `release()` / `sticks()` / `neutral()` は state update API であり、即時送信を保証しません。
- trace の `report_tx`、`subcommand_rx`、`subcommand_reply_tx`、`connected`、`disconnected` を確認します。
