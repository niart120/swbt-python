# 通常入力 readiness 仕様書

## 1. 概要

### 1.1 目的

GitHub Issue #149 に従い、`pair()` / `reconnect()` などの接続 API が正常終了した時点で、
controller の通常入力経路が接続初期化中の automatic input holdoff によって抑止されない
契約を定義する。

Periodic / Direct は同じ公開契約を共有する。ただし、通常入力の送信主体は異なる。
Periodic は library の `ReportLoop`、Direct は呼び出し側の明示 input operation が送信を
所有する。このため、共通の完了条件を特定の periodic report の送信有無では定義しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | Pair / active reconnect 完了直後の 50 ms press / release が、300 ms holdoff 中に local state 上で上書きされ、wire へ出ない | https://github.com/niart120/swbt-python/issues/149 |
| user decision | 「短時間入力を一度も欠落させない」キュー型契約には強めず、接続初期化由来の抑止だけを除く | conversation |
| current implementation | `ReportSender` は全 `0x21` reply 受理後に automatic input を 300 ms 抑止し、明示 input は抑止しない | `src/swbt/report_loop.py` |
| pre-change lifecycle | protocol ready で接続 waiter を起こした後、Periodic の `ReportLoop` を開始していた | 変更前の `src/swbt/gamepad/runtime.py` |
| prior validation | 300 ms は fake / hardware 比較後に維持され、ready 後の新規 subcommand は未観測 | `spec/complete/unit_082/REPLY_HOLDOFF_VALIDATION.md` |
| prior readiness contract | Periodic / Direct は supported report mode と nonzero player lights による protocol ready を共有する | `spec/complete/unit_069/CONTROLLER_HANDSHAKE_READINESS.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Periodic controller 利用者 | `await pair()` / `await reconnect()` の直後に `apply()` し、既定 8 ms 周期より長い 50 ms 後に neutral へ戻す | 接続初期化で設定された holdoff に全送信機会を奪われず、通常 cadence の `0x30` に入力が現れる | 1周期未満の全 state 遷移配送は保証しない |
| Direct controller 利用者 | 接続 API 完了直後に `send()` または意味的入力操作を呼ぶ | protocol ready 後の明示 input が従来どおり transport へ送られる | Direct に automatic report や待機用 neutral probe を追加しない |
| diagnostics 利用者 | protocol ready から通常入力 readiness までを trace する | protocol handshake 完了と public 接続 API の完了境界を区別できる | report counter のポーリングを利用者へ要求しない |
| timeout / cancellation 利用者 | Periodic が protocol ready 後の holdoff 終了を待っている間に timeout、cancel、disconnect が起きる | 接続成功を返さず、既存の cleanup と失敗 semantics を維持する | 接続 timeout budget を新たに加算しない |

## 2. 対象範囲

- `pair()`、`reconnect()`、`connect()` と対応する `try_*` API の正常終了条件。
- これらへ委譲する `create_profile()` の object return 条件。
- protocol ready と通常入力 readiness の内部境界。
- Periodic の automatic input holdoff と接続完了の同期。
- Direct の明示 input 経路が同じ公開契約を満たすことの回帰確認。
- timeout、cancellation、disconnect、close、session reset。
- diagnostics、公開 API docstring、利用者向け docs、初期設計文書の整合。
- fake transport による Pair / active reconnect と全 controller profile の検証。
- Pro Controller の代表的な実機確認。

## 3. 対象外

- `apply()` の各 state 遷移をキューに保存し、必ず1回以上配送する機能。
- report period より短い press / release を含む全 transient input の配送保証。
- Periodic の latest-state coalescing semantics の変更。
- Direct に automatic `0x30`、待機用 neutral probe、`ReportLoop` を追加すること。
- 300 ms holdoff の値、開始条件、ready 後 subcommand への適用範囲の変更。
- steady-state report cadence、deadline scheduler、Bluetooth transport の変更。
- HID report ID、byte layout、timer、IMU encoding の変更。
- Joy-Con 実機確認。共通 runtime / sender 以外へ変更が及ぶ場合は実機要否を再評価する。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_069/CONTROLLER_HANDSHAKE_READINESS.md`
- `spec/complete/unit_081/PROTOCOL_HANDSHAKE.md`
- `spec/complete/unit_082/REPLY_HOLDOFF_VALIDATION.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| 300 ms automatic input holdoff | required | done | unit_082 で implementation fact と実機比較を記録済み。値と適用範囲は変更しない |
| Switch HID / report bytes | not applicable | not applicable | `0x21` / `0x30` の ID、layout、payload を変更しない |
| Bumble / transport | not applicable | not applicable | transport の受理契約と実装を変更しない |
| OS / driver / adapter | required | done | no-open列挙とPnP driver情報で、Windows 11、`usb:0`、CSR8510 A10 `0A12:0001`、WinUSB / libwdiを実行直前に確認 |

### 5.1 事実

- `send_subcommand_reply()` は transport の受理後に holdoff deadline を更新する。
- `send_automatic_input()` は同じ sender lock 内で deadline を検査し、期限前は送信しない。
- Direct の `send_input()` は automatic input ではなく、holdoff を検査しない。
- protocol ready を成立させる最後の reply 自身が holdoff deadline を更新する。
- 変更前の runtime は接続 waiter を起こしてから Periodic の `ReportLoop` を開始していた。

### 5.2 推論

- public 接続 API の完了条件を「最初の periodic `0x30` 送信」にすると、automatic report を
  持たない Direct では成立しない。
- 共通契約は report の有無ではなく、「その reporting mode の通常入力経路が接続初期化由来の
  抑止を受けない状態」として定義できる。
- Periodic では protocol ready 時点の holdoff deadline だけを snapshot して待つと、待機中に
  受理した追加 reply が deadline を延長する競合を見落とす。readiness 公開前に受理された
  最新 reply の deadline を反映する必要がある。

### 5.3 未検証

- protocol ready 後に Switch が新しい subcommand を送る条件と頻度は未確認である。
- 接続完了後に届いた新しい reply が automatic input を再び一時抑止する挙動は、本仕様で変更しない。
- active reconnect、Joy-Con、別adapter、別OS、別firmwareでの修正後50 ms inputは未検証である。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| protocol ready | supported report mode と nonzero player lights が揃い、成立させた reply が transport に受理される | protocol handshake を停止・回収し、通常入力 readiness の評価へ進む | protocol ready 自体の predicate は変更しない |
| Periodic readiness 待機 | protocol ready だが最新 reply の automatic input holdoff 中 | public 接続成功を返さず、connection state は接続処理中のままとする | 外部の固定 sleep や report counter polling は不要 |
| Periodic readiness 成立 | readiness 公開前に受理された最新 reply の holdoff deadline に到達する | `ReportLoop` を開始してから接続成功を公開する | probe report の成功を条件にしない |
| Periodic 最初の通常 cadence | 接続 API 完了後に local state が更新される | 次の通常 cadence から latest state を送信対象にできる | 各 state の配送保証ではない |
| Direct readiness 成立 | protocol ready に到達する | 明示 input 経路が holdoff 対象外であるため、同じ接続成功契約を直ちに満たす | automatic deadline の経過を待たない |
| Direct 無送信 | Direct の接続 API が完了する | 待機確認のための `0x30` を自動送信しない | lifecycle 全体で ReportLoop を持たない |
| 追加 reply | Periodic が readiness 待機中に新しい reply を transport が受理する | 待機 deadline を最新値へ延長し、古い deadline では成功を公開しない | holdoff 更新と readiness 公開を競合させない |
| readiness 公開後の reply | 接続 API 完了後に新しい reply を受理する | 既存方針どおり automatic input holdoff を適用できる | 永続的な「無抑止」は保証しない |
| timeout | Periodic が readiness 待機中に接続操作の既存 deadline を超える | timeout として失敗し、cleanup する | 300 msを別 budget として加算しない |
| cancellation | readiness 待機中の接続 task を cancel する | readiness waiter と接続処理を停止し、既存 cancellation / cleanup semantics を維持する | background waiter を残さない |
| disconnect | readiness 公開前に link が切れる | 接続成功を返さず、失敗として待機 API を起こす | stale deadline を次 session へ持ち越さない |
| session reset | close 後に再度 open / pair / reconnect する | 前 session の holdoff deadline と readiness を再利用しない | sender は session 単位 |
| 50 ms入力 | 既定 8 ms Periodic の接続 API 完了直後に press、50 ms後に release | 初期化 holdoff に全 cadence を抑止されず、press state の periodic `0x30` が1件以上観測できる | 50 msという検証条件であり、任意の短時間入力保証ではない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | reply 受理直後の Periodic 通常入力 readiness は holdoff 期限前に成立せず、境界時刻で成立する | new | unit | no | 注入時計で wall clock 非依存に確認 |
| green | readiness 待機中に追加 reply を受理すると、古い期限では成立せず最新期限まで待つ | edge | unit | no | deadline snapshot ではなく最新値を再評価 |
| green | protocol ready 後も holdoff 中の Periodic `pair()` は完了せず、期限到達後に完了する | regression | integration | no | controlled readiness gate で Pair 経路を確認 |
| green | Periodic active reconnect は protocol ready 後の holdoff 終了まで `status="connected"` を返さない | regression | integration | no | controlled readiness gate で `try_reconnect()` を確認 |
| green | Direct の Pair / active reconnect は protocol ready で完了し、holdoff 経過や automatic `0x30` を要求しない | regression | integration | no | Pro / Joy-Con L/R を parameterize |
| green | `connect()`、`try_connect()`、`create_profile()` は選択した Pair / reconnect と同じ通常入力 readiness を使う | regression | integration | no | connect 2入口と6具象create_profileのpair委譲を確認 |
| green | Periodic の接続完了直後に50 ms保持した stateが通常 cadence の `0x30` に現れる | regression | integration | no | 既定8 msのButton Aとneutralを確認。全transient配送へ一般化しない |
| green | readiness 待機中の timeout は成功を返さず既存 cleanup を完了する | edge | integration | no | timeout 後close、`stage=input_readiness`、次回Pairのfresh readinessを確認 |
| green | readiness 待機中の cancellation / disconnect は waiter を残さず、次 session が stale readiness を再利用しない | edge | integration | no | cancellation red後にwaiter回収を追加。disconnect失敗の`stage=input_readiness`も確認 |
| green | Pro Controller の Pair または active reconnect 完了直後の50 ms Button Aがperiodic `0x30`とSwitch UIに反映される | characterization | hardware | yes | fresh PairでA付き周期`0x30`を7件記録し、利用者が対象機器側の反映を確認 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/api.md` | 接続 API 完了後に入力を開始する利用者 | 本仕様 §6 | `uv run --group docs mkdocs build --strict` | pass | Periodic / Direct 共通契約と方式差を反映。未解決なし |
| `spec/initial/architecture.md` | runtime と report loop の所有境界を確認する maintainer | 本仕様 §6 / §9 | `uv run --group docs mkdocs build --strict` | pass | report loop の開始時点を通常入力 readiness と一致。未解決なし |
| `spec/initial/lifecycle.md` | maintainer が protocol ready と通常入力 readiness の順序を追う | 本仕様 §6 / §9 | `uv run --group docs mkdocs build --strict` | pass | timeout / disconnect を含む状態遷移を反映。未解決なし |
| `spec/initial/testing.md` | fake / hardware test の分担を確認する maintainer | 本仕様 §7 | `uv run --group docs mkdocs build --strict` | pass | 50 ms は代表条件であり全 transient 保証ではないと明記。未解決なし |
| public API docstring / `docs/api.md` / `docs/usage.md` / `docs/release-notes.md` / `docs/hardware.md` | 接続後に入力する利用者と実機確認担当者 | 本仕様 §6 / §7、`spec/hardware-test-log.md` | docs build + `docs-quality-review` | pass | 契約、非保証、50 ms実機観測、未確認範囲を照合。must-fix なし |

自然言語の意味要件を固定語句の存在・不在 assertion に置き換えない。公開文書の事実性、
操作順、未保証範囲は正本との照合と `docs-quality-review` で確認する。

## 9. 設計メモ

### 9.1 共通契約

```text
connection API success
    implies
the reporting mode's normal input path is not blocked
by a holdoff already created during connection initialization
```

「通常入力経路」は reporting mode ごとに次を指す。

| reporting mode | 通常入力経路 | readiness の具体条件 |
|---|---|---|
| Periodic | local latest stateを通常 cadence で送る `ReportLoop` | readiness 公開前に受理された最新 reply の automatic input holdoff が終了済み |
| Direct | `send()` と意味的 input operation による明示送信 | protocol ready で明示 input sender が利用可能 |

この違いは公開契約の差ではなく、送信所有者の違いである。

### 9.2 `connected` の意味

`connected` と接続 API の正常終了は、protocol ready だけでなく通常入力 readiness も満たす。
diagnostics では次を分ける。

- `protocol_ready`: handshake predicate を成立させた reply が受理され、handshake task を
  停止・回収した時点。
- `input_ready`: reporting mode ごとの通常入力 readiness が成立した時点。
- `active_reconnect_result(status="connected")`: `input_ready` 後。

Direct では `protocol_ready` と `input_ready` が連続して記録される。Periodic では通常、
最後の初期化 reply が設定した holdoff の残り時間だけ間隔が空く。

`input_ready` を接続成功の linearization point とする。sender の同期境界でこれより前に
受理された reply は readiness 待機へ反映し、これより後に受理された reply は接続後の
通常処理として扱う。coroutine を再開する wall-clock 上の瞬間と Bluetooth event の到着を
完全に排他する保証は置かない。

### 9.3 holdoff と readiness の同期

readiness 判定は、holdoff deadline の単発 snapshot や `sleep(0.3)` で実装しない。
subcommand reply の transport 受理、deadline 更新、readiness の再評価を同じ sender の
同期境界で順序付ける。

readiness 公開前に追加 reply が受理された場合、その reply が更新した deadline を待つ。
readiness 公開後に受理された reply は既存の automatic input holdoff として扱う。本仕様は
ready 後 holdoff の廃止や initializing 限定化を行わない。

### 9.4 ReportLoop の開始

Periodic の `ReportLoop` は通常入力 readiness 成立後に開始する。接続完了確認のための
neutral probe は送らない。loop の最初の deadline は開始時刻から `report_period_us` 後とし、
接続完了直後の `apply()` はその時点の latest state を次回 cadence の候補にする。

Direct は lifecycle 全体で通常 `ReportLoop` を持たない。handshake 中の
`handshake_bootstrap` / `handshake_report_mode` は `ProtocolHandshake` が所有する内部
automatic neutral であり、Direct の通常入力には数えない。

### 9.5 transient input の境界

Periodic は latest-state model を維持する。複数の `apply()` が同じ通常 cadence より前に
完了した場合、中間 state は後続 state に統合され得る。これを欠落防止 queue へ変更しない。

Issue #149 の 50 ms / 8 ms は通常なら複数 cadence を含むため、接続初期化 holdoff による
全機会の抑止を検出する代表条件として使う。50 msを任意の環境、任意の period に対する
最小配送時間として公開しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/report_loop.py` | modify | automatic input readiness の待機と reply deadline 更新の同期 |
| `src/swbt/gamepad/runtime.py` | modify | protocol ready 後の mode 別 readiness、event、timeout、cleanup、diagnostics |
| `src/swbt/gamepad/interface.py` | modify | 公開接続 API docstring の readiness 契約 |
| `tests/unit/test_report_loop.py` | modify | deadline 境界と追加 reply の決定的 unit test |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | Pair / reconnect / Direct / Periodic / failure lifecycle |
| `tests/hardware/test_reply_holdoff.py` | modify | fresh Pair 完了直後50 ms入力の実機 gate |
| `spec/initial/api.md` | modify | 接続成功後の通常入力契約 |
| `spec/initial/architecture.md` | modify | ReportLoop の生成時点と runtime の wait 所有 |
| `spec/initial/lifecycle.md` | modify | protocol ready と input ready の状態遷移 |
| `spec/initial/protocol.md` | modify | holdoff 対象となる ReportLoop の開始境界を明確化 |
| `spec/initial/testing.md` | modify | fake / hardware completion gate |
| `docs/api.md` | modify | 利用者向け接続 API 説明 |
| `docs/usage.md` | modify | 接続後の入力開始手順と latest-state の非保証 |
| `docs/release-notes.md` | modify | 修正内容、互換境界、実機未確認範囲 |
| `docs/hardware.md` | modify | `protocol_ready` と `input_ready` の診断手順 |
| `spec/hardware-test-log.md` | modify | 承認後の実機条件と結果 |

実装時に実ファイル構成を再確認し、内部 helper 名をこの表へ合わせるためだけの変更は行わない。

## 11. 検証

| command | result | notes |
|---|---|---|
| `git diff --no-index --check -- NUL spec/complete/unit_086/NORMAL_INPUT_READINESS.md` | pass | 新規 untracked spec に whitespace error なし。差分ありを表す exit 1、error output なし |
| `uv run pytest tests/unit/test_report_loop.py::test_automatic_input_readiness_waits_until_reply_holdoff_boundary -q` | pass | red は `_sleep` 未対応の `TypeError`、green は `1 passed` |
| `uv run pytest tests/unit/test_report_loop.py -q` | pass | first cycle 後 `11 passed` |
| `uv run pytest tests/unit/test_report_loop.py::test_additional_reply_extends_automatic_input_readiness_wait -q` | pass | first cycle の再評価 loop で green、`1 passed` |
| targeted Pair / Direct readiness integration | pass | Periodic red は waiter 未呼び出しで timeout。runtime 分離後、既存境界を含め `9 passed` |
| targeted active reconnect readiness integration | pass | Periodic `1 passed`、Direct Pro / Joy-Con L/R `3 passed` |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py::test_periodic_input_after_pair_is_not_blocked_by_initialization_holdoff -q` | pass | 接続完了後50 msのButton Aと後続neutralをperiodic `0x30`で確認 |
| targeted timeout / cancellation / disconnect readiness integration | pass | timeout後の再Pair、task cancellation、disconnect、既存reconnect cancellationを含む `4 passed` |
| targeted connect / create_profile delegation integration | pass | connect 2入口と6具象create_profileのpair委譲、計 `8 passed` |
| `uv run ruff format --check .` | pass | `106 files already formatted` |
| `uv run ruff check .` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest tests/unit` | pass | final gateは`450 passed in 2.09s` |
| `uv run pytest tests/integration` | pass | final gateは`165 passed in 3.05s` |
| `uv run --group docs mkdocs build --strict` | pass | strict build 成功 |
| `uv run pytest --collect-only tests/hardware/test_reply_holdoff.py -q` | pass | 修正後harnessを含む10件を収集。adapter / Switch は開いていない |
| approved Pro Controller fresh Pair hardware gate | observed-pass | commandはdiagnostics reasonのtest bugで`1 failed in 5.58s`。artifactはA付き周期`0x30`を7件、neutral、cleanupを記録し、利用者がUI反映を確認。test bugは`reason=periodic`へ修正 |
| hardware artifact review | pass | debug PDUのtimer `0x15`–`0x1B`でButton A bitを7件、次のtimer `0x1C`でneutralを確認 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for completion |
| 承認範囲 | Pro Controller の Pair または active reconnect、HID advertising、subcommand handling、通常 periodic report、50 ms Button A press / release、neutral close、adapter release |
| adapter | 実行直前に対象 adapter、identity、driver を確認する。過去の `usb:0` / CSR8510 A10 / WinUSB を現在値として仮定しない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、Switch-facing 動作、cleanup plan で管理する |
| log / artifact | OS、Python / Bumble / swbt-python version、Switch model / firmware、profile / route、`protocol_ready`、`input_ready`、reply、periodic `0x30`、UI 観測を保存する |
| cleanup | neutral、ReportLoop停止、disconnect、transport close、adapter release。失敗時も同じ項目を確認する |
| 実行結果 | fresh Pairでobserved-pass。詳細は`spec/hardware-test-log.md`の2026-07-26 unit_086記録 |

実機 test は自動 trace の periodic `0x30` と利用者による Switch UI 観測を分けて記録する。
明示承認なしに `bumble` / `hardware` marker を実行しない。

## 13. 先送り事項

- ready 後 subcommand の発生条件と、steady-state holdoff の必要性。観測できた場合は unit_082
  の後続として別 work unit / Issue に分ける。
- 各 Periodic state 遷移を配送する queue。latest-state API の別契約になるため本仕様には含めない。
- report period に対する最小 transient input duration の公開保証。OS / scheduler / transport を
  含む保証設計が必要なため本仕様には含めない。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] Periodic / Direct に等価な公開契約を定義した
- [x] 「最初の periodic `0x30`」を共通 completion gate から除外した
- [x] transient input の全配送を対象外として明記した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 実装と local gate を完了した
- [x] 公開文書を更新し `docs-quality-review` を完了した
- [x] 明示承認付き実機 gate を完了した
