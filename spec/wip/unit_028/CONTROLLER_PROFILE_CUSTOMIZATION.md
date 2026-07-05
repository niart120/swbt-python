# Controller Profile Customization 仕様書

## 1. 概要

### 1.1 目的

`SwitchGamepad` 作成時に、操作へ影響しない controller identity / profile 値を指定できるようにする。初期 scope は controller color の body / buttons 6 bytes に限定し、入力状態、report period、pairing strategy、Bluetooth adapter 操作へ混ぜない。

この作業では仕様だけを定義する。実装とテスト追加は後続の TDD cycle で扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | device color など、操作に影響しない controller identity / profile customization の仕様化 | conversation |
| AGENTS | Public API、protocol 境界、根拠監査、実機安全境界 | `AGENTS.md` |
| spec-format skill | 作業仕様の配置、構成、TDD Test List、実機条件 | `.agents/skills/spec-format/SKILL.md` |
| source-audit skill | SPI address、subcommand payload、device info profile の分類 | `.agents/skills/source-audit/SKILL.md` |
| initial API | `SwitchGamepad` / `SwitchGamepadConfig` の公開 constructor 境界 | `spec/initial/api.md` |
| initial protocol | `SubcommandResponder`、`VirtualSpiFlash`、`0x02` / `0x10` の責務 | `spec/initial/protocol.md` |
| current implementation | profile、SPI、subcommand、gamepad constructor の現状 | `src/swbt/protocol/profile.py`, `src/swbt/protocol/spi.py`, `src/swbt/protocol/subcommand.py`, `src/swbt/gamepad/core.py` |
| current tests | public API、profile、SPI、subcommand、docs の既存 test surface | `tests/unit/` |
| daemon source audit | SPI color range と seed data | `E:/documents/VSCodeWorkspace/swbt-daemon/spec/references/switch-spi-core.md`, `E:/documents/VSCodeWorkspace/swbt-daemon/spec/references/switch-virtual-spi-seed-data.md` |
| upstream source audit | controller color の body / buttons range と `#RGB` 24-bit 表現 | `https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/master/spi_flash_notes.md` |
| daemon implementation | device info color source と virtual SPI color seed | `E:/documents/VSCodeWorkspace/swbt-daemon/swbt/switch/switch_device_info.c`, `switch_device_info.h`, `switch_spi.h`, `switch_spi_seed.c`, `switch_spi_seed.h` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `SwitchGamepad(..., controller_colors=ControllerColors(body=0x112233, buttons=0x445566))` | Switch からの SPI read に指定色が返る | 作成時に固定する。接続後 setter は作らない |
| protocol core | `0x10` SPI read for `0x6050`, size `6` | reply payload が request prefix と 6 bytes color を含む | Bumble / 実機なしの unit test で検証する |
| protocol core | `0x02` request device info | color source が SPI を指す profile reply を返す | 色そのものは device info reply に埋め込まない |
| reviewer | source / implementation / inference の確認 | SPI address、device info color_source、subcommand 関係の根拠分類を追える | 未検証仮説を public API 契約にしない |
| hardware follow-up | 実機で color 反映を見る | Switch UI で色表示が変わるか記録する | adapter open、advertising、pairing、report loop は明示承認が必要 |

## 2. 対象範囲

- `ControllerColors` value object の公開 API 設計。
- `SwitchGamepad(controller_colors=...)` と `SwitchGamepadConfig.controller_colors` の constructor-time 設定。
- 既定色は daemon dev seed と同じ `body=0x0D0D0D`, `buttons=0xFFFFFF` とする。
- `ControllerColors` は `body` と `buttons` を 24-bit RGB integer として受ける。
- `controller_colors=None` は既定色を使う。
- `ControllerColors` は immutable にし、`0 <= value <= 0xFFFFFF` だけを受ける。`str`、`bytes`、tuple、負数、`0x1000000` 以上は `InvalidInputError` とする。
- SPI `0x6050`-`0x6055` への seed と `0x10` SPI read reply。
- `0x02` device info reply の color source を SPI として扱うこと。
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
- `0x601B` color info exists flag の seed。daemon header には address があるが、この unit では外部 source と Switch 側の必要性を確定していない。
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

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | reviewed-for-spec | SPI address、subcommand `0x02` / `0x10` reply payload、device info color_source に関係するため。実装時は unit test fixture にも反映する |
| Bumble / transport | not applicable | not applicable | 色設定は protocol core の SPI / subcommand data で完結する。Bumble object 型や callback 型は public API に出さない |
| OS / driver / adapter | not applicable | not applicable | automated scope では adapter を開かない。実機反映確認を行う場合だけ hardware 承認境界を通す |

### 5.1 source fact

| 項目 | 値 | source | status |
|---|---:|---|---|
| SPI flash address limit | `0x80000` exclusive | `switch-spi-core.md`; `switch_spi.h` | stable boundary |
| SPI read max size | `0x1d` bytes | `switch-spi-core.md`; `switch_spi.h` | stable boundary |
| device type address / value | address `0x6012`, Pro Controller `0x03` | `switch-spi-core.md`; `switch_spi.h` | stable address/value |
| controller color range | `0x6050`-`0x6055` inclusive | `switch-spi-core.md` | stable address map; payload is caller-seeded |
| body color range and byte order | `0x6050`-`0x6052`, Body `#RGB` color, 24-bit | dekuNukem `spi_flash_notes.md` | source fact |
| buttons color range and byte order | `0x6053`-`0x6055`, Buttons `#RGB` color, 24-bit | dekuNukem `spi_flash_notes.md` | source fact |
| controller color seed length | `6` bytes | `switch-virtual-spi-seed-data.md`; `switch_spi_seed.h` | stable length derived from the range |

### 5.2 implementation fact

| 項目 | 値 | source | status |
|---|---:|---|---|
| daemon dev color seed | `0d 0d 0d ff ff ff` | `switch_spi_seed.c` | implementation default, not factory data |
| daemon seed writer | writes `controller_colors` to `SWBT_SWITCH_SPI_ADDRESS_CONTROLLER_COLORS` | `switch_spi_seed.c` | implementation behavior |
| daemon device info color source | `SWBT_SWITCH_DEVICE_INFO_COLORS_FROM_SPI = 0x01` and reply data byte 11 stores `color_source` | `switch_device_info.h`, `switch_device_info.c` | implementation behavior |
| swbt-python current SPI seed | `VirtualSpiFlash` seeds only `0x6012 = 0x03`; color bytes remain erased | `src/swbt/protocol/spi.py` | current implementation |
| swbt-python current `0x02` reply | static `DEVICE_INFO_DATA = 04 00 03 02 00 00 00 00 00 00 01 01` | `src/swbt/protocol/subcommand.py` | current implementation; last byte already matches SPI color source |
| swbt-python current `0x10` reply | returns request prefix plus `VirtualSpiFlash.read(address, size)` | `src/swbt/protocol/subcommand.py` | current implementation |
| swbt-python current construction path | `OutputReportDispatcher` creates default `SubcommandResponder`; `SwitchGamepad` does not pass profile or SPI seed | `src/swbt/gamepad/output.py`, `src/swbt/gamepad/core.py` | current implementation |

### 5.3 inference

| 項目 | 推論 | 根拠 | 実装上の扱い |
|---|---|---|---|
| custom color reflection path | Switch が `0x02` で color source を SPI と判断し、`0x10` で `0x6050` 付近を読むことで色を得る | daemon device info は `color_source=0x01`、SPI range は `0x6050`-`0x6055` | `0x02` reply と `0x10` SPI reply の unit test を分ける |
| API field split | 6 bytes を `body` 3 bytes と `buttons` 3 bytes として公開する | upstream source が body `0x6050`-`0x6052`、buttons `0x6053`-`0x6055` を `#RGB` 24-bit として示す | source fact に従い、実装時 test で byte order を固定する |
| ownership | `ControllerColors` は `InputState` ではなく profile / identity 設定に属する | 操作入力に影響せず、SPI / device info reply で観測される | `SwitchGamepad` 作成時に固定し、state update API には入れない |
| profile propagation | `SwitchGamepadConfig` から `ProControllerProfile`、`VirtualSpiFlash`、`SubcommandResponder` へ渡す必要がある | 現在の dispatcher は default responder を作るだけ | 後続実装では dispatcher 構築時に configured responder を注入する |

### 5.4 unverified hypothesis

| 項目 | 未検証内容 | 扱い |
|---|---|---|
| Switch UI reflection | Switch UI がこの 6 bytes を常に表示へ反映するか | hardware optional。automated gate にはしない |
| firmware / model difference | Switch model / firmware ごとの color read sequence 差 | 実機観測時に condition を記録する |
| bond cache interaction | 既存 bond がある場合、色変更が再 pairing なしで見えるか | public API 保証にしない |
| `0x601B` color info exists flag | `0x601B` を seed しないと色が無視される環境があるか | この unit では未実装。必要なら別 source-audit item とする |
| Switch UI の表示順 | source-backed SPI order と Switch UI 表示の対応 | public API は SPI 上の body/buttons `#RGB` として保証し、UI 表示は hardware observation まで保証しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| default colors | `SwitchGamepad(..., controller_colors=None)` | SPI `0x6050` から `0d 0d 0d ff ff ff` を返す | 既定挙動を明示する |
| custom colors | `ControllerColors(body=0x112233, buttons=0x445566)` | SPI `0x6050` から `11 22 33 44 55 66` を返す | source-backed `#RGB` order |
| validation | `body=-1`, `buttons=0x1000000`, non-int | `InvalidInputError` | 不正な値を wrap / mask しない |
| constructor fixed identity | `SwitchGamepad(controller_colors=...)` 作成後 | profile は object lifetime 中に変わらない | setter は作らない |
| state update separation | `press()` / `release()` / `apply()` / `neutral()` | controller colors は変わらない | `InputState` へ入れない |
| device info | `0x02` request device info | color source byte は SPI を指す `0x01` | 色 bytes は含めない |
| SPI read | `0x10` request address `0x6050`, size `6` | request prefix 5 bytes + color 6 bytes を返す | `SubcommandResponder` unit test で固定 |
| public docs | docs / docstring / `__all__` | `ControllerColors` と `controller_colors=` の使い方が記載される | 接続後変更不可と対象外を明記する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `ControllerColors()` が既定 body `0x0D0D0D` / buttons `0xFFFFFF` を持つ | new | unit | no | daemon dev seed と同じ値 |
| todo | `ControllerColors(body=0x112233, buttons=0x445566)` が SPI bytes `11 22 33 44 55 66` に変換される | new | unit | no | dekuNukem `spi_flash_notes.md` の `#RGB` order を固定する |
| todo | `ControllerColors` が範囲外値と non-int を `InvalidInputError` にする | edge | unit | no | mask しない。`str` / `bytes` / tuple も拒否 |
| todo | `SwitchGamepadConfig(controller_colors=...)` と `SwitchGamepad(..., controller_colors=...)` が公開 signature に出る | new | unit | no | Bumble 型を public API に露出しない test も維持 |
| todo | `SwitchGamepad.from_config()` が `controller_colors` を保持し default transport / fake transport のどちらでも protocol path へ渡す | new | unit / integration | no | existing config pass-through test に近い |
| todo | `VirtualSpiFlash` が既定色を `0x6050`-`0x6055` に seed する | new | unit | no | 既存 `0x6012` device type test を維持 |
| todo | `VirtualSpiFlash` が custom `ControllerColors` を `0x6050`-`0x6055` に seed する | new | unit | no | source-backed `#RGB` order を維持 |
| todo | `SubcommandResponder` の `0x10` SPI read reply が custom colors を返す | new | unit | no | payload `50 60 00 00 06` に対して prefix + 6 bytes |
| todo | `SubcommandResponder` の `0x02` device info reply が color_source `0x01` を保つ | regression | unit | no | color bytes を device info に入れない |
| todo | fake transport 経由の output report injection で custom color SPI reply が送信される | new | integration | no | `SwitchGamepad` から dispatcher / responder へ渡る経路を確認 |
| todo | `swbt.__all__` が `ControllerColors` を含み、package import が Bumble を解決しない | regression | unit | no | public API boundary |
| todo | public API docstring と `docs/api.md` が `ControllerColors` / `controller_colors=` を説明する | new | unit | no | 接続後 setter なしを明記 |
| deferred | 実機で Switch UI に body / buttons color が反映されるか観測する | characterization | hardware | yes | 任意の後続。hardware 承認境界を通す |

## 8. 設計メモ

### 8.1 Public API 案

```python
from swbt import ControllerColors, SwitchGamepad

pad = SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
    controller_colors=ControllerColors(
        body=0x0D0D0D,
        buttons=0xFFFFFF,
    ),
)
```

`ControllerColors` は constructor-time profile 設定である。`await pad.set_color(...)`、`pad.controller_colors = ...`、`pad.profile.colors = ...` のような接続後変更 API は作らない。

### 8.2 配置と依存方向

- public import は `from swbt import ControllerColors` とする。
- `ControllerColors` の実体は標準ライブラリだけに依存させる。
- `ProControllerProfile` は `controller_colors: ControllerColors` を持てるようにする。
- `VirtualSpiFlash` は profile から device type と controller colors を seed する。
- `SubcommandResponder` は configured `VirtualSpiFlash` と profile を受け取り、`0x02` と `0x10` を同じ profile 由来にする。
- `SwitchGamepad` / `SwitchGamepadConfig` は profile 設定を受け、`OutputReportDispatcher` に configured `SubcommandResponder` を渡す。
- `ReportLoop` の periodic input report と `InputStateStore` は color 設定を知らないままにする。

### 8.3 API を広げない判断

serial number、Bluetooth address、calibration、battery 表示は Switch 初期化や識別、補正、接続状態の意味に関わる。見た目の customization に見えても、後続の pairing / reconnect / input reflection へ影響する可能性があるため、この unit では扱わない。

player lights は `0x30` set player lights で Switch から要求される mutable session state であり、fixed identity / profile には入れない。

## 9. 対象ファイル

この仕様作成で編集するファイルは次の 1 件だけである。

| path | change | 内容 |
|---|---|---|
| `spec/wip/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` | new | controller color customization の作業仕様 |

後続実装で変更候補になるファイルは次の通り。

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profile.py` | modify | `ControllerColors` または profile field の追加 |
| `src/swbt/protocol/spi.py` | modify | color seed の追加 |
| `src/swbt/protocol/subcommand.py` | modify | configured profile / SPI flash から `0x02` / `0x10` reply を生成 |
| `src/swbt/gamepad/core.py` | modify | `controller_colors=` と config pass-through |
| `src/swbt/gamepad/output.py` | modify | configured `SubcommandResponder` injection |
| `src/swbt/__init__.py` | modify | `ControllerColors` の public export |
| `docs/api.md` | modify | public API docs |
| `tests/unit/` | modify | validation、SPI seed、subcommand reply、public API docs tests |
| `tests/integration/` | modify | fake transport 経由の configured SPI reply |

## 10. 検証

仕様書作成のみのため、実装 gate は実行しない。

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pending | 依存変更なし。後続実装で必要になった時点で実行する |
| `uv run ruff format --check .` | pending | Markdown 仕様のみ作成。後続実装で実行する |
| `uv run ruff check .` | pending | Python 実装なし。後続実装で実行する |
| `uv run ty check --no-progress` | pending | Python 実装なし。後続実装で実行する |
| `uv run pytest tests/unit` | pending | 仕様作成のみ。後続 TDD で red から開始する |
| `uv run pytest tests/integration` | pending | 実装なし。fake transport 経由の確認を追加した時点で実行する |

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

- `0x601B` color info exists flag の source audit と必要性確認。
- grip color ranges `0x6056`-`0x605B` の扱い。upstream source には存在するが、この unit の初期 scope には入れない。
- Switch UI での色反映確認。実行する場合は `hardware-harness` の承認境界を通し、`spec/hardware-test-log.md` に条件付き observation として記録する。
- serial number、Bluetooth address、calibration、battery、player lights、report period の customization は別 unit に分ける。

## 13. チェックリスト

このチェックリストは仕様作成の状態を示す。実装完了の印ではない。

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
