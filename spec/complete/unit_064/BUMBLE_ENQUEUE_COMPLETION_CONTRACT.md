# Bumble enqueue 完了契約 仕様書

## 1. 概要

### 1.1 目的

Issue #93 の実機調査で使用した詳細 timing / ACL completion probe を production source から撤去し、`BumbleHidTransport.send_interrupt()` の正常終了を「Bumble が HID interrupt payload を enqueue した」と定義する。HCI ACL completion は report ごとに待たず、明示切断時だけ pending ACL queue を drain してから L2CAP channel を閉じる。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user decision | Bumble の既存 flow control を利用し、per-report drain、独自 high-watermark、優先 queue、公開切替フラグを追加しない | conversation, 2026-07-23 |
| source fact | Bumble 0.0.230 の `hid.Device.send_data()` は interrupt L2CAP channel へ data を渡し、Host の `DataPacketQueue` が controller 申告数まで ACL packet を送って completion で枠を戻す | `.venv/Lib/site-packages/bumble/hid.py`, `.venv/Lib/site-packages/bumble/host.py` |
| hardware observation | 8 ms Periodic no-drain 200件で controller `max_in_flight=10`、最大in-flight 3、software queue depth 0、終了時 pending 0 | `spec/complete/unit_063/PERIODIC_NO_DRAIN_CHARACTERIZATION.md` |
| implementation fact | unit_064 着手時の `send_interrupt()` は `send_data()` 後に connection ACL queue の `drain()` を待ち、Direct state commit と `report_tx` はその後に進んでいた | unit_064 の RED、`src/swbt/transport/bumble.py` の変更前実装 |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Direct caller | 接続中に `await send(state)` | report 1件がBumbleへenqueueされると正常終了し、stateをcommitする | HCI completion、Switch反映は待たない |
| Periodic / subcommand sender | `0x30` または `0x21` を送る | 共通sender lockの順にBumbleへenqueueし、per-report ACL drainを行わない | 独自queueを作らない |
| lifecycle close | pending reportがある状態で明示切断する | interrupt queueをdrainしてからinterrupt / control channelを切断する | channelがない場合は従来どおりunavailable |
| maintainer | DEBUG logging設定で通常利用する | Issue #93専用timing JSONとprivate completion hookがproduction sourceから発生しない | 安定diagnosticsの新設は別議論 |

## 2. 対象範囲

- `BumbleHidTransport.send_interrupt()` のper-report ACL drainを削除する。
- `BumbleHidTransport.request_disconnect()` でinterrupt channel切断前にpending ACL queueをdrainする。
- Direct送信成功、state commit、`report_tx` の意味をtransport enqueue受理として仕様化する。
- Issue #93用のDirect / Periodic timing probe、ACL completion observer、Classic link policy実験helperと専用testをproduction treeから撤去する。
- source-audit fixture、unit / integration test、関連initial docsを新契約へ更新する。
- unit_059〜061を完了済みcharacterizationへ移し、unit_062〜063と実機ログを根拠として残す。

## 3. 対象外

- swbt独自のflow-control queue、high-watermark、report drop / coalescing、subcommand priority、credit予約。
- 公開diagnostics、timing logger、送信policy切替フラグ。
- Periodic deadline schedulerと設定8 msに対する実周期補償。観測済み約111 Hzは別GitHub Issueへ起票する。
- 改修判断のための追加Bumble adapter / Switch実機実行。実装後のproduction soakは別途ユーザ承認を得て回帰確認として実施した。
- Bumble `DataPacketQueue` の内部実装変更。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/transport-bumble.md`
- `spec/complete/unit_050/DIRECT_REPORTING_TYPES.md`
- `spec/complete/unit_059/EXPERIMENTAL_DIRECT_SEND_TIMING_PROBE.md`
- `spec/complete/unit_060/HCI_ACL_COMPLETION_CORRELATION.md`
- `spec/complete/unit_061/EXPERIMENTAL_CLASSIC_LINK_POLICY_AB.md`
- `spec/complete/unit_062/PERIODIC_ACL_DRAIN_CHARACTERIZATION.md`
- `spec/complete/unit_063/PERIODIC_NO_DRAIN_CHARACTERIZATION.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report ID、payload layout、送信順を変更しない。 |
| Bumble / transport | required | done | Bumble 0.0.230 `send_data()`、L2CAP enqueue、`DataPacketQueue.max_in_flight` / completion / `drain(handle)`をsource確認し、unit_060〜063で実機相関とno-drainを観測した。 |
| OS / driver / adapter | required | done | Windows 11 / WinUSB / CSR8510 A10のhardware-observed only。別環境へ性能値を一般化せず、契約はBumbleがenqueueを受理する境界だけに置く。 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| interrupt enqueue | connected interrupt channelへpayloadを送る | `hid_device.send_data(payload)`が正常終了すると直ちにreturnする | ACL completionを待たない |
| enqueue failure | `send_data()`が例外を投げる | `send_interrupt()`も失敗し、Direct stateとtimerをcommitしない | 同期enqueue失敗だけをcallerへ返す |
| sender ordering | inputとsubcommand replyが競合する | 既存sender lock取得順にenqueueされ、timer / session state順序を維持する | completion順は契約しない |
| explicit disconnect | interrupt channelがある | 現在のconnection ACL queueをdrainしてからinterrupt channelを切断し、その後control channelを切断する | trailing neutralを含むpending送信を切断前に処理する |
| drain failure | 明示切断前のdrainが失敗する | `DisconnectRequestResult(status="failed")`を返し、channel切断を開始しない | error metadataを保持する |
| no interrupt channel | control channelだけ、または両channelなし | controlだけなら従来どおりcontrolを切断し、両方なければunavailableを返す | drainしない |
| production residue | 通常source / testを検索する | Issue #93専用experimental module、logger、completion observer、link-policy helper参照が0件 | specs / hardware logの履歴記述は除外する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | interrupt sendはpayloadをenqueueしてもACL drainを呼ばず正常終了する | change | unit | no | REDでhandle `0x0048`のdrainを確認し、GREENでdrain 0件を確認 |
| green | host fallback queueを持つ接続でも通常sendはdrainしない | regression | unit | no | host queueの解決自体を行わない |
| green | 明示切断はpending interrupt queueをdrainしてからchannelを順に切断する | change | unit | no | `drain`、interrupt、controlの順序を確認 |
| green | disconnect前drain失敗はfailed resultとなりchannelを切断しない | edge | unit | no | `acl_drain_failed`とerror metadataを確認 |
| green | Direct sendはtransport enqueue受理まで待ち、成功後だけstateをcommitする | change | integration | no | 既存の制御可能なfake transport acceptance gateで確認 |
| green | inputとsubcommand replyの既存sender順序を維持する | regression | integration | no | Direct input後のreply prefix / timer順序を確認 |
| green | production treeからIssue #93専用probe実装と専用testがなくなる | regression | static | no | `src` / `tests` のresidue search 0件 |

## 8. 文書検証計画

公開利用者向け文書は変更しない。initial designと完了済みwork specをsource / implementation / hardware observationに照合し、enqueue成功とHCI completionを混同していないことをレビューする。

## 9. 設計メモ

- Bumbleのqueueがcontroller flow controlを所有する。swbtは第二のqueueを追加しない。
- `send_interrupt()`はasync interfaceを維持するが、Bumble実装では同期的な`send_data()` enqueue後にawaitを挟まずreturnする。
- `ReportSender`のlockはcompletion待ちではなくenqueue順序を直列化する。`report_tx`はBumbleへのenqueue受理を表し、air deliveryやSwitch反映を表さない。
- `request_disconnect()`はruntimeのtrailing neutral送信後に呼ばれるため、ここでのdrainをlifecycle barrierとする。通常send経路ではdrainしない。
- Periodic schedulerは現在、send後に固定sleepするためenqueue時間を周期へ加算する。deadline schedulerは基準deadlineから次回時刻を進め、残り時間だけsleepし、遅延tickをburst追送しない方式を後続Issueで扱う。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/bumble.py` | modify | enqueue return、disconnect前drain |
| `src/swbt/transport/base.py`, `src/swbt/diagnostics.py` | modify | transport受理と`report_tx`の意味を明記 |
| `src/swbt/transport/_bumble_acl.py` | modify | completion観測を撤去しdrain helperだけ保持 |
| `src/swbt/_experimental_direct_send_timing.py` | delete | disposable timing probe撤去 |
| `src/swbt/transport/_experimental_classic_link_policy.py` | delete | disposable A/B helper撤去 |
| `src/swbt/gamepad/runtime.py`, `src/swbt/report_loop.py` | modify | probe hook撤去 |
| `tests/unit/test_bumble_transport.py` | modify | enqueue / disconnect drain contract |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | enqueue acceptance wording / probe test撤去 |
| `tests/unit/test_source_audit_fixtures.py`, `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | implementation-policy更新 |
| `spec/initial/*.md`, `spec/complete/unit_050/DIRECT_REPORTING_TYPES.md` | modify | enqueue完了契約とdiagnostics意味 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_bumble_transport.py::test_bumble_send_interrupt_returns_after_enqueue_without_acl_drain -q` | red, expected | `drained_handles` が `[0x0048]` となり新契約の `[]` に違反 |
| 同testのGREEN再実行 | pass | 1 passed。通常sendのenqueue受理後にACL drainを呼ばない |
| `uv run pytest tests/unit/test_bumble_transport.py::test_bumble_request_disconnect_calls_interrupt_then_control_helpers -q` | red, expected | ACL queueがdrainされず、新しい順序契約に違反 |
| 同testのGREEN再実行 | pass | 1 passed。`drain -> interrupt -> control`を確認 |
| `uv run pytest tests/unit/test_bumble_transport.py::test_bumble_request_disconnect_reports_acl_drain_failure -q` | red, expected | drain例外が未処理でcallerへ送出された |
| 同testのGREEN再実行 | pass | 1 passed。failed result、`acl_drain_failed`、channel切断0件を確認 |
| `uv run pytest tests/unit/test_bumble_transport.py -q` | pass | 33 passed。host fallbackを含むenqueue / disconnect回帰を確認 |
| `uv run pytest tests/unit/test_source_audit_fixtures.py -q` | pass | 27 passed。Bumble enqueue / disconnect drain境界を根拠fixtureへ反映 |
| `uv run pytest tests/unit/test_report_loop.py -q` | pass | 5 passed。slow send中の追送なしと解放後の最新stateを確認 |
| Direct targeted integration 4件 | pass | enqueue受理前後のcommit、失敗rollback、同時操作、subcommand reply順序を確認 |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 99 files already formatted。初回は調査時追加test 2件を検出し、Ruffで整形後に再実行 |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 456 passed |
| `uv run pytest tests/integration` | pass | 131 passed |
| `rg -n '_experimental_direct_send_timing|_experimental_classic_link_policy|DirectSendTiming|PeriodicSendTiming|timing_probe|completion_observer|acl_completion_probe|direct_send_timing' src tests` | pass | 0 matches（`rg` exit 1） |
| `git diff --check` | pass | whitespace errorなし |
| production no-drain 5-minute soak | pass | 300秒間connectedを維持。periodic `0x30` 33159件、subcommand reply 16件、trace error 0件、disconnect request accepted、`transport_close_complete`、postflight `adapter_closed` |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | implementation判断にはnot required。実装後回帰として2026-07-23に5分production soakを実施 |
| 承認範囲 | dedicated `usb:0`、既存bond active reconnect、8 ms neutral Periodic 300秒、通常subcommand応答、`close(neutral=True)`、adapter解放。pairing、非neutral入力、address書換えは対象外 |
| adapter | CSR8510 A10 / `usb:0` / WinUSB。preflight / postflight identity一致 |
| 実行遮断 | 環境変数による遮断は採用せず、会話上の明示承認と具体commandで管理した |
| log / artifact | `spec/hardware-test-log.md`、`tmp/hardware/issue-93/production-no-drain-soak/` |
| cleanup | close errorなし、reason 0 disconnected、`transport_close_complete`、postflight `adapter_closed` |

## 13. 先送り事項

- Periodic deadline schedulerはGitHub Issue [#103](https://github.com/niart120/swbt-python/issues/103)へ分離した。固定deadline、残り時間だけのsleep、遅延tickのburst追送なしを扱う。
- Bumble queueの長時間飽和は未観測であり、推測だけで独自flow-controlを追加しない。再現した場合に別Issueで扱う。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test Listを作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] probe撤去とenqueue契約を実装した
- [x] 検証結果を記録した
- [x] deadline scheduler Issueを記録した
