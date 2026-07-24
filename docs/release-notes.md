# リリースノート

## 0.5.0

### 追加機能

- `ProController`、`JoyConL`、`JoyConR`、`DirectProController`、`DirectJoyConL`、`DirectJoyConR` に `create_profile()` と `profile_path` を追加しました。`create_profile()` は Bluetooth アドレスの選択方法とペアリングキーを一つの swbt プロファイル JSON に保存し、初回ペアリングまで行います。
- `create_profile()` の `local_address` を省略するか `None` にすると、専用 USB Bluetooth ドングルのアドレスを書き換えず、アダプタが起動後に報告した現在の Bluetooth アドレスにペアリング情報を結び付けます。アドレスを取得できない場合は、HID 接続待ち受けまたは再接続を始める前に `InvalidKeyStoreError` を送出します。
- 利用者が管理する `local_address` を指定すると、そのアドレスを CSR8510 A10 の揮発領域へ接続前に書き込みます。書き込み開始後の状態を確定できない場合は `AdapterIdentityRecoveryRequired` を送出します。この場合は専用 USB Bluetooth ドングルを抜き差ししてから再試行してください。
- 不正または非対応のプロファイルは `InvalidProfileError`、異なるコントローラー形状のプロファイルは `ProfileControllerMismatchError` で区別できます。

### 修正と動作変更

- `pair()`、`connect()`、`reconnect()`、`create_profile()` は、HID リンク接続だけで完了せず、初期サブコマンドへの応答とプレイヤー割り当てが完了してから正常終了するようになりました。接続初期化中の `status().connection_state` は `"initializing"` になり、入力可能になると `"connected"` へ移ります。
- 接続 API の `timeout` は、HID リンク接続とその後の初期化を合わせた期限になりました。`try_connect()` と `try_reconnect()` は、初期化中のタイムアウトを `"timeout"`、応答送信の失敗や初期化完了前の切断を `"failed"` として返します。`create_profile()` は、初期化が完了していないコントローラーオブジェクトを返しません。
- 直接送信型も、接続初期化中はライブラリがニュートラル入力を内部送信します。プレイヤー割り当てが完了すると内部の周期送信を停止し、以後は従来どおり `send()` または各入力操作を呼び出したときだけ利用者入力を送信します。
- Joy-Con L/R の初期化応答をコントローラー形状に合わせました。「持ちかた/順番を変える」画面で登録する場合も、利用者が登録用の SR+SL 入力を追加送信する必要はありません。`Button.SL` と `Button.SR` は通常のボタン入力として引き続き利用できます。
- コントローラーの既定通知が充電中として表示される問題を修正しました。すべての具象クラスで、満充電、非充電を既定として通知します。実際の電池残量や給電状態を動的に取得する機能は含みません。
- 周期送信型のレポートループを、前回の送信完了後に一定時間待つ方式から、固定時刻を基準にする方式へ変更しました。入力レポートの組み立てと送信に使った時間を次の待機時間から差し引き、遅れた回は連続送信せずに飛ばします。OS や Bluetooth 通信を含む厳密な送信間隔は保証しません。
- 直接送信型の `send()` と入力操作は、Bumble が入力レポートを送信キューへ受け付けた時点で正常終了し、ライブラリ内部の入力状態を確定します。HCI の送信完了や対象機器への反映までは待ちません。トレースログの `report_tx` も同じ時点を表します。明示的な切断では、保留中の ACL パケットの処理を待ってから通信路を閉じます。

### 破壊的変更

- すべての具象クラスから `key_store_path` を削除しました。ペアリング情報を永続化する場合は、最初に `await ProController.create_profile(...)` など、使用する具象クラスの `create_profile()` で swbt プロファイルを作成し、次回以降はコンストラクタへ `profile_path` を渡してください。一時的な接続などでペアリング情報を保存しない使い方では、`profile_path` を省略できます。
- `v0.4.0` の `key_store_path` で使用していた JSON 形式のペアリング情報には、読み込み、互換モード、自動移行を用意していません。既存ファイルは再利用できないため、コントローラー形状と対象機器の組み合わせごとに別の `profile_path` を指定して、ペアリングをやり直してください。
- `swbt-probe pair` の `--key-store` を削除し、作成済みの swbt プロファイルを指定する必須オプション `--profile` に変更しました。
- トレースログの `run_metadata` から `key_store_path`、`key_store_exists`、`key_store_previous_exists` を削除し、`profile_path` を追加しました。`reconnect_key_store_unavailable` は `reconnect_profile_unavailable` に、理由の `key_store_path_none` は `profile_path_none` に変更しました。

プロファイルの作成と再利用のコード例は[利用例](usage.md)を参照してください。

### 実機確認範囲

- Windows 11、CSR8510 A10、WinUSB、Switch 2 ファームウェア 22.5.0 の組み合わせで、利用者管理の `local_address` を使った全具象クラスの初回ペアリング、通常終了、同じプロファイルによる再接続を確認しました。
- アダプタが報告する現在の Bluetooth アドレスを使う経路は、同じ Windows 11、CSR8510 A10、WinUSB の構成で、Pro Controller、Joy-Con L、Joy-Con R の初回ペアリングと再接続を確認しました。Joy-Con L/R は登録用の SR+SL 入力を追加送信せずに初期化を完了しました。
- 8 ms を指定した周期送信型は、同じ専用 USB Bluetooth ドングルを使った 200 件の観測で、HCI の送信完了間隔の中央値が 8.038 ms になりました。他の OS、専用 USB Bluetooth ドングル、対象機器では未検証です。
- `local_address` を明示した場合に書き換えるのは CSR8510 A10 の揮発領域だけです。`close()` は書き換えたアドレスを元へ戻しません。アドレスの生成と重複回避は利用者が行ってください。CSR8510 A10 以外の専用 USB Bluetooth ドングル、出荷時アドレスの保存、公開の読み取り専用確認 API は確認対象外です。
- 同じコントローラー形状の周期送信型と直接送信型は同じプロファイルを受け付けます。Pro Controller では両方式の間で再利用した接続を実機確認済みですが、Joy-Con L/R では未確認です。詳しい確認条件と残っている制約は[実機準備手順](hardware.md)を参照してください。

## 0.4.0

### 追加機能

- `DirectProController`、`DirectJoyConL`、`DirectJoyConR` を追加しました。これらの直接送信型では、利用者が入力レポートの送信頻度を管理します。`send(state)` と各入力操作は接続済みであることを要求し、入力レポート 1 件の送信完了後に入力状態を確定します。
- `PeriodicSwitchGamepad` と `DirectSwitchGamepad` を公開しました。入力レポートをライブラリが周期送信する型と、利用者の操作ごとに送信する型を型注釈で区別できます。
- 直接送信型の `snapshot()` は最後に正常送信した入力状態を返します。未接続、非対応入力、transport の送信失敗では、直前に正常送信した状態を維持します。

### 互換性と移行

`ProController`、`JoyConL`、`JoyConR` は従来どおり周期送信型です。生成時の引数、`apply(state)`、各入力操作の契約は 0.3.0 から変更していません。

`SwitchGamepad` は生成から終了までの管理、接続、共通の入力操作を表す抽象型になりました。0.3.0 で `SwitchGamepad` 型の値に対して `apply(state)` を呼んでいたコードは、入力レポートの送信方式に応じて型注釈と呼び出しを変更してください。

| 0.3.0 | 0.4.0 | 備考 |
|---|---|---|
| `pad: SwitchGamepad` から `apply(state)` を呼ぶ | `pad: PeriodicSwitchGamepad` から `apply(state)` を呼ぶ | 従来の周期送信を維持します。 |
| 利用者の操作ごとに入力レポートを送る公開 API はなし | `pad: DirectSwitchGamepad` から `send(state)` を呼ぶ | 具象クラスは `DirectProController`、`DirectJoyConL`、`DirectJoyConR` です。 |
| `ProController(..., report_period_us=...)` | 変更なし | 直接送信型は `report_period_us` を受け取りません。 |

### 実機確認範囲

直接送信型は実機を使わない通信実装による単体テストと統合テストで、送信件数、送信成功後の状態確定、失敗時の状態維持、サブコマンド応答、終了時のニュートラル入力を確認しました。専用 USB Bluetooth ドングルと Switch 実機を使った確認は実施していません。HID レポートのバイト配置と Bumble の通信条件は 0.3.0 から変更していません。

## 0.3.0

### 追加機能

- `IMUFrame.gyro_rate()` と `IMUFrame.with_gyro_rate()` を追加しました。ジャイロの角速度を rad/s 単位で指定できます。`to_gyro_rate()` は設定値を同じ単位で返します。
- `IMUFrame.accel_g()` と `IMUFrame.with_accel_g()` を追加しました。加速度を G 単位で指定できます。`to_accel_g()` は設定値を同じ単位で返します。
- Pro Controller、Joy-Con L、Joy-Con R の仮想センサー校正値を応答し、設定した加速度とジャイロを接続先が要求する IMU 形式で送信します。
- トレース出力に、接続先が選択した IMU 形式を記録します。

### 互換性

0.2.0 の公開 API を削除または変更する破壊的変更はありません。角速度と加速度の単位変換で16ビット符号付き整数の範囲を超える値を指定した場合は、丸めずに `InvalidInputError` が送出されます。

### 実機確認範囲

Windows 11 / CSR8510 A10 / WinUSB / Switch 2 ファームウェア 22.1.0 で、Pro Controller 相当の quaternion 形式による正負 Z 方向の回転、停止、静止加速度を確認しました。Joy-Con のセンサー軸方向と、別の専用 USB Bluetooth ドングル、OS、Switch 本体、ファームウェアでは未検証です。詳細は `docs/hardware.md` と `spec/hardware-test-log.md` を参照してください。

## 0.2.0

### 破壊的変更

v0.1.1 から利用者のコードに影響する破壊的変更は次の通りです。

- `SwitchGamepad(...)` ではコントローラーを作成できなくなりました。v0.1.1 の Pro Controller 相当の使い方は `ProController(...)` に移します。`SwitchGamepad` は共通インターフェース / 型注釈用です。
- `SwitchGamepadConfig(...)` と `SwitchGamepad.from_config(...)` は公開 API から外れました。`adapter`、`key_store_path`、`report_period_us`、`controller_colors`、トレース出力設定の `diagnostics` は各コントローラーの生成時に渡します。
- v0.1.1 で使えた `SwitchGamepad(..., transport=...)` と `SwitchGamepad(..., device_name=...)` は利用できません。下位の通信実装を差し替えるエントリーポイントと、HID デバイス名やプロファイルを任意に指定するエントリーポイントは、内部実装とテスト用に限ります。
- `HidDeviceTransport`、`BondedPeer`、`DisconnectRequestResult` は `swbt` トップレベルの公開 export から外れました。transport 境界は公開拡張点ではなくなりました。

### 移行

| v0.1.1 | v0.2.0 | 備考 |
|---|---|---|
| `SwitchGamepad(...)` | `ProController(...)` | `SwitchGamepad` は共通インターフェース / 型注釈用。 |
| `SwitchGamepadConfig(...)` | 各具象クラスのコンストラクタ引数 | `from_config()` は公開 API から削除。 |
| `SwitchGamepad(..., transport=...)` | 公開 API では移行先なし | transport 差し替えは内部テスト用。 |
| `SwitchGamepad(..., device_name=...)` | `ProController(...)` / `JoyConL(...)` / `JoyConR(...)` | HID 識別情報は具象クラスが選ぶ。 |
| `from swbt import HidDeviceTransport, BondedPeer, DisconnectRequestResult` | 公開 API から削除 | transport 内部型はトップレベル export しない。 |

`ProController(...)`、`JoyConL(...)`、`JoyConR(...)` は `adapter`、`key_store_path`、`report_period_us`、`controller_colors`、トレース出力設定の `diagnostics` を受け取ります。Pro Controller、Joy-Con L、Joy-Con R では、同じ対象機器でも `key_store_path` を分けてください。

### 追加した公開 API

- `ProController`、`JoyConL`、`JoyConR` を追加しました。
- `ControllerColors` で本体、ボタン、左右グリップの色を指定できます。
- `list_adapters()` と `AdapterInfo` で、専用 USB Bluetooth ドングル候補をデバイスハンドルを開かずに列挙できます。
- Joy-Con L/R が対応しない入力は `UnsupportedInputError` として扱います。

### 実機確認範囲

Pro Controller 相当では、Windows 11 / CSR8510 A10 / WinUSB / Switch 2 ファームウェア 22.1.0 と macOS 15.7.7 / CSR8510 A10 の観測を記録しています。Linux は手順のみで、アダプタを開く処理、ペアリング、入力反映は未検証です。

Joy-Con L/R は Windows 11 / CSR8510 A10 / WinUSB / Switch 2 ファームウェア 22.1.0 で部分的に動作確認済みです。確認済み範囲は Joy-Con としての登録、利用者指定色、対応するボタン入力です。スティック入力は送信とニュートラル復帰まで確認しています。詳細な検証状態は `docs/hardware.md` と `spec/hardware-test-log.md` を正本とします。
