# Joy-Con Device Info Address Wiring 仕様書

## 1. 概要

### 1.1 目的

Joy-Con profile の実機 pairing で、Bumble transport の local Bluetooth address を `0x02` Device Info 応答へ入れる。2026-07-06 の実機 run では on-air local BD_ADDR が `00:1B:DC:F9:9F:7D` だった一方、Device Info payload は `00 00 00 00 00 00` のままだった。

この unit は Pro toast 問題の全原因を断定しない。まず protocol identity の不整合をなくし、次の実機検証で toast 表示と Device Info address を分けて観測できる状態にする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user observation | pairing は完了したが、登録 toast は Pro Controller、順番画面は Joy-Con L | conversation |
| hardware trace | Joy-Con L run は local BD_ADDR と Device Info address が一致していなかった | `spec/hardware-test-log.md` |
| issue | Bluetooth address は profile 固定値ではなく transport/session 由来として扱う | https://github.com/niart120/swbt-python/issues/50 |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Switch host | `0x02` Request Device Info | `ControllerProfile.build_device_info()` に transport local address が入る | address が取得できない transport は既存の zero fallback |
| maintainer | Joy-Con hardware trace | Bumble 初期化 event の local address と Device Info payload address を比較できる | UI toast は自動判定しない |

## 2. 対象範囲

- `HidDeviceTransport` から local Bluetooth address を取得する内部境界。
- `BumbleHidTransport` で Bumble `public_address` を Device Info 用 bytes に変換する処理。
- `SwitchGamepad` が transport open 後に `SubcommandResponder` へ address を渡す処理。
- Joy-Con hardware test が Device Info address と Bumble local address の一致を検査すること。
- 実機観測と docs の更新。

## 3. 対象外

- Bluetooth controller の public address を profile ごとに変更すること。
- Joy-Con-specific HID descriptor / SDP record の完全一致。
- Switch 側の登録済み device database を自動で消すこと。
- Joy-Con R 実機検証。
- UI toast を自動判定すること。

## 4. 関連 docs

- `spec/initial/protocol.md`
- `spec/initial/transport-bumble.md`
- `spec/complete/unit_030/JOYCON_PROFILE_IDENTITY_SPI.md`
- `spec/complete/unit_033/PROFILE_AWARE_BUMBLE_SDP.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | Device Info の address は caller supplied として既存 fixture と #50 に記録済み |
| Bumble / transport | required | done | `device_info_local_bluetooth_address_wiring` fixture に、Bumble `Address` の表示順変換と transport wiring を記録する |
| OS / driver / adapter | required | done | `spec/hardware-test-log.md` に Windows / CSR8510 A10 / WinUSB / Bumble 0.0.230 の観測を記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| transport address propagation | transport が `local_bluetooth_address()` で 6 bytes を返す | `0x02` Device Info reply の bytes 4-9 に同じ値が入る | fake transport で検証 |
| Bumble address conversion | Bumble `Address("00:1B:DC:F9:9F:7D")` | `00 1b dc f9 9f 7d` を返す | `bytes(Address)` は little-endian なので使わない |
| no address fallback | custom transport が `local_bluetooth_address()` で `None` を返す | 既存の zero address fallback を維持する | 後方互換 |
| hardware guard | Joy-Con hardware test | Bumble local address と Device Info address が一致しない場合 fail | 実行には明示承認が必要 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | fake transport の local address が Device Info reply に入る | new | integration | no | `tests/integration/test_switch_gamepad_fake_transport.py` |
| green | Bumble `Address` を Device Info 表示順 bytes に変換する | new | unit | no | `tests/unit/test_bumble_transport.py` |
| green | hardware test が local address と Device Info address の一致を要求する | new | hardware | yes | 実行は未実施 |

## 8. 設計メモ

`SubcommandResponder` はすでに `device_info_bluetooth_address` を受け取れる。今回の変更は production 経路で transport open 後に値を注入するだけに留める。

Switch 側の登録 toast が Pro Controller のまま残る場合、残る候補は二つある。ひとつは同じ物理 dongle address を過去の Pro Controller 登録と共有していること。もうひとつは Joy-Con-specific SDP / descriptor-adjacent 値の不足。どちらもこの unit では確定しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/base.py` | modify | local address 取得境界 |
| `src/swbt/transport/bumble.py` | modify | Bumble public address の変換と公開 |
| `src/swbt/gamepad/core.py` | modify | responder への address 注入 |
| `src/swbt/transport/fake.py` | modify | fake transport address |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | Device Info address propagation |
| `tests/unit/test_bumble_transport.py` | modify | Bumble address conversion |
| `tests/hardware/test_joycon_profile.py` | modify | 実機 test guard |
| `tests/unit/fixtures/source_audit/switch_protocol_values.toml` | modify | 根拠監査 fixture |
| `spec/hardware-test-log.md` | modify | 実機観測 |
| `docs/` / `README.md` | modify | Joy-Con caveat |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run ruff format --check .` | pass | 78 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit/test_bumble_transport.py tests/unit/test_source_audit_fixtures.py tests/integration/test_switch_gamepad_fake_transport.py::test_output_report_injection_uses_transport_bluetooth_address_for_device_info tests/unit/test_public_docs.py tests/unit/test_readme_docs.py tests/unit/test_public_api_boundary.py -q` | pass | 99 passed |
| `uv run pytest tests/unit -q` | pass | 325 passed |
| `uv run pytest tests/integration -q` | pass | 90 passed |
| `uv run pytest tests/hardware/test_joycon_profile.py --collect-only -q` | pass | 2 tests collected |
| hardware Joy-Con L retest | pending | ユーザ承認後に実行 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for final Joy-Con toast observation |
| 承認範囲 | USB Bluetooth dongle open、Joy-Con L HID advertising、Switch pairing、subcommand handling、periodic `0x30`、SR+SL hold、neutral cleanup、adapter release |
| adapter | `usb:0` を想定。実行前に command で明示する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `build/hardware/...` |
| cleanup | `pad.close(neutral=True)`、disconnect request、transport close、adapter release |

## 12. 先送り事項

- Joy-Con-specific SDP / descriptor-adjacent values の source-audit と実装。
- 同じ物理 dongle address を Pro / Joy-Con で使い回した場合の Switch 側登録名の扱い。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 非実機検証結果を記録した
- [ ] 実機 retest の結果または未実行理由を記録した
