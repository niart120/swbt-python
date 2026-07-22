# Periodic no-drain 特性調査 仕様書

## 1. 概要

### 1.1 目的

Issue #93 の Periodic `0x30` 送信について、Bumble の ACL queue drain を各 report 後に待たない場合に、125 Hz の設定周期、controller 内 in-flight 数、Bumble software queue、HCI completion が安定して進むかを短時間だけ観測する。production の送信契約や公開 API は変更しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | drain を外した実機検証を行う | conversation, 2026-07-23 |
| implementation fact | Bumble `DataPacketQueue` は controller が申告した `max_in_flight` まで ACL packet を送り、超過分を software queue に保持する | `.venv/Lib/site-packages/bumble/host.py` |
| hardware observation | drain ありの 8 ms Periodic は completion interval p50 20.023 ms、ACL drain p50 11.386 ms だった | `spec/hardware-test-log.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 調査者 | saved profile で `usb:0` と Switch を active reconnect する | pairing せず接続し、active reconnect result までは通常 drain を使う | dedicated adapter のみ |
| Periodic report loop | 接続後の短時間だけ drain を no-op にする | 8 ms cadence、ACL enqueue / completion、pending / in-flight / software queue depth を artifact に残す | neutral `0x30` のみ |
| cleanup | no-drain 観測窓を終了する | 通常 drain を復元して neutral close し、残存 ACL packet と adapter を解放する | 復元失敗または切断で停止 |

## 2. 対象範囲

- ignored disposable harness 内だけでの `drain_bumble_acl_queue` 一時差し替え。
- Bumble `DataPacketQueue` の `max_in_flight`、enqueue、completion、pending、controller in-flight、software queue depth の観測。
- 8 ms設定、200件以下の neutral Periodic report による短時間実機検証。
- 既存 drain あり artifact との比較。

## 3. 対象外

- production transport、公開 constructor、公開 diagnostics schema、通常の send completion contract の変更。
- pairing、button / stick / IMU 操作、BD_ADDR 書換え、Classic link policy の変更。
- Switch UI 上の入力反映時刻の測定。
- no-drain を既定動作にする判断。

## 4. 関連 docs

- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_062/PERIODIC_ACL_DRAIN_CHARACTERIZATION.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 既存の neutral `0x30` builder 出力だけを使い、layout を変更しない。 |
| Bumble / transport | required | done | Bumble 0.0.230 `DataPacketQueue` の enqueue、`max_in_flight`、`on_packets_completed()`、`pending` を確認した。 |
| OS / driver / adapter | required | done | Windows 11、WinUSB、CSR8510 A10、Bumble 0.0.230、Python 3.13.5。preflight / postflight は HCI / CSR address `0E:08:71:C0:B4:5C` 一致と `adapter_closed` を記録した。 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| reconnect | production drain のまま saved profile へ active reconnect | active reconnect result 後だけ no-drain 観測窓へ入る | connected 後に遅れて届くsubcommand replyは観測窓に含まれ得る |
| enqueue-only send | 8 ms周期の neutral Periodic report | `send_interrupt()` は HID enqueue 後に戻り、次周期へ進む | harness process 内だけ |
| queue flow | controller completion が届く | pending / in-flight が減り、software queue が継続増加しないか観測できる | 結果は事前に仮定しない |
| cleanup | 規定 sample 到達、timeout、disconnect、例外 | drain を復元し、neutral close と adapter close を試みる | cleanup を優先する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | harness の help と静的検査が adapter を開かず成功する | regression | unit | no | ignored file を個別に検査した |
| green | `usb:0` で controller buffer size と no-drain 中の queue transition を記録する | characterization | hardware | yes | `max_in_flight=10`、最大実測in-flight 3、software queue depth 0 |
| green | no-drain 観測後に通常 drain を復元し clean close する | characterization | hardware | yes | 最終pending 0、`transport_close_complete`、postflight `adapter_closed` |

## 8. 文書検証計画

not applicable。公開文書を変更しない。

## 9. 設計メモ

- monkeypatch は active reconnect result 後に適用する。result より前の送信は現行 drain を維持するが、Switchからの初期subcommandはresult後にも届くため、replyを実験から完全には分離できない。
- no-drain 終了時は差し替えを先に復元する。続く `close(neutral=True)` の neutral report が既存 pending を含む connection queue の drain を待つことで、可能な範囲で送信完了後に閉じる。
- `pending` は host-wide の queued total と completed total の差である。controller in-flight と software queue depth を別項目として記録する。
- Switch が report を受信・反映した時刻は HCI completion からは分からない。
- 2026-07-23 の有効runでは、8 ms設定のneutral Periodic 200件を記録した。report completion intervalはp50 8.979 ms / p95 10.054 ms、transport sendはp50 0.087 msだった。controller申告は `max_packet_size=310` / `max_in_flight=10`、最大pending / in-flightは3、software queue depthは全transitionで0だった。
- 同じ接続の unit_062 drain あり観測はcompletion interval p50 20.023 ms / transport send p50 11.455 msだった。no-drainで約8.98 msまで短縮した事実は、per-report drainがPeriodic cadenceを遅らせていたことを支持する。ただし1 run、1 adapter、短時間のcharacterizationであり、長時間安定性は未検証である。
- active reconnect完了後にもSwitchから初期subcommandが16件届いたため、共有interrupt経路のsubcommand reply 16件もno-drain観測窓に含まれた。traceは全16件の `subcommand_reply_tx` を記録したが、HCI completionはSwitchがreplyを意味的に受理した証明ではない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tmp/hardware/issue-93/periodic_send_timing_benchmark.py` | modify, ignored | enqueue-only policy と ACL queue transition artifact |
| `spec/hardware-test-log.md` | modify | 承認範囲、結果、cleanup |
| `spec/complete/unit_063/PERIODIC_NO_DRAIN_CHARACTERIZATION.md` | new | 作業仕様と検証記録 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run ruff format --check tmp/hardware/issue-93/periodic_send_timing_benchmark.py` | passed | adapter を開かない。1 file already formatted |
| `uv run ruff check tmp/hardware/issue-93/periodic_send_timing_benchmark.py` | passed | adapter を開かない。All checks passed |
| `uv run python tmp/hardware/issue-93/periodic_send_timing_benchmark.py --help` | passed | adapter を開かず `--acl-completion-policy {drain,enqueue-only}` を確認 |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --output tmp/hardware/issue-93/periodic-no-drain/adapter-identity-preflight.json` | passed | HCI / CSR address 一致、`adapter_closed` |
| first hardware command, artifact `01-8ms` | stopped before no-drain | L2CAP connection からACL queueを直接参照する仮定が不一致。active reconnect後、通常drainのままclean close。production helperと同じ host resolver に修正した |
| `uv run python tmp/hardware/issue-93/periodic_send_timing_benchmark.py --adapter usb:0 --profile-path tmp/hardware/issue-93/direct-pro-profile.json --artifact-dir tmp/hardware/issue-93/periodic-no-drain/02-8ms --reconnect-timeout 10 --report-period-us 8000 --samples 200 --sample-timeout 10 --acl-completion-policy enqueue-only` | passed | Periodic 200件。interval p50 8.979 ms / p95 10.054 ms。最大in-flight 3/10、software queue 0、最終pending 0 |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --output tmp/hardware/issue-93/periodic-no-drain/adapter-identity-postflight.json` | passed | HCI / CSR address 一致、`adapter_closed` |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | dedicated `usb:0` open、saved profile active reconnect、接続後の neutral-only Periodic `0x30` を8 ms設定で最大200件 enqueue-only送信、ACL queue private state の観測、通常 drain 復元、neutral close、adapter release、postflight identity probe。新規 pairing、button / stick / IMU、BD_ADDR 書換えは含まない。 |
| adapter | dedicated CSR8510 A10 / WinUSB / `usb:0`。既存 local address `0E:08:71:C0:B4:5C` と saved profile を使う。 |
| 実行遮断 | 環境変数による遮断は採用しない。会話上の明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `tmp/hardware/issue-93/periodic-no-drain/` の pre/postflight identity、trace、timing JSONL、ACL queue JSONL、summary |
| cleanup | no-drain patch を `finally` で復元後、`close(neutral=True)`、queue observer 復元、adapter close、postflight identity。unexpected disconnect、software queue の継続増加、trace error で追加 run を停止する。 |

## 13. 先送り事項

- no-drain の結果を受けた bounded enqueue、high-watermark drain、subcommand reply 優先制御は別作業単位で設計する。
- 長時間125 Hz、入力変化、Switch側反映、切断率、subcommand reply受理の比較は未検証である。今回の短時間neutral runだけでproduction contractを変更しない。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
