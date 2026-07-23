# Periodic deadline scheduler 仕様書

## 1. 概要

### 1.1 目的

Periodic input report の送信周期を、前回送信後の固定待機時間ではなく、単調時計上の固定 deadline 間隔として扱う。snapshot、report build、transport enqueue に使った時間を次回の待機時間から差し引き、遅延した tick は burst で追送しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | no-drain 後も 8 ms 設定の completion interval が p50 8.979 ms だったため、処理時間を周期へ加算しない deadline scheduler を導入する | Issue #103 |
| hardware observation | 1 adapter、1接続、短時間の no-drain 200件で completion interval p50 8.979 ms / p95 10.054 ms、transport send p50 0.087 ms | `spec/complete/unit_063/PERIODIC_NO_DRAIN_CHARACTERIZATION.md` |
| implementation fact | 着手時の `ReportLoop._run()` は固定周期を sleep した後に `send_next_report()` を await する | `src/swbt/report_loop.py` |
| prior contract | 通常送信は Bumble enqueue 完了まで待ち、report ごとの ACL drain は行わない | `spec/complete/unit_064/BUMBLE_ENQUEUE_COMPLETION_CONTRACT.md` |
| hardware observation | 実装 commit `50bba8e` を `usb:0` / 既存 bond / neutral-only 8 ms Periodic 200件で計測し、completion interval p50 8.038 ms / p95 9.093 ms を観測した | `spec/hardware-test-log.md`、`tmp/hardware/issue-103/periodic-deadline-8ms-01/` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Periodic controller | 8 ms 周期で report を送信し、各 send に処理時間がかかる | send 開始 deadline は単調時計上で 8 ms 間隔に進み、処理時間を次の sleep から差し引く | OS scheduling 精度や Switch 側反映時刻は保証しない |
| Periodic controller | send が1周期を超えて遅延する | 過去 deadline を飛ばし、現在時刻以上の最初の deadline まで待つ | 遅延 tick を burst 追送しない |
| caller | send 遅延中に `apply()` で state を更新する | 遅延後の次回 report は送信時点の最新 state を使う | 古い state を tick 数分 queue しない |
| subcommand path | periodic と subcommand reply が競合する | 既存の共通 sender lock、timer、reply 順序を維持する | reply priority / holdoff policy は変更しない |

## 2. 対象範囲

- `ReportLoop` の periodic scheduling を単調時計上の固定 deadline へ変更する。
- fake clock と fake sleep を使う決定的な unit test を追加する。
- 送信処理時間の周期加算、周期超過時の skip、遅延後の最新 state を検証する。
- `spec/initial/lifecycle.md` と `spec/initial/testing.md` の periodic scheduling 契約を更新する。
- 承認済みの専用 adapter と既存 bond で neutral-only Periodic 200件を計測し、Issue #93 の旧 scheduler 観測と比較する。

## 3. 対象外

- `report_period_us` の既定値変更。
- HID report ID、payload layout、timer byte、IMU encoding の変更。
- Bumble ACL flow control、enqueue、drain、queue depth、priority policy の変更。
- subcommand reply の priority、holdoff 時間、sender lock の変更。
- OS scheduler、Bluetooth controller、Switch firmware に対する厳密な 125 Hz 保証。
- 新規 pairing、HID advertising、button / stick / IMU 入力、BD_ADDR 書換え。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_063/PERIODIC_NO_DRAIN_CHARACTERIZATION.md`
- `spec/complete/unit_064/BUMBLE_ENQUEUE_COMPLETION_CONTRACT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report ID、payload、timer、周期既定値を変更しない。 |
| Bumble / transport | not applicable | not applicable | unit_064 の enqueue 完了契約を前提にするが、transport 実装と flow control は変更しない。 |
| OS / driver / adapter | required | done | unit_063 の旧観測に加え、Windows 11 / CSR8510 A10 / WinUSB / `usb:0` で実装後200件を観測した。単一環境の短時間値であり、他環境へ一般化しない。 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| fixed deadline | 周期 `P`、最初の基準時刻 `T0` | 最初の送信 deadline は `T0 + P`、以後は前回送信完了時刻ではなく deadline に `P` を加える | 単調時計を使う |
| processing compensation | deadline で送信し、処理に `D < P` かかる | 次の sleep は概ね `P - D` になる | fake clock で厳密に検証する |
| overrun skip | 処理完了時点で1件以上の deadline が過去 | 過去 deadline をすべて飛ばし、現在時刻以上の最初の deadline を次回にする | 現在時刻と一致する deadline は送信し、sleep 0 の連続追送はしない |
| latest state | overrun 中に state が更新される | 次回の1件は送信直前に snapshot した最新 state を含む | backlog を作らない |
| ordering regression | periodic と `0x21` reply が競合する | 共通 sender lock と timer sequence を維持する | 既存回帰 test で確認する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | send 処理時間が周期未満なら、次回 deadline は設定周期で進む | new | unit | no | REDは `_sleep` 注入未対応。GREENで送信時刻 8 / 16 / 24 ms、待機 8 / 6 / 6 ms。追加の構造変更なし |
| refactor-done | send が周期を超えたら、過去 deadline を飛ばして burst 追送しない | edge | unit | no | REDは期待 32 ms に対し 29 ms で即時追送。GREENで 3 ms 待って 32 ms に送信。fake clock fixtureを共通化 |
| refactor-skipped | send が次の deadline ちょうどに完了した場合は、その deadline を飛ばさない | edge | unit | no | REDは期待16 msに対し24 ms。GREENで過去時刻だけをskipし、16 msで送信。追加構造変更なし |
| refactor-done | overrun 中に state を更新すると、次回 report は最新 state を送る | regression | unit | no | 既存回帰testを実時間待機からfake clockへ変更。遅延中は1件だけ、次回32 msで最新X stateを送ることを確認 |
| refactor-skipped | sender lock、timer、subcommand reply 順序を維持する | regression | unit | no | report loop unit 8件がpass。共通sender実装は変更せず追加構造変更なし |
| green | 8 ms設定の実機 completion interval が旧 p50 8.979 ms より8 msへ近づく | characterization | hardware | yes | 承認済み `usb:0` runで p50 8.038 ms / p95 9.093 ms。初期subcommand holdoffをまたぐ長いintervalは別記 |

## 8. 文書検証計画

公開文書は変更しない。initial design の周期説明を実装と unit test に照合し、実機 125 Hz を保証する表現にしない。

## 9. 設計メモ

- `next_deadline` は整数 nanosecond で保持し、float の累積加算を避ける。
- 起動時の単調時計を基準に最初の deadline を1周期後へ置く。
- send 完了後に `next_deadline += period` とし、deadline が現在時刻より前なら周期の整数倍だけ進めて現在時刻以上の deadline にする。
- state の queue は追加せず、既存の `send_current_input()` が sender lock 内で snapshot する境界を維持する。
- fake clock 用の sleep 注入は `ReportLoop` 内部の test seam とし、公開 `SwitchGamepad` API へ露出しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/report_loop.py` | modify | fixed deadline scheduler、clock / sleep test seam |
| `tests/unit/test_report_loop.py` | modify | processing compensation、overrun skip、latest state の決定的 test |
| `spec/initial/lifecycle.md` | modify | Periodic deadline 契約 |
| `spec/initial/testing.md` | modify | fake clock 検証要件 |
| `spec/hardware-test-log.md` | modify | 承認範囲、実機周期、cleanup |
| `spec/complete/unit_065/PERIODIC_DEADLINE_SCHEDULER.md` | new | 完了した作業仕様と TDD 記録 |
| `tmp/hardware/issue-103/` | new, ignored | disposable timing harness、pre/postflight、timing / trace / summary artifact |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_report_loop.py::test_periodic_loop_uses_fixed_deadlines_when_send_takes_time -q` | red, expected | `ReportLoop.__init__()` が `_sleep` を受け取らず失敗。deadline scheduler 未実装を確認 |
| 同 test の GREEN 再実行 | pass | 1 passed。2 ms の送信処理時間を次の sleep から差し引き、8 ms deadline 間隔を維持 |
| `uv run pytest tests/unit/test_report_loop.py::test_periodic_loop_uses_fixed_deadlines_when_send_takes_time tests/unit/test_report_loop.py::test_periodic_loop_skips_overdue_deadlines_without_burst_catch_up -q` | red, expected | 1 passed, 1 failed。21 ms の send 後、将来の 32 ms deadline ではなく 29 ms で即時追送した |
| 同 2 tests の GREEN 再実行 | pass | 2 passed。overrun 後は過去 deadline を飛ばし、現在時刻以上の最初の deadline まで待機 |
| `uv run --no-sync pytest tests/unit/test_report_loop.py::test_periodic_loop_sends_when_processing_ends_on_next_deadline -q -p no:cacheprovider` | red, expected | 次のdeadlineちょうどの16 msを飛ばし、24 msに送信した |
| 同 test の GREEN 再実行 | pass | 1 passed。次のdeadlineと現在時刻が一致する場合はskipせず送信 |
| `uv run pytest tests/unit/test_report_loop.py -q` | pass | 8 passed。deadline、latest state、sender lock、timer、subcommand reply holdoff / 順序を確認 |
| `uv sync --dev` | environment failure | workspace内 `.uv-cache/sdists-v9/.git` 作成が実行環境のmetadata保護で拒否された。依存解決や製品コードの失敗ではない |
| `$env:UV_CACHE_DIR=<user-temp-cache>; uv sync --dev` | pass | 53 packages resolved、41 packages checked。`.venv/.lock` 警告は出たが終了コード0 |
| `$env:RUFF_CACHE_DIR=<user-temp-cache>; uv run --no-sync ruff format --check .` | pass | 99 files already formatted |
| `$env:RUFF_CACHE_DIR=<user-temp-cache>; uv run --no-sync ruff check .` | pass | All checks passed |
| `uv run --no-sync ty check --no-progress` | pass | All checks passed |
| `uv run --no-sync pytest tests/unit -q --basetemp=<user-temp> -p no:cacheprovider` | pass | 459 passed in 3.07s |
| `uv run --no-sync pytest tests/integration -q --basetemp=<user-temp> -p no:cacheprovider` | pass | 131 passed in 2.70s |
| `uv run --no-sync python tools/csr_bd_addr_probe.py --adapter usb:0 --output tmp/hardware/issue-103/adapter-identity-preflight.json` | pass | HCI / CSR address `0E:08:71:C0:B4:5C` 一致、`adapter_closed` |
| `uv run --no-sync python tmp/hardware/issue-103/periodic_deadline_timing_benchmark.py --adapter usb:0 --profile-path tmp/hardware/issue-93/direct-pro-profile.json --artifact-dir tmp/hardware/issue-103/periodic-deadline-8ms-01 --baseline-summary tmp/hardware/issue-93/periodic-no-drain/02-8ms/benchmark-summary.json --implementation-commit 50bba8e --reconnect-timeout 10 --report-period-us 8000 --samples 200 --sample-timeout 10` | pass | connected、200件。interval p50 8.038 ms / p95 9.093 ms、旧 p50 8.979 ms から -0.942 ms。trace error 0、close errorなし |
| `uv run --no-sync python tools/csr_bd_addr_probe.py --adapter usb:0 --output tmp/hardware/issue-103/adapter-identity-postflight.json` | pass | preflightと同じidentity、`adapter_closed` |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 実装判断には not required。follow-up の性能確認として2026-07-23に実行済み |
| 承認範囲 | dedicated `usb:0` open、read-only identity、既存bond active reconnect、通常subcommand応答、neutral-only 8 ms Periodic 200件、neutral close、adapter release、postflight。新規pairing、advertising、button / stick / IMU、BD_ADDR書換えは対象外 |
| adapter | CSR8510 A10 / WinUSB / `usb:0`、identity `0E:08:71:C0:B4:5C` |
| 実行遮断 | 環境変数による遮断は採用せず、会話上の明示承認、具体command、cleanup planを確認した |
| log / artifact | `spec/hardware-test-log.md`、`tmp/hardware/issue-103/` |
| cleanup | `close(neutral=True)`、`transport_close_complete`、close errorなし。postflight identity一致、`adapter_closed` |

## 13. 先送り事項

- 長時間安定性、Switch 側反映時刻、別 adapter / OS / firmware での周期は未検証。
- 200件中2 interval（index 6: 952.384 ms、index 10: 711.700 ms）は初期subcommand reply 16件と既存 periodic holdoff をまたいだ。steady cadence と reply holdoff を分離した追加runは未実行。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
