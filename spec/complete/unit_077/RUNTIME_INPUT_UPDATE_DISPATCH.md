# 入力状態更新の送信方式分岐集約

## 1. 概要

`ControllerRuntime` の意味的入力操作に重複していた Periodic / Direct の
送信方式分岐を、状態変換を受け取る private helper へ集約する。各公開操作は
入力値の検査と `InputState` の変換だけを定義する。

## 2. 起点 / source

| source | 内容 |
|---|---|
| GitHub Issue #129 | runtime の入力状態更新分岐を集約する |
| `spec/initial/architecture.md` | runtime、state store、report sender の責務境界 |
| `spec/initial/testing.md` | fake transport による完了検証 |

## 3. 対象範囲

- `press()`、`sticks()`、`imu()`、`release()`、`neutral()` の実行規則を集約する。
- Periodic では `InputStateStore.update()` を使う。
- Direct では既存の operation lock、送信成功後 commit、profile 検査を維持する。

## 4. 対象外

- `tap()`、`apply()`、`send()` の統合。
- report bytes、timer、IMU encoding、送信周期、公開型階層の変更。
- 実機、Bumble adapter、Switch-facing command の実行。

## 5. 根拠監査

| 項目 | 状態 | 理由 |
|---|---|---|
| Switch HID / report bytes | not applicable | report builder と sender の入力値を変更しない |
| Bumble / adapter | not applicable | transport lifecycle を変更しない |
| runtime state commit | done | Issue #129 と既存 `ReportSender`、fake transport integration test を照合する |

## 6. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | Periodic の意味的操作が即時送信せず state だけを更新する | characterization | integration | no | 既存 fake transport test を維持する |
| refactor-done | Direct の意味的操作が1件送信し、成功後だけ state を commit する | characterization | integration | no | `test_direct_semantic_operations_send_once_and_commit_after_success` を維持する |
| refactor-done | Direct の送信失敗で snapshot を変えず、並行操作で state を失わない | regression | integration | no | 既存 failure / serialization test を維持する |
| refactor-done | 6具象 controller の fake transport 入力契約を維持する | regression | integration | no | parameterized integration test を実行する |

この unit は既存の観測可能な契約を変えない構造変更である。人工的な新規 red test は
追加せず、変更前の既存 test を characterization baseline として、変更後に同じ test を
green にする。

## 7. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | adapter、Bumble、Switch-facing command を実行しない |
| 完了 gate | unit / fake transport integration |

## 8. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q -k "direct_semantic_operations_send_once_and_commit_after_success or direct_send_failures_do_not_change_last_successfully_sent_state or direct_concurrent_operations_are_serialized_without_lost_state"` | pass | 3 passed。Direct の commit、rollback、直列化を確認した |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 439 passed |
| `uv run pytest tests/integration` | pass | 154 passed。6具象 controller を含む fake transport 契約を確認した |
| `git diff --check` | pass | whitespace error なし |

## 9. 先送り事項

- none

## 10. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 根拠監査の要否を確認した
- [x] 実機実行条件を記録した
- [x] 検証結果を記録した
- [x] complete へ移動した
