# Release Notes

## 0.2.0

### Breaking changes

利用者のコードに影響する破壊的変更は次の通りです。

- `SwitchGamepad(...)` ではコントローラーを作成できなくなりました。Pro Controller 相当のデバイスを作る場合は `ProController(...)` を使います。`SwitchGamepad` は共通インターフェース / 型注釈用です。
- `JoyCon("left", ...)` / `JoyCon("right", ...)` は `JoyConL(...)` / `JoyConR(...)` に分かれました。`side` 引数で左右を選ぶ API はありません。
- `SwitchGamepadConfig(...)` は公開 API から外れました。`adapter`、`key_store_path`、`report_period_us`、`controller_colors`、`diagnostics` は各コントローラーの生成時に渡します。
- 利用者向け生成 API では `transport=...`、`profile=...`、`device_name=...` を受け付けません。`FakeHidTransport` や profile の差し替えは内部テスト用の経路に限ります。
- 接続メソッドは `key_store_path` を受け付けません。保存済みペアリング情報を使う場合は、コントローラー作成時に `key_store_path` を指定してください。
- `ConnectionResult` は `route`、`status`、`peer_address`、`peer_count` だけを返します。transport 内部の保存済みペアリング情報オブジェクトは公開結果に含めません。

### Migration

| Old API | New API | Notes |
|---|---|---|
| `SwitchGamepad(...)` | `ProController(...)` | `SwitchGamepad` は共通インターフェース / 型注釈用。 |
| `JoyCon("left", ...)` | `JoyConL(...)` | Joy-Con（L）相当の具象コントローラー。 |
| `JoyCon("right", ...)` | `JoyConR(...)` | Joy-Con（R）相当の具象コントローラー。 |
| `SwitchGamepadConfig(...)` | 公開 API から削除 | 内部実行時 / テスト設定専用。 |
| `transport=FakeHidTransport` | 内部テストのみ | 利用者向け生成 API では transport の差し替えを受け付けない。 |

`ProController(...)`、`JoyConL(...)`、`JoyConR(...)` は `adapter`、`key_store_path`、`report_period_us`、`controller_colors`、`diagnostics` を受け取ります。Pro Controller、Joy-Con L、Joy-Con R では、同じ対象機器でも `key_store_path` を分けてください。

### Hardware scope

Pro Controller 相当では、Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 と macOS 15.7.7 / CSR8510 A10 の観測を記録しています。Linux は手順のみで、アダプタ open、ペアリング、入力反映は未検証です。

Joy-Con L は Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で限定的な観測があります。Joy-Con R、再接続、通常入力反映は未検証です。Joy-Con profile の実機互換性は保証せず、検証状態は `docs/hardware.md` と `spec/hardware-test-log.md` を正本にします。
