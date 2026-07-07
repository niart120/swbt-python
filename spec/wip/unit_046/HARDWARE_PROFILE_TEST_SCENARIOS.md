# Hardware Profile Test Scenarios 仕様書

## 1. 概要

### 1.1 目的

実機テストを再開する前に、controller profile ごとの実行順、重みづけ、承認範囲、既存 pytest node、artifact の置き場を整理する。

今回の方針は次の通り。

- Pro Controller を主経路にする。
- Joy-Con L は次点として、単体 Joy-Con profile の登録と色 SPI まで見る。
- Joy-Con R は 1 シナリオだけ実行し、未検証範囲を広げすぎない。

この仕様は実機テストの実行計画兼記録である。2026-07-07 時点では H0、Pro Controller P1/P2/P3/P4/P5/P6 を実行済みで、P7、Joy-Con L/R、H1/H2 は未実行である。P4 は当初 LR split だけで実行したが、D-pad と同じ画面で連続実行できるため LR + D-pad 統合シナリオとして再実装し、再実行済みである。

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
| source-audit fixture | `0x40` Enable IMU payload `0x02` の ProController 実機観測を条件付き hardware observation として追加 | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | 実機テスト前の計画 | どの profile をどの順で実行するかが分かる | 実機操作は別途明示承認を取る |
| developer | Pro Controller regression | pairing、full handshake、active reconnect、button / D-pad / stick、neutral cleanup を再確認できる | Switch UI の人間目視を log に残す |
| developer | Joy-Con L profile check | Joy-Con L device name / device-info、SR+SL registration、default color SPI を確認できる | normal input reflection と reconnect は完了扱いにしない |
| developer | Joy-Con R minimum check | Joy-Con R device name / device-info / SR+SL registration を 1 本だけ確認できる | 色、reconnect、通常入力は先送りする |

## 2. 対象範囲

- `docs/hardware.md`、`spec/hardware-test-log.md`、`tests/hardware/` から現時点の実機検証状態を読み、テストシナリオへ落とす。
- 共有 preflight、Pro Controller 主経路、Joy-Con L 次点、Joy-Con R 1 シナリオの実行順を定義する。
- 各シナリオの既存 pytest node、Switch 側の起動条件、観測対象、承認範囲、cleanup を記録する。
- profile ごとに artifact dir と key store を分ける方針を記録する。
- 承認済みの H0 / Pro Controller 主経路について、実行結果と artifact を追記する。
- 実行していない hardware marker test を not run として扱う。

## 3. 対象外

- 会話で承認されていない実機テストの実行。
- 会話で承認されていない Bumble adapter open、HID advertising、Switch pairing、report loop、input report 送信。
- 新しい hardware pytest の実装。
- Joy-Con L/R の通常入力反映テスト追加。
- Joy-Con R の controller color 実機確認。
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
| Switch HID / report bytes | required for P2 follow-up | done | P2 rerun 後に `0x40` Enable IMU payload `0x02` の ProController 実機観測を source-audit fixture へ条件付き hardware observation として追加した。source fact `0x00/0x01` は上書きしない |
| Bumble / transport | required for execution plan | done | adapter open、HID advertising、pairing、report loop は `hardware-harness` の承認対象として明記した |
| OS / driver / adapter | required for execution plan | done for P1/P2/P3 | Windows、CSR8510 A10、`usb:0`、Python 3.13.5、Bumble 0.0.230 を P1/P2/P3 実行結果として `spec/hardware-test-log.md` に記録した。driver は過去 Windows run から WinUSB expected として扱い、この run では再列挙していない |

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

## 6. 振る舞い仕様

### 6.1 実行重み

| profile | 重み | 理由 | 今回の実行単位 |
|---|---:|---|---|
| Pro Controller | 主経路 | verified 範囲が広く、回帰の基準になる。実機入力、active reconnect、neutral cleanup まで確認済み | preflight 後に pairing、subcommand、active reconnect input、close を実行する |
| Joy-Con L | 次点 | limited observation があり、単体 Joy-Con profile の継続検証価値が高い | device-info / SR+SL registration と default color SPI の 2 本 |
| Joy-Con R | 最小 | 実機未検証のため、最初から網羅しない | device-info / SR+SL registration の 1 本 |

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

### 6.4 Joy-Con L 次点

Joy-Con L は `build\hardware\profile-regression-20260707\joycon-l` のような dedicated artifact dir を使う。Pro Controller の key store と共有しない。

| id | command / node | Switch 起動条件 | 観測対象 | 判定 |
|---|---|---|---|---|
| L1 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]` | controller search / change grip order | `Joy-Con (L)` device name、Device Info type `0x01`、address bytes、SR+SL order input、clean close | pytest pass、trace、人間目視 |
| L2 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_profile_reads_default_controller_colors[left]` | controller search / change grip order | Joy-Con L default color SPI `0x6050` reply、SR+SL order input、UI hold | pytest pass、trace、人間目視 |

### 6.5 Joy-Con R 1 シナリオ

Joy-Con R は `build\hardware\profile-regression-20260707\joycon-r` のような dedicated artifact dir を使う。今回は 1 本だけ実行し、結果に応じて次の unit または dev-journal へ分ける。

| id | command / node | Switch 起動条件 | 観測対象 | 判定 |
|---|---|---|---|---|
| R1 | `tests/hardware/test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]` | controller search / change grip order | `Joy-Con (R)` device name、Device Info type `0x02`、address bytes、SR+SL order input、clean close | pytest pass、trace、人間目視 |

### 6.6 記録と判定

- pytest pass は trace checkpoint と cleanup の成立を示す。Switch UI 反映は自動判定しない。
- 人間目視が必要な scenario は、`spec/hardware-test-log.md` に UI 観測を別項目として記録する。
- `ConnectionTimeoutError`、`unsupported_subcommand`、`error`、neutral 後の入力残りは failure として記録し、原因を断定しない。
- Joy-Con L/R の normal input reflection、reconnect、SDP 細部一致は、この unit の実行で成功扱いにしない。

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | H0 no-open adapter discovery の結果を記録する | characterization | local | no | `uv run swbt-probe adapters --json` で `usb:0` / CSR8510 A10 を確認。`opens_adapter=false` |
| todo | H1 open-only smoke を実行し、advertising が始まらないことを記録する | regression | bumble | yes | 明示承認後 |
| todo | H2 Bumble advertising smoke を実行し、close cleanup を記録する | regression | bumble | yes | 明示承認後 |
| observed-partial | P1-P7 の Pro Controller 主経路を順に実行し、trace と目視結果を記録する | regression | hardware | yes | P1 は pass。P2 は `0x40` mode `0x02` 受け入れ修正後に pass。P3 は input semantics 用 key store 作成まで pass。P4 は LR + D-pad 統合 button check を pass。P5 は left stick hold/circle を pass。P6 は right stick hold/circle を pass。P7 は未実行 |
| green | P2 の `0x40` mode `0x02` を source-audit fixture に条件付き観測として記録する | characterization | local | no | `pro_controller_imu_enable_mode_02_observation` を追加。source fact `0x00/0x01` は上書きしない |
| green | ProController が `0x40` mode `0x02` を ACK し、session state に記録する | regression | unit | no | `test_pro_controller_enable_imu_mode_0x02_updates_session_state`。cross-firmware guarantee と IMU frame 実装は対象外 |
| todo | L1-L2 の Joy-Con L 次点シナリオを実行し、limited observation を更新する | characterization | hardware | yes | normal input reflection へ拡張しない |
| todo | R1 の Joy-Con R 最小シナリオを実行し、結果を not verified から更新するか判断する | characterization | hardware | yes | 1 本だけ実行 |
| deferred | Joy-Con L/R の normal input reflection test を追加する | new | hardware | yes | 今回は既存 node で profile identity と registration を確認する |
| deferred | Joy-Con R default color SPI / UI reflection を確認する | characterization | hardware | yes | R1 の結果後に判断する |

## 8. 設計メモ

- Pro Controller は既に verified 範囲が広いため、実機環境の健全性確認と regression baseline を兼ねる。Joy-Con に進む前に Pro Controller 主経路を通す。
- P4 は LR split と D-pad の起動条件が同じで、同じ button check screen で連続確認できる。別々の active reconnect に分ける価値が低いため統合する。
- Joy-Con L は過去に limited observation があるため、Joy-Con profile の継続観測として L1 と L2 を実行する価値がある。
- Joy-Con R は未知が多い。最初は identity / registration の 1 本だけにし、失敗時に color や input reflection へ広げない。
- key store は profile ごとに分ける。同じ Switch でも Pro Controller、Joy-Con L、Joy-Con R の key store を共有しない。
- artifact dir は `build\hardware\profile-regression-20260707\...` 形式にし、profile ごとの trace、pytest log、key store を混ぜない。
- H0 以外は実機または専用 USB dongle に触れるため、実行前に adapter、対象 Switch、実行 node、Switch-facing 動作、cleanup plan を会話上で明示する。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `spec/wip/unit_046/HARDWARE_PROFILE_TEST_SCENARIOS.md` | update | 実機テストシナリオ整理と P1-P6 実行記録 |
| `spec/hardware-test-log.md` | update | P1-P6 実機観測、P4 統合再実行、artifact、cleanup 記録 |
| `tests/hardware/test_input_operations.py` | update | P4/P5 を LR + D-pad の統合 P4 hardware test に変更 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `git branch --show-current` | pass | 開始時は `main` |
| `git status --short` | pass | 開始時は clean |
| `git pull --ff-only origin main` | pass | `Already up to date.` |
| `git switch -c docs/hardware-test-scenarios` | pass | 専用ブランチを作成 |
| `uv run pytest --collect-only tests\hardware -q` | pass | 26 tests collected。adapter は開いていない |
| `uv run swbt-probe adapters --json` | pass | `opens_adapter=false`。`usb:0` / CSR8510 A10 / VID:PID `0a12:0001` / Windows `10.0.26200` / Python 3.13.5 / Bumble 0.0.230 |
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
| `uv run pytest -m bumble` | not run | adapter open は承認対象。この unit では実行しない |
| `uv run pytest -m hardware` | not run | Switch-facing 操作は承認対象。この unit では実行しない |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 実行時は required。H0 / P1-P6 は実行済み。未実行シナリオは個別承認後に実行する |
| 承認範囲 | 実行前に H1/H2/P/L/R のどの scenario を実行するか、adapter open、HID advertising、pairing、report loop、input operation、cleanup の範囲を明示する |
| adapter | 実行時に `swbt-probe adapters --json` と人間確認で決める。過去観測では `usb:0` / CSR8510 A10 / WinUSB が使われている |
| 対象機器 | 実行時に Switch model / firmware と Switch 側画面を記録する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md`、`build\hardware\profile-regression-20260707\...` |
| cleanup | neutral、report loop stop、disconnect request、transport close、adapter release を trace と log に残す |

## 12. 先送り事項

- Joy-Con L/R の normal input reflection test 追加は、今回の実行結果を見て別 unit 化する。
- Joy-Con R default color SPI / UI reflection は、R1 の identity / registration 結果後に判断する。
- Pro Controller P2 の `0x40` mode `0x02` は ProController 互換 mode として受け入れる実装に変更し、P2 retest は pass。別 firmware、別 dongle、別 OS での一般化はしない。
- Linux、macOS、別 dongle、別 firmware は今回扱わない。
- hardware runner 化は今回扱わない。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] hardware pytest node を collect-only で確認した
- [x] 実機実行前に adapter、対象 Switch、実行 node、cleanup plan の承認を得る
- [x] P1 / P2 の実機実行結果を `spec/hardware-test-log.md` に記録した
- [x] Pro Controller 主経路を再開する前に P2 の `0x40` mode `0x02` failure を source-audit / TDD で切り分ける
- [x] P3 の実機実行結果と fresh key store artifact を `spec/hardware-test-log.md` に記録した
- [x] P4 の実機実行結果、LR + D-pad 統合 trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] P5 の実機実行結果、left stick trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
- [x] P6 の実機実行結果、right stick trace、ユーザ目視結果を `spec/hardware-test-log.md` に記録した
