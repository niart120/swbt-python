# Release Notes

## 0.2.0

### Breaking changes

Rearchitecture cleanup makes the controller class model explicit. The public API now exposes concrete controller classes for construction and keeps lower-level configuration seams internal.

### Migration

| Old API | New API | Notes |
|---|---|---|
| `SwitchGamepad(...)` | `ProController(...)` | `SwitchGamepad` は shared interface / type annotation として使う |
| `JoyCon("left", ...)` | `JoyConL(...)` | 単体 Joy-Con L 相当の concrete controller |
| `JoyCon("right", ...)` | `JoyConR(...)` | 単体 Joy-Con R 相当の concrete controller |
| `SwitchGamepadConfig(...)` | public API では廃止 | internal tests / runtime setup の境界に移した |
| `transport=FakeHidTransport` | internal tests only | user-facing constructor には出さない |

`ProController(...)`, `JoyConL(...)`, `JoyConR(...)` は `adapter`, `key_store_path`, `report_period_us`, `controller_colors`, `diagnostics` を受け取ります。Pro Controller / Joy-Con L / Joy-Con R では、同じ対象機器でも `key_store_path` を分ける必要があります。

### Hardware scope

Pro Controller 相当では、Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 と macOS 15.7.7 / CSR8510 A10 の観測を記録しています。Linux は手順のみで、adapter open、pairing、input reflection は未検証です。

Joy-Con L は Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で限定的な観測があります。Joy-Con R、reconnect、通常入力反映は未検証です。Joy-Con profile の実機互換は保証せず、検証状態は `docs/hardware.md` と `spec/hardware-test-log.md` を正本にします。
