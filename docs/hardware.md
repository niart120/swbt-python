# 実機準備手順

`swbt-python` の実機接続では、PC の標準 Bluetooth 機能ではなく、Bumble から直接開く専用 USB Bluetooth ドングルを使います。
最初にドライバーとアダプタ名を確認し、その後に対象機器側でコントローラー接続画面を開いて接続します。

## 準備

### 必要なもの

| 項目 | 内容 |
|---|---|
| Python | Python 3.12 以降 |
| 専用 USB Bluetooth ドングル | PC の通常 Bluetooth 機能と共有しない専用ドングル |
| 対象機器 | 「持ちかた/順番を変える」画面へ手動で移動できること |

### ドライバーと USB アクセス

Bumble の `usb:` アダプタは USB HCI transport を libusb 経由で使います。
ここでのドライバー準備は、OS の Bluetooth 機能で使うドライバーではなく、専用ドングルを Bumble から直接開くための OS 側設定を指します。

| OS | 対応状況 | 準備 |
|---|---|---|
| Windows | 対応済み | Zadig などで専用ドングルに WinUSB / libwdi ドライバーを導入する |
| Linux | experimental | `libusb-1.0` が使えること、USB デバイスにアクセスできること、カーネルまたは BlueZ が対象ドングルを使用中でないことを確認する |
| macOS | experimental | `libusb-1.0` が使えること、macOS の Bluetooth スタックが外付け HCI を使用しない設定になっていること、必要に応じて libusb のライブラリ検索パスを指定する |

#### Windows の USB ドライバー設定

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

#### Linux の USB ドライバー設定

Linux の手順はこの文書に整備されていますが、動作検証されていないことに留意してください。

Linux では、Bumble 同梱の `libusb_package` で `libusb-1.0` が見つからない場合、OS 側で `apt install libusb-1.0-0` が必要になることがあります。USB デバイスへのアクセス権を付け、カーネルまたは BlueZ がドングルを使用中の場合は `hciconfig hciX down` などで解放する必要があります。

#### macOS の USB ドライバー設定

macOS では、macOS の Bluetooth スタックが外付け HCI を使用しないように `sudo nvram bluetoothHostControllerSwitchBehavior="never"` の設定が必要になる場合があります。実行前に現在の値を確認します。

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

`swbt-python` をソースコードを取得した作業ツリーから動かす場合、依存パッケージの作成に `pkgconf` と `openssl@3` が必要になることがあります。

```console
brew install pkgconf openssl@3
```

#### Linux / macOS の確認範囲

Linux / macOS は experimental です。ここに書いた内容は、Bumble から専用 USB Bluetooth ドングルを使う前に確認する項目です。接続成功を保証するものではありません。

Linux 上のアダプタ列挙、アダプタを開く処理、HID 接続待ち受け、ペアリング、再接続、入力反映は未確認です。macOS 15.7.7 / CSR8510 A10 では Pro Controller の限定的な動作確認結果がありますが、Joy-Con プロファイル、別ドングル、別ファームウェアでの互換性は未確認です。macOS CI 上では依存関係のインストール、単体テスト、実機を使わない通信実装による結合テスト、パッケージ作成までは確認済みです。

### アダプタ名

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

`list_adapters()` と `swbt-probe adapters --json` はアダプタ一覧確認用です。USB ディスクリプターの読み取りは行いますが、Switch に向けたペアリング、HID 接続待ち受け、レポートループは開始しません。Bumble を使う下位の通信実装としてデバイスハンドルを開きません。

`adapter` には `usb:0` のような Bumble アダプタ名を指定します。アダプタ名は PC の接続状態で変わるため、コード例の `usb:0` を固定値として扱わないでください。

## ペアリングと再接続

### ペアリングプロファイルのアドレス選択

アダプタの Bluetooth アドレスを書き換えずに接続情報を永続化する場合は、`local_address` を省略して最初のペアリング用プロファイルを作成します。

```python
pad = await ProController.create_profile(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
    pair_timeout=60.0,
)
await pad.close()
```

- この経路は Bumble の `power_on()` 後にアダプタが報告した現在の Bluetooth アドレスを使います。出荷時アドレスであることは保証しません。
- 以前に揮発領域へ書き込んだ値が USB の給電断まで残っている場合、その値が現在の既定アドレスになることがあります。
- アダプタが別のアドレスを報告した場合は新しいペアリングキーの保存領域を使い、以前のペアリングキーを自動移行しません。
- `power_on()` 後も有効な Bluetooth アドレスを取得できない場合は `InvalidKeyStoreError` とし、HID 接続待ち受けと保存済みペアリング情報を使う再接続を開始しません。

利用者管理の個別かつローカル管理のアドレスへ切り替える場合だけ、`local_address` を明示します。`local_address` を明示する経路は CSR8510 A10 の揮発領域を書き換えます。

```python
pad = await ProController.create_profile(
    adapter="usb:0",
    profile_path="profiles/switch-pro-local-address.json",
    local_address="02:12:34:56:78:9A",
    pair_timeout=60.0,
)
await pad.close()
```

- `local_address` の生成、重複回避、管理は利用者の責任です。例示した `02:12:34:56:78:9A` は共通値として使わず、利用者ごとに管理する値へ置き換えます。
- 書き換えるのは揮発領域だけです。`close()` はアドレスを元へ戻しません。
- 専用 USB Bluetooth ドングルを抜き差しすると揮発領域のアドレスが失われる場合があります。次回 `profile_path` を使うときに再適用されます。
- 書換開始後の状態を確定できず `AdapterIdentityRecoveryRequired` が送出された場合は、専用 USB Bluetooth ドングルを抜き差ししてから再試行します。
- 出荷時アドレスの読取りと保存、公開の読み取り専用確認 API、CSR8510 A10 以外の互換性判定は行いません。

作成済みプロファイルは次のように再利用します。プロファイル JSON にはアドレスとペアリングキーが同居するため、別の対象機器やコントローラー種別と共有しません。

```python
pad = ProController(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
)
await pad.reconnect(timeout=60.0)
```

### Joy-Con / 直接送信型のペアリング情報

周期送信型と直接送信型は、いずれもアダプタ識別情報とペアリングキーを保存する `profile_path` を使います。保存ファイルは Pro Controller、Joy-Con L、Joy-Con R のコントローラー形状ごとに分けます。同じコントローラー形状の周期送信型と直接送信型の間で同じプロファイルを受け付けますが、方式間再利用は実機未検証です。

運用例:

- Pro Controller 相当: `profiles/pro-controller.json`（swbt プロファイル）
- Joy-Con L 相当: `profiles/joy-con-left.json`
- Joy-Con R 相当: `profiles/joy-con-right.json`

同じコントローラー形状でも、接続先の対象機器を分ける場合はペアリング情報の保存ファイルも分けてください。1 つの保存ファイルは「1 つの対象機器」と「1 つのコントローラー形状」の組み合わせに固定します。

## コントローラー別の実機確認状況

以下の表は、各コントローラー種別の動作確認状況をまとめたものです。

| コントローラー | 確認状況 | 確認済み | 未確認 | プロファイルの保存先 |
|---|---|---|---|---|
| Pro Controller | 一部確認済み | 2026-07-20 の unit_052 では `local_address` を明示するプロファイルの揮発アドレス準備、初回ペアリング、保存済みペアリング情報を使う再接続を確認。2026-07-24 の unit_066 では同じ Windows 11 / CSR8510 A10 / WinUSB 構成で、アダプタ既定アドレスのプロファイルによる初回ペアリング、プロファイル内容を変えない再接続、再接続時に HID 接続待ち受け、ペアリング、鍵更新が発生しないことを確認 | アダプタ既定アドレスのプロファイルを初回ペアリング後に終了するときのニュートラル入力、USB の給電断後に現在の Bluetooth アドレスが変わる場合、Linux、CSR8510 A10 以外、別ファームウェア | 対象機器ごとに別の `profile_path` を使う |
| Joy-Con L | 一部確認済み | 2026-07-20 に Windows 11 / CSR8510 A10 / WinUSB / Switch 2 ファームウェア 22.5.0 で、ペアリングプロファイルの揮発アドレス準備、初回ペアリング、通常終了、同一プロファイルによる再接続を確認 | SDP の細部一致、USB の給電断と再接続後の再適用、OS / ドングル / ファームウェアをまたぐ互換性 | コントローラー形状と対象機器ごとに別の `profile_path` を使う |
| Joy-Con R | 一部確認済み | 2026-07-20 に Windows 11 / CSR8510 A10 / WinUSB / Switch 2 ファームウェア 22.5.0 で、ペアリングプロファイルの揮発アドレス準備、初回ペアリング、通常終了、同一プロファイルによる再接続を確認 | SDP の細部一致、USB の給電断と再接続後の再適用、OS / ドングル / ファームウェアをまたぐ互換性。初回ペアリング終了時の Bumble / usb1 コールバック警告は実機テストログを参照 | コントローラー形状と対象機器ごとに別の `profile_path` を使う |

## 確認済みの動作

2026-07-07 時点では、Windows 11、CSR8510 A10、WinUSB / libwdi、Switch 2 ファームウェア 22.1.0 の組み合わせで次を確認済みです。

- Pro Controller の初回ペアリング、保存済みペアリング情報を使う再接続、主要な初期化シーケンス。
- Pro Controller の A / L / R ボタン、十字キー、左スティック / 右スティック、ニュートラル復帰、切断。
- Joy-Con L/R の登録と利用者指定色。
- Joy-Con L の十字キー入力、Joy-Con R の ABXY 入力。
- Joy-Con L/R の対応スティック入力送信とニュートラル復帰。

2026-07-05 時点では、macOS 15.7.7、CSR8510 A10、Homebrew `libusb`、Switch 2、アダプタ名 `usb:0` の組み合わせで次を確認済みです。

- 初回ペアリング。
- 保存済みペアリング情報を使う再接続。
- 主要な初期化シーケンス。
- ボタン入力の反映。
- ニュートラル復帰。

確認済み条件のトレースログ、Bumble バージョン、Python バージョン、ドライバー情報はリポジトリ内の `spec/hardware-test-log.md` にあります。

## 注意事項

Linux / macOS で必要になる OS 側設定は、Bumble から専用 USB Bluetooth ドングルを使うためのものです。PC に内蔵されている通常 Bluetooth 機能と同じアダプタは使わないでください。

## トラブルシューティング

### アダプタが開けない

- 専用 USB Bluetooth ドングルを使っているか確認します。
- Windows では WinUSB / libwdi に切り替わっているか確認します。
- 専用ドングルのアダプタ名を指定しているか確認します。
- `list_adapters()` または `swbt-probe adapters --json` でアダプタ名を確認します。
- `adapters=[]` は HCI 候補 0 件です。ドライバー、USB 接続、OS 側の占有状態を確認します。
- `AdapterDiscoveryError` は libusb の読み込みや USB 列挙開始の失敗です。アダプタを開く処理の失敗とは別に扱います。

### ペアリングがタイムアウトする

- 対象機器がコントローラー接続画面にいるか確認します。
- `pair()` または `connect(..., allow_pairing=True)` を使っているか確認します。
- トレースログに `protocol_initialization_started` がなければ、HID リンク接続前に停止しています。イベントがあり `protocol_ready` がなければ、`subcommand_rx`、`subcommand_reply_tx`、`protocol_initialization_failed`、`connection_timeout` を確認します。

### 保存済みペアリング情報がない

- `reconnect()` / `try_reconnect()` は保存済みペアリング情報がない場合、`no_bond` として失敗します。
- 初回接続では `connect(..., allow_pairing=True)` か `pair()` を使います。
- すべての具象クラスで、コントローラー形状と対象機器ごとに別の `profile_path` を指しているか確認します。

### アダプタの Bluetooth アドレスを取得できない

- アダプタ既定アドレスのプロファイルで `InvalidKeyStoreError` が発生した場合は、トレースログの `local_bluetooth_address_configured` を確認します。
- このイベントがない場合は、Bumble が `power_on()` 後に Bluetooth アドレスを取得できていません。HID 接続待ち受けや保存済みペアリング情報を使う再接続は開始されていないため、専用ドングルの USB 接続とドライバーを確認してから再試行します。

### 現在の接続先が複数ある

- 1 つのプロファイルに複数の現在の再接続候補がある状態です。
- 対象機器ごとにプロファイルを分けます。
- 復旧する場合は該当プロファイルを削除し、`create_profile()` で作り直してからペアリングをやり直します。

### 入力が対象機器の画面に反映されない

- `pair()` / `connect()` / `reconnect()` が正常終了しているか確認します。正常終了は初期サブコマンド応答とプレイヤー割り当ての完了を含みます。
- `tap()` は即時レポートを送ります。`press()` / `release()` / `sticks()` / `neutral()` は状態更新 API であり、即時送信を保証しません。
- トレースログの `protocol_ready`、`report_tx`、`subcommand_rx`、`subcommand_reply_tx`、`disconnected` を確認します。
