# Profile Aware Subcommand State 仕様書

## 1. 概要

### 1.1 目的

subcommand 応答から Pro Controller 固定の応答データを外し、profile に基づく応答を返す。合わせて、report mode、IMU enable、vibration enable などの要求状態を fixed `ControllerProfile` から分離し、mutable session state として保持する。

`ControllerProfile` は固定 identity / protocol profile を表す。Switch からの subcommand によって変わる状態を profile に混ぜない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| parent issue | Joy-Con support plan と順序 | https://github.com/niart120/swbt-python/issues/48 |
| child issue | profile-aware subcommand と report mode state | https://github.com/niart120/swbt-python/issues/52 |
| dependency | profile injection | https://github.com/niart120/swbt-python/issues/49 |
| dependency | Joy-Con profile identity / Device Info | https://github.com/niart120/swbt-python/issues/50 |
| dependency | profile-aware input report mapping | https://github.com/niart120/swbt-python/issues/51 |
| initial protocol | subcommand responder、reply queue、supported subcommands | `spec/initial/protocol.md` |
| initial lifecycle | connected 時の report loop と mutable connection state | `spec/initial/lifecycle.md` |
| source-audit | subcommand ID、ACK byte、payload、unsupported mode の扱い | `.agents/skills/source-audit/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | `0x02 Device Info` | profile 由来の device type / fixed bytes と session address を含む reply | address は profile 固定値にしない |
| Switch host | `0x03 Set input report mode` | 要求 report mode を mutable session state に保持する | unsupported mode を黙って `0x30` 扱いしない |
| Switch host | `0x40 Enable IMU` | IMU enable state を保持する | `InputState` に入れない |
| Switch host | `0x48 Enable vibration` | vibration enable state を保持する | high-level rumble API は作らない |
| maintainer | profile object | fixed identity だけを持つ | mutable state を混ぜない |

## 2. 対象範囲

- `SubcommandResponder` が `ControllerProfile` を受け取る構造。
- `0x02 Device Info` が profile helper と session / transport 由来 address を使う構造。
- `0x03 Set input report mode` の要求値を mutable session state として保持する仕様。
- `0x30` を標準対応 mode として扱う最小範囲。
- `0x3F` など unsupported report mode の扱いを source-audit 後に test で明示する仕様。
- `0x40 Enable IMU` の状態保持。
- `0x48 Enable vibration` の状態保持。
- mutable state の所有者を `SubcommandResponder` 内部または `SubcommandSessionState` 相当へ分ける設計。
- Pro Controller の既存 subcommand 応答 regression。

## 3. 対象外

- `0x3F` simple HID report の完全実装。
- 実機と完全一致する全 subcommand 対応。
- rumble waveform の実処理。
- player lights の public API 化。
- profile に mutable session state を混ぜること。
- `InputState` に report mode / IMU enable / vibration enable を入れること。
- 実 transport から Device Info 用 Bluetooth address を取得する wiring。必要なら unit_033 または別 issue。
- 実機、Bumble adapter、Switch-facing 動作の実行。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/protocol.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_005/M4_SUBCOMMAND_RESPONDER_HARDWARE.md`
- `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md`
- https://github.com/niart120/swbt-python/issues/48
- https://github.com/niart120/swbt-python/issues/49
- https://github.com/niart120/swbt-python/issues/50
- https://github.com/niart120/swbt-python/issues/51
- https://github.com/niart120/swbt-python/issues/52

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | subcommand ID、ACK byte、Device Info payload、unsupported report mode の扱いを source-audit fixture に記録した |
| Bumble / transport | required | deferred | Device Info 用 Bluetooth address を実 transport から得る wiring は対象外。unit_033 以降で扱う |
| OS / driver / adapter | not applicable | not applicable | 仕様作成と unit test では adapter を開かない |

### 5.1 監査対象

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| `0x02` Device Info Pro tail | existing `03 02` | hardware observation / implementation fact | `spec/complete/unit_028/CONTROLLER_PROFILE_CUSTOMIZATION.md` | Pro existing contract |
| Joy-Con `0x02` payload | pending | pending | source-audit required | do not generalize Pro bytes |
| `0x03` ACK byte | `0x80` | implementation fact | existing `subcommand_reply_payloads` fixture and unit test | ACK compatibility retained |
| unsupported report mode handling | requested byte stored; only `0x30` supported | implementation fact | `subcommand_report_mode_session_state` fixture | unsupported mode is not silently coerced to `0x30` |
| `0x40` enable IMU payload semantics | `0x00` disable / `0x01` enable | source fact | `subcommand_imu_vibration_enable_state` fixture | session state only |
| `0x48` enable vibration payload semantics | `0x00` disable / `0x01` enable | source fact | `subcommand_imu_vibration_enable_state` fixture | session state only |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| fixed profile | `ControllerProfile` | kind、device identity、descriptor、capabilities など固定値だけを持つ | report mode 等は入れない |
| session state | `SubcommandSessionState` 相当 | report mode、IMU enable、vibration enable、player lights request などを保持する | owner は明示する |
| Device Info | `0x02` | profile helper と session address から reply を作る | Joy-Con bytes は audit 後 |
| report mode | `0x03` with `0x30` | session state に current report mode として保持する | `ReportLoop` が参照する必要を確認 |
| unsupported mode | `0x03` with unsupported mode | source-audit 済みの扱いで test に固定する | 黙って `0x30` 扱いしない |
| IMU state | `0x40` | enabled / disabled を session state に保持する | IMU frame の送信可否とは分ける |
| vibration state | `0x48` | enabled / disabled を session state に保持する | waveform 処理はしない |
| Pro regression | existing Pro subcommands | 既存 tests を維持する | profile-aware 化で壊さない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | `SubcommandResponder` が profile を受け取り、`0x02` Device Info を profile helper 経由で返す | new | unit | no | `test_device_info_subcommand_uses_configured_profile` |
| done | `0x02` Device Info に呼び出し元から渡された Bluetooth address が反映される | new | unit | no | `test_device_info_subcommand_uses_caller_bluetooth_address` |
| done | `0x03 Set input report mode` の要求値が session state に保持される | new | unit | no | `test_set_input_report_mode_updates_session_state` |
| done | unsupported report mode の扱いが source-audit 済みの期待で固定される | edge | unit | no | ACK 互換で `unsupported_report_mode` に保持する |
| done | unsupported report mode を黙って `0x30` として扱わない | regression | unit | no | `test_unsupported_input_report_mode_is_recorded_without_coercing_to_0x30` |
| done | `0x40 Enable IMU` の要求値が session state に保持される | new | unit | no | `test_enable_imu_updates_session_state` |
| done | `0x48 Enable vibration` の要求値が session state に保持される | new | unit | no | `test_enable_vibration_updates_session_state` |
| done | profile と session state の所有者が code / test 名から分かる | regression | unit | no | `test_controller_profile_does_not_hold_mutable_subcommand_session_state` |
| done | Pro Controller の既存 subcommand reply tests が維持される | regression | unit | no | unit suite で維持 |
| done | fake transport output report injection で session state の更新を観測できる | new | integration | no | `test_output_report_injection_records_subcommand_session_state` |

## 8. 設計メモ

- `ControllerProfile` は immutable に寄せる。session state は connection / responder lifetime の mutable state として分ける。
- `SubcommandResponder` 内部に mutable state を持つ場合、test が state の lifetime を明確にできるようにする。別の `SubcommandSessionState` 値に分ける場合は owner を `SwitchGamepad` / dispatcher / responder のどこに置くか決める。
- `ReportLoop` が current report mode を参照するかは実装時に確認する。`0x30` のみ送る範囲では構造だけを用意し、`0x3F` 実装は別 unit に残す。
- player lights は session state 候補だが public API 化しない。必要なら request value を保持して diagnostics に出す程度に留める。
- existing unit_028 の Pro `0x02` tail `03 02` は Joy-Con へ一般化しない。
- self-review で、profile validation のために `SwitchGamepad.press()` / `release()` / `sticks()` が state store lock 外で read-modify-write している競合を検出した。`InputStateStore.update()` で検証込みの atomic update に直し、lock 待ち中の concurrent `press()` が stale state を上書きしない regression test を追加した。
- self-review で、`SwitchGamepadConfig(profile=...)` と profile 由来 `default_report_period_us` の検証不足を検出した。`ControllerProfile` と `SwitchGamepadConfig` の validation を追加した。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/subcommand.py` | modify | profile-aware responder と session state |
| `src/swbt/protocol/profile.py` | modify | Device Info helper と fixed identity boundary |
| `src/swbt/gamepad/output.py` | modify | responder / session state wiring |
| `src/swbt/gamepad/core.py` | modify | session state owner を置く場合 |
| `src/swbt/report_loop.py` | inspect / modify | report mode 参照が必要か確認 |
| `src/swbt/diagnostics.py` | modify | unsupported mode や session state event を記録する場合 |
| `tests/unit/test_subcommand_responder.py` | modify | Device Info、report mode、IMU、vibration |
| `tests/unit/test_gamepad_output_dispatcher.py` | modify | output report 経由の session state update |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | fake transport 経由の session state |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | 監査済み subcommand 値だけ追加 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 依存変更なし |
| `uv run ruff format --check .` | pass | 77 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 310 passed |
| `uv run pytest tests/integration` | pass | 82 passed |
| `uv run pytest tests/unit/test_subcommand_responder.py tests/unit/test_source_audit_fixtures.py tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_records_subcommand_session_state -q` | pass | 34 passed |
| `git diff --check` | pass | whitespace error なし |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 仕様作成では不要。unit / fake integration でも不要 |
| 承認範囲 | 後続で実機 subcommand sequence を観測する場合は、adapter open、HID advertising、pairing または reconnect、Switch-facing output report / subcommand handling、periodic report loop、cleanup の明示承認が必要 |
| adapter | 仕様作成では使用しない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実機時は subcommand raw bytes、reply、session state change、OS、driver、dongle、Bumble version、Switch model / firmware を記録する |
| cleanup | neutral、report loop 停止、transport close、adapter release |

## 12. 先送り事項

- `0x3F` simple HID report の実装。現時点では ACK 互換で `unsupported_report_mode` として記録する。
- Device Info 用 Bluetooth address を Bumble transport から取得する wiring。
- Joy-Con 固有 subcommand payload の完全一致。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] fixed `ControllerProfile` と mutable session state を分離した
- [x] unsupported report mode を黙って `0x30` として扱っていない
