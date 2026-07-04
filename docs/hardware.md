# Hardware

この文書は実機、Bluetooth adapter、driver、pairing / reconnect、troubleshooting の正本です。ここに書く確認済み範囲は `docs/hardware-test-log.md` と completed specs の観測に限定します。別構成への保証には使いません。

## Requirements

| 項目 | 内容 |
|---|---|
| Python | Python 3.12 以降。確認済み run は Python 3.13.5 |
| Bumble | `bumble>=0.0.230,<0.0.231`。確認済み run は Bumble 0.0.230 |
| adapter | Bumble から開ける専用 USB Bluetooth dongle |
| driver | OS 標準 Bluetooth stack と adapter を共有しない設定 |
| 対象機器 | controller pairing / search 画面へ手動で移動できること |

## Confirmed Configuration

2026-07-04 時点の確認済み構成です。

| 項目 | 値 |
|---|---|
| OS | Windows 11 |
| Bluetooth dongle | CSR8510 A10 |
| driver | WinUSB / libwdi |
| adapter | `usb:0` |
| Python | Python 3.13.5 |
| Bumble | Bumble 0.0.230 |
| 対象機器 | Switch 2 |
| firmware | 22.1.0 |

この構成では、pairing、L2CAP、full observed subcommand handshake、Button A、neutral 後の入力残りなし、D-pad、left / right stick、active bond reuse reconnect を観測済みです。active bond reuse reconnect は明示的な Classic authentication / encryption 後に HID control / interrupt L2CAP open と `active_reconnect_result status=connected` を記録した run に基づきます。

incoming route の分離は観測済みですが、同じ trace に `classic_pairing` と `key_store_update` が出たため、pairing-free incoming bond reuse は未確認です。

## Unconfirmed Configuration

- Linux / libusb permission と udev rule。
- macOS。
- CSR8510 A10 以外の Bluetooth dongle。
- Switch 2 / firmware 22.1.0 以外の対象機器と firmware。
- pairing-free incoming bond reuse。
- OS 標準 Bluetooth stack と同じ adapter を共有する構成。

未確認構成は確認済みとして扱いません。上記で動かない場合でも、確認済み構成の失敗とは別に切り分けます。

## Adapter And Driver

Bumble から開く adapter は専用 USB Bluetooth dongle にしてください。OS 標準 Bluetooth stack が使っている adapter を共有しないでください。

Windows では WinUSB / libwdi の構成で確認済みです。標準 driver のままでは Bumble から開けない場合があります。

Linux は libusb 権限設定が必要になる想定ですが、この repo では未確認です。macOS も未確認です。

adapter 名は環境ごとに変わります。`swbt-probe adapters --json` で候補を確認できます。この command は adapter 一覧確認用であり、Switch-facing pairing や report loop は開始しません。

## Pairing And Reconnect

`key_store_path` は pairing 情報を保存する JSON key store path です。保存済み bond を使う場合は `SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json")` のように指定します。

`connect(timeout=..., allow_pairing=True)` は保存済み bond があれば reconnect を優先し、bond がない場合だけ pairing fallback へ進みます。初回 pairing では対象機器を controller pairing / search 画面に置いてください。

`reconnect(timeout=...)` は key store に current bonded peer が 1 件ある場合だけ active reconnect を試します。pairing fallback はしません。

1 つの key store に複数の current peers を混ぜないでください。複数 current peers は `multiple current peers` の不正状態として扱い、どの peer を使うかを推測しません。別対象機器には別の `key_store_path` を使ってください。

## Troubleshooting

### Adapter Does Not Open

- 専用 USB Bluetooth dongle を使っているか確認します。
- Windows では WinUSB / libwdi に切り替わっているか確認します。
- OS 標準 Bluetooth stack と同じ adapter を共有していないか確認します。
- `swbt-probe adapters --json` で adapter moniker を確認します。

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

- 接続直後ではなく、full observed subcommand handshake 後に入力を送っているか確認します。
- `tap()` は即時 report を送ります。`press()` / `release()` / `sticks()` / `neutral()` は state update API であり、即時送信を保証しません。
- trace の `report_tx`、`subcommand_rx`、`subcommand_reply_tx`、`connected`、`disconnected` を確認します。
- 別 firmware、別 dongle、別 OS では未確認として扱います。
