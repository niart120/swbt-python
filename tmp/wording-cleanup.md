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

## 2026-07-08 docs/api.md

### 編集内容の客観説明

- `swbt.gamepad.*` や `swbt.transport.*` の deep import をテストと移行作業に限定する説明、Bumble 型や transport protocol を public API に露出しない説明が削除された。
- `Top-Level Exports` の導入文は、`swbt.__all__` の公開名一覧という説明から、トップレベル公開 API と主な利用用途を説明する文に変わった。
- `list_adapters()` の説明では、専用 USB Bluetooth dongle、adapter、host などの英語混じりの表記が、専用 USB Bluetooth ドングル、デバイス名称、アダプタ、ホストなどの日本語寄りの表現に置き換えられた。
- `list_adapters()` の説明から、Nintendo Switch 本体や周辺 Bluetooth host を列挙しないこと、候補 0 件と列挙不能を別状態として扱うこと、serial alias を永続指定として使うこと、Bluetooth controller power on を開始しないことが削除された。
- `AdapterInfo.name` の説明は、controller の `adapter` に渡す adapter moniker という説明から、`usb:N` などの名称を取得するための値という説明に変わった。
- Controller class の説明では、`concrete controller` が `具象クラス` に置き換えられた。`SwitchGamepad` を共通 interface として使う説明は残っている。
- `adapter`、`key_store_path`、`report_period_us`、`controller_colors` の説明は短縮された。public controller では `adapter` が必須であること、profile ごとの既定周期、HID Device 表示名、controller color の作成時固定、SPI read 応答の byte layout は削除された。
- Resource scope と connection の説明では、`advertising`、`pairing`、`reconnect`、`report loop` などが、HID 接続待ち受け、ペアリング、再接続、レポートループなどに置き換えられた。
- 接続 API の表では、pairing fallback をしないこと、bond の語、current peer の語が削られ、保存済み接続情報、接続結果、タイムアウト、接続失敗という利用者向けの語が増えた。
- 入力 API の表では、button set、stick、report、release report などの表記が、ボタン入力状態、スティック入力、レポート、押上レポートなどに置き換えられた。`apply(state)` が差分適用ではないこと、`tap()` が接続済みを要求することは削除された。
- `Input Model` は Joy-Con の後ろから `Observation` の前へ移動された。API の並びとして、入力 API の直後に入力モデルを説明する構成に変わった。
- IMU、Stick、InputState、ControllerColors の説明は、日本語の補足が増えた一方で、raw、frame、sample、sensor、immutable state などの英語語彙は一部残った。
- Joy-Con の説明では、対応 button の列挙が `Button.L` などの enum 完全名から `L` などの表示名寄りの表記へ変わった。
- Joy-Con の未対応入力説明は、片側 profile が持たない入力という一般説明から、`JoyConL` と `JoyConR` に渡すと `UnsupportedInputError` が送出される具体例の説明に変わった。
- Joy-Con の章から、同じ対象機器でも profile を変える場合は key store を共有しないこと、`JoyConPair` が public API にないこと、2026-07-06 の Joy-Con L 実機観測、Joy-Con R / reconnect / 通常入力反映 / SDP 完全一致の未検証事項が削除された。
- `Errors And Diagnostics` では、例外説明が 1 段落に短縮された。`DiagnosticsConfig(trace_writer=...)`、JSON Lines trace、secret material を記録しない説明は削除された。
- `Transport Boundary` の章全体が削除された。Bluetooth HID transport を内部境界とする説明、backend object を利用者 API に渡さない説明、別 backend の公式 API がまだない説明は `docs/api.md` から消えた。

### 気づき

- `AdapterInfo` の文脈で `AdaptroInfo.name` という表記が入っている。これは客観説明上は変更点として扱ったが、用語辞書を作るなら `AdapterInfo` に統一する候補になる。
- `transport`、`key store`、`state update API`、`complete state`、`immutable state` などは日本語化せず残っている。API 用語として残す語と、利用者向け説明で日本語化する語を分ける必要がある。

## 2026-07-08 docs/index.md

### 編集内容の客観説明

- 末尾にあった「実機や Bluetooth adapter に依存する条件は docs/hardware.md にある」という案内文が削除された。
- `docs/hardware.md` への導線自体は箇条書きに残っているため、同じページ内での hardware guide への誘導が重複しない構成になった。

## ここまでの差分から抽出した用語辞書候補

この表は確定辞書ではなく、README.md、docs/api.md、docs/index.md の差分から抽出した候補である。後続の docs 整理で表記をそろえるための作業台として使う。

| 対象 | 候補表記 | 旧表記 / 揺れ | メモ |
|---|---|---|---|
| USB Bluetooth 機器 | 専用 USB Bluetooth ドングル | USB Bluetooth dongle、Bluetooth dongle、Bluetoothドングル | 利用者が物理機器として読む箇所では日本語寄りにする。`専用` を付けるかは文脈で判断が必要。 |
| OS 側の準備 | ドライバー | driver | Windows 手順や Zadig の説明では日本語表記へ寄せる流れ。 |
| firmware | FWバージョン | firmware | README では `FWバージョン` に変わった。公開 docs 全体で使うには `ファームウェア` と比較検討が必要。 |
| adapter | アダプタ | adapter | UI や利用者手順では `アダプタ`。コード引数 `adapter` はそのまま残す。 |
| adapter name | アダプタ名 / アダプタの名称 | adapter 名、adapter moniker | 利用者に渡す値として説明する場合は `アダプタ名` が読みやすい。 |
| pairing | ペアリング | pairing | API 名や `allow_pairing` はそのまま、説明文は日本語化する流れ。 |
| reconnect | 再接続 | reconnect | メソッド名 `reconnect()` は残し、説明文では `再接続` を使う。 |
| HID advertising | HID 接続待ち受け | advertising、HID advertising | Switch から見える接続待機動作として説明する場合の候補。 |
| periodic report loop | レポートループ | periodic report loop、report loop | 入力レポート送信の周期処理を説明する語。 |
| input report | 入力レポート / レポート | input report、report | API 説明では `レポート` が増えているが、HID 文脈では `入力レポート` の方が曖昧さが少ない。 |
| key store | key store / 接続情報ファイル | JSON key store path、接続情報ファイル | README では利用者向けに `接続情報ファイル`、API 詳細では `key store` が残る。二層に分ける候補。 |
| bond | 保存済み接続情報 / ペアリング情報 | bond | 利用者向け説明では `bond` を避ける流れ。protocol / transport 内部では残す候補。 |
| button | ボタン | button | enum 名や型名はそのまま、説明文では `ボタン`。 |
| stick | スティック | stick | 型名 `Stick` はそのまま、説明文では `スティック入力`。 |
| D-pad | 十字キー | D-pad | Joy-Con の説明では `十字キー` に寄せる流れ。 |
| neutral | ニュートラル | neutral | `neutral()` は API 名として残し、入力状態の説明では `ニュートラル入力`。 |
| timeout | タイムアウト | timeout | 例外や status 値はそのまま、説明文は日本語化する。 |
| error thrown | 送出されます | 投げます、返します | 例外説明では `送出されます` に寄せる流れ。 |
| concrete controller | 具象クラス | concrete controller | 型説明では `具象クラス`。 |
| public API | 公開 API / public API | public API、公開API | 差分内で揺れがある。日本語本文では `公開 API` に統一する候補。 |
| transport | transport | トランスポート | API 境界語として英語のまま残っている。辞書では「残す専門語」に分類する候補。 |
| profile | profile / プロファイル | profile、プロファイル | controller profile と色 profile で揺れがある。文脈ごとに決める必要がある。 |
| IMU frame | IMU frame / IMU 入力単位 | frame、入力単位 | 利用者向けには `IMU 入力単位`、API 詳細では `IMU frame` を併記する候補。 |
| accelerometer / gyroscope | 加速度 / ジャイロ | accelerometer、gyroscope、gyro | `gyro` は API 名として残し、説明では日本語補足を付ける候補。 |
| troubleshooting | トラブルシューティング | troubleshooting | docs 導線では日本語化する流れ。 |
