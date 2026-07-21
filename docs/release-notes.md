# Release Notes

## Unreleased

### 追加機能

- `ProController.create_profile()` と `ProController(profile_path=...)` を追加しました。利用者が管理する `local_address` とペアリングキーを一つの swbt プロファイル JSON に保存し、CSR8510 A10 の揮発領域にある Bluetooth アドレスを接続前に準備します。
- `JoyConL` / `JoyConR` にも `create_profile()` と `profile_path` を追加しました。プロファイルには `joycon_l` / `joycon_r` を保存し、異なるコントローラー種別で開くと `ProfileControllerMismatchError` をアダプタ準備前に送出します。
- 揮発領域への書換開始後の状態を確定できない場合は `AdapterIdentityRecoveryRequired` を送出します。`close()` は接続資源だけを閉じ、書き換えたアドレスを元へ戻しません。

### 破壊的変更

- 全 concrete controller から `key_store_path` を削除しました。再接続と初回ペアリングには `profile_path` を使い、新規プロファイルはコンストラクタではなく `await ControllerClass.create_profile(...)` で作成します。
- native JSON key-store の読み込み、互換モード、自動移行はありません。既存ファイルは再利用できないため、controller shape と対象機器ごとに新しい profile を作成してください。
- `create_profile(..., exp_local_address=...)` は `create_profile(..., local_address=...)` に、`ExpLocalAddressRecoveryRequired` は `AdapterIdentityRecoveryRequired` に改名しました。
- profile の controller 分類から Direct / Periodic を除きました。新規 JSON は `pro` / `joycon_l` / `joycon_r` を保存します。`direct_*` を保存した既存 profile は互換ではないため、別の profile path で作成し直して再ペアリングしてください。schema version は更新しません。同じ controller shape の Direct / Periodic が新しい profile を共有できますが、その方式間の実機再利用は未検証です。

### 対応範囲

対象は CSR8510 A10 の揮発領域への書換経路です。永続領域は変更しません。`local_address` の生成と重複回避は利用者の責任です。CSR8510 A10 以外のドングル、出荷時アドレスの保存、公開の読み取り専用確認 API は対象外です。

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

直接送信型は fake transport を使った単体テストと統合テストで、送信件数、送信成功後の状態確定、失敗時の状態維持、サブコマンド応答、終了時のニュートラル入力を確認しました。専用 USB Bluetooth ドングルと Switch 実機を使った確認は実施していません。HID レポートのバイト配置と Bumble の通信条件は 0.3.0 から変更していません。

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

### Breaking changes

v0.1.1 から利用者のコードに影響する破壊的変更は次の通りです。

- `SwitchGamepad(...)` ではコントローラーを作成できなくなりました。v0.1.1 の Pro Controller 相当の使い方は `ProController(...)` に移します。`SwitchGamepad` は共通インターフェース / 型注釈用です。
- `SwitchGamepadConfig(...)` と `SwitchGamepad.from_config(...)` は公開 API から外れました。`adapter`、`key_store_path`、`report_period_us`、`controller_colors`、トレース出力設定の `diagnostics` は各コントローラーの生成時に渡します。
- v0.1.1 で使えた `SwitchGamepad(..., transport=...)` と `SwitchGamepad(..., device_name=...)` は利用できません。下位の通信実装を差し替えるエントリーポイントと、HID device name や profile を任意に指定するエントリーポイントは、内部実装とテスト用に限ります。
- `HidDeviceTransport`、`BondedPeer`、`DisconnectRequestResult` は `swbt` トップレベルの公開 export から外れました。transport 境界は公開拡張点ではなくなりました。

### Migration

| Old API | New API | Notes |
|---|---|---|
| `SwitchGamepad(...)` | `ProController(...)` | `SwitchGamepad` は共通インターフェース / 型注釈用。 |
| `SwitchGamepadConfig(...)` | 各具象クラスの constructor 引数 | `from_config()` は公開 API から削除。 |
| `SwitchGamepad(..., transport=...)` | 公開 API では移行先なし | transport 差し替えは内部テスト用。 |
| `SwitchGamepad(..., device_name=...)` | `ProController(...)` / `JoyConL(...)` / `JoyConR(...)` | HID identity は具象クラスが選ぶ。 |
| `from swbt import HidDeviceTransport, BondedPeer, DisconnectRequestResult` | 公開 API から削除 | transport 内部型はトップレベル export しない。 |

`ProController(...)`、`JoyConL(...)`、`JoyConR(...)` は `adapter`、`key_store_path`、`report_period_us`、`controller_colors`、トレース出力設定の `diagnostics` を受け取ります。Pro Controller、Joy-Con L、Joy-Con R では、同じ対象機器でも `key_store_path` を分けてください。

### New public API

- `ProController`、`JoyConL`、`JoyConR` を追加しました。
- `ControllerColors` で controller body / buttons / grip カラーを指定できます。
- `list_adapters()` と `AdapterInfo` で、専用 USB Bluetooth ドングル候補をデバイスハンドルを開かずに列挙できます。
- Joy-Con　L (R) が対応しない入力は `UnsupportedInputError` として扱います。

### Hardware scope

Pro Controller 相当では、Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 と macOS 15.7.7 / CSR8510 A10 の観測を記録しています。Linux は手順のみで、アダプタ open、ペアリング、入力反映は未検証です。

Joy-Con L/R は Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で部分的に動作確認済みです。確認済み範囲は Joy-Con としての登録、利用者指定色、対応するボタン入力です。スティック入力は送信とニュートラル復帰まで確認しています。詳細な検証状態は `docs/hardware.md` と `spec/hardware-test-log.md` を正本とします。
