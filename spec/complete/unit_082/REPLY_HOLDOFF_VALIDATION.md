# reply 後 automatic input holdoff 検証仕様書

## 1. 概要

### 1.1 目的

Issue #139 に従い、`0x21` subcommand reply 後の 300 ms automatic input holdoff を、fake transport と実機で比較可能にする。実機比較の結果に基づいて値と適用範囲を維持・変更・削除のいずれかに決定する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | 300 ms の必要性と handshake / Periodic / Direct の適用範囲を比較する | https://github.com/niart120/swbt-python/issues/139 |
| 既存実装 | reply 後に全 automatic input を 300 ms 抑制する | `src/swbt/report_loop.py` |
| 実装記録 | 値を未検証の互換策として維持し、A/B 検証を後続へ分離した | `spec/complete/unit_081/PROTOCOL_HANDSHAKE.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| fake transport | `0x21` reply と automatic `0x30` | reply 時刻、抑制中の不送信、期限到達後の最初の送信を決定的に記録できる | wall clock に依存しない |
| Direct controller | reply 後の明示入力または trailing neutral | automatic input ではないため holdoff されない | Direct の自動送信は追加しない |
| Switch 実機 | 300 ms、短縮値、抑制なしの各設定 | pairing、protocol ready、入力反映、切断 cleanup を同一条件で比較する | 明示承認なしに実行しない |

## 2. 対象範囲

- `ReportSender` の holdoff clock を注入可能にする。
- fake transport が reply / automatic input の送信順と時刻関係を記録する characterization test を追加する。
- 300 ms、短縮値、抑制なしを選択できる実機検証手段と hardware test を追加する。
- 実機比較、`spec/hardware-test-log.md` の記録、設計文書の方針決定を行う。

## 3. 対象外

- HID report の byte layout 変更。
- steady-state の report cadence 改善。
- Bumble transport の実装変更。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/protocol.md`
- `spec/initial/testing.md`
- `spec/complete/unit_081/PROTOCOL_HANDSHAKE.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| reply 後 holdoff | required | done | 300 ms は implementation fact。2026-07-25のfake characterizationと実機比較で、100 msのPeriodic劣化と0 msのready timeoutを確認し、300 ms維持を決定した |
| Switch HID / report bytes | not applicable | not applicable | report ID と byte layout を変更しない |
| Bumble / transport | required | not applicable | 実装変更はしない。実機時の adapter / Switch 条件だけを記録する |
| OS / driver / adapter | required | pending | hardware-harness 承認後の run metadata を記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| holdoff 開始 | `0x21` reply の送信完了 | injected monotonic clock の reply 時刻から holdoff を開始する | transport 送信完了前には開始しない |
| automatic input | holdoff 中 | `ProtocolHandshake` と `ReportLoop` の automatic `0x30` は送られない | 送信順と時刻を fake transport で確認する |
| 期限到達 | reply 時刻 + holdoff | 最初の automatic `0x30` を送る | 境界時刻を明示する |
| Direct input | holdoff 中の明示 `send_input()` | 送る | Direct に automatic task は作らない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | fake transport が reply、抑制中の不送信、期限到達後の automatic input を injected 時刻で記録する | characterization | unit | no | reply 0.000 s、0.299 s まで不送信、0.300 s に automatic `0x30` を確認 |
| green | holdoff 中の明示 input が送られ、automatic input だけが抑制される | characterization | unit | no | `send_input(..., reason="direct")` は reply 直後に送信される |
| green | 300 ms、100 ms、抑制なしで Pro Periodic / Direct の reconnect と input reflection を比較する | characterization | hardware | yes | 300 msはreconnectとfresh pairingでpass。100 msはPeriodic劣化とA反映未確認。0 msはPeriodic / Directともpublic ready前にtimeoutし、fresh pairingで未認識 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/protocol.md` | maintainer が確定した値と範囲を追う | 2026-07-25実機比較 | `uv run --group docs mkdocs build --strict` | done | docs build pass |
| `spec/hardware-test-log.md` | 実行条件と結果を追う | 実機 artifact | review | done | 300 ms維持判断と未観測範囲を記録 |

## 9. 設計メモ

時刻注入は testability のためだけに追加し、既定値は process monotonic clock とする。holdoff の値、適用範囲、Bumble transport の責務は実機比較前に変更しない。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/report_loop.py` | modify | holdoff monotonic clock の注入 |
| `tests/unit/test_report_loop.py` | modify | fake transport の時刻付き characterization |
| `tests/hardware/test_reply_holdoff.py` | new | 300 ms、100 ms、抑制なしの Periodic / Direct active reconnect 比較 |
| `spec/hardware-test-log.md` | modify | 実機結果と利用者観測 |
| `spec/initial/protocol.md` | modify | 300 ms維持とscope維持の判断 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_report_loop.py -q` | pass | 10 passed。時刻注入した fake transport characterization を含む |
| `uv run ruff format --check src/swbt/report_loop.py tests/unit/test_report_loop.py` | pass | 2 files already formatted |
| `uv run ruff check src/swbt/report_loop.py tests/unit/test_report_loop.py` | pass | all checks passed |
| `uv run ty check --no-progress` | pass | all checks passed |
| `uv run pytest tests/unit/test_report_loop.py tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 149 passed。既存 reply / periodic 順序回帰を含む |
| `git diff --check` | pass | whitespace error なし |
| approved hardware reconnect / fresh pairing comparison | pass with characterization findings | 300 msを維持。100 msはPeriodic劣化とA反映未確認、0 msは公開ready前timeoutとfresh pairing未認識。範囲縮小の実機根拠は得られなかった |
| `uv run ruff format --check .` | pass | 106 files already formatted |
| `uv run ruff check .` | pass | all checks passed |
| `uv run ty check --no-progress` | pass | all checks passed |
| `uv run pytest tests/unit` | pass | 446 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `uv run --group docs mkdocs build --strict` | pass | documentation built successfully |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | dedicated `usb:0`、adapter open、active reconnect、fresh pairing / advertising、neutral periodic report、Direct input、Button A、close、adapter release を会話上で承認済み |
| adapter | `usb:0`。HCI / CSR addressは`0E:08:71:C0:B4:5C`で一致。driverはOS権限不足で今回未再確認 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build/hardware/unit_082/` に trace と pytest log を残す |
| cleanup | neutral、report loop 停止、transport close、adapter release |

## 13. 先送り事項

- ready後にSwitchが新しいsubcommandを送った場合のholdoff必要性は、この実機比較では未観測。initializing限定へ変更する根拠にはしない。後続でready後subcommandを観測できる環境が得られた場合に再評価する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] fake transport、実機、static、unit、integration、docs gateの検証結果を記録した
