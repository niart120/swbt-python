# Profile Aware Bumble SDP 仕様書

## 1. 概要

### 1.1 目的

Bumble transport / SDP 初期化から Pro Controller 固定の descriptor や device name を外し、`ControllerProfile` から導出する。

HID report descriptor、SDP record、Class of Device、HID subclass、country code、supervision timeout、SSR fields は Switch / Bumble 境界の protocol 値である。source-audit 済みの範囲だけを変更し、根拠がない値は Pro-compatible 固定として残す理由を明記する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| parent issue | Joy-Con support plan と順序 | https://github.com/niart120/swbt-python/issues/48 |
| child issue | profile を Bumble transport / SDP setup へ渡す | https://github.com/niart120/swbt-python/issues/53 |
| dependency | profile injection | https://github.com/niart120/swbt-python/issues/49 |
| dependency | Joy-Con profile identity | https://github.com/niart120/swbt-python/issues/50 |
| dependency | Joy-Con input report mapping | https://github.com/niart120/swbt-python/issues/51 |
| initial transport | Bumble HID transport、SDP record、HID descriptor の責務 | `spec/initial/transport-bumble.md` |
| initial risks | HID descriptor / SDP record 不一致のリスク | `spec/initial/risks.md` |
| source-audit | descriptor、SDP、L2CAP、Bumble HID Device helper、driver 仮定の根拠分類 | `.agents/skills/source-audit/SKILL.md` |
| hardware-harness | adapter open、advertising、pairing、report loop の承認境界 | `.agents/skills/hardware-harness/SKILL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| transport factory | Pro / Joy-Con profile | `BumbleHidTransport` まで同じ profile が渡る | public import 時に Bumble を解決しない |
| SDP builder | `profile.hid_report_descriptor` | SDP descriptor list に profile 由来 descriptor を入れる | descriptor bytes は source-audit 済みだけ |
| device name | profile default と user override | 未指定時は profile name、明示指定時は user value | #49 override 規則 |
| maintainer | descriptor 以外の SDP / Bluetooth 固定値 | profile-aware 値または Pro-compatible 固定理由を追える | Joy-Con 完全一致と書かない |

## 2. 対象範囲

- transport factory の引数に `profile: ControllerProfile` を追加する。
- `BumbleHidTransport` が `ControllerProfile` を受け取る。
- `BumbleHidTransport` 内部で `ProControllerProfile()` を直接生成しない。
- SDP record 生成時の HID report descriptor を `profile.hid_report_descriptor` から渡す。
- device name の既定値を `profile.device_name` に寄せる。
- `device_name` 明示 override が profile default より優先されること。
- Joy-Con L/R で key store を分ける運用の記録。
- descriptor 以外の SDP / Bluetooth 固定値の audit scope を明示する。

## 3. 対象外

- Bluetooth stack の低レベル再設計。
- Joy-Con L/R の同時接続 orchestration。
- 実機検証結果に基づく SDP record の微調整。
- Bumble から Device Info 用 Bluetooth address を取得する API 設計。必要になった場合は別 follow-up。
- `JoyConPair` 実装。
- 仕様作成時の実機、Bumble adapter、Switch-facing 動作。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_003/M2_BUMBLE_HID_TRANSPORT.md`
- `spec/complete/unit_004/M3_PAIRING_L2CAP.md`
- `spec/complete/unit_027/ADAPTER_DISCOVERY_API.md`
- `src/swbt/transport/_bumble_sdp.py`
- `tests/unit/test_bumble_sdp.py`
- https://github.com/niart120/swbt-python/issues/48
- https://github.com/niart120/swbt-python/issues/49
- https://github.com/niart120/swbt-python/issues/50
- https://github.com/niart120/swbt-python/issues/51
- https://github.com/niart120/swbt-python/issues/53

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | done | Pro-compatible descriptor は既存 `hid_report_descriptor` fixture、profile/SDP 境界は `profile_aware_bumble_sdp_boundary` fixture に記録した |
| Bumble / transport | required | done | SDP record、Class of Device、HID country、supervision、SSR、Bumble helper の profile-aware / fixed 境界を fixture と spec に記録した |
| OS / driver / adapter | conditional | not run | この unit では Bumble adapter / Switch 実機を使わない。Joy-Con profile の実機互換は未検証として docs に記録した |

### 5.1 監査対象

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| Pro Controller HID descriptor | existing 203 bytes | source fact | `hid_report_descriptor` fixture, `test_pro_controller_hid_descriptor_is_203_bytes` | keep / verified |
| Joy-Con L HID descriptor | Pro-compatible descriptor inherited for now | implementation fact | `profile_aware_bumble_sdp_boundary` fixture | Joy-Con-specific bytes remain unaudited |
| Joy-Con R HID descriptor | Pro-compatible descriptor inherited for now | implementation fact | `profile_aware_bumble_sdp_boundary` fixture | Joy-Con-specific bytes remain unaudited |
| SDP HID descriptor list | `ControllerProfile.hid_report_descriptor` | implementation fact | `test_bumble_sdp_builder_uses_supplied_hid_descriptor`, `test_bumble_initialize_device_uses_profile_hid_descriptor` | done |
| Class of Device | `0x002508` | implementation fact | `swbt_daemon_reference_discovery_identity`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |
| HID device subclass | `0x08` | implementation fact | `_bumble_sdp.py`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |
| HID country code | `0x21` | implementation fact | `btstack_reference_hid_sdp_policy`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |
| HID parser / profile version | parser `0x0111`, profile `0x0101` | implementation fact | `_bumble_sdp.py`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |
| supervision timeout | `0x0c80` | implementation fact | `btstack_reference_hid_sdp_policy`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |
| SSR host max latency / min timeout | `0xffff` / `0xffff` | implementation fact | `btstack_reference_hid_sdp_policy`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |
| virtual cable / reconnect initiate / remote wake / normally connectable | `true` / `true` / `true` / `true` | implementation fact | `_bumble_sdp.py`, `profile_aware_bumble_sdp_boundary` | Pro-compatible fixed |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| profile propagation | `SwitchGamepadConfig.profile` | transport factory から `BumbleHidTransport` / SDP builder まで到達する | unit test で spy する |
| descriptor source | profile with descriptor | SDP descriptor list が profile descriptor を使う | descriptor bytes は audit 済みだけ |
| device name default | profile default name | transport / SDP service name が profile name を使う | user override なし |
| device name override | `device_name="..."` | user value が profile default を上書きする | #49 rule |
| Pro regression | Pro profile | existing descriptor / SDP test が維持される | behavior-preserving |
| Joy-Con descriptor pending | Joy-Con profile without audited descriptor | descriptor を契約化しない | implementation は audit 後 |
| fixed SDP values | descriptor 以外の values | profile-aware にした値、または Pro-compatible fixed 理由を spec に残す | Joy-Con 完全一致と書かない |
| key store operation | Joy-Con L/R | 左右 / profile ごとに key store を分ける運用を docs に残す | pair 混線を避ける |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| done | transport factory が profile を `BumbleHidTransport` へ渡す | new | unit | no | `test_default_transport_factory_passes_resource_config_to_bumble_transport` |
| done | `BumbleHidTransport` が profile を保持し、内部で `ProControllerProfile()` を直接生成しない | new | unit | no | `test_pro_controller_profile_direct_construction_is_limited_to_profile_factory`, `rg` で transport 側に直接生成なし |
| done | SDP builder が profile の HID descriptor を descriptor list に入れる | new | unit | no | `test_bumble_sdp_builder_uses_supplied_hid_descriptor`, `test_bumble_initialize_device_uses_profile_hid_descriptor` |
| done | Pro Controller profile の descriptor / SDP output が既存 test と一致する | regression | unit | no | `test_bumble_sdp_builder_preserves_reference_hid_attributes` |
| done | device name 未指定時は profile default が SDP service name へ渡る | new | unit | no | `test_from_config_uses_profile_device_name_unless_user_overrides` |
| done | `device_name` 明示 override が profile default を上書きする | new | unit | no | 同上 |
| done | descriptor 以外の SDP / Bluetooth 固定値が audit table または fixture から追える | new | unit / docs | no | `profile_aware_bumble_sdp_boundary` fixture |
| done | Joy-Con descriptor bytes が source-audit 済みでない場合、stable fixture に入らない | edge | unit / docs | no | fixture で unaudited と明記し、Joy-Con-specific descriptor は追加していない |
| done | Joy-Con L/R profile を使う場合、key store を左右別にする docs / examples がある | new | docs | no | `docs/hardware.md` の Profile-specific Key Stores |

## 8. 設計メモ

- `_bumble_sdp.py` の固定値は descriptor だけではない。Class of Device、HID subclass、country code、parser / profile version、supervision timeout、SSR host latency / timeout、virtual cable、reconnect initiate、remote wake、normally connectable を audit 対象として扱う。
- source-audit がない値は Pro-compatible 固定として残してよいが、その理由とリスクを spec に残す。Joy-Con 完全一致とは書かない。この unit では Class of Device `0x002508` と SDP の descriptor-adjacent 値を Pro-compatible fixed として扱う。
- Joy-Con descriptor は unit_031 の input report mapping と同じ根拠に依存する。現時点では Joy-Con-specific descriptor bytes を確定しない。
- `device_name` は transport / SDP の表示名であり、Device Info payload とは分ける。
- Joy-Con L/R は別の仮想 Bluetooth HID device として扱うため、key store は左右別 / profile 別に分ける運用を docs に出す。
- docs/hardware.md の profile-specific key store 節は gpt-5.5 sub-agent が独立して執筆し、main agent が scope と wording をレビューした。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/transport_factory.py` | modify | profile を default transport へ渡す |
| `src/swbt/gamepad/core.py` | modify | profile と device_name override の transport wiring |
| `src/swbt/transport/bumble.py` | modify | profile を受け取る |
| `src/swbt/transport/_bumble_sdp.py` | modify | descriptor / service name / fixed SDP values の扱い |
| `src/swbt/protocol/profile.py` | modify | `hid_report_descriptor` と device name default |
| `tests/unit/test_gamepad_transport_factory.py` | modify | profile propagation |
| `tests/unit/test_bumble_transport.py` | modify | `BumbleHidTransport` の profile保持 |
| `tests/unit/test_bumble_sdp.py` | modify | descriptor / SDP fixed values |
| `tests/unit/test_public_api_boundary.py` | modify | Bumble import boundary |
| `docs/hardware.md` | modify | key store を左右 / profile 別に分ける運用。unit_034 と調整 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_bumble_sdp.py tests/unit/test_source_audit_fixtures.py tests/unit/test_public_docs.py::test_hardware_doc_separates_confirmed_unconfirmed_and_troubleshooting -q` | pass | 19 passed |
| `uv run pytest tests/unit/test_gamepad_transport_factory.py tests/unit/test_bumble_transport.py tests/unit/test_bumble_sdp.py tests/unit/test_public_api_boundary.py::test_from_config_uses_profile_device_name_unless_user_overrides tests/unit/test_public_api_boundary.py::test_default_transport_without_key_store_records_reconnect_limitation tests/unit/test_source_audit_fixtures.py tests/unit/test_public_docs.py::test_hardware_doc_separates_confirmed_unconfirmed_and_troubleshooting -q` | pass | 61 passed |
| `uv sync --dev` | pass | 依存変更なし |
| `uv run ruff format --check .` | pass | 77 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 312 passed |
| `uv run pytest tests/integration` | pass | 82 passed |
| `git diff --check` | pass | whitespace error なし |
| `uv run pytest -m bumble` | not run | 実行には hardware-harness の明示承認が必要 |
| `uv run pytest -m hardware` | not run | Switch-facing 動作は対象外。実行には明示承認が必要 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | 仕様作成では不要。unit test でも不要。Bumble adapter / Switch で descriptor と SDP を確認する場合だけ必要 |
| 承認範囲 | Bumble adapter open、Bluetooth Classic HID Device 初期化、discoverable / connectable、HID advertising、pairing、report loop、Switch-facing output report を含む場合は、対象 adapter、command、動作範囲、cleanup plan の明示承認が必要 |
| adapter | 仕様作成では使用しない。実行時は例 `usb:0` のように専用 USB Bluetooth dongle を指定する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | OS、driver、dongle identity、adapter string、Bumble version、Python version、Switch model / firmware、descriptor / SDP source、command、result、cleanup |
| cleanup | advertising 停止、neutral、report loop 停止、transport close、adapter release |

## 12. 先送り事項

- Joy-Con descriptor bytes は source-audit 完了まで pending。この unit では Pro-compatible descriptor を profile から渡すだけで、Joy-Con-specific descriptor bytes は確定しない。
- descriptor 以外の SDP / Bluetooth 固定値は Pro-compatible fixed として残した。Joy-Con 完全一致が必要になった場合は別 unit で source-audit と実機検証を行う。
- Device Info 用 Bluetooth address の transport wiring。
- Joy-Con L/R 同時接続 orchestration。
- 実機検証に基づく SDP 微調整。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
- [x] descriptor / SDP / Class of Device / HID subclass / country / supervision / SSR を audit scope に含めた
- [x] 未監査 Joy-Con descriptor を確定していない
