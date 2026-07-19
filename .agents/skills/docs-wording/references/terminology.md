# 用語辞書

公開 API の識別子と日本語の説明語を区別する。クラス名、メソッド名、引数名、状態値はバッククォートで囲んで正確な綴りを残し、地の文に使う一般名詞は日本語へ寄せる。

| 対象 | 推奨表記 | 残す表記 / 避ける揺れ | 方針 |
|---|---|---|---|
| public API | 公開 API | `public API`, `公開API` | 日本語本文では「公開 API」に統一する。 |
| module root / import | モジュール直下 / インポート | `module root`, `import` | コードや import 文は変更しない。読み込み元の説明では「`swbt` モジュール直下」のように書く。 |
| class / interface | クラス / 抽象型 | `class`, `interface` | 公開クラス名は残す。抽象基底の説明では「抽象型」を使う。 |
| concrete controller | 具象クラス | `concrete controller`, `具象コントローラー` | コントローラー種別を実装するクラスの説明に使う。 |
| lifecycle | 生成から終了までの管理 | `lifecycle` | 生成、接続、終了をまとめた責務を具体的に書く。 |
| Periodic / Direct | 周期送信型 / 直接送信型 | `Periodic 具象クラス`, `Direct 具象クラス` | `PeriodicSwitchGamepad` や `DirectProController` など完全な公開クラス名は残す。説明上の分類には日本語を使う。 |
| state | 状態 / 入力状態 | `state` | 引数名 `state` や `InputState` は残す。地の文では対象を明示する。 |
| local state | ライブラリ内部の入力状態 | `local state`, `ローカルの状態` | 利用者側の状態と区別する必要がある箇所で使う。 |
| state update API | 状態更新 API | `state update API` | 現在の入力状態の一部を変更する API の分類に使う。 |
| action API | 操作 API | `action API` | 押下と解放など複数の処理をまとめる API の分類に使う。 |
| complete state API | 完全入力状態 API | `complete state`, `完全状態 API` | 構築済みの `InputState` で入力全体を置き換える API の分類に使う。 |
| immutable | 変更不能 | `immutable`, `イミュータブル` | 公開 API の値がその場で変更されない性質を説明する。型名は変更しない。 |
| USB Bluetooth 機器 | 専用 USB Bluetooth ドングル | `USB Bluetooth dongle`, `Bluetooth dongle`, `Bluetoothドングル` | PC 内蔵 Bluetooth と区別する文脈では「専用」を付ける。 |
| OS 側の準備 | ドライバー | `driver` | Windows 手順や Zadig の説明では日本語表記を使う。 |
| firmware | ファームウェア / FW バージョン | `firmware` | 公開文書の本文では「ファームウェア」を基本とする。短いバージョン表記では「FW バージョン」も使える。 |
| adapter | アダプタ | `adapter` | 引数 `adapter` と Bumble の adapter string は残す。利用者向けの説明では「アダプタ」を使う。 |
| adapter name | アダプタ名 / アダプタの名称 | `adapter 名`, `adapter moniker` | `adapter=...` に渡す値の説明では「アダプタ名」を使う。 |
| no-open snapshot | 開かずに取得した情報 / 列挙時点の情報 | `no-open`, `snapshot` | 何を開かず、いつ取得した情報かを具体的に書く。メソッド名 `snapshot()` は残す。 |
| USB descriptor | USB ディスクリプター | `USB descriptor` | USB 規格の構造名としてカタカナ表記を使う。 |
| pairing | ペアリング | `pairing` | `allow_pairing` と `pair()` は残す。説明文では「ペアリング」を使う。 |
| reconnect | 再接続 | `reconnect` | メソッド名 `reconnect()` は残す。説明文では「再接続」を使う。 |
| bond | 保存済みペアリング情報 / ペアリング情報 | `bond`, `保存済み接続情報` | ペアリング後に保存される鍵と相手機器情報を指す。 |
| current peer | 現在の接続先 / 現在の接続先情報 | `current peer` | key store の状態を利用者向けに説明する場合に使う。 |
| pairing key | ペアリングキー | `pairing key` | HID 識別情報との対応を説明する場合に使う。 |
| HID identity | HID 識別情報 | `HID identity` | `HID` は残し、`identity` を日本語化する。 |
| HID advertising | HID 接続待ち受け | `advertising`, `HID advertising`, `広告` | 対象機器からの接続を待つ動作として説明する。 |
| periodic report loop | レポートループ | `periodic report loop`, `report loop` | 入力レポートを周期送信する処理を指す。 |
| input report | 入力レポート / レポート | `input report`, `report` | HID 入力であることが文脈から明らかでない場合は「入力レポート」と書く。 |
| output report | 出力レポート / ホストからの出力レポート | `output report`, `host output report` | 送信元を区別する必要がある箇所では「ホストからの」を付ける。 |
| subcommand reply | サブコマンド応答 / 応答 | `subcommand reply`, `reply` | 識別子ではない説明語を日本語化する。 |
| button | ボタン | `button` | enum 名や引数名は残す。説明文では「ボタン」を使う。 |
| stick | スティック入力 / スティック | `stick` | 型名 `Stick` は残す。入力種別の説明では「スティック入力」を使う。 |
| D-pad | 十字キー | `D-pad` | Joy-Con や入力操作の説明では「十字キー」を使う。 |
| neutral | ニュートラル入力 / ニュートラル | `neutral` | メソッド名 `neutral()` は残す。入力状態の説明では「ニュートラル入力」を使う。 |
| profile | profile / プロファイル | `profile`, `プロファイル` | API 境界語として残す場合と説明語として日本語化する場合を文書内で混在させない。 |
| IMU frame | IMU frame / IMU 入力単位 | `frame` | API 詳細では `IMU frame` を使える。利用者向けには「IMU 入力単位」を併記する。 |
| sample / sensor | 入力分または入力値 / センサー | `sample`, `sensor` | 入力数を説明する場合は「1 入力分」「3 入力分」のように具体化する。 |
| accelerometer / gyroscope | 加速度 / ジャイロ | `accelerometer`, `gyroscope`, `gyro` | `gyro` は API 名として残す。説明では日本語を使う。 |
| transport | transport | `トランスポート` | API 境界語として英語のまま残す。必要なら「下位の通信実装」と補足する。 |
| transport open | transport を開く処理 | `transport open` | `transport` は残し、動作を日本語化する。 |
| resource scope | リソースの有効範囲 / リソース管理 | `resource scope` | `async with` の説明では管理対象と開始・終了を具体的に書く。 |
| timeout | タイムアウト | `timeout` | 例外名と状態値は残す。説明文では「タイムアウト」を使う。 |
| error thrown | 送出されます | `投げます`, `返します` | 例外説明では「送出されます」に統一する。 |
| JSON object | JSON オブジェクト | `JSON object` | `JSON` は残し、一般名詞を日本語化する。 |
| tuple / bytes | タプル / バイト列 | `tuple`, `bytes` | Python の型名を示す場合はバッククォート付きで残す。一般説明では日本語を使う。 |
| 単位と換算尺度 | `G` / `rad/s` / `dps/raw` / `ms` | 単位に含まれる英字 | 数式、単位、換算尺度として使う英字は変更しない。意味を説明する文章は日本語で書く。 |
| Change Grip/Order | 持ちかた/順番を変える | `Change Grip/Order`, `持ち方/順番を変える` | Switch の日本語 UI 名は「持ちかた/順番を変える」と書く。 |
| diagnostics | トレース出力 | `diagnostics`, `診断`, `ロギング` | `DiagnosticsConfig` と引数 `diagnostics` は残す。原因を自動判定する機能とは説明しない。 |
| trace | トレースログ / トレース | `trace`, `JSON Lines trace` | ファイルに残る実行記録は「トレースログ」と書く。引数名、変数名、ファイル名は残す。 |
| troubleshooting | トラブルシューティング | `troubleshooting` | 文書の見出しや導線では日本語化する。 |
