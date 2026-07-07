# Hardware Profile Test Scenarios 仕様書

## 1. 概要

### 1.1 目的

実機テストを再開する前に、controller profile ごとの実行順、重みづけ、承認範囲、既存 pytest node、artifact の置き場を整理する。

今回の方針は次の通り。

- Pro Controller は主経路として、pairing、subcommand、active reconnect、button / stick input、neutral cleanup、close の広い回帰基準にする。
- Joy-Con L/R は、Pro Controller 経路と重複しない Joy-Con 固有リスクを重点的に見る。
- Joy-Con R を薄く実行した理由は、未検証だからではなく、Pro Controller / Joy-Con L で確認済みの経路を R でも重複確認する価値が低いためである。
- Joy-Con happy path は、side-specific button map と有効な片側 stick を追加シナリオとして設計する。

この仕様は実機テストの実行計画兼記録である。2026-07-07 時点では H0/H1/H2、Pro Controller P1/P2/P3/P4/P5/P6/P7、Joy-Con L L1/L2/L3/L4、Joy-Con R R1/R2/R3/R4 を実行済みである。Joy-Con L L2 は既定色診断 run を補助観測として残し、主シナリオを利用者指定色の確認へ差し替えて pass した。Joy-Con R R1 は初回 pytest が `0x22` NFC/IR MCU state 未対応による `unsupported_subcommand` で observed-fail になり、`0x22` ACK 互換処理後の rerun は pass した。R1 初回のユーザ目視は赤 body / 青 buttons、rerun のユーザ目視は赤 body / グレー buttons である。どちらも UI 目視観測であり、専用 SPI color scenario の pass 条件にはしない。P4 は当初 LR split だけで実行したが、D-pad と同じ画面で連続実行できるため LR + D-pad 統合シナリオとして再実装し、再実行済みである。L3 は D-pad 入力の UI 目視まで pass、L4 は Switch UI が横持ち Joy-Con のスティック補正を拒否したため hold 観測までの条件付き pass とする。R2 は ABXY 入力の UI 目視まで pass、R3 は L4 と同じ横持ち制約により right stick hold までの条件付き pass、R4 は custom color SPI と UI 目視まで pass とする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | 実機テストを始める前にブランチを切り、Pro Controller 主経路、Joy-Con L 次点、Joy-Con R 1 シナリオの重みづけで整理する | conversation |
| hardware guide | Pro Controller は verified、Joy-Con L は limited observation、Joy-Con R は not verified として記録済み | `docs/hardware.md` |
| hardware log | Windows / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 の Pro Controller 入力、Joy-Con L registration / color 観測 | `spec/hardware-test-log.md` |
| testing policy | `@pytest.mark.bumble` と `@pytest.mark.hardware` の分類、CI 必須外の扱い | `spec/initial/testing.md` |
| public API policy | 現在の concrete controller class は `ProController`、`JoyConL`、`JoyConR` | `spec/rearchitecture/03-public-api-config-profile.md` |
| hardware tests | 実行可能な pytest node と artifact fixture | `tests/hardware/` |
| hardware-harness | adapter open、advertising、pairing、report loop、hardware marker の承認境界 | `.agents/skills/hardware-harness/SKILL.md` |
| source-audit fixture | `0x40` Enable IMU payload `0x02` の ProController 実機観測と、`0x22` NFC/IR MCU state source fact / ACK policy を追加 | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | 実機テスト前の計画 | どの profile をどの順で実行するかが分かる | 実機操作は別途明示承認を取る |
| developer | Pro Controller regression | pairing、full handshake、active reconnect、button / D-pad / stick、neutral cleanup を再確認できる | Switch UI の人間目視を log に残す |
| developer | Joy-Con L profile / happy path check | Joy-Con L device name / device-info、SR+SL registration、利用者指定色の SPI reply、D-pad、left stick を確認する計画が分かる | stick は Switch UI の横持ち制約を条件付き pass として扱う |
| developer | Joy-Con R 重点確認 | Joy-Con R device name / device-info / SR+SL registration、ABXY、right stick、custom color SPI / UI を確認する計画が分かる | Pro Controller / Joy-Con L と重複する確認は増やさない |

## 2. 対象範囲

- `docs/hardware.md`、`spec/hardware-test-log.md`、`tests/hardware/` から現時点の実機検証状態を読み、テストシナリオへ落とす。
- 共有 preflight、Pro Controller 主経路、Joy-Con L 次点、Joy-Con R 重点シナリオの実行順を定義する。
- 各シナリオの既存 pytest node、Switch 側の起動条件、観測対象、承認範囲、cleanup を記録する。
- profile ごとに artifact dir と key store を分ける方針を記録する。
- 承認済みの H0 / Pro Controller 主経路について、実行結果と artifact を追記する。
- Joy-Con happy path として、Joy-Con L の D-pad / left stick、Joy-Con R の ABXY / right stick を追加設計する。
- R1 の UI 色観測と専用 SPI color scenario を分け、Joy-Con R custom color を R4 として確認する。
- 実行していない hardware marker test を not run として扱う。

## 3. 対象外

- 会話で承認されていない実機テストの実行。
- 会話で承認されていない Bumble adapter open、HID advertising、Switch pairing、report loop、input report 送信。
- Joy-Con 横持ち状態で Switch のスティック補正 UI を完了させること。
- Linux、macOS、CSR8510 A10 以外の dongle、別 firmware の検証。

## 4. 関連 docs

- `docs/hardware.md`
- `spec/hardware-test-log.md`
- `spec/initial/testing.md`
- `spec/initial/transport-bumble.md`
- `spec/rearchitecture/03-public-api-config-profile.md`
- `tests/hardware/README.md`
- `tests/hardware/test_bumble_transport.py`
- `tests/hardware/test_context_manager_resource_scope.py`
- `tests/hardware/test_pairing_l2cap.py`
- `tests/hardware/test_input_operations.py`
- `tests/hardware/test_close_disconnect.py`
- `tests/hardware/test_joycon_profile.py`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required for P2/R1 follow-up | done for P2 and R1 local fix | P2 rerun 後に `0x40` Enable IMU payload `0x02` の ProController 実機観測を source-audit fixture へ条件付き hardware observation として追加した。R1 初回後に `0x22` NFC/IR MCU state source fact を追加し、ACK 互換処理を unit test で固定した |
| Bumble / transport | required for execution plan | done | adapter open、HID advertising、pairing、report loop は `hardware-harness` の承認対象として明記した |
| OS / driver / adapter | required for execution plan | done for executed scenarios | Windows、CSR8510 A10、`usb:0`、Python 3.13.5、Bumble 0.0.230 を実行済み scenario の結果として `spec/hardware-test-log.md` に記録した。driver は過去 Windows run から WinUSB expected として扱い、この run では再列挙していない |

### 5.1 P2 `0x40` mode `0x02` 監査

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| `0x40` Enable IMU source fact | `0x00` disable / `0x01` enable | source fact | `subcommand_imu_vibration_enable_state` fixture | stable session-state policy。source fact として維持 |
| Joy-Con L `0x40` mode | `0x02` | hardware observation | `joycon_imu_enable_mode_02` fixture | Joy-Con L 条件付き観測。ProController の `0x02` 受け入れ根拠とは別 entry で扱う |
| ProController P2 after clear | `0x40` payload first byte `0x02` | hardware observation | `pro_controller_imu_enable_mode_02_observation` fixture、`build\hardware\profile-regression-20260707\pro-p2-after-clear\...` | Windows / CSR8510 A10 / Switch 2 22.1.0 条件付き観測。TDD で ProController 互換 mode として受け入れ実装済み |
| current ProController policy | accepted modes `(0x00, 0x01, 0x02)` | implementation fact | `src\swbt\protocol\profiles\pro_controller.py`、`src\swbt\protocol\subcommand.py`、`tests\unit\test_subcommand_responder.py` | `test_pro_controller_enable_imu_mode_0x02_updates_session_state` が現行期待を固定 |

未解決事項:

- Switch 2 firmware 22.1.0 が ProController pairing / initialization 中にも `0x40` mode `0x02` を送る条件は未確定。
- `0x02` は ProController でも `imu_mode=0x02` として session state に記録し、IMU enabled として diagnostics に出す。IMU frame の意味実装はしない。
- 別 firmware、別 dongle、別 OS で同じ `0x40` mode `0x02` が出るかは未検証。

### 5.2 R1 `0x22` NFC/IR MCU state 監査

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| `0x22` NFC/IR MCU state source fact | `0x00` suspend / `0x01` resume / `0x02` resume for update | source fact | `subcommand_nfc_ir_mcu_state` fixture、dekuNukem Nintendo Switch reverse engineering notes | stable session-state policy。source fact として維持 |
| Joy-Con R R1 initial run | repeated `0x22` payload first byte `0x01` | hardware observation | `build\hardware\profile-regression-20260707\joycon-r\joycon-right-profile-pairing.jsonl` | Windows / CSR8510 A10 / Switch 2 22.1.0 条件付き観測。初回 pytest は `unsupported_subcommand` で observed-fail |
| current `0x22` policy | ACK `0x80`、reply-to `0x22`、data なし | implementation fact | `subcommand_nfc_ir_mcu_state_ack_policy` fixture、`src\swbt\protocol\subcommand.py`、`tests\unit\test_subcommand_responder.py` | ACK 互換のみ。NFC/IR MCU state を public API や session state として公開しない |

未解決事項:

- `0x22` が Joy-Con R で繰り返される条件は未確定。
- `0x22` ACK 互換処理後の R1 hardware rerun は pass。別 firmware、別 dongle、別 OS で同じ `0x22` sequence になるかは未検証。
- NFC、IR camera、MCU firmware update の意味実装は今回扱わない。

## 6. 振る舞い仕様

### 6.1 実行重み

| profile | 重み | 理由 | 今回の実行単位 |
|---|---:|---|---|
| Pro Controller | 主経路 | verified 範囲が広く、回帰の基準になる。実機入力、active reconnect、neutral cleanup まで確認済み | preflight 後に pairing、subcommand、active reconnect input、close を実行する |
| Joy-Con L | 次点 | limited observation があり、単体 Joy-Con profile の継続検証価値が高い。D-pad と left stick は Joy-Con L 固有の happy path として追加価値がある | 実行済みは device-info / SR+SL registration と custom color SPI。追加設計は D-pad / left stick |
| Joy-Con R | 最小から重点確認へ変更 | Pro Controller / Joy-Con L と重複する確認は価値が低い。一方で ABXY、right stick、右 Joy-Con custom color は Joy-Con R 固有の重点シナリオとして見る価値がある | 実行済みは device-info / SR+SL registration、ABXY、right stick、custom color |

### 6.2 共有 preflight

| id | command / node | marker | Switch 起動条件 | 観測対象 | 承認範囲 |
|---|---|---|---|---|---|
| H0 | `uv run swbt-probe adapters --json` | none | 不要 | no-open adapter discovery。`opens_adapter=false` の確認 | adapter open なし。承認対象外だが、専用 dongle の識別確認として実行結果を残す |
| H1 | `tests/hardware/test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble` | bumble | 不要 | `open()` が advertising を開始しないこと、close cleanup | USB dongle open、Bumble Device 初期化、close。HID advertising、pairing、report loop、入力送信は含めない |
| H2 | `tests/hardware/test_bumble_transport.py::test_bumble_hid_transport_advertising_smoke_records_diagnostics` | bumble | 不要 | Bumble HID advertising smoke、SDP / HID descriptor registration、close | USB dongle open、Classic HID 初期化、HID advertising、close。Switch pairing と入力送信は含めない |

### 6.3 Pro Controller 主経路

Pro Controller は `build\hardware\profile-regression-20260707\pro` のような dedicated artifact dir を使う。同じ profile 内で prerequisite key store を共有する test は同じ artifact dir を使い、別 profile と key store を共有しない。

| id | command / node | Switch 起動条件 | 観測対象 | 判定 |
|---|---|---|---|---|
| P1 | `tests/hardware/test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics` | controller search / change grip order | `Pro Controller` advertising、pairing、HID control / interrupt L2CAP、clean close | pytest pass と trace |
| P2 | `tests/hardware/test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands` | controller search / change grip order | full observed subcommand window、全観測 subcommand への `0x21` reply、unsupported subcommand なし | pytest pass と trace |
| P3 | `tests/hardware/test_input_operations.py::test_switch_input_semantics_pairing_writes_fresh_key_store` | controller search / change grip order | input semantics 用 fresh key store 作成、full handshake、non-neutral input なし | pytest pass と `input-semantics-key-store.json` |
| P4 | `tests/hardware/test_input_operations.py::test_switch_button_check_lr_and_dpad_after_active_reconnect_for_manual_reflection` | 入力デバイスの動作チェック > ボタンの動作チェック選択直前 | active reconnect、A entry、R-only、L-only、L+R、D-pad up / right / down / left、neutral | pytest pass、trace、debug log、人間目視 |
| P5 | `tests/hardware/test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[left]` | スティックの補正選択直前 | active reconnect、left stick hold、circle、neutral | pytest pass、trace、人間目視 |
| P6 | `tests/hardware/test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]` | スティックの補正選択直前 | active reconnect、right stick hold、circle、neutral | pytest pass、trace、人間目視 |
| P7 | `tests/hardware/test_close_disconnect.py::test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation` | controller search / change grip order。登録画面から A で抜けられる状態 | full handshake 後の A、neutral、disconnect request、post-close UI observation window | pytest pass、trace、人間目視 |

### 6.4 Joy-Con L 次点 / happy path

Joy-Con L は `build\hardware\profile-regression-20260707\joycon-l` のような dedicated artifact dir を使う。Pro Controller の key store と共有しない。

| id | command / node | Switch 起動条件 | 観測対象 | 判定 |
|---|---|---|---|---|
| L1 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]` | controller search / change grip order | `Joy-Con (L)` device name、Device Info type `0x01`、address bytes、SR+SL order input、clean close | pytest pass、trace、人間目視 |
| L2 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_left_profile_reads_custom_controller_colors` | controller search / change grip order | Joy-Con L 利用者指定色 SPI `0x6050` reply、SR+SL order input、UI hold | pytest pass、trace、人間目視 |
| L3 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_left_button_check_dpad_after_reconnect_for_manual_reflection` | 入力デバイスの動作チェック > ボタンの動作チェック画面。Joy-Con L profile には Button A がないため画面 entry は人間操作で行う | Joy-Con L の active reconnect、D-pad up / right / down / left、各入力後 neutral。期待 button bytes は up `000002`、right `000004`、down `000001`、left `000008` | pytest pass、trace、人間目視 |
| L4 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_left_stick_calibration_after_reconnect_for_manual_reflection` | スティックの補正画面。Joy-Con L profile には Button A がないため画面 entry は人間操作で行う | Joy-Con L の active reconnect、left stick hold、circle、neutral。right stick は Joy-Con L profile では無効なため送らない | 条件付き pass。pytest は trace / cleanup pass。ユーザ目視では hold を確認したが、Switch UI は横持ち Joy-Con のため補正を拒否した |

### 6.5 Joy-Con R 重点シナリオ

Joy-Con R は `build\hardware\profile-regression-20260707\joycon-r` のような dedicated artifact dir を使う。R1 は identity / registration の最小確認として実行済みである。追加シナリオは Pro Controller / Joy-Con L と重複する全面確認ではなく、Joy-Con R 固有の ABXY、right stick、custom color に絞る。

| id | command / node | Switch 起動条件 | 観測対象 | 判定 |
|---|---|---|---|---|
| R1 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]` | controller search / change grip order | `Joy-Con (R)` device name、Device Info type `0x02`、address bytes、SR+SL order input、clean close | pytest pass、trace、人間目視 |
| R2 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_right_button_check_abxy_after_reconnect_for_manual_reflection` | 入力デバイスの動作チェック > ボタンの動作チェック選択直前 | Joy-Con R の active reconnect、A entry、Y / X / B / A、各入力後 neutral。期待 button bytes は source fact / implementation fact として Y `010000`、X `020000`、B `040000`、A `080000` | pytest pass、trace、人間目視 |
| R3 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_right_stick_calibration_after_reconnect_for_manual_reflection` | スティックの補正画面 | Joy-Con R の active reconnect、right stick hold、circle、neutral。left stick は Joy-Con R profile では無効なため送らない | 条件付き pass。pytest は trace / cleanup pass。Switch UI は横持ち Joy-Con のため補正を拒否した |
| R4 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_right_profile_reads_custom_controller_colors` | controller search / change grip order | Joy-Con R 利用者指定色 SPI `0x6050` reply、SR+SL order input、UI hold。期待色は body 緑 `0x00ff00`、buttons 紫 `0x8000ff` | pytest pass、trace、人間目視 |

### 6.6 記録と判定

- pytest pass は trace checkpoint と cleanup の成立を示す。Switch UI 反映は自動判定しない。
- 人間目視が必要な scenario は、`spec/hardware-test-log.md` に UI 観測を別項目として記録する。
- `ConnectionTimeoutError`、`unsupported_subcommand`、`error`、neutral 後の入力残りは failure として記録し、原因を断定しない。
- Joy-Con L/R の button / stick reflection は L3/L4/R2/R3 の追加シナリオで扱う。L1/L2/R1/R4 の成功だけでは通常入力の成功扱いにしない。
- SL/SR は L1/R1 の order input で確認済みとし、追加 happy path では D-pad、ABXY、有効な片側 stick を優先する。
- Joy-Con profile が持たない反対側 stick を hardware happy path で入力しない。反対側 stick の拒否または中立維持は protocol / unit layer で確認する。
- 片側 Joy-Con のスティック補正画面は、横持ち Joy-Con に対して「横持ちだと補正できません」と拒否することがある。この場合、pytest pass と hold / report 目視を条件付き pass とし、補正 UI の完了を pass 条件にしない。

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | H0 no-open adapter discovery の結果を記録する | characterization | local | no | `uv run swbt-probe adapters --json` で `usb:0` / CSR8510 A10 を確認。`opens_adapter=false` |
| green | H1 open-only smoke を実行し、advertising が始まらないことを記録する | regression | bumble | yes | `1 passed in 0.32s`。trace は `transport_open_complete` / `transport_close_complete`、`advertising_start` / `host_connection` なし。ユーザ目視でも Switch 側反応なし |
| green | H2 Bumble advertising smoke を実行し、close cleanup を記録する | regression | bumble | yes | `1 passed in 0.52s`。trace は `advertising_start` / `transport_close_complete`、`connection_request` / `host_connection` / `classic_pairing` なし。ユーザ目視でも Switch 側接続反応なし |
| green | P1-P7 の Pro Controller 主経路を順に実行し、trace と目視結果を記録する | regression | hardware | yes | P1 は pass。P2 は `0x40` mode `0x02` 受け入れ修正後に pass。P3 は input semantics 用 key store 作成まで pass。P4 は LR + D-pad 統合 button check を pass。P5 は left stick hold/circle を pass。P6 は right stick hold/circle を pass。P7 は A exit / disconnect close path を pass |
| green | P2 の `0x40` mode `0x02` を source-audit fixture に条件付き観測として記録する | characterization | local | no | `pro_controller_imu_enable_mode_02_observation` を追加。source fact `0x00/0x01` は上書きしない |
| green | ProController が `0x40` mode `0x02` を ACK し、session state に記録する | regression | unit | no | `test_pro_controller_enable_imu_mode_0x02_updates_session_state`。cross-firmware guarantee と IMU frame 実装は対象外 |
| green | L1-L2 の Joy-Con L 次点シナリオを実行し、limited observation を更新する | characterization | hardware | yes | L1 は接続情報削除後の rerun で pass。初回 L1 は on-wire Joy-Con L だが Pro Controller toast。L2 は利用者指定色 scenario に差し替えて pass。既定色 run は補助観測として扱う |
| green | R1 初回の Joy-Con R 最小シナリオを実行し、`0x22` failure と UI 登録観測を記録する | characterization | hardware | yes | pytest は `unsupported_subcommand: 0x22` で observed-fail。trace は Joy-Con R identity / Device Info / SR+SL / cleanup を記録。ユーザ目視では赤 body / 青 buttons の Joy-Con (R) として登録された |
| green | `0x22` NFC/IR MCU state を source-audit fixture と unit test で固定し、ACK 互換処理を追加する | regression | unit | no | `test_set_nfc_ir_mcu_state_acknowledges_supported_modes`。MCU semantic state は実装しない |
| green | R1 を `0x22` 修正後に再実行し、pytest failure が解消したか確認する | characterization | hardware | yes | `1 passed in 24.45s`。trace は `0x22` 2 件への reply、Joy-Con R Device Info、SR+SL、cleanup、`error` なしを記録。ユーザ目視では赤 body / グレー buttons の pairing を確認 |
| green | L3 Joy-Con L button check で D-pad up / right / down / left を確認する | new | hardware | yes | `1 passed in 20.67s`。初期ペアリングで L3 用 key store を作成後、active reconnect で D-pad up `000002`、right `000004`、down `000001`、left `000008` を送信。ユーザは Switch UI で上右下左の順に押されたことを目視確認した |
| conditional-pass | L4 Joy-Con L stick calibration で left stick hold / circle を確認する | new | hardware | yes | `1 passed in 15.62s`。trace は active reconnect、handshake、left stick hold 120 reports、32 step circle、neutral、cleanup を記録。ユーザは hold を確認したが、Switch UI は横持ち Joy-Con のため補正を拒否した。full calibration UI 完了ではなく hold までの条件付き pass とする |
| green | R2 Joy-Con R button check で Y / X / B / A を確認する | new | hardware | yes | R2 用 fresh pairing 後、active reconnect で A entry、Y `010000`、X `020000`、B `040000`、A `080000`、各 neutral を送信。初回は画面遷移 precondition が外れて observed-partial、rerun は `1 passed in 7.29s` かつユーザ目視で期待どおりの入力を確認 |
| conditional-pass | R3 Joy-Con R stick calibration で right stick hold / circle を確認する | new | hardware | yes | `1 passed in 10.38s`。trace は active reconnect、handshake、right stick hold 120 reports、32 step circle、neutral、cleanup を記録。ユーザは横持ち Joy-Con では補正が通らないことを期待どおり確認。full calibration UI 完了ではなく hold までの条件付き pass |
| green | R4 Joy-Con R custom color SPI / UI reflection を専用シナリオで確認する | characterization | hardware | yes | `1 passed in 24.43s`。SPI `0x6050` bytes `00ff008000ff00ffffffff00`、body 緑、buttons 紫を確認。R1 の色目視とは別 scenario として pass |

## 8. 設計メモ

- Pro Controller は既に verified 範囲が広いため、実機環境の健全性確認と regression baseline を兼ねる。Joy-Con に進む前に Pro Controller 主経路を通す。
- P4 は LR split と D-pad の起動条件が同じで、同じ button check screen で連続確認できる。別々の active reconnect に分ける価値が低いため統合する。
- Joy-Con L は過去に limited observation があるため、Joy-Con profile の継続観測として L1 と L2 を実行する価値がある。L2 は L1 と同じ見え方になる既定色ではなく、`controller_colors` 明示指定が profile default より優先されることを実機で見る。
- 当初 Joy-Con R を R1 の 1 本に絞った理由は、未知だから検証を避けるためではない。identity / registration、SR+SL、subcommand 応答は R1 で見ており、Pro Controller / Joy-Con L で既に見た経路を R で重複確認する価値が低かったためである。その後、button map と有効 stick と利用者指定色は左右差が潜在バグになり得るため、R2/R3/R4 を happy path 補強として追加した。
- Joy-Con の追加 happy path は、左右で byte 面が分かれる button map と有効 stick に絞る。Joy-Con L は D-pad と left stick、Joy-Con R は ABXY と right stick を見る。
- SL/SR は L1/R1 の SR+SL order input で確認済みとする。追加 happy path では SL/SR を再確認せず、潜在バグになりやすい ABXY / D-pad と stick path を優先する。
- Joy-Con stick scenario は Switch の補正 UI 完了を狙うのではなく、有効 stick 側の report 送信と目視可能な hold を狙う。片側 Joy-Con の横持ち制約で補正 UI に入れない場合は device/UI 制約として扱う。
- R4 は R1 の registration 中に見えた色とは分ける。R4 では `controller_colors` 明示指定、SPI `0x6050` bytes、人間目視の body / buttons を揃えて確認する。
- key store は profile ごとに分ける。同じ Switch でも Pro Controller、Joy-Con L、Joy-Con R の key store を共有しない。
- L3/L4/R2/R3 は active reconnect を前提に設計する。reconnect 自体を Joy-Con の主張として検証するのではなく、Switch UI の対象画面へ進めるための手段として使う。
- artifact dir は `build\hardware\profile-regression-20260707\...` 形式にし、profile ごとの trace、pytest log、key store を混ぜない。
- H0 以外は実機または専用 USB dongle に触れるため、実行前に adapter、対象 Switch、実行 node、Switch-facing 動作、cleanup plan を会話上で明示する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `spec/wip/unit_046/HARDWARE_PROFILE_TEST_SCENARIOS.md` | update | 実機テストシナリオ整理、P1-P7 / L1-L4 / R1-R4 実行記録、Joy-Con R を薄くした理由の修正、Joy-Con happy path 補強設計 |
| `spec/hardware-test-log.md` | update | P1-P7 / L1-L4 / R1-R4 実機観測、L2 default-color 補助観測、P4 統合再実行、artifact、cleanup 記録 |
| `src/swbt/protocol/subcommand.py` | update | `0x22` NFC/IR MCU state の ACK 互換処理を追加 |
| `tests/unit/test_subcommand_responder.py` | update | `0x22` ACK 互換処理の unit test を追加 |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | update | `0x22` source fact と ACK policy を fixture に追加 |
| `tests/unit/test_source_audit_fixtures.py` | update | `0x22` source-audit fixture の検証を追加 |
| `tests/hardware/test_input_operations.py` | update | P4/P5 を LR + D-pad の統合 P4 hardware test に変更 |
| `tests/hardware/test_joycon_profile.py` | update | Joy-Con L L2 用の custom controller color hardware test、L3 D-pad button check hardware test、L4 left stick hold / circle hardware test、R2 ABXY button check、R3 right stick hold / circle、R4 Joy-Con R custom color hardware test を追加。L3/L4/R2/R3 の画面準備待ちは記録だけにし、固定 sleep は入れない |

## 10. 検証

| command | result | notes |
|---|---|---|
| `git branch --show-current` | pass | 開始時は `main` |
| `git status --short` | pass | 開始時は clean |
| `git pull --ff-only origin main` | pass | `Already up to date.` |
| `git switch -c docs/hardware-test-scenarios` | pass | 専用ブランチを作成 |
| `uv run pytest --collect-only tests\hardware -q` | pass | 26 tests collected。adapter は開いていない |
| `uv run swbt-probe adapters --json` | pass | `opens_adapter=false`。`usb:0` / CSR8510 A10 / VID:PID `0a12:0001` / Windows `10.0.26200` / Python 3.13.5 / Bumble 0.0.230 |
| `uv run pytest tests\hardware\test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\h1-open-only --log-file build\hardware\profile-regression-20260707\h1-open-only\h1-open-only-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 0.32s`。trace は `transport_open_complete`、`disconnect_request status=unavailable`、`transport_close_complete` を記録し、`advertising_start` / `host_connection` はなし。ユーザ目視でも Switch 側反応なし |
| `uv run pytest tests\hardware\test_bumble_transport.py::test_bumble_hid_transport_advertising_smoke_records_diagnostics -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\h2-advertising-smoke --log-file build\hardware\profile-regression-20260707\h2-advertising-smoke\h2-advertising-smoke-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 0.52s`。trace は `transport_open_complete`、`local_bluetooth_address_configured address=001bdcf99f7d`、`classic_link_policy_configured settings=0x0005`、`advertising_start`、`transport_close_complete` を記録し、`connection_request` / `host_connection` / `classic_pairing` / `error` はなし。ユーザ目視でも Switch 側接続反応なし |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p1-pairing-l2cap-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 2.96s`。P1 pairing / L2CAP。non-neutral input は送っていない |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p2-subcommand-window-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-fail | `1 failed in 8.17s`。`ProController` 実行中に `0x40` Enable IMU payload `0x02` 相当で `ProtocolError`。ユーザ目視では青 Joy-Con toast 後に ProCon 接続 |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro-p2-after-clear --log-file build\hardware\profile-regression-20260707\pro-p2-after-clear\p2-subcommand-window-after-clear-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-fail | `1 failed in 7.52s`。接続情報削除後。trace は `device_name=Pro Controller`、`class_of_device=0x002508`、`connected`、`report_mode=0x30`、`0x40` `ProtocolError` 7 件、`transport_close_complete`。ユーザ目視では ProCon toast 後に ProCon として pairing |
| `uv run pytest tests\unit\test_subcommand_responder.py -q` | red | `1 failed, 20 passed`。`test_pro_controller_enable_imu_mode_0x02_updates_session_state` が `ProtocolError` で失敗 |
| `uv run pytest tests\unit\test_subcommand_responder.py tests\unit\test_source_audit_fixtures.py -q` | pass | `43 passed in 0.15s`。ProController `0x40` mode `0x02` と source-audit fixture を確認 |
| `uv run pytest tests\unit -q` | pass | `362 passed in 1.43s` |
| `uv run pytest tests\unit\test_source_audit_fixtures.py -q` | pass | `22 passed in 0.09s`。`pro_controller_imu_enable_mode_02_observation` を条件付き hardware observation として検証 |
| `uv run ruff format --check .` | pass | `89 files already formatted` |
| `uv run ruff check .` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest tests\integration -q` | pass | `93 passed in 0.98s` |
| `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro-p2-accept-imu-02 --log-file build\hardware\profile-regression-20260707\pro-p2-accept-imu-02\p2-subcommand-window-accept-imu-02-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 8.05s`。trace は `imu_mode=0x02`、`0x48`、`0x21`、`transport_close_complete`、`error` / `unsupported_subcommand` なし |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_semantics_pairing_writes_fresh_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p3-input-semantics-key-store-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 9.76s`。`input-semantics-key-store.json` を fresh 作成。trace は `route=pairing`、`key_store_update status=succeeded`、full handshake、`imu_mode=0x02`、`transport_close_complete`、`error` / `unsupported_subcommand` なし。non-neutral input は送っていない |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_separate_l_r_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p4-button-lr-split-pytest-debug.log --log-file-level=DEBUG -q -s` | superseded-pass | `1 passed in 10.97s`。P3 の `input-semantics-key-store.json` を使った active reconnect。trace は R-only `400000`、L-only `000040`、L+R `400040`、neutral、`transport_close_complete`、`classic_pairing` / `key_store_update` / `advertising_start` / `error` なし。ユーザ目視では同時押しは厳密観測不可だがキー入力確認済みのため pass 扱い。この run は D-pad と統合できるため統合 P4 に置き換えた |
| `uv run pytest --collect-only tests\hardware -q` | pass | P4/P5 統合後。25 tests collected。adapter は開いていない |
| `uv run ruff check tests\hardware\test_input_operations.py` | pass | `All checks passed!` |
| `uv run ruff format --check tests\hardware\test_input_operations.py` | pass | `1 file already formatted` |
| `uv run ty check --no-progress` | pass | `All checks passed!`。P4/P5 統合後 |
| `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_lr_and_dpad_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p4-button-lr-dpad-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 14.09s`。P3 の `input-semantics-key-store.json` を使った active reconnect。trace は R-only `400000`、L-only `000040`、L+R `400040`、D-pad up `000002`、right `000004`、down `000001`、left `000008`、各 hold 後 neutral、`transport_close_complete`、`classic_pairing` / `key_store_update` / `advertising_start` / `error` なし。ユーザ目視でも期待値どおりの入力を確認 |
| `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p5-left-stick-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 16.83s`。P3 の `input-semantics-key-store.json` を使った active reconnect。trace は left stick hold `hold_report_count=120`、circle `steps=32` / `step_seconds=0.15`、neutral、`transport_close_complete`、`classic_pairing` / `key_store_update` / `advertising_start` / `error` なし。ユーザ目視では hold と反時計回り / 左回転の circle を確認。回転方向は `x=cos(angle)`、`y=sin(angle)`、angle 増加の実装と一致 |
| `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p6-right-stick-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 16.87s`。P3 の `input-semantics-key-store.json` を使った active reconnect。trace は right stick hold `hold_report_count=120`、circle `steps=32` / `step_seconds=0.15`、neutral、`transport_close_complete`、`classic_pairing` / `key_store_update` / `advertising_start` / `error` なし。ユーザ目視では hold と circle を確認 |
| `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p7-post-handshake-a-close-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 7.90s`。trace は full handshake、Button A exit、neutral、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete`、post-close UI observation checkpoint、`error` なし。ユーザ目視では A で登録画面を抜けたことと close 後の接続解除を確認 |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l --log-file build\hardware\profile-regression-20260707\joycon-l\l1-joycon-left-profile-pairing-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-partial | `1 passed in 24.51s`。trace は `Joy-Con (L)` local name、Device Info `controller_type=0x01`、address bytes 一致、SR+SL `000030`、neutral、`transport_close_complete`、`error` なし。ユーザ目視では初期登録 toast が Pro Controller として出て、登録自体は完了 |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-after-clear --log-file build\hardware\profile-regression-20260707\joycon-l-after-clear\l1-joycon-left-profile-pairing-after-clear-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | Switch 側接続情報削除後。`1 passed in 24.50s`。trace は Joy-Con L discovery / Device Info / SR+SL / neutral / cleanup を記録し、`error` なし。ユーザ目視では青色 Joy-Con (L) として認識され、toast も正常 |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_reads_default_controller_colors[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l2-colors --log-file build\hardware\profile-regression-20260707\joycon-l-l2-colors\l2-joycon-left-default-colors-pytest-debug.log --log-file-level=DEBUG -q -s` | superseded-pass | `1 passed in 24.43s`。SPI `0x6050` bytes は既定値 `00b2ff32323200b2ff00b2ff` と一致。ユーザ目視では L1 と同様の色として認識されたため、L2 主シナリオから外し、利用者指定色の確認に差し替える |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_left_profile_reads_custom_controller_colors' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors --log-file build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors\l2-joycon-left-custom-colors-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 24.58s`。trace は Joy-Con L Device Info `04000102001bdcf99f7d0101`、custom SPI `0x6050` bytes `ff00000000ffff00ffff8000`、SR+SL `000030`、neutral、`transport_close_complete`、`error` なしを記録。ユーザ目視では赤 body / 青 buttons を確認 |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r --log-file build\hardware\profile-regression-20260707\joycon-r\r1-joycon-right-profile-pairing-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-fail | `1 failed in 24.45s`。trace は Joy-Con R Device Info `04000202001bdcf99f7d0101`、SR+SL `300000`、neutral、cleanup を記録したが、repeated `0x22` payload `01...` が `UnsupportedSubcommandError` になった。ユーザ目視では赤 body / 青 buttons の Joy-Con (R) として登録された |
| `uv run pytest tests\unit\test_subcommand_responder.py -q` | red | `4 failed, 21 passed`。`0x22` ACK 互換 test 追加直後は `UnsupportedSubcommandError` で失敗 |
| `uv run pytest tests\unit\test_subcommand_responder.py tests\unit\test_source_audit_fixtures.py -q` | pass | `49 passed in 0.16s`。`0x22` source-audit fixture と ACK 互換処理を確認 |
| `uv run ruff format --check src\swbt\protocol\subcommand.py tests\unit\test_subcommand_responder.py tests\unit\test_source_audit_fixtures.py` | pass | `3 files already formatted` |
| `uv run ruff check src\swbt\protocol\subcommand.py tests\unit\test_subcommand_responder.py tests\unit\test_source_audit_fixtures.py` | pass | `All checks passed!` |
| `uv run pytest tests\unit -q` | pass | `368 passed in 1.29s`。`0x22` 修正後の full unit |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack --log-file build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack\r1-joycon-right-profile-pairing-after-0x22-ack-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 24.45s`。trace は Joy-Con R Device Info `04000202001bdcf99f7d0101`、`0x22` 2 件への `0x21` reply、SR+SL `300000`、neutral、`transport_close_complete`、`error` なしを記録。ユーザ目視では赤 body / グレー buttons の pairing を確認 |
| `git diff --check` | pass | Joy-Con happy path 追加設計と L3/L4 実装 / 記録差分に whitespace error なし |
| `rg "未検証範囲を広げすぎな[い]\|実機未検証のた[め]\|normal input reflection tes[t]\|通常入力反映テスト追[加]\|未知が多[い]" spec\wip\unit_046\HARDWARE_PROFILE_TEST_SCENARIOS.md` | pass | 古い理由づけと大きすぎる deferred item が残っていないことを確認 |
| `uv run pytest --collect-only tests\hardware\test_joycon_profile.py -q` | pass | L3 実装後。6 tests collected。adapter は開いていない |
| `uv run ruff format --check tests\hardware\test_joycon_profile.py` | pass | `1 file already formatted` |
| `uv run ruff check tests\hardware\test_joycon_profile.py` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!` |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l3 --log-file build\hardware\profile-regression-20260707\joycon-l-l3\l3-joycon-left-initial-pairing-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 24.49s`。L3 用 fresh key store 作成。Device Info `0x01`、SR+SL `000030`、cleanup を記録 |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_left_button_check_dpad_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-after-clear --log-file build\hardware\profile-regression-20260707\joycon-l-after-clear\l3-joycon-left-button-check-dpad-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-fail | `1 failed in 6.77s`。古い key store で active reconnect 認証失敗。non-neutral input は送っていない |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_left_button_check_dpad_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l3 --log-file build\hardware\profile-regression-20260707\joycon-l-l3\l3-joycon-left-button-check-dpad-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-fail | `1 passed in 11.67s` だが、ユーザ目視ではボタンの動作チェック画面に入れておらず、下入力が入ってそのまま終了した。pytest pass は trace 送信確認のみで UI pass ではない |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_left_button_check_dpad_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l3-rerun2 --log-file build\hardware\profile-regression-20260707\joycon-l-l3-rerun2\l3-joycon-left-button-check-dpad-rerun2-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 20.67s`。trace は active reconnect、handshake、up `000002`、right `000004`、down `000001`、left `000008`、各 neutral、cleanup を記録。ユーザ目視では上右下左の順に押されたことを確認 |
| `uv run pytest --collect-only tests\hardware\test_joycon_profile.py -q` | pass | L4 実装後。7 tests collected。adapter は開いていない |
| `uv run ruff format --check tests\hardware\test_joycon_profile.py` | pass | `1 file already formatted` |
| `uv run ruff check tests\hardware\test_joycon_profile.py` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!`。L4 実装後 |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_left_stick_calibration_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l4 --log-file build\hardware\profile-regression-20260707\joycon-l-l4\l4-joycon-left-stick-calibration-pytest-debug.log --log-file-level=DEBUG -q -s` | conditional-pass | `1 passed in 15.62s`。trace は active reconnect、handshake、left stick hold `hold_report_count=120`、circle `steps=32` / `step_seconds=0.15`、neutral、cleanup を記録。ユーザ目視では hold を確認したが、Switch UI は横持ち Joy-Con のため補正を拒否した |
| `uv run pytest --collect-only tests\hardware\test_joycon_profile.py -q` | pass | R2/R3/R4 実装後。10 tests collected。adapter は開いていない |
| `uv run ruff format --check tests\hardware\test_joycon_profile.py` | pass | `1 file already formatted` |
| `uv run ruff check tests\hardware\test_joycon_profile.py` | pass | `All checks passed!` |
| `uv run ty check --no-progress` | pass | `All checks passed!`。R2/R3/R4 実装後 |
| `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r2 --log-file build\hardware\profile-regression-20260707\joycon-r-r2\r2-joycon-right-initial-pairing-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 24.37s`。R2 用 fresh key store 作成。Device Info `0x02`、SR+SL `300000`、cleanup を記録 |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_button_check_abxy_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r2 --log-file build\hardware\profile-regression-20260707\joycon-r-r2\r2-joycon-right-button-check-abxy-pytest-debug.log --log-file-level=DEBUG -q -s` | observed-partial | `1 passed in 7.80s`。trace は active reconnect、A entry、Y/X/B/A、neutral、cleanup を記録したが、ユーザ目視では画面遷移に入っていなかったため UI pass ではない |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_button_check_abxy_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r2-rerun2 --log-file build\hardware\profile-regression-20260707\joycon-r-r2-rerun2\r2-joycon-right-button-check-abxy-rerun2-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 7.29s`。trace は active reconnect、A entry、Y `010000`、X `020000`、B `040000`、A `080000`、各 neutral、cleanup を記録。ユーザ目視では入力として期待どおりだった |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_stick_calibration_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r3 --log-file build\hardware\profile-regression-20260707\joycon-r-r3\r3-joycon-right-stick-calibration-pytest-debug.log --log-file-level=DEBUG -q -s` | conditional-pass | `1 passed in 10.38s`。trace は active reconnect、right stick hold 120 reports、32 step circle、neutral、cleanup を記録。ユーザ目視では横持ち Joy-Con では補正が通らないことを確認した |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_profile_reads_custom_controller_colors -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors --log-file build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors\r4-joycon-right-custom-colors-pytest-debug.log --log-file-level=DEBUG -q -s` | pass | `1 passed in 24.43s`。trace は custom SPI `0x6050` bytes `00ff008000ff00ffffffff00`、SR+SL `300000`、cleanup を記録。ユーザ目視では body 緑 / buttons 紫を確認 |
| `git diff --check` | pass | R2/R3/R4 実装と記録差分に whitespace error なし |
| `uv run pytest -m bumble` | not run | adapter open は承認対象。この unit では実行しない |
| `uv run pytest -m hardware` | not run | Switch-facing 操作は承認対象。この unit では実行しない |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 実行時は required。H0/H1/H2 / P1-P7 / L1/L2/L3/L4 / R1/R2/R3/R4 は実行済み。L4/R3 は hold 観測までの条件付き pass |
| 承認範囲 | 実行前に H1/H2/P/L/R のどの scenario を実行するか、adapter open、HID advertising、pairing、report loop、input operation、cleanup の範囲を明示する |
| adapter | 実行時に `swbt-probe adapters --json` と人間確認で決める。過去観測では `usb:0` / CSR8510 A10 / WinUSB が使われている |
| 対象機器 | 実行時に Switch model / firmware と Switch 側画面を記録する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md`、`build\hardware\profile-regression-20260707\...` |
| cleanup | neutral、report loop stop、disconnect request、transport close、adapter release を trace と log に残す |

## 12. 先送り事項

- L4 は left stick hold まで条件付き pass。横持ち Joy-Con に対する Switch 補正 UI の拒否は device/UI 制約として扱い、full calibration UI 完了は今回の完了条件にしない。
- R3 は right stick hold まで条件付き pass。横持ち Joy-Con に対する Switch 補正 UI の拒否は device/UI 制約として扱い、full calibration UI 完了は今回の完了条件にしない。
- Pro Controller P2 の `0x40` mode `0x02` は ProController 互換 mode として受け入れる実装に変更し、P2 retest は pass。別 firmware、別 dongle、別 OS での一般化はしない。
- Joy-Con R R1 初回で観測した repeated `0x22` payload `0x01` は ACK 互換処理に留める。NFC/IR MCU の意味実装はしない。
- Linux、macOS、別 dongle、別 firmware は今回扱わない。
- hardware runner 化は今回扱わない。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] hardware pytest node を collect-only で確認した
- [x] 実機実行前に adapter、対象 Switch、実行 node、cleanup plan の承認を得る
- [x] H1 open-only smoke の実行結果、trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] H2 advertising smoke の実行結果と trace を `spec/hardware-test-log.md` に記録した
- [x] P1 / P2 の実機実行結果を `spec/hardware-test-log.md` に記録した
- [x] Pro Controller 主経路を再開する前に P2 の `0x40` mode `0x02` failure を source-audit / TDD で切り分ける
- [x] P3 の実機実行結果と fresh key store artifact を `spec/hardware-test-log.md` に記録した
- [x] P4 の実機実行結果、LR + D-pad 統合 trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] P5 の実機実行結果、left stick trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] P6 の実機実行結果、right stick trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] P7 の実機実行結果、A exit / close trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] L1 の初回実行、Switch 側接続情報削除後 rerun、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] L2 の default-color 補助観測と custom-color pass、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] R1 初回実行の `0x22` failure とユーザ目視登録結果を `spec/hardware-test-log.md` に記録した
- [x] `0x22` NFC/IR MCU state の source-audit fixture と unit test を追加した
- [x] `0x22` 修正後に R1 を再実行して pass / fail とユーザ目視結果を記録した
- [x] Joy-Con R を薄くした理由を、未検証回避ではなく重複確認価値の低さとして修正した
- [x] Joy-Con happy path として L3 D-pad、L4 left stick、R2 ABXY、R3 right stick を追加設計した
- [x] L3 の Joy-Con L D-pad hardware test を実装し、実機 pass とユーザ目視結果を記録した
- [x] L4 の Joy-Con L left stick hardware test を実装し、hold までの条件付き pass と横持ち Joy-Con UI 制約を記録した
- [x] R2 の Joy-Con R ABXY hardware test を実装し、rerun の実機 pass とユーザ目視結果を記録した
- [x] R3 の Joy-Con R right stick hardware test を実装し、hold までの条件付き pass と横持ち Joy-Con UI 制約を記録した
- [x] R4 の Joy-Con R custom color hardware test を実装し、SPI reply と body 緑 / buttons 紫のユーザ目視結果を記録した
