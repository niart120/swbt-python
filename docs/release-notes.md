# Release Notes

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
