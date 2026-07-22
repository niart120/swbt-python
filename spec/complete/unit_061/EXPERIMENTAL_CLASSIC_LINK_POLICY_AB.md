# Experimental Classic Link Policy A/B 仕様書

## 1. 概要

### 1.1 目的

Issue #93 の Direct `send()` の ACL completion delay について、現行 Classic link policy が sniff を許可することと遅延の関係を比較する。production default、公開 API、Direct send の completion contract は変更しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| unit_060 hardware observation | 40 件の neutral Direct send は Bumble の `SNIFF` snapshot 中に完了し、completion delay と ACL drain はほぼ一致した | `spec/hardware-test-log.md` |
| swbt implementation | reference default link policy は role switch `0x0001` と sniff `0x0004` の OR である | `src/swbt/transport/bumble.py:53-67,848-866` |
| Bumble 0.0.230 source | mode `2` は `SNIFF`、mode change が connection の mode / interval を更新する | `.venv/Lib/site-packages/bumble/hci.py:7678-7692`, `.venv/Lib/site-packages/bumble/device.py:6337-6346` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| swbt 開発者 | 現行 policy `0x0005` の neutral Direct send | baseline の completion delay、mode / interval を artifact に残す | 既存挙動を変更しない |
| swbt 開発者 | role-switch-only candidate `0x0001` の neutral Direct send | mode / interval と delay を baseline と比較できる | Active へ遷移すること、sniff を禁止することは未検証 |
| 実機調査者 | paired Switch / dedicated dongle | 各 run の reconnect、close、adapter release を確認する | 明示承認後だけ実行 |

## 2. 対象範囲

- private experimental helper と ignored disposable harness に `allow-sniff` (`0x0005`) と `role-switch-only` (`0x0001`) の選択を追加する。
- 各 process で選択した値だけを Bumble transport module の private reference policy へ一時適用し、終了時に復元する。
- artifact summary と lifecycle trace に比較条件を残す。
- A/B を同一 profile、neutral Direct send、同一 adapter で交互に比較する手順を定義する。

## 3. 対象外

- `src/swbt/` の production default、公開 constructor、公開 diagnostics schema の変更。
- Bumble の patch / fork、HCI exit-sniff command、link policy の恒久設定。
- ACL drain の削除、bounded enqueue、periodic report loop の評価。
- pairing、button / stick input、BD_ADDR write / restore、physical power cycle。

## 4. 関連 docs

- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/complete/unit_060/HCI_ACL_COMPLETION_CORRELATION.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | neutral state の既存 report だけを使う |
| Bumble / transport | required | done | `0x0005` は role switch と sniff の reference bits。`0x0001` はその role-switch bit のみを残す比較候補であり、効果は実機で観測する |
| OS / driver / adapter | required | done | Windows 11 / CSR8510 A10 / WinUSB / Bumble 0.0.230 の既存 paired profile に限定する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| allow-sniff baseline | harness に `allow-sniff` を指定 | Bumble が `0x0005` を設定し、summary と trace に条件が残る | 現行 reference default と同じ |
| role-switch-only candidate | harness に `role-switch-only` を指定 | Bumble が `0x0001` を設定し、summary と trace に条件が残る | mode が Active になる保証はない |
| process cleanup | benchmark 成功・失敗 | private reference policy を元へ戻し、neutral close / adapter release を行う | process 間に設定を持ち越さない |
| A/B artifact | 各 policy の benchmark | policy ごとの artifact directory を使う | JSONL に Bluetooth address、link key、payload を追加しない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `allow-sniff` 指定が `0x0005` を選び、summary に比較条件を残す | new | unit | no | selector は `test_allow_sniff_policy_selects_current_reference_settings`、harness の `--help` で option を確認。actual artifact は hardware item で確認 |
| green | `role-switch-only` 指定が `0x0001` を選び、終了時に元の private reference policy を復元する | regression | unit | no | `test_role_switch_only_policy_restores_reference_value_after_context` で確認 |
| green | 不正な policy 名は adapter open 前に失敗する | edge | unit | no | `test_unknown_policy_is_rejected_before_adapter_open` で確認 |
| deferred | policy A/B/A/B/A/B の各 run が active reconnect、neutral send、close、postflight を記録する | characterization | hardware | yes | `0x0001` は neutral send 3 件後に reason `19` で切断されたため反復を停止。baseline と recovery のみ完了 |

## 8. 文書検証計画

not applicable。公開文書と公開 API は変更しない。

## 9. 設計メモ

`0x0001` がこの Switch 接続で sniff 遷移を抑えるかは未検証である。比較の判定は policy 名ではなく、Direct timing event の `classic_mode_*` / `classic_interval_*` と completion delay 分布で行う。

各 policy は別 Python process で実行し、process 内でも元の module value を `finally` で復元する。実行順は drift を減らすため `allow-sniff`, `role-switch-only` を 3 回ずつ交互にする。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_experimental_classic_link_policy.py` | new | private policy selector と temporary override context |
| `tmp/hardware/issue-93/direct_send_timing_benchmark.py` | modify | ignored disposable harness の policy selector と summary metadata |
| `tests/unit/test_experimental_classic_link_policy.py` | new | adapter を開かない selector / restoration test |
| `spec/complete/unit_061/EXPERIMENTAL_CLASSIC_LINK_POLICY_AB.md` | new | 比較条件、TDD、実機承認境界 |
| `spec/hardware-test-log.md` | modify | 承認済み A/B 実行時だけ追記 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_experimental_classic_link_policy.py -q` | passed | RED は private helper 未実装による import error、GREEN は 1 passed |
| `uv run pytest tests/unit/test_experimental_classic_link_policy.py -q` | passed | temporary override の RED は helper 未実装による import error、GREEN は 2 passed |
| `uv run pytest tests/unit/test_experimental_classic_link_policy.py -q` | passed | 3 passed。未知名は `ValueError` で拒否 |
| `uv run python tmp/hardware/issue-93/direct_send_timing_benchmark.py benchmark --help` | passed | adapter を開かずに `--link-policy {allow-sniff,role-switch-only}` を確認 |
| `uv run ruff check tmp/hardware/issue-93/direct_send_timing_benchmark.py` | passed | ignored disposable harness も個別に確認 |
| `uv run ruff format --check .` | passed | 102 files already formatted |
| `uv run ruff check .` | passed | All checks passed |
| `uv run ruff format --check tmp/hardware/issue-93/direct_send_timing_benchmark.py` | passed | ignored harness も個別に確認 |
| `uv run ruff check tmp/hardware/issue-93/direct_send_timing_benchmark.py` | passed | All checks passed |
| `uv run ty check --no-progress` | passed | All checks passed |
| `uv run pytest tests/unit` | passed | 461 passed |
| `uv run pytest tests/integration` | passed | 134 passed |
| `git diff --check` | passed | tracked diff の whitespace error なし |
| approved allow-sniff characterization | passed | `0x0005`、DEBUG 120 event は全件 success、completion delay p50 9.894 ms / p95 12.604 ms、mode 2 / raw interval 8 |
| approved role-switch-only characterization | stopped | `0x0001`、HID channel open 後に neutral send 3 件で reason `19` (`REMOTE_USER_TERMINATED_CONNECTION`)。summary は未生成 |
| approved recovery characterization / postflight | passed | `0x0005` で reconnect / neutral send / `transport_close_complete`。postflight は `adapter_closed` |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | implementation は不要。A/B characterization は必要 |
| 承認範囲 | dedicated adapter、policy A/B、active reconnect、neutral Direct send、DEBUG file output、`close(neutral=True)`、adapter release、postflight を command とともに確認する |
| adapter | `usb:0`。実行直前に CSR8510 A10 / WinUSB を read-only に確認する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | policy 別 summary、timing JSONL、lifecycle trace、preflight / postflight、OS、driver、Bumble version を記録する |
| cleanup | policy module value を復元し、logger handler を外し、`close(neutral=True)`、`transport_close_complete`、postflight の `adapter_closed` を確認する |

## 13. 先送り事項

- `0x0001` が有意差を示しても、production default 変更の判断は Switch input reflection、reconnect、消費電力を含む別作業単位で行う。
- 有意差がなければ、別 dongle / OS driver / Bumble version を比較する adapter characterization を次の候補とする。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] disposable harness の unit test と実装を完了した
- [x] 承認済み A/B characterization を実行し、candidate の stop condition を記録した
