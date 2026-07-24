# CONTROLLER_HANDSHAKE_READINESS 仕様書

## 1. 概要

### 1.1 目的

`ProController`、`JoyConL`、`JoyConR` の接続成功を、HID control / interrupt
channel が開いた時点ではなく、Switch の初期 subcommand に応答し、通常入力を
受け付けられる protocol ready へ到達した時点として定義する。

`create_profile()` は protocol ready に到達してから controller object を返す。
`pair()`、`reconnect()`、`connect()` と対応する `try_*` API も同じ完了境界を使う。
Periodic / Direct の送信方式はこの境界を共有する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | subcommand sequence 完了後に利用者へ object を返し、Pro Controller / Joy-Con L / Joy-Con R を併せて設計する | conversation |
| current lifecycle | `pair()` は HID control / interrupt channel 接続だけで戻る | `src/swbt/gamepad/runtime.py` |
| current public API | concrete controller の `create_profile()` は `pair()` 後に object を返す | `spec/initial/api.md`、`src/swbt/gamepad/core.py` |
| Pro Controller 実機観測 | 初期化終盤で `0x30 00`、`0x48`、`0x21`、`0x30 01` を受信し、最後の応答後に入力反映を確認した | `spec/hardware-test-log.md`、unit_067 / unit_068 hardware artifact |
| Joy-Con 実機観測 | 初期 subcommand 応答後の SR+SL hold で Joy-Con L/R の登録を確認した | `spec/hardware-test-log.md`、`spec/complete/unit_046/HARDWARE_PROFILE_TEST_SCENARIOS.md` |
| upstream precedent | joycontrol は controller profile ごとの `0x04` trigger elapsed 値を返し、player lights 設定後を入力受付可能として待つ | joycontrol pinned source |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| profile 作成利用者 | `await ProController.create_profile(...)` | Switch が通常入力を受理できる状態になってから object が返る | L2CAP 接続だけでは返さない |
| Joy-Con 利用者 | `JoyConL` / `JoyConR` の初回 pairing | profile に合った登録用 trigger elapsed reply を返し、player assignment 完了後に object が返る | 利用者 object を先に返して SR+SL を要求しない |
| 既存 profile 利用者 | `connect()` / `reconnect()` | bonded reconnect 後の初期 subcommand sequence と player assignment を待って成功する | pairing fallback の選択規則は変えない |
| Direct 利用者 | Direct Pro / Joy-Con の `create_profile()` / `connect()` | periodic report loop に依存せず、subcommand reply により同じ ready 条件へ到達する | ready 前の利用者入力は送らない |
| diagnostics 利用者 | 接続が初期化途中で停止する | link 接続、観測済み subcommand、report mode、player lights、失敗原因を区別できる | 固定 subcommand 集合を成功条件にしない |

## 2. 対象範囲

- `ProController`、`JoyConL`、`JoyConR` と対応する Direct controller の接続完了条件。
- transport link 接続と protocol ready の内部 event 分離。
- `SwitchHidSessionState` による report mode と player lights の接続単位の状態管理。
- `0x04` trigger buttons elapsed reply の profile 対応。
- `0x30` player lights reply 送信後の ready 判定。
- `pair()`、`reconnect()`、`connect()`、`try_reconnect()`、`try_connect()`、
  `create_profile()` の完了、timeout、失敗 semantics。
- ready 前の Periodic / Direct 入力送信境界。
- fake transport による全 profile / reporting type の検証。
- Pro Controller / Joy-Con L / Joy-Con R の明示承認付き実機 gate。
- diagnostics と初期設計文書の更新。

## 3. 対象外

- firmware、Switch model、adapter、OS をまたいだ subcommand 順序の固定保証。
- `{0x02, 0x08, 0x10, 0x03, 0x04, 0x40, 0x48, 0x21, 0x30}` の
  全件受信を公開 API の契約にすること。
- Joy-Con Pair API と左右 Joy-Con の同時登録。
- amiibo、NFC、IR camera の意味実装。
- ready 後の Switch UI 画面遷移完了を自動判定すること。
- 初回実装での SR+SL input report 自動送信。profile 対応した `0x04` reply だけで
  Joy-Con の player assignment が進まない場合は、実機結果を記録して設計を再開する。
- Nintendo 非公開仕様を公式保証として扱うこと。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/complete/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/complete/unit_032/PROFILE_AWARE_SUBCOMMAND_STATE.md`
- `spec/complete/unit_046/HARDWARE_PROFILE_TEST_SCENARIOS.md`
- `spec/hardware-test-log.md`
- `tests/unit/fixtures/source_audit/switch_protocol_values.toml`

## 5. 根拠監査

### 5.1 監査結果

| 項目 | 値 | 根拠分類 | source | status |
|---|---|---|---|---|
| `0x03` | input report mode。`0x30` は standard full mode | source fact | [dekuNukem protocol notes](https://github.com/dekuNukem/Nintendo_Switch_Reverse_Engineering/blob/d2ece786a81b5b72a7ddc2742ce97a2afa7a637f/bluetooth_hid_subcommands_notes.md)、`subcommand_report_mode_session_state` fixture | stable |
| `0x04` payload layout | L、R、ZL、ZR、SL、SR、HOME の順に 7 個の UInt16LE。単位は 10 ms | source fact | dekuNukem protocol notes | stable |
| Pro Controller の登録用 `0x04` 値 | L / R を各 300 tick、残りを 0 | implementation fact | joycontrol `protocol.py`、`swbt-daemon/swbt/switch/switch_subcommand_dispatcher.c`、現行 swbt-python | established precedent |
| Joy-Con L/R の登録用 `0x04` 値 | SL / SR を各 300 tick、残りを 0 | implementation fact | [joycontrol protocol.py](https://github.com/mart1nro/joycontrol/blob/3adf0b2878b2a9677644a88eda351e122f432095/joycontrol/protocol.py) | hardware verification required |
| 現行 swbt-python の `0x04` | 全 profile に Pro Controller 用 L / R 値を返す | implementation fact | `src/swbt/protocol/subcommand.py`、`tests/unit/test_subcommand_responder.py` | profile bug candidate |
| `0x08` | Switch は接続ごとに `0x08 00` を送る | source fact | dekuNukem protocol notes | stable observation from reverse engineering |
| `0x30` payload | 下位 4 bit は点灯、上位 4 bit は点滅する player light の bitfield | source fact | dekuNukem protocol notes | stable |
| player lights 後の入力受付 | joycontrol は `0x30` reply 送信後に event を立て、`ControllerState.connect()` はその event を待つ | implementation fact | joycontrol `protocol.py` / [controller_state.py](https://github.com/mart1nro/joycontrol/blob/3adf0b2878b2a9677644a88eda351e122f432095/joycontrol/controller_state.py) | strong precedent |
| 現行 Switch 2 の Pro sequence | 終盤に `0x30 00`、`0x48`、`0x21`、`0x30 01`。最後の `0x30` reply 後に入力反映を確認 | hardware observation | `spec/hardware-test-log.md`、unit_067 / unit_068 trace と debug log | tested condition only |
| Joy-Con L 登録 | 初期 sequence の応答後に SR+SL `000030` を hold して登録成功 | hardware observation | `spec/hardware-test-log.md` 2026-07-06 / 2026-07-07 | tested condition only |
| Joy-Con R 登録 | 初期 sequence の応答後に SR+SL `300000` を hold して登録成功。`0x22` を追加観測 | hardware observation | `spec/hardware-test-log.md` 2026-07-07 | tested condition only |
| 全 profile 共通の固定 required set | firmware と profile を問わず 9 種類すべてが必須 | unverified hypothesis | stable source なし | completion gate にしない |
| `0x30` ACK | swbt-python / joycontrol は `0x80`、既存 source-audit fixture と swbt-daemon は `0xb0` | implementation fact conflict | local implementations、joycontrol | ready 判定に ACK 固定値を使わず、実装前に fixture を再監査する |

### 5.2 未解決事項

- Joy-Con L/R が profile 対応した `0x04` reply だけで、追加の SR+SL input report なしに
  nonzero player lights へ到達するかは swbt-python 実機で未検証である。
- Joy-Con の成功済み trace は SR+SL 後の player lights payload を構造化 event として
  記録していない。実装後 gate では payload と reply 完了順を記録する。
- `0x30` ACK の `0x80` / `0xb0` 差は、ready 条件から独立して再監査する。現行
  swbt-python の `0x80` は Switch 2 の成功済み sequence で受理されているが、
  cross-firmware guarantee にはしない。
- Nintendo 公式の公開 protocol 仕様は確認できていない。source fact は公開された
  reverse engineering notes の記述範囲を表す。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| link 接続 | HID control / interrupt channel が利用可能 | runtime は `initializing` になり、subcommand reply 経路を開始する | public 接続 API はまだ戻らない |
| intermediate player lights | reply 送信済みの `0x30 00` | player lights を session に記録するが ready にしない | current Switch 2 で観測済み |
| report mode | reply 送信済みの `0x03 30` | `report_mode_supported=True` を session に記録する | unsupported mode は ready にしない |
| protocol ready | 同じ session で supported report mode と nonzero player lights が揃い、対応 reply が transport に受理された | runtime を `connected` にし、待機中の接続 API を完了する | subcommand の順序は固定しない |
| duplicate player lights | ready 後に同じ `0x30` を再受信 | 通常 reply は返すが ready event は再発火しない | diagnostics は通常受信として残す |
| malformed player lights | `0x30` payload が空 | `ProtocolError` として接続初期化を失敗させる | 既存の無条件 simple ACK から変更 |
| Pro `0x04` | trigger elapsed request | L / R = 300 tick の reply を返す | 既存値を維持 |
| Joy-Con `0x04` | trigger elapsed request | SL / SR = 300 tick の reply を返す | L/R と Direct/Periodic で同じ profile policy |
| factory return | `create_profile()` が link 接続済み、protocol 初期化中 | object を返さず待機する | ready 後だけ caller が lifetime を所有 |
| success-required API | `pair()` / `reconnect()` / `connect()` | protocol ready 後だけ正常終了する | `"connected"` の意味を強化 |
| result API | `try_reconnect()` / `try_connect()` | protocol ready 後だけ `status="connected"` | handshake timeout は `"timeout"`、protocol failure は `"failed"` |
| timeout | advertising / transport connect から ready までに指定時間を超える | 1 個の deadline で失敗し、観測済み subcommand と session state を diagnostics に残して cleanup する | link と handshake で timeout を二重消費しない |
| early disconnect | link 接続後、ready 前に disconnect | 接続成功にせず失敗として待機 API を起こす | 半初期化 object を返さない |
| Periodic の ready 前入力 | 利用者が接続前に `press()` / `apply()` で state を準備済み | local state は保持するが、initializing 中の periodic / subcommand reply は neutral wire state を使う | ready 後の次回 report から利用者 state を使う |
| Direct の ready 前入力 | 接続 API と並行して利用者入力を試す | `ClosedError` を維持し、入力を送らない | internal link 接続を public connected とみなさない |
| session reset | disconnect 後の新しい接続 | report mode、player lights、ready event、観測済み subcommand を初期化する | 前回 session の ready を再利用しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `0x04` reply は Pro Controller で L / R = 300 tick を返す | regression | unit | no | 現行 byte を保持。profile 対応実装後も pass |
| green | `0x04` reply は Joy-Con L/R で SL / SR = 300 tick を返す | new | unit | no | profile parameterized。全 profile 共通 L/R 値による red 後に green |
| green | `0x30 00` は session に記録されるが protocol ready にならない | new | unit | no | simple ACK から session state へ移し、zero で ready にならないことを確認 |
| green | supported `0x03 30` と nonzero `0x30` が同じ session で揃うと ready predicate が成立する | new | unit | no | 到着順と点灯 / 点滅 bit を入れ替え、constant-false red 後に green |
| green | `0x30` reply の transport 受理前には ready event が発火しない | regression | integration | no | Direct fake send を event で停止し、受理後だけ pair 完了 |
| green | `0x30` reply の送信失敗は ready にせず接続失敗へ伝播する | edge | integration | no | session state を送信前へ戻し、pair failure と cleanup を確認 |
| green | HID channel 接続だけでは `pair()` が完了せず、state は `initializing` になる | regression | integration | no | link 接続直後に完了する red 後、link / ready event を分離 |
| green | known set の一部を省略または重複しても ready predicate が揃えば `pair()` が完了する | edge | integration | no | `0x03` / `0x30` だけで完了し、`0x30` 重複でも再発火しない |
| green | Pro / Joy-Con L / Joy-Con R の `create_profile()` は protocol ready 後だけ object を返す | new | integration | no | 全 concrete class の `pair()` 境界と factory の委譲・失敗 cleanup を確認 |
| green | Periodic / Direct の全 concrete controller が同じ ready 境界を使う | new | integration | no | 6 concrete class parameterized |
| green | Periodic の接続前 state は initializing 中に wire へ出ず、ready 後に反映される | edge | integration | no | loop は ready 後に開始し、subcommand reply prefix は neutral |
| green | Direct の input operation は link 接続後でも ready 前は失敗し、ready 後は送信できる | edge | integration | no | `ClosedError` 後、ready で送信成功 |
| green | timeout は link と handshake を含む 1 個の budget で評価される | new | unit / integration | no | advertising と reconnect+ready を外側の1 deadlineで囲み、timeout diagnostics に session state を記録 |
| green | ready 前 disconnect / unsupported subcommand は待機 API を直ちに failure で起こす | edge | integration | no | disconnect と reply failure を timeout 前に通知。unsupported は既存 protocol failure 経路を共有 |
| green | reconnect session は前回の report mode / player lights / ready を再利用しない | regression | integration | no | reopen 時の session reset に player lights / ready を追加 |
| green | `protocol_ready` は reply event より後に 1 回だけ記録される | new | integration | no | observed subcommands、profile kind、route と event 順を確認 |
| todo | Pro Controller の fresh pairing / reconnect が nonzero player lights reply 後に戻る | characterization | hardware | yes | exact sequence は assertion しない |
| todo | Joy-Con L の profile 対応 `0x04` だけで fresh pairing が完了するか確認する | characterization | hardware | yes | manual SR+SL を送らず UI と trace を確認 |
| todo | Joy-Con R の profile 対応 `0x04` だけで fresh pairing が完了するか確認する | characterization | hardware | yes | optional `0x22` は completion gate にしない |
| todo | Joy-Con L/R の active reconnect が追加の登録 input なしで ready へ戻る | characterization | hardware | yes | profile ごとに実行 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/api.md` | object を受け取った時点の利用可能条件 | 本仕様 §6 / §9 | `uv run mkdocs build --strict` | todo | 実装完了時に更新 |
| `spec/initial/lifecycle.md` | link connected と protocol ready の状態遷移 | 本仕様 §9.1 | `uv run mkdocs build --strict` | todo | 実装完了時に更新 |
| `spec/initial/protocol.md` | player lights session state と profile 対応 `0x04` | 本仕様 §5 / §9.2 / §9.3 | `uv run mkdocs build --strict` | todo | ACK 差分を再監査 |
| `spec/initial/testing.md` | fake / hardware の分担 | 本仕様 §7 / §12 | `uv run mkdocs build --strict` | todo | 実機未実行 |

## 9. 設計メモ

### 9.1 lifecycle state

| public `connection_state` | 内部条件 | 接続 API |
|---|---|---|
| `opened` | transport resource 準備済み | 待機前 |
| `advertising` / `reconnecting` | link 確立待ち | 待機中 |
| `initializing` | HID control / interrupt channel 利用可能、protocol ready 未到達 | 待機中 |
| `connected` | protocol ready 到達 | 正常終了可能 |
| `failed` | protocol error、reply failure、ready 前 disconnect | 失敗終了 |

transport の connected callback 用 event と public 接続成功用 event を分ける。
report sender と subcommand responder は link connected から利用できるが、利用者入力の
connected guard は protocol ready event を見る。

### 9.2 ready predicate

同じ `SwitchHidSession` 内で次を満たすことを protocol ready とする。

```text
report_mode_supported is true
and player_lights is not None
and player_lights != 0x00
and predicate を成立させた subcommand reply が transport に受理済み
```

player lights は点灯 bit と点滅 bit のどちらも assignment として扱うため、下位 nibble
だけではなく 1 byte 全体の nonzero を見る。`0x30 00` は current Switch 2 で初期化途中に
観測されているため完了に使わない。

`0x03` と `0x30` の到着順は契約にしない。各 reply 送信成功後に session predicate を
再評価し、初めて成立した 1 回だけ ready event を発火する。

### 9.3 profile 対応 trigger elapsed

`0x04` は reply payload の field layout と、pairing 用に合成する button 選択を分ける。
button 選択は `ControllerProfile` が持ち、encoder が 14 byte へ変換する。

| profile | 300 tick を設定する field | reply data |
|---|---|---|
| Pro Controller | L、R | `2c012c0100000000000000000000` |
| Joy-Con L | SL、SR | `00000000000000002c012c010000` |
| Joy-Con R | SL、SR | `00000000000000002c012c010000` |

300 tick は 10 ms 単位で 3000 ms を表す。

profile 対応 `0x04` により Switch が player assignment を進める設計を先に検証する。
初期実装では Periodic / Direct の違いをまたぐ一時的な SR+SL report pump を追加しない。

### 9.4 subcommand の扱い

| subcommand | ready との関係 |
|---|---|
| `0x03` | supported report mode は ready predicate の一部 |
| `0x30` | nonzero player lights は ready predicate の一部 |
| `0x04` | profile ごとの player assignment 進行に使うが、受信そのものを固定 gate にしない |
| `0x02` / `0x08` / `0x10` | 現行初期 sequence で必要な互換応答。受信集合を完了条件にしない |
| `0x21` / `0x22` / `0x40` / `0x48` | profile / firmware に応じて応答する。受信有無を完了条件にしない |

全観測 subcommand に reply があることは diagnostics / hardware test の整合確認に使う。
「何種類見えたか」と「利用者入力を受け付けられるか」を同じ条件にしない。

### 9.5 public API と timeout

- `create_profile()` は内部 object を作成後、`pair()` が protocol ready へ到達してから返す。
- `pair()` / `reconnect()` / `connect()` の正常終了は protocol ready を意味する。
- `try_*` の `"connected"` も同じ意味にする。
- timeout は 1 回の接続操作に 1 個の deadline を作り、transport connect、HID channel、
  subcommand handshake で残り時間を共有する。
- timeout または failure では half-ready 接続を cleanup し、object を factory caller に返さない。
- 明示 constructor で object を先に所有している場合も、接続 API が戻る前の
  `status().connection_state` は `initializing` とする。

### 9.6 ready 前の input state

Periodic API は接続前の state 準備を許しているため、local state の更新自体は維持する。
ただし initializing 中の wire report と `0x21` reply prefix は neutral state を使う。
ready 後に wire state の選択を local state store へ切り替える。

Direct は ready 前の利用者 input operation を拒否する。subcommand reply は Direct でも
内部 report sender から送れるため、ready 判定に periodic report loop は必要ない。

### 9.7 diagnostics

少なくとも次を構造化 event として記録する。

- `protocol_initialization_started`: route、profile kind。
- `subcommand_session_state`: report mode、player lights、ready predicate。
- `protocol_ready`: route、profile kind、report mode、player lights、観測済み subcommand。
- `protocol_initialization_failed`: stage、error type、観測済み subcommand、session state。
- `connection_timeout`: `stage="protocol_initialization"` と残りの session state。

`subcommand_reply_tx` の後に `protocol_ready` を記録し、trace から送信完了順を確認できるようにする。

### 9.8 cancellation / reset

- 接続 API の task cancellation は ready waiter と内部 deadline を解除し、既存 cleanup 規則へ渡す。
- disconnect、close、次回 open のいずれでも ready event と session state を初期化する。
- 前回 session の nonzero player lights を reconnect の成功に流用しない。
- ready と disconnect が競合した場合、reply 送信完了より先に disconnect が確定していれば
  成功を返さない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/session.py` | modify | player lights と ready predicate を connection-scoped state に追加 |
| `src/swbt/protocol/subcommand.py` | modify | `0x30` payload state、profile 対応 `0x04` reply |
| `src/swbt/protocol/profiles/base.py` | modify | pairing trigger button policy |
| `src/swbt/protocol/profiles/pro_controller.py` | modify | L / R policy |
| `src/swbt/protocol/profiles/joycon.py` | modify | SL / SR policy |
| `src/swbt/gamepad/output.py` | modify | reply 送信成功後の ready notification |
| `src/swbt/gamepad/runtime.py` | modify | link / ready event、deadline、input gate、diagnostics |
| `src/swbt/gamepad/connection.py` | modify | reconnect / connect result を protocol ready に接続 |
| `tests/unit/test_subcommand_responder.py` | modify | profile 対応 `0x04`、`0x30` validation |
| `tests/unit/test_protocol_session.py` | new | ready predicate と reset |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | 全 profile / reporting type の lifecycle |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | trigger elapsed policy と `0x30` ACK conflict の監査結果 |
| `tests/hardware/test_pairing_profile.py` | modify | profile ごとの ready trace / UI gate |
| `spec/initial/api.md` | modify | object return / connected semantics |
| `spec/initial/lifecycle.md` | modify | initializing / ready state |
| `spec/initial/protocol.md` | modify | player lights session state、profile 対応 `0x04` |
| `spec/initial/testing.md` | modify | fake / hardware gate |
| `spec/hardware-test-log.md` | modify | 明示承認後の実機結果だけ追記 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `git diff --check` | pass | tracked 差分に whitespace error なし。新規仕様書は末尾空白を別途検査 |
| `uv run mkdocs build --strict` | pass | 設計文書とリンクの機械検証 |
| `uv run pytest tests/unit/test_subcommand_responder.py::test_trigger_buttons_elapsed_subcommand_builds_pairing_reply tests/unit/test_subcommand_responder.py::test_joycon_trigger_buttons_elapsed_reports_sr_sl_pairing_hold -q` | pass | `3 passed`。Joy-Con は red `2 failed` を確認後に profile 対応して green |
| `uv run pytest tests/unit/test_protocol_session.py::test_zero_player_lights_is_recorded_without_protocol_readiness tests/unit/test_subcommand_responder.py::test_simple_ack_subcommands_build_0x21_reply -q` | pass | `6 passed`。player lights field 不在の red 後に `0x30 00` state を実装 |
| `uv run pytest tests/unit/test_protocol_session.py -q` | pass | `3 passed`。ready predicate の red `2 failed` 後に report mode + nonzero player lights 条件で green |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_pair_starts_advertising_and_waits_for_fake_connection -q` | pass | `1 passed`。link 接続だけで pair task が完了する red 後に `initializing` / ready event を分離 |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_pair_waits_until_ready_subcommand_reply_is_transport_accepted -q` | pass | `1 passed`。fake transport に delayed send がない red 後、受理待ちを追加して ready event 順を確認 |
| `uv run ruff format --check .` | pass | `100 files already formatted` |
| `uv run ruff check .` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest tests/unit -q` | pass | `474 passed` |
| `uv run pytest tests/integration -q` | pass | `152 passed` |
| `uv run mkdocs build --strict` | pass | 公開 docs と初期設計のリンク・site build |
| Pro / Joy-Con L / Joy-Con R hardware gate | not run | 明示承認が必要 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for completion |
| 承認範囲 | 対象 profile ごとに adapter open、pairing または active reconnect、HID advertising、subcommand handling、neutral report、UI 観測、close を列挙する |
| adapter | 実行直前に確認した専用 adapter。過去観測は `usb:0` / CSR8510 A10 / WinUSB |
| 対象機器 | Switch model / firmware、controller search または change grip/order 画面を記録する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、adapter、command、Switch-facing 範囲、cleanup plan で管理する |
| log / artifact | profile、route、`0x04` reply data、`0x03` mode、すべての `0x30` payload、reply 完了順、`protocol_ready`、UI 観測を保存する |
| cleanup | neutral、disconnect request、transport close、adapter release。timeout / failure でも同じ cleanup を確認する |

実機 gate は Pro Controller、Joy-Con L、Joy-Con R を別 run とする。Joy-Con run では
利用者または test から SR+SL input report を送らず、profile 対応 `0x04` reply の効果を
分離する。自動登録が進まない場合は timeout を pass にせず、観測結果を本仕様へ戻す。

## 13. 先送り事項

- Joy-Con の profile 対応 `0x04` だけで登録できない場合の内部 SR+SL report pump。
  Periodic / Direct 共通の bounded handshake sender として別 Intent Delta を作る。
- ready 後の player lights 更新を公開 API で通知する機能。
- controller order slot や UI 画面を公開 object として表現する機能。
- firmware ごとの alternative ready marker。nonzero player lights が得られない実機観測が
  出た場合だけ、hardware evidence とともに追加する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] Pro Controller / Joy-Con L / Joy-Con R と Periodic / Direct の境界を設計した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 固定 subcommand 集合を public completion gate から除外した
- [x] Joy-Con の profile 対応 trigger elapsed policy を記録した
- [x] 実機実行条件を記録した
- [x] `0x30` ACK conflict を再監査した
- [x] 実装と local gate を完了した
- [ ] Pro Controller / Joy-Con L / Joy-Con R の実機 gate を完了した
- [x] 初期設計文書へ完了後の contract を反映した
