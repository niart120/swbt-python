# Post-M5 入力意味検証 仕様書

## 1. 概要

### 1.1 目的

`unit_006` は `tap(Button.A)` の Switch UI 反映と `neutral()` 後の入力残りなしを確認して完了した。この unit では、M5 完了条件から外した入力の意味反映を追加で観測する。対象は L+R、D-pad、left / right stick、release / neutral の実機上の見え方である。

接続経路は `unit_007` で確認した active bond reuse reconnect を使う。直近の key store 仕様変更を考慮し、古い `.pytest_cache` artifact は流用しない。この unit の artifact dir 内で fresh pairing により key store を作り直し、その key store を使って active reconnect した後に入力を送る。reconnect / key store の仕様設計そのものは `unit_007` の完了済み範囲とし、この unit では入力意味検証の前提手順としてだけ扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| completed M5 | Button A / neutral は確認済み。L+R は tick 数のみ確認、stick は fake report のみ確認 | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| hardware log | post-handshake run は Button A と neutral を確認。stick semantic reflection は未観測 | `docs/hardware-test-log.md` |
| roadmap | M5 は input operation API。M6 reconnect、M7 examples は別 unit | `spec/initial/roadmap.md` |
| testing | Hardware tests の Button A / L+R / neutral と reconnect の境界 | `spec/initial/testing.md` |
| risks | scheduler jitter、firmware 差分、documentation drift | `spec/initial/risks.md` |
| completed M6 | active bond reuse reconnect は HOME / 通常画面条件で observed-pass。`classic_pairing` / `key_store_update` なしで `connected` まで到達 | `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` |
| Nintendo support | ボタンの動作チェックは「入力デバイスの動作チェック」から「ボタンの動作チェック」を選ぶ | https://support-jp.nintendo.com/app/answers/detail/a_id/35165/ |
| Nintendo support | スティックの補正は「スティックの補正」を選び、対象スティックを倒し続けて反応を確認する | https://support-jp.nintendo.com/app/answers/detail/a_id/35164/ |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| developer | fresh pairing with `key_store_path` | この unit の artifact dir に reconnect 用 key store が作られる | Switch 側は controller search / change grip order screen で待機する |
| developer | active reconnect | 入力検証前に `active_reconnect_result status=connected` が trace に残る | `classic_pairing`、`key_store_update`、`advertising_start` が出た run は active reconnect 入力検証として扱わない |
| developer | `tap(Button.A)` from button check selection | Switch 側が「ボタンの動作チェック」画面へ入る | Switch 本体は「ボタンの動作チェック」選択画面直前で待機する |
| developer | `press(Button.L, Button.R)` | ボタン動作チェック画面で L+R として見える | 実機承認と人間の目視が必要 |
| developer | `press(Button.DPAD_*)` | ボタン動作チェック画面で D-pad up / right / down / left が個別に見える | 実機承認と人間の目視が必要 |
| developer | left / right stick input | スティック補正画面で stick 方向と円入力が観測できる | Switch 本体は「スティックの補正」選択画面直前で待機する |
| developer | `release()` / `neutral()` | 押下や stick 値が解除され、残留入力がない | neutral fail-safe を使う |
| maintainer | hardware matrix / README 判断 | Button A 以外の入力を保証対象に含めるか判断できる | 初期 release gate とは分けて扱う |

## 2. 対象範囲

- `unit_013` artifact dir 内で fresh key store を作る prerequisite test。
- fresh key store を使った active reconnect 後の L+R semantic reflection。
- fresh key store を使った active reconnect 後の D-pad up / right / down / left semantic reflection。
- fresh key store を使った active reconnect 後の left / right stick semantic reflection。
- release / neutral 後の残留入力なしの再確認。
- ボタン入力検証は Switch 本体を「入力デバイスの動作チェック」→「ボタンの動作チェック」選択画面直前で待機させ、`tap(Button.A)` で当該画面に入る手順に固定する。
- スティック入力検証は Switch 本体を「スティックの補正」選択画面直前で待機させ、`tap(Button.A)` で当該画面に入った後、対象 stick を倒し続け、続けて円入力を送る手順に固定する。
- 実機 trace と人間目視結果を `docs/hardware-test-log.md` に記録すること。
- `tests/hardware/test_input_operations.py` に active reconnect characterization test を追加すること。

## 3. 対象外

- `tap(Button.A)` の再完了判定。これは `unit_006` で完了済み。
- reconnect、key store、pairing-free reconnect の設計変更。これは `unit_007`。
- 古い key store artifact の再利用。
- examples、README、CLI。これは `unit_008` と `unit_012`。
- macro scheduler。
- 複数 controller。
- 全 OS / firmware / dongle の保証。

## 4. 関連 docs

- `spec/complete/unit_006/M5_INPUT_OPERATION_API.md`
- `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `spec/wip/unit_008/M7_PACKAGING_EXAMPLES_CLI.md`
- `spec/complete/unit_012/INITIAL_RELEASE_GATE.md`
- `docs/hardware-test-log.md`
- `tests/hardware/README.md`
- Nintendo Support Q&A: https://support-jp.nintendo.com/app/answers/detail/a_id/35165/
- Nintendo Support Q&A: https://support-jp.nintendo.com/app/answers/detail/a_id/35164/

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | Button bit と stick pack は M0 fixture と unit tests で固定済み。実機上の button / stick の意味反映は unit_013 hardware run とユーザ目視で確認した |
| Bumble / transport | required | observed-pass for Button A path and active reconnect prerequisite | `unit_006` post-handshake run で Button A / neutral は observed-pass。`unit_007` で active bond reuse reconnect は observed-pass |
| OS / driver / adapter | required | observed | Windows / CSR8510 A10 / WinUSB / `usb:0`、Switch 2 / firmware 22.1.0 で active reconnect 入力意味検証を確認済み |
| Nintendo UI 手順 | required | source-checked | Nintendo Support Q&A でボタン動作チェックとスティック補正の標準 UI 手順を確認した。pytest は UI 反映を自動判定しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| fresh key store setup | `try_connect(allow_pairing=True)` with `key_store_path` | fresh key store が作られ、`key_store_update status=succeeded` が trace に残る | 古い artifact は使わない |
| active reconnect prerequisite | `try_reconnect()` | `active_reconnect_result status=connected` が trace に残る | `classic_pairing`、`key_store_update`、`advertising_start` は出ないこと |
| button check entry | `tap(Button.A)` | 「ボタンの動作チェック」画面へ入る | Switch は選択画面直前で待機する |
| L+R hold | `press(Button.L, Button.R)` | L+R が一定期間維持され、ボタン動作チェック画面で意味反映を目視できる | tick 数だけでなく目視結果を書く |
| L+R release | `release(Button.L, Button.R)` | L+R が解除される | 他入力の保持 / 解放も記録する |
| stick calibration entry | `tap(Button.A)` | 「スティックの補正」画面へ入る | Switch は選択画面直前で待機する |
| left stick hold / circle | `InputState.with_sticks(left_stick=...)` | 左 stick の倒し続け入力と円入力が観測できる | 円入力は複数 step の `Stick.normalized(...)` で送る |
| right stick hold / circle | `InputState.with_sticks(right_stick=...)` | 右 stick の倒し続け入力と円入力が観測できる | 左 stick とは別 run で記録する |
| neutral after analog | `neutral()` | stick と button が neutral に戻る | 残留入力なしを目視する |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| hardware-pass | unit_013 用 fresh key store setup test を trace 付きで追加する | new | hardware | yes | 2026-07-04 に `input-semantics-key-store.json` を artifact dir 内に作り直した。non-neutral input は送っていない |
| hardware-pass | active reconnect 後にボタン動作チェック画面へ A で入り、R-only / L-only / L+R hold / release checkpoint を trace と debug log に残す | new | hardware | yes | 初回 L+R run はユーザ目視で L だけが押されているように見えた。追加の split diagnosis では R-only `400000`、L-only `000040`、L+R `400040` の `0x30` report 送信を debug log で確認した。ユーザ判断により、Switch button check UI の同時押し表示制約として button 側は pass 扱い |
| hardware-pass | active reconnect 後にボタン動作チェック画面へ A で入り、D-pad up / right / down / left を個別 checkpoint として trace と debug log に残す | characterization | hardware | yes | 2026-07-04 に pytest は pass。active reconnect、full handshake、A entry、D-pad up `000002`、right `000004`、down `000001`、left `000008`、各方向後の neutral、close cleanup を記録した。ユーザ目視確認あり |
| hardware-pass | active reconnect 後に左 stick 補正画面へ A で入り、hold / circle / neutral checkpoint を trace に残す | new | hardware | yes | 2026-07-04 に pytest は pass。active reconnect、full handshake、A entry、left stick hold、16-step circle、neutral、close cleanup を記録した。ユーザ目視確認あり。ただし回転が速く、直ぐ終わったようにも見えたという留保あり |
| hardware-pass | active reconnect 後に右 stick 補正画面へ A で入り、hold / circle / neutral checkpoint を trace に残す | new | hardware | yes | 2026-07-04 の初回 right stick run は速すぎて visual-inconclusive。A 後 1.5 秒待ち、hold 120 reports、32-step circle 0.15 秒間隔に遅くした再実験でユーザ目視確認あり |
| done | `docs/hardware-test-log.md` に L+R / D-pad / stick の人間目視結果と artifact を記録する | new | docs | yes | L+R、D-pad、left stick、right stick slow rerun の目視確認を記録済み |

## 8. 設計メモ

- pytest の pass は trace checkpoint と cleanup の成立だけを示す。semantic reflection は人間目視を log に残す。
- `unit_006` の完了条件は変更しない。ここで失敗しても Button A / neutral の完了事実は取り消さない。
- unit_013 の実機観測は Switch 2 / firmware 22.1.0 で行った。
- active reconnect 入力検証では `classic_pairing`、`key_store_update`、`advertising_start` が出ないことを assert する。これらが出た run は incoming / pairing 系の観測として別扱いにする。
- fresh key store setup はこの unit の実験再現性のために行う。key store の仕様や保証範囲は `unit_007` を変更しない。
- L+R の実装上の report packing は unit test で `40 00 40` と固定済み。unit_013 split diagnosis では R-only `400000`、L-only `000040`、L+R `400040` の outgoing `0x30` report を debug log で確認した。Switch button check UI は同時押しを片方だけ表示する制約があると扱い、button 側は pass とする。
- D-pad の実装上の report packing は unit test で up `00 00 02`、right `00 00 04`、down `00 00 01`、left `00 00 08` と固定済み。unit_013 の D-pad 実機検証では、この順に個別 hold と neutral を送る。
- stick 補正画面は画面遷移直後に入力が短すぎると人間が観測しづらい。stick characterization test では A 後 1.5 秒待ち、hold 120 reports、32-step circle 0.15 秒間隔を使う。
- stick の観測 UI は Switch 標準の「スティックの補正」に固定する。game-specific な画面は使わない。
- ボタンの観測 UI は Switch 標準の「入力デバイスの動作チェック」配下の「ボタンの動作チェック」に固定する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tests/hardware/test_input_operations.py` | modify | fresh key store setup、active reconnect button / D-pad / stick characterization tests |
| `docs/hardware-test-log.md` | modify | L+R / D-pad / stick semantic run entry |
| `spec/complete/unit_013/POST_M5_INPUT_SEMANTIC_CHARACTERIZATION.md` | modify | 実行結果と checklist |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | Resolved 41 packages、Checked 41 packages |
| `uv run pytest --collect-only tests\hardware\test_input_operations.py -q` | pass | 8 tests collected。実機は使っていない |
| `uv run ruff format --check tests\hardware\test_input_operations.py` | pass | 1 file already formatted。button split diagnosis 追加後に再確認 |
| `uv run ruff check tests\hardware\test_input_operations.py` | pass | button split diagnosis 追加後に再確認 |
| `uv run ruff format --check .` | pass | 50 files already formatted。D-pad test 追加後に再確認 |
| `uv run ruff check .` | pass | All checks passed。D-pad test 追加後に再確認 |
| `uv run ty check --no-progress` | pass | All checks passed。D-pad test 追加後に再確認 |
| `uv run pytest tests\unit tests\integration -q` | pass | 202 passed in 1.73s。Switch 2 / firmware 22.1.0 追記後に再確認 |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_semantics_pairing_writes_fresh_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect -q -s` | pass | 1 passed in 9.85s。Switch を controller search / change grip order screen で待機。fresh key store を作成し、full observed handshake 後に close した。non-neutral input は送っていない。artifact は `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\input-semantics-fresh-pairing.jsonl` と `input-semantics-key-store.json` |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect -q -s` | observed-partial | 1 passed in 9.37s。active reconnect、full observed handshake、A entry checkpoint、L+R hold checkpoint、neutral checkpoint、close cleanup を記録。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出なかった。ユーザ目視では L だけが押されているように見え、L+R 同時押し表示は未確認 |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_separate_l_r_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-lr-split-pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 10.96s。active reconnect、full observed handshake、A entry、R-only、L-only、L+R、neutral checkpoint、close cleanup を記録。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出なかった。debug log では R-only `400000` が 30 件、L-only `000040` が 29 件、L+R `400040` が 30 件。ユーザ判断により、同時押しは Switch button check UI が片方だけ表示する制約として pass 扱い |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_dpad_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-dpad-pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 11.71s。active reconnect、full observed handshake、A entry、D-pad up `000002`、right `000004`、down `000001`、left `000008`、各方向後の neutral checkpoint、close cleanup を記録。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出なかった。ユーザ目視確認あり |
| `git diff --check` | pass | whitespace error なし |
| `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\left-stick-pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 10.64s。active reconnect、full observed handshake、A entry、left stick hold、16-step circle、neutral checkpoint、close cleanup を記録。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出なかった。ユーザ目視確認あり。ただし回転が速く、直ぐ終わったようにも見えたという留保あり |
| `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-pytest-debug.log --log-file-level=DEBUG -q -s` | visual-inconclusive | 1 passed in 10.62s。active reconnect、full observed handshake、A entry、right stick hold、16-step circle、neutral checkpoint、close cleanup を記録。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出なかった。ユーザ目視では速すぎて見えなかったため、semantic pass にはしない |
| `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-slow-pytest-debug.log --log-file-level=DEBUG -q -s` | hardware-pass | 1 passed in 16.77s。active reconnect、full observed handshake、A entry 後 `settle_seconds=1.5`、right stick hold `hold_report_count=120`、32-step circle `step_seconds=0.15`、neutral checkpoint、close cleanup を記録。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出なかった。ユーザ目視確認あり |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | adapter open、HID advertising、fresh pairing、key store write、active reconnect、full observed handshake wait、Button A、L+R、D-pad up / right / down / left、left / right stick hold、left / right stick circle、neutral、close |
| adapter | `usb:0` など、専用 USB Bluetooth dongle の具体的 adapter string |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、pytest log、human-visible UI observation |
| cleanup | neutral、report loop stop、transport close、adapter release |
| fresh key store 起動条件 | Switch を controller search / change grip order screen で待機させる |
| ボタン起動条件 | Switch を「入力デバイスの動作チェック」→「ボタンの動作チェック」選択画面直前で待機させる |
| スティック起動条件 | Switch を「スティックの補正」選択画面直前で待機させる。left / right は別 run で記録する |

## 12. 先送り事項

- reconnect / key store / disconnect competing cleanup の設計変更は `unit_007`。
- examples / CLI / README usage は `unit_008`。
- release gate と README / risks の最終整合は `unit_012`。
- macro scheduler と複数 controller は初期対象外。

## 13. チェックリスト

このチェックリストは unit_013 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] post-M5 入力意味検証 unit として切り出した
- [x] 対象範囲と対象外を `unit_006` / M6 / M7 / release gate から分離した
- [x] L+R / D-pad / stick characterization test を実装した
- [x] 実機承認、command、artifact、cleanup、目視結果を記録した
- [x] collect-only / format / lint の local gate を実行し、検証欄を結果で更新した
- [x] 完了条件を満たしたら `spec/complete` へ移動する
