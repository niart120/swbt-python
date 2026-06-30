# M2 Bumble HID Transport 仕様書

## 1. 概要

### 1.1 目的

Bumble を使って USB Bluetooth dongle を開き、Bluetooth Classic HID Device transport を構成する。M2 は Switch pairing 成功を完了条件にしない。adapter open、Bumble device 初期化、Classic 有効化、HID Device 初期化、discoverable / connectable、close の安定化までを扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M2 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| transport-bumble | Bumble transport の責務、OS 注意点、adapter bring-up | `spec/initial/transport-bumble.md` |
| risks | Bumble Classic HID、OS / driver、dongle 差分 | `spec/initial/risks.md` |
| hardware-harness skill | adapter open と HID advertising の承認境界 | `.agents/skills/hardware-harness/SKILL.md` |
| source-audit skill | Bumble HID Device / SDP / descriptor / driver 前提の根拠分類 | `.agents/skills/source-audit/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| developer | `BumbleHidTransport(adapter="usb:0").open()` | USB HCI transport、Bumble device、HID Device 初期化が完了する | 明示承認が必要 |
| developer | `start_advertising()` | discoverable / connectable に入る | Switch pairing 成功は M3 |
| developer | `close()` を複数回呼ぶ | 例外なく後始末される | cleanup を diagnostics に残す |
| library code | Bumble 由来例外 | `TransportOpenError` など swbt 例外に変換される | Bumble 型を public API に出さない |

## 2. 対象範囲

- `BumbleHidTransport`。
- Bumble USB HCI transport open / close。
- Bumble device 生成。
- Bluetooth Classic 有効化。
- HID Device helper の初期化。
- SDP record と HID descriptor の Bumble への受け渡し。
- discoverable / connectable 状態への遷移。
- control / interrupt callback を上位 callback へ渡す境界。
- adapter、OS、Python version、Bumble version、driver 情報の diagnostics 記録。
- open 失敗の `TransportOpenError` 変換。

## 3. 対象外

- Switch pairing 成功の保証。
- L2CAP control / interrupt channel open の実機確認。
- Button A の実機反映。
- reconnect。
- Linux / macOS の動作保証。
- OS 標準 Bluetooth adapter の利用。

## 4. 関連 docs

- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/wip/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | `tests/unit/fixtures/source_audit/switch_protocol_values.toml` の `hid_report_descriptor` を HID descriptor handoff source とする。SDP record は Bumble 側の構築境界として扱い、descriptor bytes と混ぜない |
| Bumble / transport | required | done | `bumble_hid_device_api` と `bumble_classic_visibility` に `bumble==0.0.230` の HID Device helper、Classic PSM、callback、discoverable / connectable 前提を記録した |
| OS / driver / adapter | required | done | `swbt_python_adapter_driver_boundary` は未検証仮説、`swbt_daemon_csr8510_winusb_observation` は既存 daemon の条件付き実機観測として分離した。M2 の adapter open は別途承認が必要 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| adapter open | `adapter="usb:0"` | USB HCI transport を開く | 承認対象 |
| device init | open 済み transport | Bumble device を生成し Classic を有効化する | Bumble version を記録 |
| HID setup | profile descriptor | HID Device helper、SDP record、HID descriptor を設定する | descriptor は監査済み値 |
| advertising | `start_advertising()` | discoverable / connectable 状態になる | Switch-facing 動作のため承認対象 |
| send interrupt | connected channel なし | 明確な送信失敗を返す | M2 では実 channel 未接続を許容しない |
| close | open 途中または open 済み | 可能な範囲で close し、複数回呼んでも破綻しない | cleanup event を記録 |
| exception mapping | Bumble 例外 | `swbt.errors` の transport 例外へ変換する | 元例外型は diagnostics |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | Bumble package を import できない環境でも `swbt` public import は壊れない | regression | unit | no | `test_public_api_import_does_not_resolve_bumble` で固定 |
| green | `BumbleHidTransport` が adapter string を diagnostics に記録する | new | unit | no | `test_bumble_transport_records_adapter_string_in_diagnostics` で固定。adapter open は fake opener |
| green | Bumble open 失敗が `TransportOpenError` に変換される | new | unit | no | `test_bumble_open_failure_is_mapped_to_transport_open_error` で固定 |
| green | open 途中の失敗でも close cleanup が呼ばれる | edge | unit | no | `test_bumble_open_failure_after_handle_open_closes_handle` で固定 |
| green | close を複数回呼んでも例外を出さない | edge | unit | no | `test_bumble_close_is_idempotent` で固定 |
| green | `swbt.transport.bumble` 以外が Bumble を import していない | regression | unit | no | `test_only_bumble_transport_module_may_resolve_bumble` で固定 |
| todo | `adapter="usb:0"` で USB HCI transport を開ける | new | bumble | yes | 明示承認、専用 dongle、cleanup plan が必要 |
| todo | Bumble device を生成し Classic を有効化できる | new | bumble | yes | `@pytest.mark.bumble` |
| todo | HID Device 初期化、discoverable / connectable へ遷移できる | new | bumble | yes | Switch pairing は M3 |
| todo | adapter 情報、OS、Python version、Bumble version が diagnostics に残る | new | bumble | yes | hardware log に転記可能な粒度 |

## 8. 設計メモ

- M2 の実機手前検証は USB Bluetooth dongle を Bumble から開くため、`hardware-harness` の承認境界を通す。
- Windows では専用 dongle と WinUSB assignment を前提にする。内蔵 Bluetooth や常用 adapter を対象にしない。
- `BumbleHidTransport` の public constructor は `adapter` など単純な値だけを受ける。Bumble object は受けない。
- SDP record と HID descriptor は protocol profile から受け取り、Bumble 固有 object への変換は transport 内で行う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/bumble.py` | new | Bumble transport 実装 |
| `src/swbt/transport/base.py` | modify | 実 transport に必要な callback / send interface |
| `src/swbt/protocol/profile.py` | modify | HID descriptor / SDP 用 profile data |
| `src/swbt/diagnostics.py` | modify | adapter と runtime metadata |
| `src/swbt/errors.py` | modify | transport 例外 |
| `tests/unit/` | modify | mock による Bumble boundary tests |
| `tests/integration/` | modify | fake transport との境界維持 |
| `tests/hardware/` | new | `@pytest.mark.bumble` adapter tests |

## 10. 検証

この表は M2 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit\test_public_api_boundary.py::test_public_api_import_does_not_resolve_bumble -q` | pass | 1 passed。public API import が Bumble import を解決しないことを確認した |
| `uv run pytest tests\unit\test_bumble_transport.py::test_bumble_transport_records_adapter_string_in_diagnostics -q` | pass | 1 passed。adapter string が diagnostics に記録されることを fake opener で確認した |
| `uv run pytest tests\unit\test_bumble_transport.py::test_bumble_open_failure_is_mapped_to_transport_open_error -q` | pass | 1 passed。fake opener の失敗が `TransportOpenError` に変換され、error event が残ることを確認した |
| `uv run pytest tests\unit\test_bumble_transport.py::test_bumble_open_failure_after_handle_open_closes_handle -q` | pass | 1 passed。open 後初期化失敗時に handle cleanup が呼ばれることを確認した |
| `uv run pytest tests\unit\test_bumble_transport.py::test_bumble_close_is_idempotent -q` | pass | 1 passed。`close()` を複数回呼んでも handle cleanup が一度だけ呼ばれることを確認した |
| `uv run pytest tests\unit\test_public_api_boundary.py::test_only_bumble_transport_module_may_resolve_bumble -q` | pass | 1 passed。`swbt.transport.bumble` 以外の `swbt` module import が Bumble を解決しないことを確認した |
| `uv run pytest tests\unit -q` | pass | 77 passed |
| `uv run ruff format --check .` | pass | 32 files already formatted |
| `uv run ruff check .` | pass | lint pass |
| `uv run ty check --no-progress` | pass | type check pass |
| `uv run pytest tests/unit tests/integration` | pending | M2 実装後に local automated gate として実行する |
| `uv run pytest -m bumble` | pending-approval | 専用 adapter、command、cleanup plan の明示承認後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for adapter bring-up; Switch 本体は不要 |
| 承認範囲 | USB Bluetooth dongle open、Bumble device 初期化、Classic 有効化、HID Device 初期化、discoverable / connectable、close |
| adapter | 例: `usb:0`。実行時に専用 dongle であることを確認する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `docs/hardware-test-log.md`、diagnostics trace |
| cleanup | advertising 停止、HID Device close、Bumble transport close、adapter release |

## 12. 先送り事項

- Switch pairing と L2CAP channel open は M3 で扱う。
- 実機 subcommand sequence は M4 で扱う。
- Linux / macOS の保証範囲は初期 release gate で改めて判断する。

## 13. チェックリスト

このチェックリストは M2 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] Bumble / HID descriptor / SDP / OS driver 前提の根拠監査を実施し、状態を更新した
- [ ] M2 の local automated gate を実行し、検証欄を結果で更新した
- [ ] adapter を使う検証は承認、command、cleanup、結果を記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
