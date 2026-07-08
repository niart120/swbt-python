# Release Notes

## 0.2.0

### Breaking changes

コントローラークラス構成を明示するため、公開 API は生成用の具象コントローラークラスを公開し、下位の構成値やテスト用の差し替え口は内部に閉じます。

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
