# HCI ACL Completion Correlation 仕様書

## 1. 概要

### 1.1 目的

Issue #93 で観測した約 30 ms の ACL drain を、Bumble host が対象 connection の `Number Of Completed Packets` を処理した時刻まで分解する。併せて Classic link mode / interval の snapshot を同じ Direct `send()` に記録し、sniff mode との相関を観測可能にする。

この作業は private な調査 probe の拡張である。公開 diagnostics、通常送信の completion contract、queue policy は変更しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| Issue #93 | Direct caller が ACL drain のため 8 ms cadence を維持できない | `niart120/swbt-python#93` |
| unit_059 hardware observation | CSR8510 A10 / Bumble 0.0.230 で Direct `send()` の median は約 30 ms、ACL drain は約 29.8 ms | `spec/hardware-test-log.md` |
| Bumble 0.0.230 source | `DataPacketQueue.drain(handle)` は connection の `drained` event を待ち、`on_packets_completed()` が completion event を処理して event を set する | `.venv/Lib/site-packages/bumble/host.py:48-187,1166-1174` |
| Bumble 0.0.230 source | default link policy `0x0005` は role switch と sniff mode を許可し、`mode_change` は connection の classic mode / interval を更新する | `src/swbt/transport/bumble.py:49-63,811-829`, `.venv/Lib/site-packages/bumble/host.py:1711-1717`, `.venv/Lib/site-packages/bumble/device.py:6337-6346` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| swbt 開発者 | DEBUG 有効の Direct `send()` と Bumble queue | enqueue 後に対象 connection の completion handler が呼ばれた delay と packet count を同じ JSON event に記録する | Bumble private implementation への一時 hook。DEBUG 無効では hook しない |
| swbt 開発者 | Direct `send()` 時の Classic connection | enqueue / completion 時点の mode と interval を記録する | mode 値を安定 public contract にしない |
| 実機調査者 | dedicated dongle と paired Switch | completion delay と ACL drain の差、mode / interval を比較する | 明示承認後だけ実行。neutral input のみ |

## 2. 対象範囲

- `swbt.experimental.direct_send_timing` の private JSON event に completion handler 時刻と Classic mode snapshot を追加する。
- Bumble `DataPacketQueue.on_packets_completed(packet_count, connection_handle)` を DEBUG probe 中だけ temporary に観測し、対象 handle の最初の completion を記録する。
- HID enqueue 前後と ACL drain 後の mode / interval を記録する。
- fake Bumble queue で handler の時刻、別 connection handle の除外、hook 復元を unit test する。
- 実機では unit_059 の paired profile を用い、active reconnect と neutral Direct send だけで比較する。

## 3. 対象外

- Bumble package の patch / fork / version update。
- ACL drain の削除、send completion semantics の変更、bounded enqueue、backpressure、stale report drop。
- Periodic report loop の実機評価。
- payload bytes、input state、Bluetooth address、link key の DEBUG 出力。
- pairing profile の新規作成、address restore、physical power cycle。

## 4. 関連 docs

- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/complete/unit_059/EXPERIMENTAL_DIRECT_SEND_TIMING_PROBE.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | payload と report layout を変更・出力しない |
| Bumble / transport | required | done | `on_packets_completed()` は対象 handle の in-flight を減らし 0 なら `drained` を set する。`drain()` はその event を await する。hook は Bumble 0.0.230 の temporary observation だけに使う |
| OS / driver / adapter | required | done | 約30 ms は Windows 11 / CSR8510 A10 / WinUSB / Bumble 0.0.230 の hardware observation。値を一般化しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| DEBUG 無効 | Direct `send()` | completion hook、clock read、JSON event を作らない | unit_059 の契約を維持 |
| 対象 completion | queue が Direct send の connection handle を completed と通知 | event に `acl_completion_event_delay_ns` と `acl_completion_packet_count` を入れる | delay は enqueue 開始から host handler 実行まで |
| 別 connection completion | queue が異なる handle を completed と通知 | 対象 send の completion fields を更新しない | host-wide queue との混同を防ぐ |
| link mode snapshot | enqueue と completion / drain 時点 | `classic_mode_*` と `classic_interval_*` を入れる | Bumble が属性を公開しない fake では `null` |
| hook 非対応 queue | `on_packets_completed` を差し替えられない | send の既存成功 / failure を維持し completion fields は `null` | 調査 probe が transport を壊さない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | DEBUG 有効の Bumble fake Direct send が対象 completion handler の delay、packet count、enqueue / completion mode snapshot を 1 event に出す | new | unit | no | `test_bumble_interrupt_probe_records_acl_queue_timing` で確認 |
| green | 別 connection handle の completion は現在の Direct send event を completion 済みにしない | edge | unit | no | 初回実装の handle filter を `test_bumble_interrupt_probe_ignores_other_connection_acl_completion` で回帰確認 |
| green | completion hook を外した後の queue は元の handler を使い、次の send で二重観測しない | regression | unit | no | `test_bumble_interrupt_probe_restores_acl_completion_handler` で連続2送信後の handler と event 数を確認 |
| green | hook 非対応 queue の Direct send は成功し completion fields を null にする | edge | unit | no | `test_bumble_interrupt_probe_allows_queue_without_completion_handler` で確認 |
| green | paired Switch への neutral Direct send で completion delay、ACL drain、Classic mode / interval を収集する | characterization | hardware | yes | 2026-07-22、40 event。詳細は `spec/hardware-test-log.md` |

## 8. 文書検証計画

not applicable。private experimental logger と実機記録だけを変更し、利用者向け文書と公開 API は変更しない。

## 9. 設計メモ

`DataPacketQueue` は host-wide queue だが `on_packets_completed()` の引数には connection handle がある。temporary wrapper は対象 handle だけを記録し、元の handler を必ず復元する。completion 時刻は controller / USB callback から Bumble host handler へ到着した時点であり、Switch がゲーム入力を反映した時刻ではない。

Classic sniff mode は default policy が許可するだけで、実際に遷移した証拠ではない。enqueue、completion、drain の各 snapshot と実機 `mode_change` 観測を分けて扱う。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/_experimental_direct_send_timing.py` | modify | private JSON fields の初期値 |
| `src/swbt/transport/_bumble_acl.py` | modify | temporary completion observer と mode snapshot helper |
| `src/swbt/transport/bumble.py` | modify | DEBUG Direct send 中だけ observer を attach / detach |
| `tests/unit/test_bumble_transport.py` | modify | fake queue の completion correlation test |
| `spec/hardware-test-log.md` | modify | 承認済み実機結果がある場合だけ追記 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_bumble_transport.py -k acl_queue_timing -q` | passed | RED は completion field 未実装による `KeyError`、GREEN は 1 passed / 32 deselected |
| `uv run pytest tests/unit/test_bumble_transport.py -k "acl_queue_timing or ignores_other_connection_acl_completion" -q` | passed | 2 passed / 32 deselected。別 handle 専用の completion では対象 event の completion fields は null |
| `uv run pytest tests/unit/test_bumble_transport.py -k restores_acl_completion_handler -q` | passed | 1 passed / 34 deselected。各 Direct send 後に元の completion handler へ復元され、event は 1 send につき 1 件 |
| `uv run pytest tests/unit/test_bumble_transport.py -k without_completion_handler -q` | passed | 1 passed / 35 deselected。completion callback がない queue でも send は success、completion fields は null |
| `uv run ruff format --check .` | passed | 100 files already formatted |
| `uv run ruff check .` | passed | All checks passed |
| `uv run ty check --no-progress` | passed | All checks passed |
| `uv run pytest tests/unit` | passed | 458 passed |
| `uv run pytest tests/integration` | passed | 134 passed |
| `git diff --check` | passed | whitespace error なし |
| approved hardware characterization | passed | `usb:0` / saved profile / neutral Direct send。completion delay p50 9.757 ms、ACL drain p50 9.746 ms、40/40 success |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | implementation は不要。characterization は必要 |
| 承認範囲 | dedicated adapter、active reconnect、neutral Direct send、DEBUG file output、`close(neutral=True)`、adapter release を command とともに確認する |
| adapter | `usb:0` は候補。実行直前に CSR8510 A10 / WinUSB であることを read-only に確認する |
| executed command | `uv run python tmp/hardware/issue-93/direct_send_timing_benchmark.py benchmark --adapter usb:0 --profile-path tmp/hardware/issue-93/direct-pro-profile.json --artifact-dir tmp/hardware/issue-93/hci-completion-correlation --reconnect-timeout 10 --paced-8ms-samples 10 --paced-16ms-samples 10 --burst-samples 20 --diagnostic-8ms-samples 20 --diagnostic-16ms-samples 20` |
| Switch-facing scope | saved profile の active reconnect と neutral Direct send のみ。新規 pairing、button / stick input、BD_ADDR 書換えは行わない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | timing JSONL、lifecycle trace、summary、OS、driver、Bumble version、Switch model / firmware を `spec/hardware-test-log.md` に記録する |
| cleanup | logger handler を外し、`close(neutral=True)`、`transport_close_complete`、read-only postflight の `adapter_closed` を確認する |

## 13. 先送り事項

- completion event が約30 ms遅れる下位原因（controller firmware、USB / WinUSB scheduling、Classic air link、Switch link policy）は、この probe 単独では確定しない。
- sniff mode が観測されても、default link policy の変更を production default にしない。別 work unit で input reflection と消費電力・reconnect への影響を評価する。
- send completion contract の変更は queue policy を伴う別 Issue とする。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] fake Bumble queue による実装と検証を完了した
- [x] 承認済み実機 characterization を実行した
