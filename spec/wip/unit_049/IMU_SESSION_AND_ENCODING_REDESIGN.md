# IMU Session and Encoding Redesign 仕様書

## 1. 概要

### 1.1 目的

Switchがsubcommand `0x40`で指定するIMU mode、利用者が設定するIMU入力値、quaternion形式の生成に必要な姿勢状態を別の責務と寿命へ分離する。

現行実装の`InputReportBuilder`は、report bytesの組み立てに加え、shared session stateのreset要求の消費、clock取得、quaternion姿勢更新、前回時刻の更新を行う。この責務混在を解消し、各層をBumbleやSwitch実機なしで決定的にunit testできる構造へ置き換える。

このunitは内部APIの互換性を保証しない。一方、public `SwitchGamepad` / `InputState` / `IMUFrame` APIと、mode `0x01` / `0x02-0x05`の確認済みwire bytesは回帰対象とする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | IMU送信経路のアクター、状態所有、値モデル、mode遷移、message順序を再設計する | 2026-07-12 conversation |
| current implementation | `SubcommandSessionState` がIMU modeと一回消費型reset flagを持ち、`InputReportBuilder` がそれを消費する | `src/swbt/protocol/subcommand.py`, `src/swbt/protocol/input_report.py` |
| current lifecycle | subcommand session stateはruntime生成時に一度作られ、input report builderはopenごとに作られる | `src/swbt/gamepad/runtime.py` |
| completed unit | raw / rad/s / GのIMU入力API、factory calibration、mode別wire packingの現行契約 | `spec/complete/unit_025/IMU_INPUT_SHORTHAND_API.md`, `spec/complete/unit_047/VIRTUAL_GYRO_CALIBRATION.md`, `spec/complete/unit_048/VIRTUAL_ACCELEROMETER_CALIBRATION.md` |
| initial design | host要求はmutable session state、profileはfixed identity、`InputState` はraw 3 frameとする境界 | `spec/initial/architecture.md`, `spec/initial/protocol.md`, `spec/initial/lifecycle.md` |
| MissionControl | `0x00` はNull、`0x01` はStandard、`0x02-0x05` はQuaternionのpackerを選ぶ | https://github.com/ndeadly/MissionControl/tree/d3941d433f15827de8aea116d61ea17bb61d0bcc/mc_mitm/source/controllers |
| hardware observation | mode `0x02` packing mode 2でPro Controller profileの正負Z回転と静止がSwitch 2 / firmware 22.1.0 / スプラトゥーン3に反映された | `spec/hardware-test-log.md`, `spec/complete/unit_047/VIRTUAL_GYRO_CALIBRATION.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | subcommand `0x40` + mode `0x00-0x05` | ACK後のperiodic `0x30`が指定modeの36 byte IMU blockを持つ | 未対応modeでは現在状態を変更しない |
| library user | raw / rad/s / Gから作った`IMUFrame` 1または3個 | public APIの契約どおり`InputStateStore`にraw 3 frameが保持される | wire modeは利用者が指定しない |
| protocol session | 新規HID接続 | host要求状態とquaternion生成状態が初期化される | 前回接続のmodeを引き継がない |
| report scheduler | input snapshot、session snapshot、report時刻 | 副作用のないreport組み立てと明示的な次状態を得る | ACKとperiodic reportの順序を直列化する |
| Switch host | subcommand `0x10` SPI read | profile由来のfactory calibration bytesを得る | SPI readはIMU modeや姿勢状態を変更しない |
| unit test | 明示的な旧状態、IMU frame、時刻 | 同じ入力から同じbytesと次状態を得る | global clock、shared one-shot flag、transportを不要とする |

### 1.4 Intent Delta

unit_047は、`SubcommandSessionState`と`InputReportBuilder`が同じinstanceを共有し、subcommandがreset要求を記録し、builderが一度だけ消費する設計を完了状態とした。その後の監査で、host要求状態はruntime objectの寿命、quaternion状態はopenごとのbuilder寿命となり、HID接続generationと一致しないことが確認された。

本unitは、unit_047が固定したpublic IMU API、mode `0x01`のraw bytes、mode `0x02-0x05`のpacking mode 2、3 sampleの姿勢反映を維持する。一方、shared one-shot reset flag、stateful builder、runtime寿命のsubcommand stateは廃止する。

観測可能な変更は、mode未指定 / `0x00`の36 byteゼロ化、接続generationごとのhost要求状態reset、`0x40` ACKを新modeのperiodic reportより先に送る順序保証の3点とする。これらは単なる内部名変更として扱わず、独立したbehavior testで導入する。

## 2. 対象範囲

- hostがsubcommand `0x40`で指定するIMU modeを、接続ごとのprotocol session stateに保持する。
- report mode、IMU mode、vibration有効状態を、fixed `ControllerProfile`から分離した同一のhost-requested session stateに置く。
- quaternion姿勢と前回report時刻を、quaternion mode epochに属する状態として保持する。
- `SubcommandSessionState.consume_imu_mode_reset_request()`と一回消費型reset flagを削除する。
- `InputReportBuilder`からsession stateの参照、clock取得、quaternion姿勢更新を除き、入力が同じなら出力が同じ組み立て器にする。
- IMU wire生成は、明示的な現在状態、`InputState.imu_frames`、profile校正、report時刻を受け、36 byte blockと次状態を返す。
- 新しい接続generationでhost-requested stateとIMU encoding stateを初期化する。
- subcommand ACKとperiodic input reportを1つの接続generation内で直列化する。
- mode未指定とmode `0x00`はIMU disabledとし、periodic `0x30`を送る場合は36 byte IMU blockをゼロにする。
- mode `0x01`はraw 6軸値を3 frame、signed int16 little-endianでそのまま送る。
- mode `0x02-0x05`は現行のpacking mode 2と3 sampleの姿勢反映を維持する。
- acceptedな`0x40`要求は、同じmodeの再要求を含めて新しいIMU encoding epochを開始する。
- `0x40`とSPI `0x10` readが互いの状態を変更しないことを固定する。
- public API、protocol unit test、fake transport integration test、initial design docsを追従させる。

## 3. 対象外

- `SwitchGamepad.imu()`、`InputState`、`IMUFrame`のpublic signature変更。
- raw int16、rad/s、Gの公開変換尺度の変更。
- public APIからquaternionやhost IMU modeを直接指定する機能。
- 加速度とジャイロのセンサーフュージョン、重力方向推定、ノイズ、温度ドリフトの模擬。
- Joy-Con固有の物理軸方向の確定。
- packing mode 0 / 1の生成。mode `0x02-0x05`は現行どおりpacking mode 2を使う。
- report送信周期、timer進行、Bumble、SDP、L2CAP、pairing方式の変更。
- 長時間停止後の経過時間上限や角速度フィルタの新設。根拠のない上限値をこのunitで導入しない。
- custom profile calibrationに対応した新しい物理単位public API。現行`IMUFrame.gyro_rate()` / `accel_g()`は共通既定校正のconvenience APIとして維持する。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/protocol.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_025/IMU_INPUT_SHORTHAND_API.md`
- `spec/complete/unit_047/VIRTUAL_GYRO_CALIBRATION.md`
- `spec/complete/unit_048/VIRTUAL_ACCELEROMETER_CALIBRATION.md`
- `spec/hardware-test-log.md`
- `docs/api.md`
- `docs/usage.md`
- `docs/agent-brief.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | source-audit fixtureとunit_047が`0x01` standard、`0x02-0x05` quaternion packing mode 2をMissionControl commitと実機観測に紐付けている |
| mode `0x00` / 未指定 | required | done | MissionControlはInactiveで`NullMotionPacker`を選び36 bytesをゼロ化する。このupstream implementation factを採用し、現行swbt-pythonのraw fallbackを修正する |
| subcommand `0x40` | required | done | `0x40`はSPI writeではなくSensorSleep / IMU mode要求。現行parserとsource-audit fixtureでoutput report payloadを固定済み |
| SPI calibration | required | done | `0x10` read、`0x6020-0x6037`のfactory calibrationはunit_047 / unit_048とsource-audit fixtureで固定済み。IMU modeから独立する |
| Bumble / transport | not applicable | not applicable | transport bytesの受け渡しとBumble APIは変更しない |
| OS / driver / adapter | not applicable | not applicable | 内部session寿命とlocal/fake transport testが主対象。新しいadapter仮定を追加しない |

### 5.1 監査値

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| IMU mode request | subcommand `0x40` payload first byte | source fact / implementation fact | MissionControl `switch_controller.hpp`, `emulated_switch_controller.cpp`, local parser/tests | stable session command |
| disabled mode | `0x00` | implementation fact / implementation policy | MissionControl `NullMotionPacker` | 36 byte zero blockへ変更する |
| standard mode | `0x01` | implementation fact | MissionControl `StandardMotionPacker`, unit_047 | existing wire bytesを維持 |
| quaternion modes | `0x02-0x05` | implementation fact | MissionControl `QuaternionMotionPacker`, unit_047 | existing packing mode 2を維持 |
| standard IMU block | 3 × accel XYZ + gyro XYZ, Int16LE | source fact / implementation fact | source-audit fixture, `spec/initial/protocol.md` | stable |
| quaternion IMU block | accel 3 sample、signed 21-bit 3成分、11-bit ms timestamp、sample count `3` | implementation fact / hardware observation | MissionControl、unit_047、Switch 2実機観測 | Pro Z軸で確認済み |
| factory calibration read | subcommand `0x10`, SPI `0x6020-0x6037` | source fact / implementation fact | unit_047 / unit_048 | mode状態を変更しない |
| Joy-Con物理軸 | 未確定 | unverified hypothesis | Joy-Con実機で観測手段なし | 軸反転を追加しない |

## 6. 振る舞い仕様

### 6.1 状態の所有と寿命

| 状態 | 所有者 | 生成 | 破棄 / reset | 禁止する所有者 |
|---|---|---|---|---|
| fixed identity / capability / calibration | `ControllerProfile` | gamepad config構築時 | gamepad object破棄時 | `InputState`, protocol session |
| virtual SPI bytes | `VirtualSpiFlash` | profileから構築時 | profile / responder破棄時 | IMU mode state |
| button / stick / raw IMU 3 frame | `InputStateStore` | gamepad object構築時 | public update、disconnect neutral | protocol session |
| report / IMU / vibrationのhost要求状態 | connection-scoped `SwitchHidSession` | 新しいHID接続generation開始時 | disconnect / close / failed connection | `ControllerProfile`, `InputStateStore`, responder-local hidden state |
| quaternion orientation / previous report time | session内のIMU encoding state | quaternion epoch開始時 | accepted `0x40`、disconnect、close | `InputReportBuilder`, global singleton |
| report timer / reply queue / holdoff | `ReportLoop` | report loop構築時 | report loop停止時 | IMU encoder |
| Bluetooth / L2CAP connection | `HidDeviceTransport` | transport connection開始時 | disconnect / close | protocol value object |

新しいsessionは、transportの`connected`確定後、最初のoutput report処理とReportLoop開始より前に作る。同じ`SwitchGamepad`をclose後に再openした場合も、前回のhost要求状態を引き継がない。

### 6.2 IMU入力値モデル

| 境界 | canonical value | 変換規則 |
|---|---|---|
| public `IMUFrame` / `InputState` | accel XYZ + gyro XYZのraw signed int16、3 frame | 現行public契約を維持 |
| `gyro_rate()` convenience | rad/sから共通既定gyro calibrationでrawへ変換 | `0.070 dps/raw`、clampしない |
| `accel_g()` convenience | Gから共通既定accelerometer calibrationでrawへ変換 | `1/4096 G/raw`、clampしない |
| standard wire | raw 3 frame | 校正で再変換せずInt16LEで格納 |
| quaternion wire | raw gyro 3 sampleをactive profile calibrationでrad/sへ戻す | 3 sampleをreport間隔の3等分として時系列順に次姿勢へ反映 |
| quaternion acceleration | raw accel 3 sample | センサーフュージョンに使わずpacking mode 2の各位置へ保持 |

`InputState`にhost IMU mode、quaternion、clock、profile calibrationを保持させない。同じraw 3 frameを、connection sessionが持つmodeに応じてwire encoderが表現する。

### 6.3 mode遷移

| 現在mode | `0x40` 入力 | 次mode | IMU encoding state | ACK後のperiodic IMU block |
|---|---:|---|---|---|
| 未指定 / disabled | `0x00` | disabled | identity / no previous time | 36 byte zero |
| any | `0x01` | standard | quaternion状態を破棄 | raw 3 frame |
| any | `0x02-0x05` | quaternion | identity / no previous timeで新epoch | packing mode 2 |
| same quaternion mode | 同じmode | same quaternion mode | identity / no previous timeで新epoch | identityから再開 |
| any | unsupported | 変更なし | 変更なし | 従前modeを維持 |

mode未指定はdisabledと同じ出力にする。`imu_enabled` booleanをmodeと別に保持せず、`mode != 0x00`から導出する。

### 6.4 subcommandと送信順序

acceptedな`0x40`は次の1イベントとして扱う。

1. payload modeをprofile capabilityで検証する。
2. host-requested session stateを新modeへ遷移させる。
3. IMU encoding epochを新modeに合わせて初期化する。
4. `0x21` ACKをreply queueへ入れる。
5. ACKを新modeで生成される最初のperiodic `0x30`より先に送る。

`0x40`受信前に生成を開始したperiodic reportは旧modeで完了してよい。`0x40`処理完了後に生成するreportは新modeに統一する。session遷移、reply queue追加、periodic report生成を、接続generationの同一直列化境界で処理する。

### 6.5 IMU wire生成

wire生成は、現在状態を暗黙に更新するobject methodではなく、必要な入力と次状態を明示する。内部名称は実装前に確定するが、契約は次の形とする。

```python
result = encode_imu_block(
    state=current_imu_encoding_state,
    mode=current_host_imu_mode,
    frames=input_state.imu_frames,
    profile=controller_profile,
    now_ns=report_time_ns,
)

motion_bytes = result.block
next_imu_encoding_state = result.state
```

- 引数objectは変更しない。
- 同じstate、mode、frames、profile、`now_ns`は同じresultを返す。
- 初回quaternion reportのelapsed timeは`0`とする。
- clockが後退した場合のelapsed timeは`0`とする。
- quaternionは更新後に正規化する。
- 方向計算を表す内部関数名に`integrate`を既定採用しない。数学手段ではなく「前姿勢と角速度sampleから次姿勢を得る」責務を名前で表す。

### 6.6 SPIとsessionの独立

- subcommand `0x10` SPI readは`VirtualSpiFlash`からbytesを返すだけで、host-requested session stateとIMU encoding stateを変更しない。
- subcommand `0x40`はIMU modeとIMU encoding epochだけを変更し、`VirtualSpiFlash`、`ControllerProfile`、`InputStateStore`を変更しない。
- quaternion変換はactive profileのgyro calibrationを読むが、calibration自体はsession stateへ複製しない。

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | mode `0x01`が現行のraw 3 frame bytesを変えず生成する | characterization | unit | no | expected-green characterization。異なる3 frameの36 bytesを明示fixtureで固定 |
| refactor-skipped | mode `0x02-0x05`が現行のidentity、正負Z、3 sample、packing mode 2 bytesを維持する | characterization | unit | no | expected-green characterization。4 mode共通の36 byte fixtureと既存のidentity / 正負Z / 3 sample testsを確認 |
| refactor-done | 同じIMU encoding state、frame、profile、時刻が同じ36 byte blockと次状態を返す | new | unit | no | immutable state / resultと明示時刻のpure encoderを追加。現行packerは互換wrapperへ縮小 |
| refactor-skipped | `InputReportBuilder`が同じinput、IMU block、timerから同じ49 byte reportを返す | regression | unit | no | 完成済み36 byte blockの明示配置経路を追加。legacy session / clock経路の削除はconnection session切替itemで行う |
| todo | standard modeが3つのraw frameを校正変換せずInt16LEで保持する | regression | unit | no | public raw API契約 |
| todo | quaternion modeがactive profile calibrationでraw gyro 3 sampleを角速度へ戻し、各3 sampleが次姿勢に寄与する | regression | unit | no | accel 3 sampleもそのまま保持 |
| todo | quaternion生成の初回時刻差とclock後退を`0`とし、入力stateを変更しない | edge | unit | no | 時刻上限は追加しない |
| todo | 初期sessionとmode `0x00`が36 byteゼロのIMU blockを生成する | new | unit | no | 現行raw fallbackをsource-backed null behaviorへ修正 |
| todo | `0x40 01`がACKされ、次のperiodic reportがstandard raw形式になる | regression | integration | no | fake transport |
| todo | `0x40 02-05`がACKされ、次のperiodic reportがquaternion形式になる | regression | integration | no | 3 profileのmode capabilityを維持 |
| todo | acceptedな同mode再要求が姿勢と前回時刻を初期化する | regression | unit | no | one-shot reset flagを使わない |
| todo | standard / quaternion / disabled間の遷移が次のepochへ姿勢を持ち越さない | new | unit | no | mode遷移表を固定 |
| todo | 未対応modeが例外となり、mode、姿勢、前回時刻を変更しない | edge | unit | no | profile capabilityで検証 |
| todo | `0x40` ACKが新modeの最初のperiodic `0x30`より先に送られる | regression | integration | no | fake transportでreport順序を検査 |
| todo | disconnect / close後の新接続がIMU mode、vibration、report mode、quaternion状態を引き継がない | new | integration | no | 同じ`SwitchGamepad`とfake transport factoryで接続generationを更新 |
| todo | disconnect時に`InputStateStore`は従来どおりneutralへ戻り、profile / SPI bytesは変わらない | regression | integration | no | session寿命とgamepad寿命の分離 |
| todo | `0x10` SPI readの前後でIMU modeとIMU encoding stateが変わらない | regression | unit | no | SPIとsessionの独立 |
| todo | `0x40`の前後でfactory calibration bytesとraw `InputState` が変わらない | regression | unit | no | modeと値モデルの独立 |
| todo | public raw / rad/s / G helperの現行契約を維持する | regression | unit | no | public value API変更なし |
| todo | `SwitchGamepad.imu()`がstate update APIとして現行契約を維持する | regression | integration | no | 接続不要、即時送信の保証なし |
| todo | diagnosticsがaccepted IMU mode、encoding format、connection generationを記録し、reset flagの内部用語を公開しない | new | integration | no | 値そのものは記録しない |
| deferred | Pro Controllerの正負Zが実機で反映される | regression | hardware | yes | unit_047で確認済み。wire fixture差分がない限り再実行しない |

## 8. 設計メモ

### 8.1 論理アクター

```text
Switch host
  ↓ output report / subcommand
HidDeviceTransport
  ↓ bytes
OutputReportParser
  ↓ parsed command
SwitchHidSession
  ├─ host-requested state
  ├─ IMU encoding state
  └─ subcommand result / next session state
       ↓ reply queue
ReportLoop
  ├─ InputStateStore snapshot
  ├─ explicit report time
  └─ IMU wire result
       ↓
InputReportBuilder
       ↓ 0x30 bytes
HidDeviceTransport
       ↓
Switch host
```

`SwitchHidSession`は論理アクター名であり、必ずしも独立async taskとして実装しない。必要な契約は、接続generation単位の状態所有と、subcommand / periodic eventの直列化である。

### 8.2 内部型の方針

- wire値を表すmodeはraw `int`の分岐に散らさず、内部enumまたは同等のvalue objectで分類する。
- `imu_enabled`は独立mutable fieldにせずmodeから導出する。
- quaternionとprevious timeはimmutable stateにし、wire生成結果が次stateを返す。
- `SubcommandResponder`はreply bytes生成とsession遷移の結果を返し、hidden mutable sessionを所有しない。
- `InputReportBuilder`は完成した36 byte IMU blockを受け取り、report全体の配置だけを担当する。
- profile capabilityとcalibrationは参照だけとし、session stateへ複製しない。

### 8.3 Tidy decision

```text
Tidy decision:
- classification: mixed
- action: split
- reason: mode 0x01 / 0x02-0x05のwire回帰を保つ責務分離と、disabled出力・接続generation・ACK順序の観測可能な修正を同じTDD itemに混ぜない。
- verification: characterization unit tests、pure encoding unit tests、fake transport integration testsを順に実行する。
```

実装は次の分割を基本とする。

1. 現行のmode `0x01` / `0x02-0x05`のcharacterization testを追加する。
2. 明示state / explicit timeのIMU wire生成へ置き換え、既存wire fixtureをgreenに保つ。
3. connection-scoped sessionとmode遷移を導入する。
4. disabledゼロ出力、再接続reset、ACK順序を個別のbehavior itemとして実装する。
5. green後に命名、型配置、fixture重複を整理する。

### 8.4 内部互換方針

次は削除またはsignature変更を許容する。

- `SubcommandSessionState`
- `_ImuSessionState`
- `consume_imu_mode_reset_request()`
- `QuaternionMotionPacker`
- `InputReportBuilder(..., session_state=..., clock_ns=...)`
- testsからの内部fieldへの直接依存

次は互換を維持する。

- public import surface
- `SwitchGamepad` / `ProController` / `JoyConL` / `JoyConR`のpublic API
- `IMUFrame` / `InputState`のvalue contract
- mode `0x01`のraw 3 frame bytes
- mode `0x02-0x05`のpacking mode 2 bytesと正負方向
- factory SPI calibration bytes

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/session.py` | new | connection-scoped host state、IMU encoding state、mode遷移 |
| `src/swbt/protocol/imu_report.py` | new | explicit state / explicit timeの36 byte IMU wire生成 |
| `src/swbt/protocol/motion.py` | delete | stateful `QuaternionMotionPacker`を置き換える |
| `src/swbt/protocol/input_report.py` | modify | session / clock依存を削除し、完成IMU blockを配置する |
| `src/swbt/protocol/subcommand.py` | modify | hidden mutable sessionとone-shot reset flagを削除し、遷移結果を返す |
| `src/swbt/gamepad/output.py` | modify | parsed commandをconnection sessionへ渡し、replyを直列化境界でqueueする |
| `src/swbt/gamepad/runtime.py` | modify | connection generationごとのsession生成 / 破棄 |
| `src/swbt/report_loop.py` | modify | explicit report time、session状態更新、ACK優先を同一送信境界で扱う |
| `tests/unit/test_input_report.py` | modify | pure builderとwire regression |
| `tests/unit/test_subcommand_responder.py` | modify | mode遷移結果と状態不変性 |
| `tests/unit/test_imu_report.py` | new | pure IMU encoding、値変換、姿勢、bit packing |
| `tests/unit/test_report_loop.py` | modify | session更新とreply優先 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | connection generation、mode遷移、ACK / periodic順序 |
| `spec/initial/architecture.md` | modify | connection session actorと状態所有 |
| `spec/initial/protocol.md` | modify | disabled / standard / quaternion遷移とIMU wire生成契約 |
| `spec/initial/lifecycle.md` | modify | session生成 / 破棄とreconnect reset |
| `spec/initial/testing.md` | modify | pure IMU encodingとfake connection generation tests |
| `docs/api.md`, `docs/usage.md`, `docs/agent-brief.md` | modify | public APIは不変のまま、mode自動切替と内部状態寿命の説明を追従 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | pass | 27 passed。IMU mode、packing mode 2、factory calibrationの既存根拠fixtureを確認 |
| `uv run pytest tests/unit/test_input_report.py::test_imu_mode_01_preserves_three_distinct_raw_frames -q` | pass | 1 passed。mode `0x01`の異なるraw 3 frameをInt16LE 36 bytesで固定 |
| `uv run pytest tests/unit/test_input_report.py -q` | pass | quaternion mode共通fixture、identity、正負Z、3 sampleと既存input report回帰を確認 |
| `uv run pytest tests/unit/test_imu_report.py -q` | red | collection error。`swbt.protocol.imu_report` が未実装の`ModuleNotFoundError`を確認 |
| `uv run pytest tests/unit/test_imu_report.py tests/unit/test_input_report.py -q` | pass | 54 passed。明示state / timeの決定性と既存wire bytesを確認 |
| `uv run ruff format --check src/swbt/protocol/imu_report.py src/swbt/protocol/motion.py tests/unit/test_imu_report.py` | pass | 3 files already formatted |
| `uv run ruff check src/swbt/protocol/imu_report.py src/swbt/protocol/motion.py tests/unit/test_imu_report.py` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit/test_input_report.py::test_input_report_builder_places_an_explicit_imu_block_deterministically -q` | red | `imu_block` が未対応の`TypeError`を確認 |
| `uv run pytest tests/unit/test_input_report.py -q` | pass | 54 passed。明示IMU blockの決定的配置とlegacy回帰を確認 |
| `uv run ruff format --check src/swbt/protocol/input_report.py tests/unit/test_input_report.py` | pass | 2 files already formatted |
| `uv run ruff check src/swbt/protocol/input_report.py tests/unit/test_input_report.py` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `git diff --no-index --check -- NUL spec/wip/unit_049/IMU_SESSION_AND_ENCODING_REDESIGN.md` | pass | 新規未追跡ファイルにwhitespace errorなし |
| `rg -n "\\[(?:TO)(?:DO)\\]|(?:T)(?:BD)|(?:x)(?:xx)" spec/wip/unit_049` | pass | 本番用placeholderの残存なし |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。このunitは既存source / hardware observationとlocal unit / fake transportで実装する |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。wire fixture差分や新しい実機仮説が出た場合は、明示承認、対象 adapter、command、cleanup planを確認する |
| log / artifact | unit / integration test output、git diff |
| cleanup | なし |

## 12. 先送り事項

- custom profile calibrationと`IMUFrame.gyro_rate()` / `accel_g()`の物理単位契約を完全にprofile-awareにするpublic APIは別unitで扱う。現行helperは共通既定校正のconvenience APIとして回帰させる。
- quaternion姿勢更新の長時間gap上限、noise、drift、加速度fusionは根拠とuse caseが必要なため別unitにする。
- Joy-Con L/Rの物理軸方向は実機検証手段がないため未検証のまま維持する。
- unit_047のPro Controller実機回帰は、wire fixtureが一致する限り再実行しない。差分が出た場合だけ`hardware-harness`の承認境界へ戻す。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test Listの初期案を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件と未実行理由を記録した
- [ ] characterization testで現行wire bytesを固定した
- [ ] explicit state / explicit timeのIMU wire生成を実装した
- [ ] connection-scoped sessionとmode遷移を実装した
- [ ] one-shot reset flagとstateful builder依存を削除した
- [ ] disabled、standard、quaternionのmode分岐を実装した
- [ ] ACKとperiodic reportの順序をfake transportで固定した
- [ ] close / reconnectでhost-requested stateを引き継がないことを固定した
- [ ] public IMU APIとexisting wire fixtureの回帰を確認した
- [ ] initial designとpublic docsを実装結果へ追従させた
- [ ] standard gateの結果を記録した
