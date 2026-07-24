# Direct close 前入力反映観測 仕様書

## 1. 概要

### 1.1 目的

Direct controller の実機テストで、入力送信後に `close()` へ進む前の観測窓を設ける。通常送信中は入力が Switch へ届かず、切断前の ACL queue drain で初めて送られる退行を、従来の local state assertion だけで成功扱いしない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| external review / user request | Direct pairing 実機テストは `send()` 後に local state だけを確認して直ちに `close()` するため、close 前の Switch 入力反映を確認できない | `tests/hardware/test_pairing_profile.py` |
| current transport contract | Direct の成功と `report_tx` は Bumble enqueue 受理を表し、Switch 反映を表さない。切断時は pending ACL queue を drain する | `spec/complete/unit_064/BUMBLE_ENQUEUE_COMPLETION_CONTRACT.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| hardware test operator | Switch の入力確認画面を開き、Direct controller の sentinel button を送信する | `close()` 開始前の観測窓で対象 button が表示される | 画面反映は pytest だけでは判定せず、利用者確認を hardware log に記録する |
| transport regression | 通常 send の queue が close まで進行しない | pytest の trace 順序は通っても、close 前の Switch 画面確認が失敗する | close 時 drain による遅延送信を成功根拠にしない |

## 2. 対象範囲

- Direct Pro Controller / Joy-Con L / Joy-Con R の fresh pairing 実機テスト。
- 実機 gate は Direct Pro / Button A の代表ケースを先に実行する。
- Direct input の enqueue 後、neutral と `close()` の前に設ける手動観測窓。
- operator の準備条件、期待 button、観測窓完了、close 開始、cleanup を trace に記録する。
- pytest pass と Switch UI の目視結果を別の証拠として扱う。

## 3. 対象外

- `send()` を controller completion や Switch 反映まで待つ API への変更。
- Bumble `DataPacketQueue` の内部計測や production diagnostics の追加。
- CI での実機入力反映検証。
- report bytes、button bit、controller profile の変更。
- active reconnect の入力反映。今回の起点は fresh pairing test の acceptance gap であり、reconnect は別検証とする。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_050/DIRECT_REPORTING_TYPES.md`
- `spec/complete/unit_054/EXP_LOCAL_ADDRESS_PROFILE_DIRECT.md`
- `spec/complete/unit_064/BUMBLE_ENQUEUE_COMPLETION_CONTRACT.md`
- `tests/hardware/README.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 既存の sentinel `InputState` と report builder を変更しない |
| Bumble / transport | required | done | unit_064 の enqueue 受理と disconnect 前 drain 契約を利用する。新しい transport 仮定は追加しない |
| OS / driver / adapter | required | done | Windows 11、専用 `usb:0`、CSR8510 A10、WinUSB、Bumble 0.0.230、Python 3.13.5 で代表ケースを実行し、`spec/hardware-test-log.md` に記録した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| operator preparation | Direct fresh pairing を開始する | Switch の controller search / change grip order 画面、controller、button、観測秒数を trace と stderr に出す | 画面準備なしの run は input reflection の根拠にしない |
| pre-close observation | `send(sentinel_state)` が正常終了する | local state と direct `report_tx` を確認し、neutral / close を呼ばず観測窓を維持する | `report_tx` 自体は enqueue 受理だけを表す |
| cleanup ordering | 観測窓が完了する | 観測窓完了後に初めて `close(neutral=True)` を開始する | button pressed を残さない |
| evidence classification | pytest が pass する | enqueue、trace 順序、profile、cleanup の成功として扱う | Switch UI は利用者確認が記録された場合だけ observed-pass |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | fresh pairing の Direct input は close 前の観測窓を完了してから neutral close する | regression | hardware | yes | Pro / Button A の代表ケースが `1 passed in 33.27s`。Joy-Con L / R は collection のみ |
| green | trace は direct enqueue、観測窓完了、close 開始、transport close の順序を保持する | regression | hardware | yes | direct `0x30` index 23、観測窓完了 71、close 開始 72、transport close 103、cleanup 104 |
| green | Switch UI に対象 button が close 前に表示される | characterization | hardware | yes | 利用者が観測窓中の画面反応とコントローラー認識を目視確認した |

## 8. 文書検証計画

公開文書は変更しない。作業仕様、hardware test docstring、`tests/hardware/README.md` を照合し、pytest pass と人間の目視結果を混同していないことをレビューする。

## 9. 設計メモ

### Test Desiderata Review

| test | value | trade-off | decision |
|---|---|---|---|
| fake transport Direct send | isolated、deterministic、fast、precise | Switch-facing queue progression を表さない | 既存 integration test を維持する |
| Direct pre-close hardware observation | representative。close drain に隠れる退行を観測できる | 手動、低速、adapter と Switch 状態に依存する | CI 外の承認制 hardware test として追加する |
| Bumble private queue assertion | queue 内部には precise | Bumble 内部構造へ密結合し、Switch 反映を証明しない | 追加しない |

### Gaps

- 自動化された Switch UI assertion はない。利用者確認と hardware log が必要。
- 観測窓は queue completion の時刻を測定しない。close 前に入力反映を確認するための時間境界である。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tests/hardware/test_pairing_profile.py` | modify | Direct fresh pairing に operator checkpoint と close 前観測窓を追加 |
| `spec/complete/unit_068/DIRECT_PRE_CLOSE_INPUT_REFLECTION.md` | new | 対象範囲、検証境界、実機条件を記録 |
| `spec/hardware-test-log.md` | modify | 実機 rerun、cleanup、利用者確認を記録 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 53 packages resolved |
| `uv run ruff format --check .` | pass | 100 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 468 passed |
| `uv run pytest tests/integration` | pass | 137 passed |
| `uv run pytest tests/hardware/test_pairing_profile.py --collect-only -q` | pass | adapter を開かず14件を収集。Direct fresh / reconnect は各3 controller |
| `uv run pytest tests/hardware/test_pairing_profile.py -q` | skipped | adapter option を指定せず14件すべて skip。実機経路は未実行 |
| `uv sync --dev --group docs` | pass | docs dependencies を同期 |
| `uv run mkdocs build --strict` | pass | strict build 成功 |
| read-only adapter identity preflight / postflight | pass | HCI / CSR はともに `0E:08:71:C0:B4:5C`、postflight は `adapter_closed` |
| Direct Pro fresh pairing / Button A | pass | `1 passed in 33.27s`。30秒の close 前観測窓と trace 順序 assertion が成功 |
| Switch UI 目視 | observed-pass | 利用者が close 前に画面反応とコントローラー認識を確認 |
| 先行 reconnect 2件 | failed before send | HCI authentication failure reason 5。Button A 送信と観測窓より前の失敗であり、input reflection の判定には使用しない |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for input reflection completion |
| 承認範囲 | 専用 adapter open、profile identity preparation、Direct HID fresh pairing、sentinel button 1件、close 前観測窓、neutral close |
| adapter | dedicated `usb:0`、CSR8510 A10、VID:PID `0A12:0001`、WinUSB |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build/hardware/unit_068/direct-pro-fresh-pre-close-20260724-115129/` と利用者目視結果を `spec/hardware-test-log.md` に記録 |
| cleanup | `close(neutral=True)`、disconnect、transport close、adapter release を実行。postflight で identity 一致と `adapter_closed` を確認 |

## 13. 先送り事項

- Joy-Con L / Joy-Con R の同一観測は未実行。今回の完了 gate は仕様どおり Direct Pro / Button A の代表ケースとし、両 variant は必要になった時点で同じ parameterized test を実行する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] close 前観測窓を実装した
- [x] 非実機 gate の結果を記録した
- [x] 実機 rerun と利用者確認を記録した
