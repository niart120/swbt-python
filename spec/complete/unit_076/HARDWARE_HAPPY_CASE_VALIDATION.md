# unit_075 実機 Happy Case 検証 仕様書

## 1. 概要

### 1.1 目的

Issue #125 / unit_075 の `controllers.py` module移動後に、公開controllerの
実機接続経路が既存の構造変更で壊れていないことを、全量ではなく代表的な
happy caseで確認する。実機観測の正本は `spec/hardware-test-log.md` とし、
この仕様書は実行範囲、承認、判定、未検証範囲を束ねる。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | e2e 実機テストを少数の happy caseで実行する | conversation |
| Issue #125 / PR #126 | 6具象controllerを`controllers.py`へ移動した | `https://github.com/niart120/swbt-python/issues/125` / `https://github.com/niart120/swbt-python/pull/126` |
| hardware harness policy | adapter、Switch、承認、cleanup、artifactを記録する | `.agents/skills/hardware-harness/SKILL.md` |
| hardware observation log | 実行条件とtrace artifactの正本 | `spec/hardware-test-log.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library maintainer | adapter-default Pro profileをfresh pairingする | Bumble HID、pairing、protocol ready、profile保存、closeが成功する | dedicated `usb:0`だけを使う |
| protocol maintainer | Switchからsubcommandを受信する | 観測した全subcommandへ`0x21` replyを返し、5秒観測後にerrorなくcloseする | 新しいprofileを使い、全subcommand matrixは対象外 |
| API maintainer | full handshake後にButton Aを送る | Switch UIの登録画面が遷移し、neutral復帰とdisconnect closeが完了する | 画面結果は利用者の目視確認とtraceを分けて記録する |

## 2. 対象範囲

- adapter-default Pro Controllerのfresh pairingとnormal close。
- fresh pairing後のsubcommand observation window。
- full handshake後のButton A、neutral、disconnect close。
- trace artifact、profile、Switch UI目視結果、cleanup結果の記録。
- 既存profileのactive reconnect失敗を、fresh pairingへ切り替えた根拠として記録する。

## 3. 対象外

- 全hardware marker testの実行。
- Joy-Con、Direct controller、multi-address、battery、controller colorの実機検証。
- protocol bytesや実装コードの変更。
- local address rewrite、CSR write、warm reset、dongle identity変更。
- Switch firmwareごとの網羅的保証。

## 4. 関連 docs

- `spec/hardware-test-log.md`
- `tests/hardware/README.md`
- `spec/initial/testing.md`
- `spec/complete/unit_075/CONCRETE_CONTROLLER_MODULE.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | not applicable | 実装やprotocol定数を変更せず、既存hardware testの観測結果だけを記録する |
| Bumble / transport | required | observed | Bumble 0.0.230でHID初期化、L2CAP、pairing、closeを実行しtraceに記録した |
| OS / driver / adapter | required | observed | Windows 11、CSR8510 A10、WinUSB、`usb:0`をhardware logに記録した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| fresh pairing | 新規artifact directory、adapter-default Pro | `classic_pairing`、key store保存、L2CAP、protocol ready、neutral close | `1 passed in 5.23s` |
| subcommand observation | pairing後、5秒以上の観測窓 | `subcommand_rx` 16件すべてにreply、error 0件 | `1 passed in 14.64s` |
| Button A reflection | full handshake後、Button A、neutral | pytest ordering pass、Switch UI画面遷移を利用者が目視確認 | `1 passed in 10.15s` |
| stale profile reconnect | 既存adapter-default profile | HCI authentication failureを検出し、再試行せずcleanupする | fresh pairingへ切り替える判断材料 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | adapter-default Pro fresh pairingがprofile保存とprotocol readyまで完了する | characterization | hardware | yes | `test_switch_adapter_default_profile_fresh_pairing_and_close` |
| refactor-done | 観測subcommand全件へ`0x21` replyを返しerrorなくcloseする | characterization | hardware | yes | 16 receive / 16 reply、unsupported 0、error 0 |
| refactor-done | Button A後のneutral、disconnect、close順序を満たす | characterization | hardware | yes | Switch UI画面遷移を利用者が目視確認 |
| deferred | active reconnectの再成功 | characterization | hardware | yes | stored link keyと現在bond不一致の疑い。fresh pairingなしの再試行はしない |
| deferred | Joy-Con / Direct / battery / colorの追加実機確認 | characterization | hardware | yes | 全量実行を避け、必要な変更単位で後続実施 |

## 8. 文書検証計画

利用者向けdocs、README、公開API docstring、release notesは変更しないため、
`docs-quality-review` は適用しない。`spec/hardware-test-log.md` と本仕様書の
command、artifact、承認、cleanupをtraceと照合する。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/hardware-test-log.md` | maintainer / 実機条件と結果の追跡 | trace、pytest結果、利用者目視 | `git diff --check` | done | none |
| `unit_076` | maintainer / happy caseの範囲と先送り | hardware harness、trace、conversation | diff review | done | none |

## 9. 設計メモ

- hardware logは実機観測の正本であり、unit_075の構造変更仕様へ結果を混ぜない。
- 既存profile reconnectはadapter address一致後に認証失敗した。原因はstored link keyと
  現在のSwitch bond不一致の可能性として扱い、確定事実とはしない。
- fresh pairingでは新しいlink keyをprofileに保存し、Switch UIの登録表示を利用者が確認した。
- protocol上のpytest passとSwitch UI目視結果は別の根拠として記録する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `spec/hardware-test-log.md` | modify | 失敗1本、成功3本、承認、cleanup、artifactを追記 |
| `spec/complete/unit_076/HARDWARE_HAPPY_CASE_VALIDATION.md` | new | 実機happy caseの仕様と判定 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/hardware/test_pairing_profile.py::test_switch_adapter_default_profile_reuses_address_after_normal_close --basetemp=tmp/pytest-hw-075-1 --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir tmp/hardware/unit_075/happy-20260725-pro-reconnect` | failed as expected diagnostic | 1.47s。`HCI AUTHENTICATION_FAILURE_ERROR [0x5]`。cleanup完了、再試行なし |
| `uv run pytest tests/hardware/test_pairing_profile.py::test_switch_adapter_default_profile_fresh_pairing_and_close --basetemp=tmp/pytest-hw-075-2 --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir tmp/hardware/unit_075/happy-20260725-pro-fresh` | pass | 1 passed in 5.23s |
| `uv run pytest tests/hardware/test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands --basetemp=tmp/pytest-hw-075-3 --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir tmp/hardware/unit_075/happy-20260725-pro-subcommands` | pass | 1 passed in 14.64s |
| `uv run pytest tests/hardware/test_close_disconnect.py::test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation --basetemp=tmp/pytest-hw-075-4 --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir tmp/hardware/unit_075/happy-20260725-pro-button-a` | pass | 1 passed in 10.15s。Button Aの画面遷移を目視確認 |
| `git diff --check` | pass | hardware logとspecのwhitespace確認 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | 会話上で`usb:0`、fresh pairing、subcommand observation、Button A、neutral close、adapter closeを明示承認 |
| adapter | dedicated CSR8510 A10 dongle、`usb:0`、WinUSB |
| OS / runtime | Windows 11、Python 3.13.5、Bumble 0.0.230、swbt-python 0.5.1 |
| Switch | Switch 2。firmware versionは今回のrunで未記録 |
| 実行遮断 | 環境変数による遮断は採用せず、会話承認と対象commandで管理した |
| log / artifact | `spec/hardware-test-log.md`、`tmp/hardware/unit_075/happy-20260725-pro-*` |
| cleanup | 各testの`finally`でneutral close、disconnect、transport close、adapter releaseを確認 |

## 13. 先送り事項

- stale profile active reconnectの再成功は、Switch側bond状態を確認してから別hardware runで扱う。
- Joy-Con、Direct、battery、controller colorの実機検証は、それぞれの変更またはrelease gateで必要になった場合に実施する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test Listまたは文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
