# Joy-Con SDP Identity Policy 仕様書

## 1. 概要

### 1.1 目的

Joy-Con profile の Bluetooth Classic HID SDP record から Pro Controller 固定の identity-adjacent 値を外す。2026-07-06 の実機 retest では `0x02` Device Info が Joy-Con L + 実 local address になっても Pro Controller toast が残ったため、Device Info 以外の identity source として SDP policy を切り分けた。SDP policy 反映後の retest では、ユーザ目視で Joy-Con として登録された。

この unit では Joy-Con 固有 HID descriptor bytes は新規に確定しない。joycontrol の SDP XML は現行と同じ 203 bytes descriptor を使っているため、まず SDP attribute policy だけを profile-aware にする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| hardware observation | Device Info address `00 1b dc f9 9f 7d` を送っても Pro Controller toast が出て Joy-Con 登録が完了しなかった | `spec/hardware-test-log.md` |
| hardware observation | SDP policy 反映後の Joy-Con L retest で、同じ local address を Device Info に返し、SR+SL hold 後にユーザ目視で Joy-Con として登録された | `spec/hardware-test-log.md` |
| source fact | joycontrol の SDP XML は service name `Wireless Gamepad`、description `Gamepad`、provider `Nintendo`、country `0x00`、HID profile `0x0100`、normally connectable `false`、boot device `true`、SSR `0x0640/0x0320` を使う | https://github.com/mart1nro/joycontrol/blob/master/joycontrol/profile/sdp_record_hid.xml |
| implementation fact | 現行 swbt-python は service name に profile device name を使い、それ以外は Pro-compatible fixed としている | `src/swbt/transport/_bumble_sdp.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Bumble transport | Joy-Con L/R profile | SDP record が Joy-Con 用 policy を使う | Pro profile の SDP は既存値を維持 |
| maintainer | Joy-Con hardware trace | Device Info 以外の SDP identity 変更後に registration を再観測できる | 実機 UI は自動判定しない |

## 2. 対象範囲

- `ControllerProfile` に SDP policy を持たせる内部境界。
- `build_hid_service_records()` が profile の SDP policy を受け取る処理。
- Joy-Con L/R profile で joycontrol SDP XML と同じ policy 値を使うこと。
- Pro Controller profile の既存 SDP policy を維持する regression test。
- 根拠監査 fixture と作業仕様の更新。

## 3. 対象外

- Joy-Con-specific HID report descriptor bytes の新規確定。
- Class of Device `0x002508` の変更。joycontrol も同値を使うため、この unit では維持する。
- Switch 側の登録済み device database を消すこと。
- 実機再実行。
- Joy-Con R 実機検証。

## 4. 関連 docs

- `spec/complete/unit_033/PROFILE_AWARE_BUMBLE_SDP.md`
- `spec/complete/unit_035/JOYCON_DEVICE_INFO_ADDRESS_WIRING.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | joycontrol SDP XML の descriptor bytes は現行 203 bytes と一致する。新しい descriptor は追加しない |
| Bumble / transport | required | done | `joycontrol_sdp_record_policy` fixture に SDP attribute policy を記録する |
| OS / driver / adapter | required | done | 変更動機は `spec/hardware-test-log.md` の Windows / CSR8510 A10 / Bumble 0.0.230 観測に限定する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| Pro SDP regression | Pro profile | service name `Pro Controller`、country `0x21`、remote wake true、profile `0x0101`、normally connectable true、boot false、SSR `0xffff/0xffff` | 既存挙動維持 |
| Joy-Con SDP policy | Joy-Con L/R profile | service name `Wireless Gamepad`、description `Gamepad`、provider `Nintendo`、device release `0x0100`、country `0x00`、profile `0x0100`、normally connectable false、boot true、SSR `0x0640/0x0320` | joycontrol SDP XML 由来 |
| descriptor boundary | Joy-Con L/R profile | HID descriptor は現行 203 bytes を維持 | descriptor 差分は別 unit |
| transport wiring | `_default_initialize_device()` | profile の SDP policy が SDP builder に渡る | device local name は `Joy-Con (L)` / `(R)` のまま |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | Joy-Con profile が joycontrol SDP policy を保持する | new | unit | no | `tests/unit/test_protocol_profile.py` |
| green | SDP builder が Joy-Con policy の attributes を出力する | new | unit | no | `tests/unit/test_bumble_sdp.py` |
| green | Bumble initialize が profile SDP policy を builder へ渡す | new | unit | no | `tests/unit/test_bumble_transport.py` |
| green | Pro SDP policy が既存値から変わらない | regression | unit | no | `tests/unit/test_bumble_sdp.py` |
| hardware-pass | Joy-Con L 実機 retest で registration を再観測する | hardware | hardware | yes | 2026-07-06。ユーザ目視で Joy-Con として登録 |

## 8. 設計メモ

`device_name` は HCI local name と public API の表示名であり、SDP primary service name とは分ける。Joy-Con では HCI local name を `Joy-Con (L)` / `Joy-Con (R)` のままにし、SDP service name は joycontrol XML に合わせて `Wireless Gamepad` にする。

Class of Device `0x002508` と HID descriptor 203 bytes は Pro 固定に見えるが、joycontrol も同じ値を使う。そのため今回の実装では変更しない。SDP policy 反映後の Windows / CSR8510 A10 / Switch 2 firmware 22.1.0 retest では Joy-Con として登録されたが、debug log は SDP attribute read を直接表示しない。別 adapter / firmware へ一般化しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/protocol/profile.py` | modify | SDP policy dataclass と Joy-Con policy |
| `src/swbt/transport/_bumble_sdp.py` | modify | policy-aware SDP builder |
| `src/swbt/transport/bumble.py` | modify | profile SDP policy wiring |
| `tests/unit/test_protocol_profile.py` | modify | profile policy test |
| `tests/unit/test_bumble_sdp.py` | modify | SDP attribute test |
| `tests/unit/test_bumble_transport.py` | modify | transport wiring test |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | source-audit fixture |
| `tests/unit/test_source_audit_fixtures.py` | modify | fixture coverage |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_protocol_profile.py::test_joycon_profiles_use_joycontrol_sdp_policy tests/unit/test_bumble_sdp.py::test_bumble_sdp_builder_uses_joycon_policy tests/unit/test_bumble_transport.py::test_bumble_initialize_device_uses_profile_hid_descriptor -q` | red | expected: missing `hid_sdp_policy` and missing `sdp_policy` wiring |
| `uv run pytest tests/unit/test_protocol_profile.py::test_joycon_profiles_use_joycontrol_sdp_policy tests/unit/test_bumble_sdp.py::test_bumble_sdp_builder_uses_joycon_policy tests/unit/test_bumble_transport.py::test_bumble_initialize_device_uses_profile_hid_descriptor -q` | pass | 3 passed |
| `uv run pytest tests/unit/test_protocol_profile.py tests/unit/test_bumble_sdp.py tests/unit/test_bumble_transport.py::test_bumble_initialize_device_uses_profile_hid_descriptor tests/unit/test_source_audit_fixtures.py -q` | pass | 58 passed |
| `uv run ruff format --check .` | pass | 78 files already formatted after `uv run ruff format .` reformatted `_bumble_sdp.py` |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` | pass | 330 passed |
| `uv run pytest tests/integration -q` | pass | 91 passed |
| `uv run pytest tests/hardware/test_joycon_profile.py --collect-only -q` | pass | 2 tests collected; adapter not opened |
| `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-sdp-policy-20260706 --log-file build\hardware\joycon-left-sdp-policy-20260706\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-joycon-sdp-policy -q -s` | hardware-pass | 1 passed in 24.40s。trace は `device_info_data=04000102001bdcf99f7d0101` と SR+SL `000030` hold reports を記録。ユーザ目視で Joy-Con として登録 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for final toast / registration observation |
| 承認範囲 | USB Bluetooth dongle open、Joy-Con L HID advertising、Switch pairing、subcommand handling、periodic `0x30`、SR+SL hold、neutral cleanup、adapter release |
| adapter | `usb:0` を想定。実行前に command で明示する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build/hardware/...` |
| cleanup | `pad.close(neutral=True)`、disconnect request、transport close、adapter release |

## 12. 先送り事項

- Joy-Con-specific HID descriptor bytes の source-audit と実機 A/B。現時点では joycontrol SDP XML と同じ 203 bytes descriptor を維持する。
- Joy-Con R、Joy-Con reconnect、Joy-Con profile の通常入力反映、別 firmware / dongle での registration は未検証。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
