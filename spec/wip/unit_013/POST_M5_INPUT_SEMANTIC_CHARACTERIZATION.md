# Post-M5 入力意味検証 仕様書

## 1. 概要

### 1.1 目的

`unit_006` は `tap(Button.A)` の Switch UI 反映と `neutral()` 後の入力残りなしを確認して完了した。この unit では、M5 完了条件から外した入力の意味反映を追加で観測する。対象は L+R、stick、必要に応じた d-pad / release の実機上の見え方であり、reconnect や key store は扱わない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| completed M5 | Button A / neutral は確認済み。L+R は tick 数のみ確認、stick は fake report のみ確認 | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| hardware log | post-handshake run は Button A と neutral を確認。stick semantic reflection は未観測 | `docs/hardware-test-log.md` |
| roadmap | M5 は input operation API。M6 reconnect、M7 examples は別 unit | `spec/initial/roadmap.md` |
| testing | Hardware tests の Button A / L+R / neutral と reconnect の境界 | `spec/initial/testing.md` |
| risks | scheduler jitter、firmware 差分、documentation drift | `spec/initial/risks.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| developer | `press(Button.L, Button.R)` | Switch 側の確認画面または対象 UI で L+R として見える | 実機承認と人間の目視が必要 |
| developer | left / right stick input | stick 方向が Switch 側で観測できる | どの画面で観測するかを command 実行前に決める |
| developer | `release()` / `neutral()` | 押下や stick 値が解除され、残留入力がない | neutral fail-safe を使う |
| maintainer | hardware matrix / README 判断 | Button A 以外の入力を保証対象に含めるか判断できる | 初期 release gate とは分けて扱う |

## 2. 対象範囲

- full observed handshake 後の L+R semantic reflection。
- full observed handshake 後の left / right stick semantic reflection。
- release / neutral 後の残留入力なしの再確認。
- 実機 trace と人間目視結果を `docs/hardware-test-log.md` に記録すること。
- 必要なら `tests/hardware/test_input_operations.py` に post-handshake characterization test を追加すること。

## 3. 対象外

- `tap(Button.A)` の再完了判定。これは `unit_006` で完了済み。
- reconnect、key store、pairing-free reconnect。これは `unit_007`。
- examples、README、CLI。これは `unit_008` と `unit_012`。
- macro scheduler。
- 複数 controller。
- 全 OS / firmware / dongle の保証。

## 4. 関連 docs

- `spec/complete/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `spec/wip/unit_008/M7_PACKAGING_EXAMPLES_CLI.md`
- `spec/wip/unit_012/INITIAL_RELEASE_GATE.md`
- `docs/hardware-test-log.md`
- `tests/hardware/README.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done for bytes / pending for semantics | Button bit と stick pack は M0 fixture と unit tests で固定済み。実機上の L+R / stick の意味反映は未観測 |
| Bumble / transport | required | observed-pass for Button A path | `unit_006` post-handshake run で same transport path の Button A / neutral は observed-pass |
| OS / driver / adapter | required | observed-partial | Windows / CSR8510 A10 / WinUSB / `usb:0` で Button A は確認済み。Switch model / firmware は未記録 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| L+R hold | `press(Button.L, Button.R)` | L+R が一定期間維持され、対象 UI で意味反映を目視できる | tick 数だけでなく目視結果を書く |
| L+R release | `release(Button.L, Button.R)` | L+R が解除される | 他入力の保持 / 解放も記録する |
| left stick | `InputState.with_sticks(left_stick=...)` | 左 stick の方向が対象 UI で観測できる | 観測 UI を固定する |
| right stick | `InputState.with_sticks(right_stick=...)` | 右 stick の方向が対象 UI で観測できる | UI に右 stick 反映がある画面を選ぶ |
| neutral after analog | `neutral()` | stick と button が neutral に戻る | 残留入力なしを目視する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | post-handshake 後に L+R hold / release checkpoint を trace に残す | new | hardware | yes | 既存 test の full-handshake wait を再利用する |
| todo | post-handshake 後に left stick input / neutral checkpoint を trace に残す | new | hardware | yes | fake report bytes は既存 integration test で固定済み |
| todo | post-handshake 後に right stick input / neutral checkpoint を trace に残す | new | hardware | yes | 右 stick が見える UI を事前に決める |
| todo | `docs/hardware-test-log.md` に L+R / stick の人間目視結果と artifact を記録する | new | docs | yes | pytest pass だけを semantic pass にしない |
| deferred | d-pad semantic reflection を追加で確認する | characterization | hardware | yes | release の保証範囲に入れるかは後で決める |

## 8. 設計メモ

- pytest の pass は trace checkpoint と cleanup の成立だけを示す。semantic reflection は人間目視を log に残す。
- `unit_006` の完了条件は変更しない。ここで失敗しても Button A / neutral の完了事実は取り消さない。
- Switch model / firmware が分かる場合は、この unit の run で必ず記録する。
- stick の観測 UI が不安定なら、game-specific な挙動ではなく Switch 標準の入力確認画面を優先する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tests/hardware/test_input_operations.py` | modify | post-handshake L+R / stick characterization test |
| `docs/hardware-test-log.md` | modify | L+R / stick semantic run entry |
| `spec/wip/unit_013/POST_M5_INPUT_SEMANTIC_CHARACTERIZATION.md` | modify | 実行結果と checklist |

## 10. 検証

この表は unit_013 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests\hardware\test_input_operations.py --collect-only -q` | pending | hardware test 追加後に収集確認する |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_lr_and_sticks_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 ...` | pending-approval | 明示承認、対象 UI、cleanup plan が揃った場合だけ実行する |
| `uv run pytest tests/unit tests/integration -q` | pending | hardware test helper が production API に影響する場合に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | adapter open、HID advertising、pairing or existing connection、full observed handshake wait、L+R、stick、neutral、close |
| adapter | `usb:0` など、専用 USB Bluetooth dongle の具体的 adapter string |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、pytest log、human-visible UI observation |
| cleanup | neutral、report loop stop、transport close、adapter release |

## 12. 先送り事項

- reconnect / key store / disconnect competing cleanup は `unit_007`。
- examples / CLI / README usage は `unit_008`。
- release gate と README / risks の最終整合は `unit_012`。
- macro scheduler と複数 controller は初期対象外。

## 13. チェックリスト

このチェックリストは unit_013 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] post-M5 入力意味検証 unit として切り出した
- [x] 対象範囲と対象外を `unit_006` / M6 / M7 / release gate から分離した
- [ ] L+R / stick characterization test を実装した
- [ ] 実機承認、command、artifact、cleanup、目視結果を記録した
- [ ] 必要な local gate を実行し、検証欄を結果で更新した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
