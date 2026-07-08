# Hardware

`swbt-python` の実機接続では、PC の標準 Bluetooth 機能ではなく、Bumble から直接開く専用 USB Bluetooth ドングルを使います。
最初にドライバーとアダプタ名を確認し、その後に対象機器側でコントローラー接続画面を開いて接続します。

## Setup

### General Requirements

| 項目 | 内容 |
|---|---|
| Python | Python 3.12 以降 |
| USB Bluetooth ドングル | PC の通常 Bluetooth 機能と共有しない専用ドングル |
| 対象機器 | "持ち方/順番を変える" 画面へ手動で移動できること |

### Driver / USB Access

Bumble の `usb:` アダプタは USB HCI transport を libusb 経由で使います。
ここでのドライバー準備は、OS の Bluetooth 機能で使うドライバーではなく、専用ドングルを Bumble から直接開くための OS 側設定を指します。

| OS | status | 準備 |
|---|---|---|
| Windows | supported | Zadig などで専用ドングルに WinUSB / libwdi ドライバーを導入する |
| Linux | experimental | `libusb-1.0` が使えること、USB デバイスにアクセスできること、kernel / BlueZ が対象ドングルを使用中でないことを確認する |
| macOS | experimental | `libusb-1.0` が使えること、macOS の Bluetooth stack が外付け HCI を使用しない設定になっていること、必要に応じて libusb の library path を指定する |

#### Windows USB & Driver Setup

Windows では、Zadig などで専用 USB Bluetooth ドングルに WinUSB / libwdi ドライバーを導入する必要があります。

[Zadig](https://zadig.akeo.ie/) は、Windows 上で WinUSB などの汎用 USB ドライバーを対象デバイスへ入れるためのツールです。

Zadig での実施手順:

1. 専用 USB Bluetooth ドングルを接続し、Zadig を管理者権限で起動する。
2. 対象のドングルを選択する。
   - 一覧に出ない場合は `Options > List All Devices` を使う。
3. 選択した USB デバイスの VID / PID が対象ドングルと一致することを確認する。
4. ドライバーとして `WinUSB` を選ぶ。
5. `Install Driver` を実行する。

Zadig の操作画面と詳細: [Zadig 2.x User Guide](https://github.com/pbatard/libwdi/wiki/Zadig)。

#### Linux USB & Driver Setup

Linux の手順はこの Hardware Guide に整備されていますが、動作検証されていないことに留意してください。

Linux では、Bumble 同梱の `libusb_package` で `libusb-1.0` が見つからない場合、OS 側で `apt install libusb-1.0-0` が必要になることがあります。USB デバイスへのアクセス権を付け、kernel / BlueZ がドングルを使用中の場合は `hciconfig hciX down` などで解放する必要があります。

#### macOS USB & Driver Setup

macOS では、macOS の Bluetooth stack が外付け HCI を使用しないように `sudo nvram bluetoothHostControllerSwitchBehavior="never"` の設定が必要になる場合があります。実行前に現在の値を確認します。

```console
nvram bluetoothHostControllerSwitchBehavior
```

`libusb-1.0.dylib` が見つからない場合は、Homebrew で `libusb` を入れます。

```console
brew install libusb
```

Intel Mac の Homebrew 環境では、`libusb1` が `/usr/local/opt/libusb/lib` を自動探索しない場合があります。その場合は、実行時に `DYLD_LIBRARY_PATH` を指定します。

```console
export DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib
uv run swbt-probe adapters --json
```

`swbt-python` を source checkout から動かす場合、依存 package の build で `pkgconf` と `openssl@3` が必要になることがあります。

```console
brew install pkgconf openssl@3
```

#### Linux / macOS Verification Scope

Linux / macOS は experimental です。ここに書いた内容は、Bumble から専用アダプタを使う前に確認する項目です。接続成功を保証するものではありません。

Linux 上のアダプタ列挙、アダプタ open、HID 接続待ち受け、ペアリング、再接続、入力反映はまだ確認していません。macOS CI 上では依存関係のインストール、単体テスト、fake transport を使った結合テスト、パッケージ作成までは確認済みです。CI では USB Bluetooth ドングルを使いません。

### Adapter Name

ドライバー準備後、Bumble から見えるアダプタ名を確認します。

Python から確認する場合は `list_adapters()` を使います。

```python
from swbt import list_adapters

for info in list_adapters():
    print(info.name, info.aliases)
```

`info.name` は `ProController(adapter=info.name)` など具象コントローラーの `adapter` に渡す値です。`list_adapters()` は専用 USB Bluetooth ドングル候補を列挙します。対象機器本体や周辺 Bluetooth ホストは列挙しません。

CLI から確認する場合は `swbt-probe adapters --json` を使います。

```powershell
swbt-probe adapters --json
```

`list_adapters()` と `swbt-probe adapters --json` はアダプタ一覧確認用です。USB descriptor の読み取りは行いますが、Switch に向けたペアリング、HID 接続待ち受け、レポートループは開始しません。Bumble transport としてデバイスハンドルを開きません。

`adapter` には `usb:0` のような Bumble アダプタ名を指定します。アダプタ名は PC の接続状態で変わるため、コード例の `usb:0` を固定値として扱わないでください。

## Pairing And Reconnect

`key_store_path` はペアリング情報を保存する JSON key store path です。保存済みペアリング情報を使う場合は `ProController(adapter="usb:0", key_store_path="switch-bond.json")` のように指定します。

### Profile-specific Key Stores

key store はコントローラー種別ごとに分けてください。Pro Controller 相当、Joy-Con L 相当、Joy-Con R 相当のように HID identity や SDP record が異なる profile を同じ key store に混ぜると、保存済みペアリング情報と接続待ち受け時の identity の対応が崩れます。

運用例:

- Pro Controller 相当: `keys/pro-controller.json`
- Joy-Con L 相当: `keys/joy-con-left.json`
- Joy-Con R 相当: `keys/joy-con-right.json`

同じ profile でも、接続先の対象機器を分ける場合は key store も分けてください。1 つの key store は「1 つの対象機器」と「1 つの controller profile」の組み合わせに固定します。

## Controller Profile Verification Matrix
以下の表は、各コントローラー種別の動作確認状況をまとめたものです。

| Controller profile | Status | Verified scope | Not verified | Key store |
|---|---|---|---|---|
| Pro Controller | verified | Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 でペアリング、再接続、Button A / 十字キー / 左スティック / 右スティック、ニュートラル後の入力残りなしを確認。macOS 15.7.7 / CSR8510 A10 でもペアリング、active reconnect、Button 入力、ニュートラル後の入力残りなしを確認 | Linux、CSR8510 A10 以外のドングル、別 firmware、ペアリングなしの incoming 経路でのペアリング情報再利用 | 対象機器と controller profile ごとに別の `key_store_path` を使う |
| Joy-Con L | limited observation | Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で Joy-Con L device name、device-info reply、subcommand 応答、SR+SL 登録のユーザ目視を記録 | 再接続 / 通常入力反映、SDP の細部一致、OS / ドングル / firmware をまたぐ互換性 | Pro Controller と Joy-Con R とは別の `key_store_path` を使う |
| Joy-Con R | not verified | unit tests と fake transport integration で profile selection と unsupported input を確認 | ペアリング、再接続 / 通常入力反映、Switch UI 登録、OS / ドングル / firmware をまたぐ互換性 | Pro Controller と Joy-Con L とは別の `key_store_path` を使う |

## Confirmed Behavior

2026-07-04 時点では、Windows 11、CSR8510 A10、WinUSB / libwdi、Switch 2 firmware 22.1.0 の組み合わせで次を確認済みです。

- 初回ペアリング。
- 保存済みペアリング情報を使う再接続。
- Button A、十字キー、左スティック / 右スティックの入力反映。
- ニュートラル後に入力が残らないこと。

2026-07-05 時点では、macOS 15.7.7、CSR8510 A10、Homebrew `libusb`、Switch 2、adapter `usb:0` の組み合わせで次を確認済みです。

- 初回ペアリング。
- 保存済みペアリング情報を使う active reconnect。
- 主要 subcommand への応答を含む初期化 sequence。
- Button 入力の反映。
- ニュートラル後に入力が残らないこと。

確認済み条件のトレースログ、Bumble version、Python version、ドライバー情報は repository 内の `spec/hardware-test-log.md` にあります。

## Notes

Linux / macOS で必要になる OS 側設定は、Bumble から専用 USB Bluetooth ドングルを使うためのものです。PC に内蔵されている通常 Bluetooth 機能と同じアダプタは使わないでください。

## Troubleshooting

### Adapter Does Not Open

- 専用 USB Bluetooth ドングルを使っているか確認します。
- Windows では WinUSB / libwdi に切り替わっているか確認します。
- 専用ドングルのアダプタ名を指定しているか確認します。
- `list_adapters()` または `swbt-probe adapters --json` でアダプタ名を確認します。
- `adapters=[]` は HCI 候補 0 件です。ドライバー、USB 接続、OS 側の占有状態を確認します。
- `AdapterDiscoveryError` は libusb の読み込みや USB 列挙開始の失敗です。アダプタ open 失敗とは別に扱います。

### Pairing Timeout

- 対象機器がコントローラー接続画面にいるか確認します。
- `pair()` または `connect(..., allow_pairing=True)` を使っているか確認します。
- トレースログに `advertising_start`、`connection_request`、`host_connection` があるか確認します。

### No Bond

- `reconnect()` / `try_reconnect()` は保存済みペアリング情報がない場合、`no_bond` として失敗します。
- 初回接続では `connect(..., allow_pairing=True)` か `pair()` を使います。
- `key_store_path` が別ファイルを指していないか確認します。

### Multiple Current Peers

- 1 つの key store に複数の現在の再接続候補がある状態です。
- 対象機器ごとに key store を分けます。
- 復旧する場合は該当 key store を削除し、ペアリングをやり直します。

### Input Is Not Reflected In The UI

- ペアリングまたは再接続直後の初期通信が終わってから入力を送っているか確認します。
- `tap()` は即時レポートを送ります。`press()` / `release()` / `sticks()` / `neutral()` は state update API であり、即時送信を保証しません。
- トレースログの `report_tx`、`subcommand_rx`、`subcommand_reply_tx`、`connected`、`disconnected` を確認します。
