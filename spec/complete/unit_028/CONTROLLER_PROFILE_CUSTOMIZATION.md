# Controller Profile Customization 仕様書

## 1. 概要

### 1.1 目的

`SwitchGamepad` 作成時に、操作へ影響しない controller identity / profile 値を指定できるようにする。初期 scope は controller color の body / buttons / left grip / right grip 12 bytes に限定し、入力状態、report period、pairing strategy、Bluetooth adapter 操作へ混ぜない。

この作業では controller color customization の public API、protocol seed、subcommand reply、fake transport 経路を TDD で実装する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | device color など、操作に影響しない controller identity / profile customization の仕様化 | conversation |
| AGENTS | Public API、protocol 境界、根拠監査、実機安全境界 | `AGENTS.md` |
| spec-format skill | 作業仕様の配置、構成、TDD Test List、実機条件 | `.agents/skills/spec-format/SKILL.md` |
| source-audit skill | SPI address、subcommand payload、device info profile の分類 | `.agents/skills/source-audit/SKILL.md` |
| initial API | `SwitchGamepad` / `SwitchGamepadConfig` の公開 constructor 境界 | `spec/initial/api.md` |
| initial protocol | `SubcommandResponder`、`VirtualSpiFlash`、`0x02` / `0x10` の責務 | `spec/initial/protocol.md` |
| implementation | profile、SPI、subcommand、gamepad constructor の実装 | `src/swbt/protocol/profile.py`, `src/swbt/protocol/spi.py`, `src/swbt/protocol/subcommand.py`, `src/swbt/gamepad/core.py` |
| tests | public API、profile、SPI、subcommand、docs、fake transport integration の test surface | `tests/unit/`, `tests/integration/` |
| daemon source audit | SPI color range と seed data | `E:/documents/VSCodeWorkspace/swbt-daemon/spec/references/switch-spi-core.md`, `E:/documents/VSCodeWorkspace/swbt-daemon/spec/references/switch-virtual-spi-seed-data.md` |
| upstream source audit | controller color の body / buttons / left grip / right grip range と `#RGB` 24-bit 表現 | `https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/spi_flash_notes.md` |
| implementation audit | mizuyoukanao/btstack の `0x02` device info reply、fixed SPI reply、`send_padcolor` が body / buttons / left grip / right grip の 12 bytes placement を使う | `https://github.com/mizuyoukanao/btstack/blob/ec9e2858003c19b1591a9acefd265bb4673fcb6e/example/btkeyLib.c` |
| daemon implementation | device info tail bytes と virtual SPI color seed | `E:/documents/VSCodeWorkspace/swbt-daemon/swbt/switch/switch_device_info.c`, `switch_device_info.h`, `switch_spi.h`, `switch_spi_seed.c`, `switch_spi_seed.h` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `SwitchGamepad(..., controller_colors=ControllerColors(body=0x112233, buttons=0x445566, left_grip=0x778899, right_grip=0xAABBCC))` | Switch からの SPI read に指定色が返る | 作成時に固定する。接続後 setter は作らない |
| protocol core | `0x10` SPI read for `0x6050`, size `12` | reply payload が request prefix と 12 bytes color を含む | Bumble / 実機なしの unit test で検証する |
| protocol core | `0x02` request device info | Pro Controller profile bytes `04 00 03 02 <6 byte address> 03 02` を返す | 色そのものは device info reply に埋め込まない |
| reviewer | source / implementation / inference の確認 | SPI address、device info profile bytes、subcommand 関係の根拠分類を追える | 未検証仮説を public API 契約にしない |
| hardware follow-up | 実機で color 反映を見る | Switch UI で色表示が変わるか記録する | adapter open、advertising、pairing、report loop は明示承認が必要 |

## 2. 対象範囲

- `ControllerColors` value object の公開 API 設計。
- `SwitchGamepad(controller_colors=...)` と `SwitchGamepadConfig.controller_colors` の constructor-time 設定。
- 既定色は Joy-Con-ish profile `body=0x323232`, `buttons=0xFFFFFF`, `left_grip=0x00B2FF`, `right_grip=0xFF3B30` とする。
- `ControllerColors` は `body`、`buttons`、`left_grip`、`right_grip` を 24-bit RGB integer として受ける。
- `controller_colors=None` は既定色を使う。省略した field はそれぞれ独立した既定値を使い、grip を body 色へ正規化しない。
- `ControllerColors` は immutable にし、`0 <= value <= 0xFFFFFF` だけを受ける。`str`、`bytes`、tuple、負数、`0x1000000` 以上は `InvalidInputError` とする。
- `0x601B` color info exists flag を `0x01` に seed する。
- SPI `0x6050`-`0x605B` への seed と `0x10` SPI read reply。
- `0x02` device info reply を Pro Controller profile bytes `04 00 03 02 <addr> 03 02` として返すこと。
- public API docs、docstring、`swbt.__all__` の更新方針。

## 3. 対象外

- 接続後の `set_color()`、`controller_colors=` setter、profile mutation API。
- serial number customization。
- Bluetooth address customization。
- factory / user calibration customization。
- battery / connection indicator customization。
- player lights customization。player lights は request-driven mutable session state であり、この profile 設定に含めない。
- report period customization。既存の `report_period_us` とは別の責務として維持する。
- high-level rumble API。
- 複数 controller の profile 管理。
- Switch UI で色が見えることを release blocker にすること。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_001/M0_PROTOCOL_CORE.md`
- `spec/complete/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/complete/unit_009/PORTING_SOURCE_AUDIT.md`
- `E:/documents/VSCodeWorkspace/swbt-daemon/spec/references/switch-spi-core.md`
- `E:/documents/VSCodeWorkspace/swbt-daemon/spec/references/switch-virtual-spi-seed-data.md`
- `https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/spi_flash_notes.md`
- `https://github.com/mizuyoukanao/btstack/blob/ec9e2858003c19b1591a9acefd265bb4673fcb6e/example/btkeyLib.c`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | SPI address、subcommand `0x02` / `0x10` reply payload、device info profile bytes を TDD fixture に反映した |
| Bumble / transport | not applicable | not applicable | 色設定は protocol core の SPI / subcommand data で完結する。Bumble object 型や callback 型は public API に出さない |
| OS / driver / adapter | not applicable | not applicable | automated scope では adapter を開かない。実機反映確認を行う場合だけ hardware 承認境界を通す |

### 5.1 source fact

| 項目 | 値 | source | status |
|---|---:|---|---|
| SPI flash address limit | `0x80000` exclusive | `switch-spi-core.md`; `switch_spi.h` | stable boundary |
| SPI read max size | `0x1d` bytes | `switch-spi-core.md`; `switch_spi.h` | stable boundary |
| device type address / value | address `0x6012`, Pro Controller `0x03` | `switch-spi-core.md`; `switch_spi.h` | stable address/value |
| color info exists flag | address `0x601B`, value `0x01` means color info exists | dekuNukem `spi_flash_notes.md`; `switch_spi.h` | source-backed seed value |
| controller color range | `0x6050`-`0x605B` inclusive | dekuNukem `spi_flash_notes.md` | stable address map; payload is caller-seeded |
| body color range and byte order | `0x6050`-`0x6052`, Body `#RGB` color, 24-bit | dekuNukem `spi_flash_notes.md` | source fact |
| buttons color range and byte order | `0x6053`-`0x6055`, Buttons `#RGB` color, 24-bit | dekuNukem `spi_flash_notes.md` | source fact |
| left grip color range and byte order | `0x6056`-`0x6058`, Left Grip `#RGB` color, 24-bit, added in Switch firmware 5.0.0 for Pro | dekuNukem `spi_flash_notes.md` | source fact |
| right grip color range and byte order | `0x6059`-`0x605B`, Right Grip `#RGB` color, 24-bit, added in Switch firmware 5.0.0 for Pro | dekuNukem `spi_flash_notes.md` | source fact |
| controller color seed length | `12` bytes | dekuNukem `spi_flash_notes.md` range `0x6050`-`0x605B` | stable length derived from the range |

### 5.2 implementation fact

| 項目 | 値 | source | status |
|---|---:|---|---|
| daemon dev color seed | `0d 0d 0d ff ff ff` | `switch_spi_seed.c` | implementation default for body/buttons only, not factory data |
| daemon seed writer | writes `controller_colors` to `SWBT_SWITCH_SPI_ADDRESS_CONTROLLER_COLORS` | `switch_spi_seed.c` | implementation behavior |
| daemon seed length | `6` bytes for body/buttons | `switch-virtual-spi-seed-data.md`; `switch_spi_seed.h` | implementation fact; swbt-python intentionally extends to source-backed grip range |
| daemon color flag handling | `SWBT_SWITCH_SPI_ADDRESS_COLOR_INFO_EXISTS = 0x601B` is defined, but the dev seed writer does not seed it | `switch_spi.h`, `switch_spi_seed.c` | implementation fact; swbt-python chooses the source-backed seed |
| daemon device info tail | default swbt-pro profile reply data tail is `01 01`; byte 11 is named `color_source` and `SWBT_SWITCH_DEVICE_INFO_COLORS_FROM_SPI = 0x01` | `switch_device_info.h`, `switch_device_info.c` | implementation behavior; 2026-07-05 の Switch 2 / firmware 22.1.0 観測では independent Pro grip UI reflection には足りなかった |
| swbt-python SPI seed | `VirtualSpiFlash` seeds `0x6012 = 0x03`, `0x601B = 0x01`, and `0x6050`-`0x605B` from `ControllerColors` | `src/swbt/protocol/spi.py` | current implementation |
| swbt-python `0x02` reply | static `DEVICE_INFO_DATA = 04 00 03 02 00 00 00 00 00 00 03 02` | `src/swbt/protocol/subcommand.py` | current implementation; mizuyoukanao/btstack の `reply02` と 2026-07-05 hardware observation に合わせる |
| swbt-python `0x10` reply | returns request prefix plus configured `VirtualSpiFlash.read(address, size)` | `src/swbt/protocol/subcommand.py` | current implementation |
| swbt-python construction path | `SwitchGamepad` builds `ProControllerProfile(controller_colors=...)` and injects `SubcommandResponder(profile=...)` into `OutputReportDispatcher` | `src/swbt/gamepad/core.py` | current implementation |
| mizuyoukanao/btstack `0x02` reply | `reply02` returns device info data `03 48 03 02 <6 byte address> 03 02` after HIDP/report/ack/subcommand bytes | `mizuyoukanao/btstack` commit `ec9e2858003c19b1591a9acefd265bb4673fcb6e`, `example/btkeyLib.c` | implementation fact; successful swbt-python hardware characterization used the same tail `03 02` |
| mizuyoukanao/btstack `0x6050` reply | `reply1050` contains SPI read subcommand `0x10`, address bytes `50 60 00 00`, size `0x18`, followed by 12 controller color bytes at reply indexes `0x15`-`0x20` | `mizuyoukanao/btstack` commit `ec9e2858003c19b1591a9acefd265bb4673fcb6e`, `example/btkeyLib.c` | implementation fact; confirms body/buttons/left grip/right grip placement but uses a fixed 24-byte reply fixture |
| mizuyoukanao/btstack color setter | `send_padcolor(pad_color, button_color, leftgrip_color, rightgrip_color)` writes low byte, middle byte, high byte to each 3-byte field | same source | implementation fact; do not use this as swbt-python public input order because caller-side color integer convention is not documented in that repo |

### 5.3 inference

| 項目 | 推論 | 根拠 | 実装上の扱い |
|---|---|---|---|
| custom color reflection path | Switch は `0x02` device info 後に `0x10` で `0x6050` 付近を読み、body/buttons/grip 色を得る。Windows / Switch 2 / firmware 22.1.0 では independent Pro grip UI reflection に device-info tail `03 02` が必要だった | `01 01` tail、nonzero BD_ADDR だけ、`0x605C=00` はいずれも grip が body 色に寄った。`03 02` tail では `0x6056`-`0x605B` の left/right grip が UI に反映された | `0x02` reply と `0x10` SPI reply の unit test を分け、実機条件は hardware observation として記録する |
| API field split | 12 bytes を `body`、`buttons`、`left_grip`、`right_grip` 各 3 bytes として公開する | upstream source が `0x6050`-`0x605B` を各 `#RGB` 24-bit として示し、mizuyoukanao/btstack も同じ 4 fields の placement を実装している | source fact に従い、実装時 test で byte order を固定する。mizuyoukanao/btstack の setter 引数 order は undocumented なので public API の根拠にしない |
| default color profile | `body=0x323232`, `buttons=0xFFFFFF`, `left_grip=0x00B2FF`, `right_grip=0xFF3B30` | body と grip が同色だと実機観測で区別しづらい。Joy-Con-ish profile は body/buttons と左右 grip の 4 fields をログと UI 観測で区別しやすい | public API docs に明記し、test で固定する。daemon dev seed とは意図的に分ける |
| ownership | `ControllerColors` は `InputState` ではなく profile / identity 設定に属する | 操作入力に影響せず、SPI / device info reply で観測される | `SwitchGamepad` 作成時に固定し、state update API には入れない |
| profile propagation | `SwitchGamepadConfig` から `ProControllerProfile`、`VirtualSpiFlash`、`SubcommandResponder` へ渡す | dispatcher 構築時に configured responder を注入する | fake transport integration test で確認済み |

### 5.4 hardware observation / remaining hypothesis

| 項目 | 内容 | 扱い |
|---|---|---|
| Switch UI reflection | Switch UI がこの color range を表示へ反映するか | 2026-07-05 に Windows / Switch 2 / firmware 22.1.0 で sentinel `body=0xFF0000`, `buttons=0x0000FF`, `left_grip=0xFF00FF`, `right_grip=0xFF8000` を返した。device-info tail `01 01` では body が赤、buttons が青、grip も赤に見えた。device-info tail `03 02` では左 grip がマゼンタ、右 grip がオレンジに見え、zero BD_ADDR でも同じ表示が保持された |
| device-info tail characterization | `0x02` reply の末尾 2 bytes と grip UI reflection の関係 | nonzero BD_ADDR だけ、または SPI `0x605C=00` だけでは grip は body 色に寄った。tail `03 02` で独立 grip 色が反映された。tail の意味名は未確定なので、現時点では `device-info tail 03 02` として扱う |
| firmware / model difference | Switch model / firmware ごとの color read sequence 差 | 実機観測時に condition を記録する |
| bond cache interaction | 既存 bond がある場合、色変更が再 pairing なしで見えるか | public API 保証にしない |
| Switch UI の表示順 | source-backed SPI order と Switch UI 表示の対応 | Windows / Switch 2 / firmware 22.1.0 の tail `03 02` sentinel run では `body=0xFF0000`, `buttons=0x0000FF`, `left_grip=0xFF00FF`, `right_grip=0xFF8000` が赤 body / 青 buttons / 左マゼンタ / 右オレンジとして目視確認済み。public API は SPI 上の body/buttons/grip `#RGB` を保証し、UI 表示は条件付き observation として扱う |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| default colors | `SwitchGamepad(..., controller_colors=None)` | SPI `0x6050` から `32 32 32 ff ff ff 00 b2 ff ff 3b 30` を返す | Joy-Con-ish profile。body/buttons/left grip/right grip は独立した既定値 |
| custom colors | `ControllerColors(body=0x112233, buttons=0x445566, left_grip=0x778899, right_grip=0xAABBCC)` | SPI `0x6050` から `11 22 33 44 55 66 77 88 99 aa bb cc` を返す | source-backed `#RGB` order |
| omitted grip colors | `ControllerColors(body=0x112233, buttons=0x445566)` | `left_grip=0x00B2FF`, `right_grip=0xFF3B30` の既定値を保つ | grip は body に fallback しない |
| color info flag | default / custom colors のどちらでも | SPI `0x601B` から `01` を返す | source-backed flag。daemon dev seed との差異は互換ではなく堅牢性を優先する |
| validation | `body=-1`, `buttons=0x1000000`, `left_grip="red"`, `right_grip=bytes`, non-int | `InvalidInputError` | 不正な値を wrap / mask しない |
| constructor fixed identity | `SwitchGamepad(controller_colors=...)` 作成後 | profile は object lifetime 中に変わらない | setter は作らない |
| state update separation | `press()` / `release()` / `apply()` / `neutral()` | controller colors は変わらない | `InputState` へ入れない |
| device info | `0x02` request device info | `04 00 03 02 00 00 00 00 00 00 03 02` を返す | 色 bytes は含めない。Bluetooth address customization はこの unit では持たない |
| SPI read | `0x10` request address `0x6050`, size `12` | request prefix 5 bytes + color 12 bytes を返す | `SubcommandResponder` unit test で固定 |
| public docs | docs / docstring / `__all__` | `ControllerColors` と `controller_colors=` の使い方が記載される | 接続後変更不可と対象外を明記する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `ControllerColors()` が既定 body `0x323232` / buttons `0xFFFFFF` / left grip `0x00B2FF` / right grip `0xFF3B30` を持つ | new | unit | no | `tests/unit/test_protocol_profile.py` |
| green | `ControllerColors(body=0x112233, buttons=0x445566, left_grip=0x778899, right_grip=0xAABBCC)` が SPI bytes `11 22 33 44 55 66 77 88 99 aa bb cc` に変換される | new | unit | no | `tests/unit/test_protocol_profile.py` |
| green | `ControllerColors(body=0x112233, buttons=0x445566)` が omitted grip を独立 default の `0x00B2FF` / `0xFF3B30` に保つ | new | unit | no | `tests/unit/test_protocol_profile.py` |
| green | `ControllerColors` が body / buttons / left grip / right grip の範囲外値と non-int を `InvalidInputError` にする | edge | unit | no | `tests/unit/test_protocol_profile.py` |
| green | `SwitchGamepadConfig(controller_colors=...)` と `SwitchGamepad(..., controller_colors=...)` が公開 signature に出る | new | unit | no | `tests/unit/test_public_api_boundary.py` |
| green | `SwitchGamepad.from_config()` が `controller_colors` を保持し default transport / fake transport のどちらでも protocol path へ渡す | new | unit / integration | no | `tests/integration/test_switch_gamepad_fake_transport.py` |
| green | `VirtualSpiFlash` が既定色を `0x6050`-`0x605B` に seed する | new | unit | no | `tests/unit/test_virtual_spi_flash.py` |
| green | `VirtualSpiFlash` が custom `ControllerColors` を `0x6050`-`0x605B` に seed する | new | unit | no | `tests/unit/test_virtual_spi_flash.py` |
| green | `VirtualSpiFlash` が `0x601B` に color info exists flag `01` を seed する | new | unit | no | `tests/unit/test_virtual_spi_flash.py` |
| green | `SubcommandResponder` の `0x10` SPI read reply が custom colors を返す | new | unit | no | `tests/unit/test_subcommand_responder.py` |
| green | `SubcommandResponder` の `0x02` device info reply が Pro Controller profile bytes `04 00 03 02 00 00 00 00 00 00 03 02` を返す | regression | unit | no | `tests/unit/test_subcommand_responder.py` |
| green | fake transport 経由の output report injection で default / custom color SPI reply が送信される | new | integration | no | `tests/integration/test_switch_gamepad_fake_transport.py` |
| green | `swbt.__all__` が `ControllerColors` を含み、package import が Bumble を解決しない | regression | unit | no | `tests/unit/test_package_import.py`, `tests/unit/test_public_api_boundary.py` |
| green | public API docstring と `docs/api.md` が `ControllerColors` / `controller_colors=` を説明する | new | unit | no | `tests/unit/test_public_api_docstrings.py`, `tests/unit/test_public_docs.py` |
| hardware-pass | tracked hardware test で実機が sentinel body / buttons / left grip / right grip の 12 bytes color block を読み、production default `0x02` reply `04 00 03 02 00 00 00 00 00 00 03 02` を使うことを確認する | characterization | hardware | yes | `tests/hardware/test_controller_colors.py`。2026-07-05 Windows / Switch 2 / firmware 22.1.0。trace は device info `040003020000000000000302` と color bytes `ff 00 00 00 00 ff ff 00 ff ff 80 00` を記録。ユーザは左 grip がマゼンタ、右 grip がオレンジに見えたと報告。UI 表示は自動判定しない |
| hardware-pass | 実機で Switch UI に body / buttons color が反映されるか観測する | characterization | hardware | yes | 2026-07-05 Windows / Switch 2 / firmware 22.1.0。trace は `0x6050` SPI read reply `00 c8 53 ff eb 3b` を記録し、ユーザは緑 body / 黄 buttons の controller 表示を目視確認 |
| hardware-pass | 実機で device-info tail と grip UI reflection の関係を切り分ける | characterization | hardware | yes | 2026-07-05 Windows / Switch 2 / firmware 22.1.0。tail `01 01`、nonzero BD_ADDR だけ、SPI `0x605C=00` だけでは body/grip が赤、buttons が青のままだった。tail `03 02` では left/right grip がマゼンタ/オレンジに変わり、zero BD_ADDR でも保持された |

## 8. 設計メモ

### 8.1 Public API 案

```python
from swbt import ControllerColors, SwitchGamepad

pad = SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
    controller_colors=ControllerColors(
        body=0x323232,
        buttons=0xFFFFFF,
        left_grip=0x00B2FF,
        right_grip=0xFF3B30,
    ),
)
```

`ControllerColors` は constructor-time profile 設定である。`await pad.set_color(...)`、`pad.controller_colors = ...`、`pad.profile.colors = ...` のような接続後変更 API は作らない。
`left_grip` と `right_grip` を省略した場合は、それぞれの既定値 `0x00B2FF` / `0xFF3B30` を使う。body 色への正規化は行わない。

### 8.2 配置と依存方向

- public import は `from swbt import ControllerColors` とする。
- `ControllerColors` は Bumble / transport / protocol parser に依存させず、入力不正は `InvalidInputError` に揃える。
- `ProControllerProfile` は `controller_colors: ControllerColors` を持てるようにする。
- `VirtualSpiFlash` は profile から device type と controller colors を seed する。
- `SubcommandResponder` は configured `VirtualSpiFlash` と profile を受け取り、`0x02` と `0x10` を同じ profile 由来にする。
- `SwitchGamepad` / `SwitchGamepadConfig` は profile 設定を受け、`OutputReportDispatcher` に configured `SubcommandResponder` を渡す。
- `ReportLoop` の periodic input report と `InputStateStore` は color 設定を知らないままにする。

### 8.3 API を広げない判断

serial number、Bluetooth address、calibration、battery 表示は Switch 初期化や識別、補正、接続状態の意味に関わる。見た目の customization に見えても、後続の pairing / reconnect / input reflection へ影響する可能性があるため、この unit では扱わない。

player lights は `0x30` set player lights で Switch から要求される mutable session state であり、fixed identity / profile には入れない。

## 9. 対象ファイル

この unit で編集したファイルは次の通り。

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profile.py` | modify | `ControllerColors` と `ProControllerProfile.controller_colors` |
| `src/swbt/protocol/spi.py` | modify | device type、color info exists flag、controller color seed |
| `src/swbt/protocol/subcommand.py` | modify | configured profile から `VirtualSpiFlash` を作る |
| `src/swbt/gamepad/core.py` | modify | `controller_colors=`、config pass-through、configured responder injection |
| `src/swbt/__init__.py` | modify | `ControllerColors` の public export |
| `docs/api.md` | modify | public API docs |
| `spec/initial/api.md` | modify | `ControllerColors` と `controller_colors=` の public API contract |
| `spec/initial/protocol.md` | modify | controller color SPI seed と `0x02` / `0x10` contract |
| `tests/unit/test_protocol_profile.py` | modify | `ControllerColors` default、byte order、validation |
| `tests/unit/test_virtual_spi_flash.py` | modify | SPI seed と flag |
| `tests/unit/test_subcommand_responder.py` | modify | custom color SPI read reply |
| `tests/unit/test_public_api_boundary.py` | modify | constructor/config signature |
| `tests/unit/test_package_import.py` | modify | `swbt.__all__` |
| `tests/unit/test_public_api_docstrings.py` | modify | public docstring contract |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | fake transport output report injection |
| `tests/hardware/test_controller_colors.py` | add | sentinel controller color SPI reply の tracked hardware characterization |
| `spec/hardware-test-log.md` | modify | tracked hardware run の条件、artifact、結果 |
| `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` | move / modify | TDD status、検証結果、完了状態 |

## 10. 検証

自動化対象は unit / fake transport integration で検証した。実機 UI 反映は 2026-07-05 に任意観測として実行し、条件付き observation として `spec/hardware-test-log.md` に記録した。sentinel color profile の tracked hardware test では on-wire SPI reply と device info reply を確認した。device-info tail `01 01` では grip が body 色に寄ったが、tail `03 02` では left/right grip がマゼンタ/オレンジとして UI に反映された。UI 表示は自動判定せず、Switch 2 / firmware 22.1.0 条件の観測として扱う。

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_protocol_profile.py` | red | `ControllerColors` 未定義による import error を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py` | pass | 3 passed。`ControllerColors()` の既定 body / buttons を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py` | red | `ControllerColors.to_spi_bytes()` 未実装による failure を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py` | pass | 4 passed。custom colors の `#RGB` SPI byte order を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py` | red | 不正な RGB 値が `InvalidInputError` にならない failure を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py` | pass | 14 passed。範囲外値と `str` / `bytes` / tuple の拒否を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_switch_gamepad_constructor_accepts_controller_colors_config` | red | `SwitchGamepadConfig(controller_colors=...)` 未対応の `TypeError` を確認 |
| `uv run pytest tests/unit/test_public_api_boundary.py::test_switch_gamepad_constructor_accepts_controller_colors_config` | pass | 1 passed。constructor / config signature と config 保持を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py` | red | `0x6050` read が erased bytes を返す failure を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py` | pass | 6 passed。既定 controller colors の SPI seed を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py` | red | `ProControllerProfile(controller_colors=...)` 未対応の `TypeError` を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py` | pass | 7 passed。custom controller colors の SPI seed を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py` | red | `0x601B` read が erased byte を返す failure を確認 |
| `uv run pytest tests/unit/test_virtual_spi_flash.py` | pass | 8 passed。color info exists flag の SPI seed を確認 |
| `uv run pytest tests/unit/test_subcommand_responder.py` | red | custom profile の SPI read が default color を返す failure を確認 |
| `uv run pytest tests/unit/test_subcommand_responder.py` | pass | 11 passed。custom controller colors の `0x10` SPI read reply と `0x02` device info profile bytes regression を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_configured_controller_colors` | red | `SwitchGamepad(controller_colors=...)` が default color を返す failure を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_configured_controller_colors` | pass | 1 passed。fake transport output report injection で custom color SPI reply を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_default_controller_colors_when_none` | pass | 1 passed。`controller_colors=None` から default color SPI reply までの経路を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_output_report_injection_uses_configured_controller_colors` | pass | 1 passed。`SwitchGamepad.from_config()` から custom color SPI reply までの経路を確認 |
| `uv run pytest tests/unit/test_package_import.py tests/unit/test_public_api_boundary.py::test_public_api_import_does_not_import_bumble tests/unit/test_public_api_boundary.py::test_public_api_import_does_not_resolve_bumble` | red | `swbt.__all__` の `ControllerColors` 不足を確認。Bumble 非解決 regression は pass |
| `uv run pytest tests/unit/test_package_import.py tests/unit/test_public_api_boundary.py::test_public_api_import_does_not_import_bumble tests/unit/test_public_api_boundary.py::test_public_api_import_does_not_resolve_bumble` | pass | 3 passed。public export と Bumble 非解決境界を確認 |
| `uv run pytest tests/unit/test_public_api_docstrings.py tests/unit/test_public_docs.py::test_api_doc_covers_top_level_public_exports_and_methods` | red | `ControllerColors` docstring の Attributes と `docs/api.md` の top-level export 不足を確認 |
| `uv run pytest tests/unit/test_public_api_docstrings.py tests/unit/test_public_docs.py::test_api_doc_covers_top_level_public_exports_and_methods` | pass | 3 passed。`ControllerColors` / `controller_colors=` の public docs と docstring を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_virtual_spi_flash.py tests/unit/test_subcommand_responder.py` | red | 16 failed, 28 passed。`left_grip` / `right_grip` 未実装、`0x6050`-`0x605B` seed 未実装、12 bytes SPI reply 未対応を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_virtual_spi_flash.py tests/unit/test_subcommand_responder.py` | pass | 44 passed。body / buttons / left grip / right grip の validation、byte order、SPI seed、subcommand reply を確認 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_configured_controller_colors tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_default_controller_colors_when_none tests/integration/test_switch_gamepad_fake_transport.py::test_from_config_output_report_injection_uses_configured_controller_colors tests/unit/test_public_api_docstrings.py` | pass | 5 passed。fake transport 経由の 12 bytes color SPI reply と public docstring を確認 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_virtual_spi_flash.py tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_default_controller_colors_when_none` | red | 4 failed, 30 passed。既定色を Joy-Con-ish profile に変え、body fallback を削除する期待値に対して旧 daemon-seed / body fallback 実装が残っていることを確認 |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_virtual_spi_flash.py tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_default_controller_colors_when_none` | pass | 34 passed。`ControllerColors()`、`VirtualSpiFlash`、fake transport の default color SPI reply が `32 32 32 ff ff ff 00 b2 ff ff 3b 30` になることを確認 |
| `uv run ruff format --check .` | pass | 73 files already formatted。Joy-Con-ish default profile 変更後に再実行 |
| `uv run ruff check .` | pass | All checks passed。Joy-Con-ish default profile 変更後に再実行 |
| `uv run ty check --no-progress` | pass | All checks passed。Joy-Con-ish default profile 変更後に再実行 |
| `uv run pytest tests/unit` | pass | 259 passed。Joy-Con-ish default profile 変更後に再実行 |
| `uv run pytest tests/integration` | pass | 72 passed。Joy-Con-ish default profile 変更後に再実行 |
| `uv sync --dev` | pass | Resolved 53 packages。Checked 41 packages |
| `uv run ruff format --check .` | pass | 73 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 259 passed |
| `uv run pytest tests/integration` | pass | 72 passed |
| `uv run python .pytest_cache\hardware\unit_028_controller_color_probe.py --adapter usb:0 --artifact-dir .pytest_cache\hardware\unit_028 --body 0x00c853 --buttons 0xffeb3b --timeout 60 --spi-timeout 25 --hold-seconds 15 --switch-start-condition "Switch 2 22.1.0 controller search / change grip order screen; UI color observation by user"` | hardware-pass | Windows 11 / CSR8510 A10 / WinUSB / Bumble 0.0.230 / Switch 2 firmware 22.1.0。trace は `0x006050` と `0x00603d` の SPI read で `controller_color_bytes=00c853ffeb3b`、`matches_expected_controller_colors=true` を記録した。ユーザは Switch UI で緑 body / 黄 buttons の controller 表示を目視確認した。non-neutral input は送っていない |
| `uv run python tmp\hardware\unit_028_controller_color_probe.py --adapter usb:0 --artifact-dir .pytest_cache\hardware\unit_028 --body 0x00c853 --buttons 0xffeb3b --left-grip 0x2962ff --right-grip 0xd50000 --timeout 60 --spi-timeout 25 --hold-seconds 15 --switch-start-condition "Switch 2 22.1.0 controller search / change grip order screen; unit_028 grip color observation by user"` | hardware-pass | Windows 11 / CSR8510 A10 / WinUSB / Bumble 0.0.230 / Switch 2 firmware 22.1.0。trace は `0x006050` size 13 で `controller_color_bytes=00c853ffeb3b2962ffd50000`、`matches_expected_controller_colors=true` を記録した。ユーザは左右 grip が青/赤に変わらず緑のままに見えると報告した。non-neutral input は送っていない |
| `uv run python tmp\hardware\unit_028_controller_color_probe.py --adapter usb:0 --artifact-dir .pytest_cache\hardware\unit_028 --trace-name controller-colors-and-grips-hold30.jsonl --body 0x00c853 --buttons 0xffeb3b --left-grip 0x2962ff --right-grip 0xd50000 --timeout 60 --spi-timeout 25 --hold-seconds 30 --switch-start-condition "Switch 2 22.1.0 controller search / change grip order screen; unit_028 grip color 30s hold observation by user"` | hardware-pass | Windows 11 / CSR8510 A10 / WinUSB / Bumble 0.0.230 / Switch 2 firmware 22.1.0。trace は `0x006050` size 13 で `controller_color_bytes=00c853ffeb3b2962ffd50000`、`matches_expected_controller_colors=true`、`hold_seconds=30.0`、`connection_state=closed` を記録した。ユーザは 30 秒後も左右 grip が緑のままと報告した。non-neutral input は送っていない |
| `uv run ruff format --check .` | pass | 74 files already formatted。tracked hardware test 追加後に実行 |
| `uv run ruff check .` | pass | All checks passed。tracked hardware test 追加後に実行 |
| `uv run ty check --no-progress` | pass | All checks passed。tracked hardware test 追加後に実行 |
| `uv run pytest tests\unit\test_virtual_spi_flash.py tests\unit\test_subcommand_responder.py tests\unit\test_protocol_profile.py -q` | pass | 44 passed。`VirtualSpiFlash` の 12 bytes seed endpoint 修正と controller color protocol tests を確認 |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel --log-file .pytest_cache\hardware\unit_028\tracked-sentinel\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 33.43s。trace は `0x006050` size 13 で sentinel `controller_color_bytes=ff00000000ffff00ffff8000`、`matches_expected_controller_colors=true`、`hold_seconds=30.0`、`manual_controller_color_cleanup connection_state=closed` を記録した。ユーザは body が赤、buttons が青、grip も赤に見えると報告した。artifact は `.pytest_cache/hardware/unit_028/tracked-sentinel/controller-colors-sentinel.jsonl` と `pytest-debug.log` |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 33.42s。旧 `DEVICE_INFO_DATA=040003020000000000000101` と sentinel color bytes `ff00000000ffff00ffff8000` を記録した。ユーザは body/grip が赤、buttons が青と報告した |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_device_info_address -m hardware --swbt-bumble-adapter usb:0 --swbt-device-info-address 00:1B:DC:F9:9F:7D --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-address --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-address\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 33.39s。旧 tail `01 01` のまま local BD_ADDR `001bdcf99f7d` を返した。ユーザ報告は body/grip が赤、buttons が青のまま |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_zero_tail_byte -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-zero-tail --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-zero-tail\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 33.38s。旧 tail `01 01` のまま `0x605C=00` を返した。ユーザ報告は body/grip が赤、buttons が青のまま |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_device_info_tail_0x03_0x02 -m hardware --swbt-bumble-adapter usb:0 --swbt-device-info-address 00:1B:DC:F9:9F:7D --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302 --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 33.42s。`device_info_data=04000302001bdcf99f7d0302` と sentinel color bytes を記録した。ユーザは左 grip がマゼンタ、右 grip がオレンジに変わったと報告した |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_device_info_tail_0x03_0x02 -m hardware --swbt-bumble-adapter usb:0 --swbt-device-info-address 00:00:00:00:00:00 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302-zero-address --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302-zero-address\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 32.79s。`device_info_data=040003020000000000000302` と sentinel color bytes を記録した。ユーザは同じように左マゼンタ、右オレンジが保持されたと報告した |
| `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-default-tail-0302 --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-default-tail-0302\pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 33.45s。production default `DEVICE_INFO_DATA=040003020000000000000302` で sentinel color bytes を返し、ユーザは同じように左マゼンタ、右オレンジが保持されたと報告した |
| `uv run ruff format src\swbt\protocol\subcommand.py tests\unit\test_subcommand_responder.py tests\hardware\test_controller_colors.py tests\conftest.py` | pass | 4 files left unchanged。device-info tail `03 02` 変更と tracked hardware characterization test 更新後に実行 |
| `uv run ruff check src\swbt\protocol\subcommand.py tests\unit\test_subcommand_responder.py tests\hardware\test_controller_colors.py tests\conftest.py` | pass | All checks passed |
| `uv run ty check --no-progress src\swbt\protocol\subcommand.py tests\unit\test_subcommand_responder.py tests\hardware\test_controller_colors.py tests\conftest.py` | pass | All checks passed |
| `uv run pytest tests\unit\test_subcommand_responder.py tests\unit\test_virtual_spi_flash.py tests\unit\test_protocol_profile.py tests\unit\test_source_audit_fixtures.py -q` | pass | 53 passed。device-info tail `03 02`、controller color SPI seed、source audit fixture を確認 |
| `uv sync --dev` | pass | Resolved 53 packages。Checked 41 packages |
| `uv run ruff format --check .` | pass | 74 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit` | pass | 259 passed |
| `uv run pytest tests\integration` | pass | 72 passed |
| `uv run pytest tests\unit\test_hardware_test_log_docs.py tests\unit\test_source_audit_fixtures.py -q` | pass | 12 passed。検証表更新後の docs/source-audit checks |
| `git diff --check` | pass | whitespace error なし |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | automated scope では不要。UI 反映確認をする場合だけ任意で必要 |
| 承認範囲 | 実機確認時は adapter open、HID advertising、pairing または reconnect、Switch-facing output report / subcommand handling、periodic report loop、cleanup を明示する |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle を指定する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics JSON Lines、Switch model / firmware、Bumble version、Python version、driver、dongle identity、SPI read sequence、UI 反映の有無 |
| cleanup | neutral、report loop 停止、transport close、adapter release |

## 12. 先送り事項

- 別 OS、別 firmware、既存 bond cache 条件での controller color UI 反映確認。この unit では Windows / Switch 2 / firmware 22.1.0 の条件付き observation まで完了とする。tracked sentinel test では production default `03 02` tail で left/right grip がマゼンタ/オレンジとして反映された。
- device-info tail `03 02` の意味名は未確定。この unit では mizuyoukanao/btstack 実装事実と Windows / Switch 2 / firmware 22.1.0 hardware observation に基づく protocol profile byte として採用する。別 firmware や別 UI での再確認は後続に回す。
- serial number、Bluetooth address、calibration、battery、player lights、report period の customization は別 unit に分ける。

## 13. チェックリスト

このチェックリストは unit_028 の実装完了状態を示す。

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] 自動化対象の TDD item が green である
- [x] 標準 gate が通っている
