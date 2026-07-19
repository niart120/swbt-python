# 既知のリスクと対策

この文書では、`swbt-python` の実装・検証で想定されるリスク、影響、対策を整理する。

## 1. Bumble Classic HID の不確実性

### 1.1 内容

Bumble は Python 製 Bluetooth stack であり、Bluetooth Classic、L2CAP、SDP、HID を扱える。ただし、本計画では Switch 向け Bluetooth Classic HID Device として使うため、Bumble の Classic HID 周辺の挙動が成否に直結する。

### 1.2 影響

- adapter open はできても pairing が進まない
- L2CAP control / interrupt channel が open しない
- HID Device として Switch に見えない
- Bumble の API 変更により実装が壊れる

### 1.3 対策

- Bumble 依存を `swbt.transport.bumble` に閉じ込める
- public API に Bumble 型を露出しない
- protocol core は Bumble なしで test する
- Bumble version を diagnostics に記録する
- `pyproject.toml` では対応確認済みの Bumble version range を明示する

## 2. Python scheduler jitter

### 2.1 内容

`ReportLoop` は `asyncio` で periodic input report を送る。Python と OS scheduler の都合により、8ms 周期を厳密に保てない可能性がある。

### 2.2 影響

- Switch 側で入力が不安定になる
- button tap が短すぎて認識されない
- subcommand reply が遅れる
- 実機では動くが CI では再現しない問題が出る

### 2.3 対策

- `report_period_us` を設定可能にする
- 実送信間隔を diagnostics に記録する
- test では fake clock を使い、実時間に依存しない
- 遅延時に過去 tick 分をまとめて送らない
- `tap()` の既定 duration は短くしすぎない

## 3. Switch firmware 差分

### 3.1 内容

Switch 本体種別や firmware version により、pairing、初期化 sequence、subcommand の順序や許容範囲が変わる可能性がある。

### 3.2 影響

- ある firmware では pairing できるが、別 firmware では失敗する
- 追加 subcommand への応答が必要になる
- `0x21` reply の内容が不足する
- input report は送れているが UI に反映されない

### 3.3 対策

- hardware test log に Switch model と firmware version を必ず記録する
- 未対応 subcommand を diagnostics に残す
- 対応済み構成と未確認構成を README に分けて書く
- firmware 差分を `testing.md` の matrix で管理する

## 4. OS / driver 差分

### 4.1 内容

Windows、Linux、macOS で USB Bluetooth dongle の扱いが異なる。Windows では WinUSB、Linux では libusb permission、macOS では USB Bluetooth dongle の扱い自体が制約になる可能性がある。

### 4.2 影響

- adapter を open できない
- OS 標準 Bluetooth stack と競合する
- 権限不足で libusb access が失敗する
- 開発者ごとに adapter moniker が異なる

### 4.3 対策

- 初期検証対象 OS を明示する
- Windows では専用 dongle と WinUSB 切り替えを前提にする
- Linux は experimental として、手順を文書化する
- macOS は Pro Controller の限定観測だけを確認済み範囲へ入れ、Joy-Con、別ドングル、別 firmware の確認済み範囲へ広げない
- macOS CI は実ハードなしの依存関係インストール、単体テスト、fake transport を使った結合テスト、package build に限定する
- `swbt-probe adapters` で候補 adapter を確認できるようにする
- OS、driver、adapter 情報を diagnostics に記録する

## 5. Bluetooth dongle 差分

### 5.1 内容

USB Bluetooth dongle の chipset や firmware によって、HCI command、Classic support、timing、pairing 挙動が異なる可能性がある。

### 5.2 影響

- ある dongle では pairing できるが、別 dongle では失敗する
- L2CAP channel open までは進むが HID data が安定しない
- reconnect が dongle 依存になる

### 5.3 対策

- 初期検証対象 dongle を限定する
- dongle VID/PID、chipset、driver を diagnostics に記録する
- hardware matrix で dongle 別に結果を管理する
- 未確認 dongle を README で保証対象外として明記する

## 6. HID descriptor / SDP record の不一致

### 6.1 内容

Switch が期待する HID descriptor や SDP record と実装内容がずれると、pairing はできても input report を受理しない可能性がある。

### 6.2 影響

- Switch 側に controller として表示されない
- HID channel は open するが subcommand が来ない
- `0x30` input report が UI に反映されない

### 6.3 対策

- 既存 `swbt-daemon` の descriptor と実機ログを参照する
- descriptor bytes を fixture として test に固定する
- SDP record 生成を Bumble transport に閉じ込める
- 実機 trace で subcommand sequence の開始有無を確認する

## 7. subcommand 応答不足

### 7.1 内容

Switch の初期化 sequence で必要な subcommand への応答が不足すると、接続処理が途中で止まる。

### 7.2 影響

- pairing 後に入力が反映されない
- Switch UI 上で controller 登録が完了しない
- 同じ report を繰り返し要求される

### 7.3 対策

- output report を diagnostics に raw bytes で記録する
- 未対応 subcommand は明示的に trace へ出す
- `SubcommandResponder` の unit test を追加してから実機再検証する
- `0x21` reply を periodic `0x30` より優先する

## 8. reconnect の不確実性

### 8.1 内容

pairing 情報の保存、link key の扱い、active reconnect / incoming reconnect の挙動は Bumble と OS / dongle の組み合わせに依存する。

key storeはbond情報のnamespaceであり、local BD_ADDRを変更しない。複数のkey storeを用意しても、同じlocal BD_ADDRのままならSwitchから見た物理device identityは分離できない。

### 8.2 影響

- 初回 pairing は成功するが reconnect できない
- reconnect 失敗後に明示 API で再 pairing できない
- key store が壊れた場合に復旧手順が必要になる
- profileごとにkey storeだけを分け、local BD_ADDRを同じまま使うと、Switch側の登録が衝突する可能性がある

### 8.3 対策

- reconnect は M6 まで public guarantee にしない
- `key_store_path` の存在と読み書きを diagnostics に記録する
- reconnect 失敗時は failure diagnostics を残して clean close する
- 自動 advertising recovery と retry loop は、pre-host-connection timeout 再発リスクを別途監査するまで M6 に含めない
- key store 削除による再 pairing 手順を文書化する
- BD_ADDR切替はCSR8510 A10のvolatile実験経路に限定し、public APIにはまだ露出しない
- address変更後はBumbleの可視化前にstandard HCI addressを照合し、不一致ならpairingを拒否する
- USB power cycleでvolatile addressが元へ戻るため、後続のidentity切替機能では起動時の再適用と復旧確認を必須にする
- 実運用addressは正規に割り当てられたuniversal EUI-48を使い、実験用local / dummy addressを流用しない

## 9. scope creep

### 9.1 内容

daemon、IPC、GUI、macro scheduler、amiibo、rumble、複数 controller を同時に進めると、protocol core と実機接続の検証が遅れる。

### 9.2 影響

- 初期 release が遅れる
- test 対象が広がりすぎる
- 不具合の原因が protocol、transport、API のどこにあるか切り分けにくくなる

### 9.3 対策

- 初期対象外の機能を README に明記する
- M0 から M5 までは単一 controller と入力反映に集中する
- daemon や CLI は `SwitchGamepad` の wrapper として後から追加する
- public API に拡張予定だけの引数を入れない

## 10. documentation drift

### 10.1 内容

実装が進むにつれて、設計文書、README、test、実機検証ログの内容がずれる可能性がある。

### 10.2 影響

- 対応済みと未確認の境界が曖昧になる
- 利用者が誤った環境で試す
- 実機問題の再現条件が残らない

### 10.3 対策

- milestone 完了時に該当文書を更新する
- hardware test 結果を matrix に反映する
- README には確認済み構成と未確認構成を分けて書く
- trace schema を安定させる

## 11. Initial release gate の確認済み / 未確認境界

### 11.1 内容

初期 release gate では、確認済み構成と未確認構成を分けて扱う。確認済み範囲は `spec/hardware-test-log.md` の実機観測に限り、未確認構成へ一般化しない。

### 11.2 確認済み範囲

| 項目 | 値 |
|---|---|
| OS | Windows 11 |
| Bluetooth dongle | CSR8510 A10 |
| driver | WinUSB / libwdi |
| adapter | `usb:0` |
| Python | 3.13.5 |
| Bumble | 0.0.230 |
| 対象機器 | Switch 2 |
| firmware | 22.1.0 |

この構成では、Pro Controller の pairing、L2CAP、full observed subcommand handshake、Button A、neutral、D-pad、left / right stick、保存済みペアリング情報を使う active reconnect を観測済みとする。Joy-Con L/R は SR+SL 登録、利用者指定色、Joy-Con L の D-pad、Joy-Con R の ABXY を観測済みとする。Joy-Con L/R の stick は hold / circle の送信までを確認済みとし、横持ち Joy-Con に対する Switch UI の補正拒否は device/UI 制約として扱う。L+R 同時押し表示は、Switch button check UI の表示制約として扱う。

macOS 15.7.7 / CSR8510 A10 / Homebrew `libusb` / Switch 2 では、Pro Controller の pairing、active reconnect、Button 入力、neutral 後の入力残りなしを限定観測として記録済みとする。

### 11.3 未確認範囲

- Linux の adapter listing、adapter open、OS 設定変更。
- Linux / libusb permission、udev rule、kernel / BlueZ 競合解消。
- macOS の Joy-Con profile、別ドングル、別 firmware。
- CSR8510 A10 以外の Bluetooth dongle。
- Switch 2 / firmware 22.1.0 以外の対象機器と firmware。
- pairing-free incoming bond reuse。
- production publish、tag push、PyPI trusted publishing。

Linux は experimental として手順を出す。ただし、動作検証済みとは書かない。macOS は Pro Controller の限定観測だけを記録し、Joy-Con profile や別ドングルでの互換性へ一般化しない。macOS CI の実ハードなし gate は、macOS runner 上で依存関係のインストール、単体テスト、fake transport を使った結合テスト、package build が壊れていないことだけを確認する。CI では USB Bluetooth ドングル、OS Bluetooth stack 設定、HID advertising、pairing、input reflection を検証しない。

上記は release gate の失敗ではなく、初期 release の保証外として README と hardware matrix に残す。publish、tag push、PyPI trusted publishing は別作業で扱い、実行前にユーザの明示確認を必要とする。
