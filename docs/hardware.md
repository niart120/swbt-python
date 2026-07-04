# Hardware

実機接続には、Bumble が直接開ける USB Bluetooth dongle と、対象機器側の pairing / reconnect 操作が必要です。確認済み条件は `docs/hardware-test-log.md` と completed specs の観測に基づきます。

## Requirements

### General

| 項目 | 内容 |
|---|---|
| Python | Python 3.12 以降 |
| USB Bluetooth dongle | PC の通常 Bluetooth 機能と共有しない専用 dongle |
| 対象機器 | controller pairing / search 画面へ手動で移動できること |

### Driver

Bumble の `usb:` adapter は USB HCI transport を libusb 経由で開きます。ここでの driver 準備は、OS の Bluetooth 機能用 driver ではなく、専用 dongle を Bumble から直接開くための OS 側設定です。

| OS | status | 準備 |
|---|---|---|
| Windows | supported | Zadig などで専用 dongle に WinUSB / libwdi driver を入れる |
| Linux | unsupported / untrusted | udev rule などで libusb のアクセス権限を与え、専用 dongle を `swbt-probe adapters --json` で確認する想定 |
| macOS | unsupported / untrusted | 追加 driver 手順は未確認。Bumble / libusb から専用 dongle を直接開けるか `swbt-probe adapters --json` で確認する想定 |

## Windows Driver Setup

Windows では、Zadig などで専用 USB Bluetooth dongle に WinUSB / libwdi driver を入れます。

[Zadig](https://zadig.akeo.ie/) は、Windows 上で WinUSB などの汎用 USB driver を対象デバイスへ入れるためのツールです。

Zadig では次の順に進めます。

- 専用 USB Bluetooth dongle を接続し、Zadig を管理者権限で起動する。
- 対象の dongle を選択する。
- 一覧に出ない場合は `Options > List All Devices` を使う。
- 選択した USB device の VID / PID が対象 dongle と一致することを確認する。
- driver は `WinUSB` を選ぶ。
- `Install Driver` を実行する。

Zadig の操作画面と詳細は [Zadig 2.x User Guide](https://github.com/pbatard/libwdi/wiki/Zadig) を確認してください。

driver 置換後、Bumble から見える adapter 名を確認します。

```powershell
swbt-probe adapters --json
```

この command は adapter 一覧確認用です。Switch-facing pairing、HID advertising、report loop は開始しません。

`adapter` には `usb:0` のような Bumble adapter 名を指定します。adapter 名は PC の接続状態で変わるため、コード例の `usb:0` を固定値として扱わないでください。

## Confirmed Behavior

2026-07-04 時点では、Windows 11、CSR8510 A10、WinUSB / libwdi、Switch 2 firmware 22.1.0 の組み合わせで次を確認済みです。

- 初回 pairing。
- 保存済み pairing 情報を使う reconnect。
- Button A、D-pad、left / right stick の入力反映。
- neutral 後に入力が残らないこと。

詳細な trace、Bumble version、Python version、driver version は [hardware-test-log](hardware-test-log.md) にあります。

## Unsupported Environments

- Linux。
- macOS。
- CSR8510 A10 以外の Bluetooth dongle。
- Switch 2 firmware 22.1.0 以外の対象機器と firmware。
- PC の通常 Bluetooth 機能と同じ adapter を使う構成。

Linux / macOS は supported ではありません。上の想定手順で adapter が見えた場合だけ pairing へ進めます。Linux の udev rule、macOS の adapter 準備、実機 pairing、入力反映は未確認です。

## Pairing And Reconnect

`key_store_path` は pairing 情報を保存する JSON key store path です。保存済み bond を使う場合は `SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json")` のように指定します。

`connect(timeout=..., allow_pairing=True)` は保存済み bond があれば reconnect を優先し、bond がない場合だけ pairing fallback へ進みます。初回 pairing では対象機器を controller pairing / search 画面に置いてください。

`reconnect(timeout=...)` は key store に current bonded peer が 1 件ある場合だけ active reconnect を試します。pairing fallback はしません。

1 つの key store に複数の current peers を混ぜないでください。複数 current peers は `multiple current peers` の不正状態として扱い、どの peer を使うかを推測しません。別対象機器には別の `key_store_path` を使ってください。

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
