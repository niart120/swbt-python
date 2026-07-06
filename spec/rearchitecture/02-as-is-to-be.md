# 02. As-is / To-be architecture

## Current architecture at a glance

```text
Current public creation path

swbt.SwitchGamepad(..., device_name=?, controller_colors=?, transport=?)
  └─ SwitchGamepadConfig(profile=default_controller_profile())
      └─ SwitchGamepad._init_from_config(...)
          ├─ InputStateStore
          ├─ DiagnosticsRecorder
          ├─ ControllerProfile replacement for colors
          ├─ OutputReportDispatcher(SubcommandResponder(profile))
          ├─ ConnectionWorkflow
          ├─ create_default_transport(..., profile)
          └─ ReportLoop(InputReportBuilder(profile))

swbt.JoyCon("left" | "right", ..., transport=?)
  └─ SwitchGamepadConfig(profile=JoyConLeftProfile | JoyConRightProfile)
      └─ inherited SwitchGamepad runtime machinery
```

低レイヤーの方向性は悪くない。controller 差分を `ControllerProfile` に寄せ、report / subcommand / transport setup が profile を受け取る流れは正しい。問題は、profile selection、runtime lifecycle、public config、test seam がすべて concrete public class から見えていることである。

## As-is responsibilities

### `SwitchGamepad` の過責務

現状の `SwitchGamepad` は、次を 1 class で所有している。

- public constructor
- async context manager
- input state update API
- connection API
- report loop 構築
- diagnostics recorder
- output report dispatcher
- transport callback 登録
- default transport 作成
- injected transport の扱い
- profile 適用

これは public facade ではなく、実行系を含む concrete runtime holder である。

### `JoyCon` の継承関係が意味を誤らせる

現状の `JoyCon` は `SwitchGamepad` を継承する thin wrapper であり、`side` を受け取って `_joycon_profile(side)` で profile を選ぶ。

この形は、Joy-Con が concrete `SwitchGamepad` の特殊形であるように見える。しかし実態としては、Pro Controller と単体 Joy-Con は同じ操作 interface を共有する別 identity の controller である。継承で表すべきなのは implementation reuse ではなく common interface である。

将来 `JoyConPair`、左右別の pairing 挙動、左右別の実機検証状態を扱う場合にも、`JoyCon(SwitchGamepad)` という関係は説明しづらい。

### `profile.py` の変更理由が多すぎる

現行 `profile.py` には次が混在している。

- HID report descriptor
- Pro Controller button map
- Joy-Con L button map
- Joy-Con R button map
- controller color
- SDP policy
- base profile
- concrete profile
- input validation
- device info payload 生成

これは file size の問題ではなく、変更理由が多いことが問題である。HID descriptor を変える変更、Joy-Con R の button map を修正する変更、color SPI を修正する変更が同じ file に集中する。

### `transport=` が backend API に見える

public constructor が `transport=` を受けると、外部利用者が任意 transport implementation を差し込める公式 API に見える。これは本来 unit test 用 seam である。

transport は open / advertising / close / disconnect request / bonded peer / reconnect / interrupt / control / callbacks を持つ。これは Bluetooth HID runtime の内部契約であり、通常利用者が直接扱う設定ではない。Backend 拡張を正式機能にするなら、別 issue で専用 API として設計する。

### 現在の docs と tests が直したい設計を固定している

README と agent brief は `SwitchGamepad` を直接生成する例を案内している。README では単体 Joy-Con を `JoyCon("left", ...)` / `JoyCon("right", ...)` で作る例も案内している。

public boundary test は、`JoyCon` が `SwitchGamepad` の thin wrapper であることを固定している。つまり、現在のテストは直したい設計を public contract として守っている。

## Target architecture at a glance

```text
Target public creation path

swbt.ProController(.)
  └─ _build_runtime(spec=_PRO_CONTROLLER_SPEC, .)
      └─ ControllerRuntime(profile=ProControllerProfile(.))

swbt.JoyConL(.)
  └─ _build_runtime(spec=_JOYCON_L_SPEC, .)
      └─ ControllerRuntime(profile=JoyConLeftProfile(.))

swbt.JoyConR(.)
  └─ _build_runtime(spec=_JOYCON_R_SPEC, .)
      └─ ControllerRuntime(profile=JoyConRightProfile(.))
```

```text
SwitchGamepad                # abstract public interface
  ↑
_RuntimeBackedGamepad        # private runtime delegation base
  ↑
  ├─ ProController
  ├─ JoyConL
  └─ JoyConR
```

`SwitchGamepad` は runtime を知らない。`_RuntimeBackedGamepad` だけが `ControllerRuntime` を知る。public concrete controller は controller identity を選び、内部 builder に resource config を渡す。

## Target module structure

```text
src/swbt/gamepad/
  __init__.py
  interface.py          # public SwitchGamepad abstract interface
  controllers.py        # public ProController, JoyConL, JoyConR
  runtime.py            # internal ControllerRuntime
  _config.py            # internal _RuntimeConfig, _ControllerSpec, _build_runtime
  _transport_factory.py # internal factory Protocol and Bumble/static factories
  connection.py
  output.py

src/swbt/protocol/
  profiles/
    __init__.py         # internal exports only
    base.py             # ControllerProfile, ControllerKind, ControllerColors, HidSdpPolicy
    pro_controller.py   # ProControllerProfile
    joycon.py           # JoyConLeftProfile, JoyConRightProfile
  buttons.py            # ButtonBitMap and concrete layout maps
  descriptors.py        # HID report descriptors
  sdp.py                # 必要なら分離
  profile.py            # 削除、または repo 内部向け re-export。root export しない
```

`core.py` は削除するか、移行中だけの薄い internal module にする。最終状態では public class を `core.py` に集めない。

## Dependency direction

許可する依存方向は次に寄せる。

```text
swbt.__init__
  └─ swbt.gamepad.controllers
      └─ swbt.gamepad._config
          ├─ swbt.protocol.profiles.*
          └─ swbt.gamepad.runtime
              ├─ swbt.protocol.input_report
              ├─ swbt.protocol.subcommand
              ├─ swbt.report_loop
              ├─ swbt.gamepad.connection
              ├─ swbt.gamepad.output
              └─ swbt.gamepad._transport_factory
```

禁止する方向は次のとおり。

```text
swbt.protocol.*              ─X→ swbt.gamepad.*
swbt.report_loop             ─X→ ProController/JoyConL/JoyConR
swbt.transport.*             ─X→ ProController/JoyConL/JoyConR
swbt.__init__ root exports    ─X→ ControllerProfile / HidDeviceTransport
public constructors           ─X→ profile / device_name / transport
```

## Boundary rules

### Rule 1: identity は concrete class が固定する

`ProController` は Pro Controller profile。`JoyConL` は Joy-Con (L) profile。`JoyConR` は Joy-Con (R) profile。この関係を public argument で崩せないようにする。

### Rule 2: profile は public config ではなく内部 truth

Profile は次を定義する。

```text
controller kind
device name
device type
device-info bytes
HID report descriptor
SDP policy
button bit map
stick capability
profile default report period
battery/vibrator bytes
controller colors default
```

大半は identity または protocol fact である。利用者が public constructor で自由に混ぜる値ではない。

### Rule 3: public config は resource config

Public constructor が受け取るのは、利用者が通常管理する値だけにする。

```text
adapter
key_store_path
report_period_us
controller_colors
diagnostics
```

### Rule 4: transport seam は internal

Bluetooth transport は implementation seam である。Public constructor argument ではない。Unit test では `_TransportFactory` や runtime helper 経由で差し込む。

### Rule 5: profile branching は局所化する

`ControllerKind` の分岐は profile construction、tests、必要なら docs example に閉じる。Runtime / report / transport code は、可能な限り profile method で差分を吸収し、kind 分岐を増やさない。
