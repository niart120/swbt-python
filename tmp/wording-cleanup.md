# 文言整理メモ

## 2026-07-08 README.md

### 編集内容の客観説明

- README 冒頭と必要環境の説明で、`Bluetooth adapter`、`driver`、`firmware`、`USB Bluetooth dongle` などの英語混じりの表記が、`Bluetoothドングル`、`ドライバー`、`FWバージョン`、`USB Bluetooth ドングル` などの日本語寄りの表記に置き換えられた。
- 公開ドキュメントへの導線では、`実機構成と troubleshooting` が `実機準備手順とトラブルシューティング` に変わり、実機向けページの位置づけが構成情報より準備手順として読める表現になった。
- `docs/` 配下でも同じ内容を確認できるという説明から、リポジトリを checkout している場合という条件説明が削除された。
- 利用例の章に `Pro Controller` の小見出しが追加され、最初のコード例が Pro Controller 向けであることが明示された。
- Pro Controller の説明では、HID advertising、pairing / reconnect、periodic report loop、neutral 送信、専用 adapter、接続情報ファイルパスといった動作列挙が削られ、A ボタン入力を送る例として短く説明する形に変わった。
- Joy-Con の見出しは `単体 Joy-Con L/R` から `Joy-Con L/R` に変わり、単体 Joy-Con であることの強調が弱まった。
- Joy-Con の説明では、`SwitchGamepad` interface と同じ契約という説明が削除され、`ProController` と同じ扱い方という説明に置き換えられた。
- 片側 Joy-Con で未対応入力が `UnsupportedInputError` になる説明、Pro Controller / Joy-Con L / Joy-Con R で `key_store_path` を分ける説明、左右ペアの `JoyConPair` が未実装である説明、2026-07-06 の Joy-Con L 実機観測と未検証項目の列挙が README から削除された。
- 実機検証の章は `接続方法` に再編され、ドングルと OS ドライバー準備の説明が前面に出た。
- 実機検証まわりでは、実機ログの正本が `spec/hardware-test-log.md` であること、adapter 名の例が `usb:0` であること、CSR8510 A10 以外の Bluetooth dongle と Switch 2 firmware 22.1.0 以外の対象機器は確認済み構成に含めないことが README から削除された。
- `試験的構成` は `実験的構成` に変わり、Linux / macOS の未確認内容は `adapter が開けるか` から `Bluetoothデバイスにアクセスできるか` へ表現が変わった。

### 後続追記用メモ

同じ観点で docs 配下の他ファイルを整理する場合は、対象ファイルごとに次の粒度で追記する。

- 表記が変わった用語。
- 説明対象が変わった箇所。
- 短縮または削除された実機条件、未検証事項、根拠参照。
- 章構成や見出しの変更。
- 利用者に見える導線や前提条件の変化。
