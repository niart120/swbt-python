# Protocol handshake 分離 仕様書

## 1. 概要

### 1.1 目的

HID link 接続から protocol ready または初期化失敗まで続く protocol handshake を、
private `ProtocolHandshake` として `ControllerRuntime` から分離する。

`ProtocolHandshake` は自動 neutral 送信 task、phase 変更通知、handshake outcome を
所有する。`SwitchHidSession`、`OutputReportDispatcher`、`ReportSender` は
`ControllerRuntime` が引き続き所有し、初期化 session は既存 instance を借用する。
protocol ready 後は handshake を破棄し、同じ dispatcher、protocol state、sender を
通常の接続処理が継続利用する。

独立した `HandshakeReportPump` component は作らない。`ReportLoop` は protocol ready 後の
Periodic controller だけが所有する固定 deadline scheduler に限定する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | handshake 送信を `ReportLoop` から分離し、Direct が `ReportLoop` を所有しない構造へ変更する | `https://github.com/niart120/swbt-python/issues/133` |
| 親 Issue | 内部構造を責務境界に沿って整理する | `https://github.com/niart120/swbt-python/issues/114` |
| 先行 refactor | reporting mode ごとの入力状態確定規則を集約済み | `https://github.com/niart120/swbt-python/issues/129` |
| current implementation | `ControllerRuntime` が handshake task、ready / failure event、protocol state 更新通知を個別に所有する | `src/swbt/gamepad/runtime.py` |
| current implementation | `ReportLoop` が ready 前 neutral、Direct ready 後停止、Periodic scheduling を兼ねる | `src/swbt/report_loop.py` |
| completed spec | link connected と protocol ready の境界、handshake 中の送信規則 | `spec/complete/unit_069/CONTROLLER_HANDSHAKE_READINESS.md` |
| design discussion | protocol handshakeをlink全体へ広げず、ready / failedで終了する期限付きcomponentとして導入する | conversation |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| `ControllerRuntime` | HID control / interrupt channel が接続する | fresh `ProtocolHandshake` を開始し、自動送信taskと一時的outcomeを直接管理しない | transport lifecycleと公開connection stateはRuntimeに残す |
| Switch host | link接続後、最初の有効なsubcommandを送る | bootstrap neutralの1秒再送を停止し、借用中のdispatcherがreplyする | protocol bytesとrollback規則を変えない |
| Switch host | supported `0x03 30` を要求する | replyがtransportに受理された後、readyまでneutralを設定周期で送る | ready前の利用者stateを送らない |
| 接続API利用者 | supported report modeとnonzero player lightsが揃うまで待つ | 自動送信taskの停止・回収後にhandshake outcomeがreadyとなり、接続APIが完了する | fixed subcommand setや固定順序を要求しない |
| Periodic controller利用者 | ready前にlocal input stateを準備する | ready前はneutral、handshake終了後の最初の通常reportからcurrent stateが送られる | ready前stateを失わない |
| Direct controller利用者 | protocol ready後に入力操作する | handshake終了後は自動`0x30` taskを持たず、明示操作だけがreportを送る | 全lifecycleで`ReportLoop`を生成しない |
| Switch host | ready後にoutput reportを送る | handshakeを経由せず、既存dispatcherがreplyとsession state更新を継続する | dispatcherをhandshakeとともに破棄しない |
| diagnostics利用者 | timeout、早期disconnect、送信失敗が起きる | task leakを残さず、既存のprotocol stateとdiagnosticsから原因を確認できる | hardware observationと公開ready条件を混同しない |

## 2. 対象範囲

- private `ProtocolHandshake` の追加。
- link接続からready / failed / stopまでの自動送信taskとhandshake outcomeの集約。
- `SwitchHidSession`、`OutputReportDispatcher`、`ReportSender`を借用する明示的な境界。
- 初期化中だけtransport output callbackを`ProtocolHandshake`経由で
  dispatcherへ渡す処理。
- ready / failed後にhandshakeを停止・破棄し、ready後のoutput reportを
  同じdispatcherへ直接渡すhandoff。
- protocol readyの通知前に自動送信taskを停止・回収する順序。
- Periodic controllerのready後にだけ`ReportLoop`を生成・開始する処理。
- Direct controllerで`ReportLoop`を生成しない処理。
- `ReportLoop`から`is_user_input_enabled`、`stop_when_user_input_enabled`、
  handshake neutral分岐を削除する。
- handshakeとready後Periodicが共有する自動input holdoffを一か所で維持する処理。
- close、timeout、caller cancellation、early disconnect、output処理失敗、
  自動送信失敗時のhandshake cleanup。
- reopen時のfresh handshake、fresh protocol state、fresh sender関連状態。
- 6具象controllerを使ったfake transport回帰検証。
- 関連する初期設計文書の責務・lifecycle記述の更新。

## 3. 対象外

- ready後も生存する`ControllerProtocolSession`への拡張。
- `SwitchHidSession`、`OutputReportDispatcher`、`ReportSender`、transportのownershipを
  handshakeへ移すこと。
- ready後のoutput report、Direct入力、Periodic schedulingをhandshakeに扱わせること。
- 独立した`HandshakeReportPump`、汎用scheduler、state machine library、
  strategy / manager階層の追加。
- protocol-ready predicateの変更。
- handshake成功条件として固定subcommand集合または固定順序を要求すること。
- bootstrap retry間隔1秒、report period既定値、reply後300 ms holdoffの値・要否・
  適用範囲の変更。
- `0x21` / `0x30`の共有timer、send lock、IMU encoding、reply順序の変更。
- HID report、subcommand、SPI、rumbleのbyte layout変更。
- transport open、advertising、pairing、active reconnect、disconnect requestの
  ownership変更。
- 接続操作全体のtimeout budget変更。
- public connection API、公開型階層、利用者向け入力semanticsの変更。
- `ProtocolHandshake`のpublic export。
- 300 ms holdoffのA/B実機検証。必要性の再評価は別作業単位で扱う。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/complete/unit_020/STRUCTURAL_REFACTOR_BOUNDARIES.md`
- `spec/complete/unit_049/IMU_SESSION_AND_ENCODING_REDESIGN.md`
- `spec/complete/unit_065/PERIODIC_DEADLINE_SCHEDULER.md`
- `spec/complete/unit_069/CONTROLLER_HANDSHAKE_READINESS.md`
- `spec/complete/unit_070/DIAGNOSTICS_AND_UNUSED_PATHS_CLEANUP.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | unit_006、unit_049、unit_069の監査済みbuilder、parser、session遷移を変更せず、既存fixtureとbyte assertionを維持する |
| report timing | required | done | bootstrap 1秒、設定済みreport period、reply後300 ms holdoffを既存値のままcharacterizationする。300 msの必要性判断は本作業に含めない |
| Bumble / transport | required | done | transport callbackと`send_interrupt()`の契約を変更せず、初期化中とready後の委譲先だけを切り替える |
| OS / driver / adapter | required | todo | task ownershipとcallback handoff変更後の完了gateとして、明示承認付き実機runで既存条件を再確認する |

### 5.1 監査結果

| 項目 | 値 / 判断 | 根拠分類 | source | status |
|---|---|---|---|---|
| link connected | HID control / interrupt channelが利用可能であり、public protocol readyではない | implementation fact / hardware observation | unit_069、`src/swbt/transport/bumble.py` | established |
| protocol ready | supported report modeとnonzero player lightsが揃い、対応replyがtransportに受理済み | implementation policy / hardware observation | unit_069、`SwitchHidSessionState.protocol_ready` | unchanged |
| bootstrap | link直後にneutralを即時送信し、有効なsubcommand未受信中だけ1秒間隔で再送 | implementation policy / hardware observation | unit_069 | unchanged |
| requested report mode | supported `0x03 30` reply後からreadyまでneutralを設定周期で送信 | implementation policy / hardware observation | unit_069 | unchanged |
| shared sender | `0x21`と`0x30`が同じlock、timer、session IMU encodingを使う | implementation fact | unit_006、unit_049、`src/swbt/report_loop.py` | unchanged |
| reply後holdoff | 自動`0x30`を300 ms抑制する | implementation fact / unseparated compatibility policy | unit_006、`src/swbt/report_loop.py` | preserved, necessity not asserted |
| ready後output report | ready到達後もrumble、subcommand、session state更新を処理する | implementation fact | `src/swbt/gamepad/output.py`、integration tests | dispatcherを借用する根拠 |
| 長寿命protocol session | 初期化componentがready後もdispatcher、sender、stateを所有すべき | inference | design discussion | Runtimeとの責務重複を招くため不採用 |

### 5.2 未解決事項

- 300 ms holdoffは既存互換策として維持するが、必要性とready後Periodicへの適用範囲は
  本仕様で確定しない。後続A/B検証の対象とする。
- 別firmware、別adapter、別OSに対するhandshake順序の一般化は行わない。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| handshake生成 | HID linkが接続する | freshなtask、wake通知、attempt count、outcomeを持つhandshakeを生成する | protocol state、dispatcher、senderは既存instanceを借用する |
| bootstrap開始 | handshakeを開始する | 自動送信taskを1個だけ開始し、neutralを直ちに送る | Runtimeは公開状態を`initializing`にする |
| bootstrap retry | 有効なsubcommandをまだparseしていない | neutralを1秒間隔で再送する | 多重起動とburst再送をしない |
| bootstrap stop | 最初の有効なsubcommandをparse | bootstrap再送を停止し、借用中dispatcherが当該subcommandへreplyする | replyと自動inputを共有senderで直列化する |
| subcommand間待機 | subcommand受信済み、supported report mode未設定 | 自動neutralを送らず、次のprotocol state更新または停止を待つ | 初期化taskはwake可能な待機状態に置く |
| requested report mode | supported `0x03 30` replyがtransportに受理済み、ready前 | 既存report periodでneutralを送る | 利用者stateを送らない |
| ready遷移 | ready predicateを成立させたreplyがtransportに受理済み | 自動送信taskを停止・回収した後にoutcomeをreadyとする | Periodic開始がhandshake送信を追い越さない |
| ready handoff | Runtimeがready outcomeを受け取る | handshakeを破棄し、後続output reportを既存dispatcherへ直接渡す | in-flight payloadを欠落・重複処理しない |
| Periodic開始 | ready handoff後のPeriodic controller | `ReportLoop`を生成・開始し、最初の通常reportからcurrent stateを送る | fixed-deadline schedulingを維持する |
| Direct ready | ready handoff後のDirect controller | 自動input taskを持たず、明示操作だけを送る | `ReportLoop`は全lifecycleで生成しない |
| ready後subcommand | handshake破棄後にSwitchがoutput reportを送る | Runtimeが同じdispatcherへ直接渡し、replyとstate更新を継続する | 新しいprotocol stateやsenderを作らない |
| reply/input競合 | 自動inputとsubcommand replyが競合する | 共通senderのlock、timer、既存holdoffで順序を維持する | holdoff値は変更しない |
| 初期化失敗 | malformed / unsupported subcommandまたはreply / 自動送信失敗 | outcomeをfailedとして待機APIを起こし、自動送信taskを回収する | Runtimeが公開connection failureへ変換する |
| early disconnect | ready前にlinkが切断する | outcomeをfailedとしてtimeout前に待機APIを起こし、handshakeを停止する | half-ready接続を成功にしない |
| timeout / cancellation | 接続操作のdeadline到達またはcaller cancellation | Runtimeが既存budgetを適用し、handshakeを停止してcleanupする | timeoutをlinkとhandshakeで二重消費しない |
| close | opened、initializing、readyのいずれかでclose | activeなhandshake、ReportLoop、transportを既存規則に沿って停止し、taskを残さない | trailing neutralとdisconnect規則を維持する |
| reopen | close後に再度open / connectする | fresh protocol state、sender関連状態、handshakeを使う | 前回のevent、outcome、attempt countを再利用しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | link接続直後にPeriodic / Directの両方がbootstrap neutralを1件送る | regression | integration | no | 6具象controllerをparameterizeする |
| todo | 有効なsubcommand未受信中だけbootstrap neutralを1秒間隔で再送する | regression | unit / integration | no | fake clockまたは明示wakeで壁時計flakeを避ける |
| todo | 最初の有効なsubcommandをparseするとbootstrap再送を停止し、同じdispatcherがreplyを返す | regression | unit / integration | no | dispatcherとsenderのidentityを切り替えない |
| todo | supported report mode未設定のsubcommand間では自動neutralを送らない | regression | integration | no | bootstrapとrequested-report-mode phaseを区別する |
| todo | supported `0x03 30` reply受理後、readyまではneutralを設定周期で送る | regression | integration | no | ready前の利用者stateをwireへ出さない |
| todo | readyを成立させるreply受理後、自動送信taskを回収してからready outcomeを返す | new | unit / integration | no | task完了と`protocol_ready` traceの順序を観測する |
| todo | ready handoff中に到着したoutput reportを欠落・重複させず1回だけ処理する | edge | unit / integration | no | 初期化中委譲から直接dispatcher委譲への切替を検証する |
| todo | ready後のoutput reportにも同じdispatcher、protocol state、senderがreplyとstate更新を継続する | regression | integration | no | handshakeだけを破棄する |
| todo | Periodicはready後の最初の通常reportからcurrent user stateを送る | regression | integration | no | ready前に準備したstateを保持する |
| todo | Directはopen、initializing、readyの全段階で`ReportLoop`を所有せず、ready後の自動`0x30`が0件になる | regression | unit / integration | no | 3 Direct具象controllerをparameterizeする |
| todo | `0x21` replyとhandshake / Periodic `0x30`が共有lockとtimerを使い、既存holdoffを維持する | characterization | unit / integration | no | 値の要否ではなく現行挙動を固定する |
| todo | 自動送信失敗はfailed outcomeを返し、自動送信taskを残さない | edge | unit / integration | no | close中のrecoverable errorと区別する |
| todo | ready前disconnectはtimeoutを待たず接続失敗となり、handshakeを残さない | edge | integration | no | pairing / active reconnect routeを確認する |
| todo | closeとcaller cancellationはinitializing中のtaskを回収する | edge | unit / integration | no | asyncio task leak warningを出さない |
| todo | reopenではfresh protocol state、fresh handshake、fresh sender timer / holdoff状態を使う | regression | integration | no | 前回outcomeとwake通知を再利用しない |
| todo | `pair()` / `connect()` / `reconnect()` / `try_*()` / `create_profile()`が従来のprotocol-ready境界を維持する | regression | integration | no | 公開APIの成功・timeout・failureを確認する |
| todo | fixed-deadline schedulerが最新state、overrun skip、no burst catch-upを維持する | regression | unit | no | unit_065の決定的testを維持する |
| todo | Periodic Pro Controllerのactive reconnectがready後の通常送信とclean closeまで完了する | characterization | hardware | yes | adapter、command、cleanupの明示承認後に実行する |
| todo | Direct Pro Controllerのactive reconnectがready後1秒以上、自動`0x30`なしでclean closeする | characterization | hardware | yes | 既存hardware testを再利用する |
| todo | Joy-Con L/Rのfresh pairingまたはactive reconnectが追加の利用者入力なしでreadyへ到達する | characterization | hardware | yes | profile非依存性をfake差分review後、実行範囲を決める |

## 8. 文書検証計画

公開README、利用者向けdocs、公開API docstring、release notesは変更しない。
初期設計文書は本仕様、実装call graph、既存の完了仕様と照合する。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/architecture.md` | maintainerがRuntime、期限付きhandshake、sender、ReportLoopの所有関係を把握する | 本仕様 §2 / §9 | `uv run --group docs mkdocs build --strict` | todo | 借用dependencyとownershipを区別する |
| `spec/initial/lifecycle.md` | maintainerがlink、handshake、ready handoff、closeの順序を追う | 本仕様 §6 / §9 | `uv run --group docs mkdocs build --strict` | todo | ready後にhandshakeが残らないことを明記する |
| `spec/initial/protocol.md` | maintainerがreplyと自動inputの共有sender境界を確認する | 本仕様 §5 / §9 | `uv run --group docs mkdocs build --strict` | todo | 300 msの必要性を確定事項として拡張しない |
| `spec/initial/testing.md` | maintainerがfake / hardware gateを選ぶ | 本仕様 §7 / §12 | `uv run --group docs mkdocs build --strict` | todo | handoff競合、task cleanup、6具象controllerを反映する |

## 9. 設計メモ

### 9.1 選択した境界

`ProtocolHandshake`は、link connectedからready / failed / explicit stopまでだけ生存する。
ここでhandshakeは固定subcommand sequenceではなく、link connectedからprotocol readyまでの
期限付き処理を表す。ready後のprotocol処理を所有しない。

```text
ControllerRuntime
  ├─ HidDeviceTransport
  ├─ InputStateStore
  ├─ SwitchHidSession
  ├─ OutputReportDispatcher
  ├─ ReportSender
  ├─ ProtocolHandshake  [initializing中だけ]
  │    └─ private automatic report task
  └─ ReportLoop                     [Periodicかつready後だけ]
```

handshakeはstate、dispatcher、senderの参照を借用する。これらを生成・破棄せず、
ready / failed後もRuntimeが同じinstanceを継続利用する。

### 9.2 lifecycleと所有状態

handshakeが所有する状態は次に限定する。

- 自動送信task。
- taskを起こすstate-change通知。
- bootstrap attempt count。
- `pending` / `ready` / `failed`の期限付きoutcome。
- task停止・回収に必要な内部状態。

公開`connection_state`、transport lifecycle、protocol state、sender timer、dispatcher、
Periodic / Directのready後処理は所有しない。

### 9.3 自動送信task

独立したphase enumは追加しない。送信状態は借用中の`SwitchHidSessionState`と
最初の有効なsubcommand受信状態から導出する。

| 初期化状態 | 自動送信 |
|---|---|
| 有効なsubcommand未受信 | neutralを即時送信し、1秒間隔で再送 |
| subcommand受信済み、supported report mode未設定 | state更新または停止を待つ |
| supported report mode、protocol ready前 | neutralを設定済みreport periodで送信 |
| protocol ready / failed / stop | taskを終了・回収する |

独立した`HandshakeReportPump`は作らず、このcoroutineを`ProtocolHandshake`のprivate実装にする。

### 9.4 output reportの委譲とhandoff

transport callbackの入口はRuntimeに残す。initializing中だけhandshakeへ委譲し、
handshakeが借用中dispatcherを呼ぶ。ready handoff後はRuntimeがdispatcherを直接呼ぶ。

```text
initializing:
  transport callback
    → ProtocolHandshake
      → shared OutputReportDispatcher

ready:
  transport callback
    → shared OutputReportDispatcher
```

Runtimeはactiveなhandshakeをlocal参照として取得してからdispatchする。ready handoffは
そのdispatch完了後に行い、1件のpayloadを初期化経路とready後経路の両方へ渡さない。
並行payloadがあり得る場合も、既存dispatcherの直列化条件を維持しながら欠落・重複を防ぐ。

### 9.5 ready遷移

ready遷移は次の順序を保証する。

```text
ready predicateを成立させるsubcommandをparse
  → replyを共有senderで送信
  → transport受理
  → protocol state確定
  → 自動送信taskを停止・回収
  → handshake outcomeをreadyにする
  → Runtimeがhandshakeを破棄
  → PeriodicだけReportLoopを生成・開始
  → Runtimeがpublic connection stateをconnectedにする
  → 接続APIが成功
```

ready後のduplicate subcommandはshared dispatcherが通常どおりreplyする。handshakeと
自動送信taskを再生成しない。

### 9.6 senderとholdoff

`ReportSender`はRuntimeが所有し、handshake、ready後`ReportLoop`、Direct入力、
trailing neutralが同じinstanceを利用する。共有lock、timer、IMU encodingを重複生成しない。

handshakeとready後Periodicの自動inputが既存holdoffを共有できるよう、holdoff状態は
自動送信経路の一か所に置く。実装候補は`ReportSender`のlock内での自動送信可否判定とする。
明示Direct入力とtrailing neutralは既存どおりholdoff対象にしない。
300 msという値と適用範囲の妥当性は本作業で変更しない。

### 9.7 不採用案

- task送信だけを独立`HandshakeReportPump`へ切り出す案は、handshake outcomeと
  ready handoffがRuntimeに残るため採用しない。
- handshakeをready後も生存する`ControllerProtocolSession`へ広げる案は、
  Runtimeとlifecycle、failure、start / stopの責務が重なるため採用しない。
- reporting全体を扱うcoordinatorやreporting mode別strategyは、本作業の境界を超えるため
  導入しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/protocol_handshake.py` | new | 期限付きoutcome、自動送信task、dispatcher委譲、stopを所有 |
| `src/swbt/gamepad/runtime.py` | modify | bootstrap fieldsを削除し、handshake lifecycle、ready handoff、ready後dispatcher委譲を調停 |
| `src/swbt/report_loop.py` | modify | ready後Periodic専用にし、handshake分岐とDirect停止条件を削除。共有自動送信holdoffの所有場所を整理 |
| `src/swbt/gamepad/output.py` | modify | handshakeから借用できる通知境界とready後直接利用を維持 |
| `tests/unit/test_protocol_handshake.py` | new | phase、outcome順序、handoff、failure、stopを決定的に検証 |
| `tests/unit/test_report_loop.py` | modify | ready後Periodic scheduler、共有sender、既存holdoffのcharacterizationへ限定 |
| `tests/unit/test_gamepad_output_dispatcher.py` | modify | 初期化中とready後で同じdispatcherが機能することを検証 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | 6具象controller、公開接続API、handoff、Direct / Periodic、cleanupを検証 |
| `tests/gamepad_factory.py` | modify | handshake導入後の内部fixture参照へ更新 |
| `spec/initial/architecture.md` | modify | Runtime、期限付きhandshake、borrowed dependency、ReportLoopの関係を更新 |
| `spec/initial/lifecycle.md` | modify | linkからready handoff、ready後、closeまでのlifecycleを更新 |
| `spec/initial/protocol.md` | modify | handshake自動送信とready後Periodicの所有者を更新 |
| `spec/initial/testing.md` | modify | handoff、task cleanup、fake / hardware gateを追加 |
| `spec/hardware-test-log.md` | modify | 承認後に実行した実機結果だけを追記 |

対象ファイルは実装時の責務確認で増減できる。新しい汎用manager、scheduler、公開moduleは
追加しない。

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_protocol_handshake.py` | not run | spec作成時点ではtest未作成 |
| `uv run pytest tests/unit/test_report_loop.py tests/unit/test_gamepad_output_dispatcher.py` | not run | sender、scheduler、dispatcher回帰 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py` | not run | 6具象controllerと公開接続API |
| `uv sync --dev` | not run | 実装完了gate |
| `uv run ruff format --check .` | not run | 実装完了gate |
| `uv run ruff check .` | not run | 実装完了gate |
| `uv run ty check --no-progress` | not run | 実装完了gate |
| `uv run pytest tests/unit` | not run | 実装完了gate |
| `uv run pytest tests/integration` | not run | 対象treeあり |
| `uv run --group docs mkdocs build --strict` | pass | spec作成時点の文書構造・リンク検証 |
| `git diff --no-index --check -- NUL spec/wip/unit_081/PROTOCOL_HANDSHAKE.md` | pass | untracked新規仕様書のwhitespace確認。差分ありを表すexit 1は成功として扱った |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for completion |
| 承認範囲 | Periodic Pro active reconnect、Direct Pro active reconnect、Joy-Con L/Rのpairingまたはreconnect、handshake自動neutral、subcommand handling、ready handoff、ready後送信、neutral close、disconnect、adapter close |
| adapter | 実行直前に利用者と確認する。過去の観測条件は`usb:0` / CSR8510 A10 / WinUSB |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象adapter、command、Switch-facing範囲、cleanup planで管理する |
| log / artifact | OS、driver、dongle identity、adapter string、Bumble version、Python version、Switch model / firmware、controller profile、reporting mode、command、result、trace、cleanupを保存する |
| cleanup | activeなhandshake / ReportLoop停止、neutral、disconnect request、transport close、adapter releaseを確認する |

fake transportと差分reviewでprofile非依存性を確認した後、Direct Joy-Con L/Rの追加実機runが
必要か判断する。実機runは`hardware-harness`を読み、実行直前にexact commandとcleanup planを
提示して明示承認を得る。

## 13. 先送り事項

- reply後300 ms holdoffの必要性、値、handshake中とready後Periodicでの適用範囲。
  source auditと実機A/Bを別作業単位で行う。
- connection単位の長寿命protocol componentや汎用session framework。
  Runtimeとの責務分割を伴うため、本作業へ含めない。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] 期限付き`ProtocolHandshake`とborrowed dependencyの境界を記録した
- [x] 独立Pumpと長寿命protocol sessionを採用しない判断を補足した
- [x] ready handoffとready後dispatcher継続利用を記録した
- [x] TDD Test Listを作成した
- [x] 既存protocol値とtimingの根拠監査状態を記録した
- [x] 実機実行条件を記録した
- [ ] red / green / refactorを完了した
- [ ] 初期設計文書を更新した
- [ ] local gateを完了した
- [ ] 明示承認付き実機gateを完了した
- [x] spec作成時点の文書検証結果と実装gateの未実行理由を記録した
