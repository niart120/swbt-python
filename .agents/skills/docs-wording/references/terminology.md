# 用語辞書

公開 API の識別子と日本語の説明語を区別する。クラス名、メソッド名、引数名、状態値はバッククォートで囲んで正確な綴りを残し、地の文に使う一般名詞は日本語へ寄せる。

| 対象 | 説明文での表記 | コード・固有名で残す表記 | 避ける表記 | 方針 |
|---|---|---|---|---|
| public API | 公開 API | `API` | `public API`, `公開API` | 日本語本文では「公開 API」に統一する。 |
| module root / import | モジュール直下 / インポート | `swbt`、import 文 | `module root`, 地の文の `import` | 読み込み元の説明では「`swbt` モジュール直下」のように書く。 |
| class / interface | クラス / 抽象型 | 公開クラス名 | 地の文の `class`, `interface` | 抽象基底の説明では「抽象型」を使う。 |
| concrete controller | 具象クラス | 公開クラス名 | `concrete controller`, `具象コントローラー` | コントローラー種別を実装するクラスの説明に使う。 |
| lifecycle | 生成から終了までの管理 | — | `lifecycle` | 生成、接続、終了をまとめた責務を具体的に書く。 |
| Periodic / Direct | 周期送信型 / 直接送信型 | `PeriodicSwitchGamepad`、`DirectProController` など完全な公開クラス名 | `Periodic 具象クラス`、`Direct 具象クラス` | 分類名と公開クラス名を分ける。 |
| state | 状態 / 入力状態 | `state`、`InputState` | 地の文の裸の `state` | 地の文では対象を明示する。 |
| local state | ライブラリ内部の入力状態 | — | `local state`、`ローカルの状態` | 利用者側の状態と区別する必要がある箇所で使う。 |
| state update API | 状態更新 API | API メソッド名 | `state update API` | 現在の入力状態の一部を変更する API の分類に使う。 |
| action API | 操作 API | API メソッド名 | `action API` | 押下と解放など複数の処理をまとめる API の分類に使う。 |
| complete state API | 完全入力状態 API | `InputState`、`apply()`、`send()` | `complete state`、`完全状態 API` | 構築済みの `InputState` で入力全体を置き換える API の分類に使う。 |
| immutable | 変更不能 | `InputState` などの型名 | `immutable`、`イミュータブル` | 公開 API の値がその場で変更されない性質を説明する。 |
| USB Bluetooth 機器 | 専用 USB Bluetooth ドングル | `USB`、`Bluetooth` | `USB Bluetooth dongle`、`Bluetooth dongle`、`Bluetoothドングル` | PC 内蔵 Bluetooth と区別する文脈では「専用」を付ける。 |
| OS 側の準備 | ドライバー | — | `driver` | Windows 手順や Zadig の説明では日本語表記を使う。 |
| firmware | ファームウェア / FW バージョン | `FW`、バージョン表記 | `firmware` | 公開文書の本文では「ファームウェア」を基本とする。 |
| adapter | アダプタ | `adapter`、Bumble の adapter string | `adapter 名`、`adapter moniker` | 引数名と説明語を分ける。 |
| adapter name | アダプタ名 / アダプタの名称 | `adapter=...` | `adapter 名`、`adapter moniker` | `adapter=...` に渡す値の説明では「アダプタ名」を使う。 |
| no-open snapshot | 開かずに取得した情報 / 列挙時点の情報 | `snapshot()` | `no-open snapshot` | 何を開かず、いつ取得した情報かを具体的に書く。 |
| USB descriptor | USB ディスクリプター | `USB` | `USB descriptor` | USB 規格の構造名としてカタカナ表記を使う。 |
| pairing | ペアリング | `allow_pairing`、`pair()` | 地の文の `pairing` | 説明文では「ペアリング」を使う。 |
| reconnect | 再接続 | `reconnect()` | 地の文の `reconnect` | 説明文では「再接続」を使う。 |
| bond | 保存済みペアリング情報 / ペアリング情報 | — | `bond`、`保存済み接続情報` | ペアリング後に保存される鍵と相手機器情報を指す。 |
| current peer | 現在の接続先 / 現在の接続先情報 | — | `current peer` | key store の状態を利用者向けに説明する。 |
| pairing key | ペアリングキー | — | `pairing key` | HID 識別情報との対応を説明する。 |
| HID identity | HID 識別情報 | `HID` | `HID identity` | `HID` は残し、`identity` を日本語化する。 |
| HID advertising | HID 接続待ち受け | `HID` | `advertising`、`HID advertising`、`広告` | 対象機器からの接続を待つ動作として説明する。 |
| periodic report loop | レポートループ | — | `periodic report loop`、`report loop` | 入力レポートを周期送信する処理を指す。 |
| input report | 入力レポート / レポート | `report` | 地の文の `input report` | HID 入力であることが文脈から明らかでない場合は「入力レポート」と書く。 |
| output report | 出力レポート / ホストからの出力レポート | `report` | 地の文の `output report`、`host output report` | 送信元を区別する必要がある箇所では「ホストからの」を付ける。 |
| subcommand reply | サブコマンド応答 / 応答 | `subcommand` | `subcommand reply`、地の文の `reply` | 識別子ではない説明語を日本語化する。 |
| button | ボタン | `Button`、`button` 引数 | 地の文の `button` | enum 名や引数名は残す。説明文では「ボタン」を使う。 |
| stick | スティック入力 / スティック | `Stick`、`stick` 引数 | 地の文の `stick` | 入力種別の説明では「スティック入力」を使う。 |
| D-pad | 十字キー | `D-pad` を引用する場合 | 地の文の `D-pad` | Joy-Con や入力操作の説明では「十字キー」を使う。 |
| neutral | ニュートラル入力 / ニュートラル | `neutral()` | 地の文の `neutral` | 入力状態の説明では「ニュートラル入力」を使う。 |
| profile | プロファイル | `profile`（API 境界の場合） | 説明文の裸の `profile`、表記の混在 | API 境界語と説明語を文書内で混在させない。 |
| IMU frame | IMU 入力単位 | `IMUFrame`、`IMU frame`（API 詳細） | 地の文の裸の `frame` | 利用者向けには「IMU 入力単位」を併記する。 |
| sample / sensor | 入力分または入力値 / センサー | `sample`、`sensor`（コードや引用） | 地の文の裸の `sample`、`sensor` | 入力数は「1 入力分」「3 入力分」のように具体化する。 |
| accelerometer / gyroscope | 加速度 / ジャイロ | `gyro`（API 名） | 地の文の `accelerometer`、`gyroscope` | 説明では日本語を使う。 |
| transport | 下位の通信実装、または transport | `transport` | `トランスポート` | API 境界語として英語のまま残す場合は、必要に応じて説明を補う。 |
| transport open | transport を開く処理 | `transport` | `transport open` | `transport` は残し、動作を日本語化する。 |
| resource scope | リソースの有効範囲 / リソース管理 | `async with` | `resource scope` | 管理対象と開始・終了を具体的に書く。 |
| timeout | タイムアウト | `timeout`（例外名、状態値） | 地の文の `timeout` | 説明文では「タイムアウト」を使う。 |
| error thrown | 送出されます | — | `投げます`、`返します` | 例外説明では「送出されます」に統一する。 |
| JSON object | JSON オブジェクト | `JSON` | `JSON object` | `JSON` は残し、一般名詞を日本語化する。 |
| tuple / bytes | タプル / バイト列 | `tuple`、`bytes`（Python の型名） | 地の文の裸の `tuple`、`bytes` | 型名を示す場合だけバッククォート付きで残す。 |
| 単位と換算尺度 | 単位表記を維持 | `G`、`rad/s`、`dps/raw`、`ms` | — | 数式、単位、換算尺度として使う英字は変更しない。意味を説明する文章は日本語で書く。 |
| Change Grip/Order | 持ちかた/順番を変える | `Change Grip/Order`（英語 UI を引用する場合） | `持ち方/順番を変える` | Switch の日本語 UI 名は「持ちかた/順番を変える」と書く。 |
| diagnostics | トレース出力 | `DiagnosticsConfig`、`diagnostics` | 地の文の `diagnostics`、`診断`、`ロギング` | 原因を自動判定する機能とは説明しない。 |
| trace | トレースログ / トレース | `trace`、`JSON Lines trace` | — | ファイルに残る実行記録は「トレースログ」と書く。 |
| troubleshooting | トラブルシューティング | — | `troubleshooting` | 文書の見出しや導線では日本語化する。 |
