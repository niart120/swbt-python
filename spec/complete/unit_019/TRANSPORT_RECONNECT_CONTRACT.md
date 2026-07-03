# Transport Reconnect Contract 仕様書

## 1. 概要

### 1.1 目的

`unit_018` で `key_store_path` を `SwitchGamepad` / `SwitchGamepadConfig` の構成値へ戻し、transport 注入を public extension point として残した。追加レビューでは、その境界に残る 2 点が指摘された。

この unit では、injected transport に対して default Bumble transport 前提の `reconnect_key_store_unavailable` diagnostics を出さないようにする。あわせて `HidDeviceTransport.list_bonded_peers()` の contract を、任意の bonded peer 一覧ではなく current reconnect candidate 0 件または 1 件を返す API として明文化する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user review input | injected transport では `reconnect_key_store_unavailable` を出さない。`list_bonded_peers()` は current reconnect candidate 0/1 件の contract と明記する | conversation, 2026-07-03 |
| completed unit | key store は構成値へ戻り、transport 注入は public extension point として残った | `spec/complete/unit_018/KEY_STORE_TRANSPORT_BOUNDARY.md` |
| implementation-before | `try_reconnect()` は `key_store_path is None` だけで diagnostics を出す | `src/swbt/gamepad.py` |
| implementation-before | `HidDeviceTransport.list_bonded_peers()` は known bonded peers を返すように読める | `src/swbt/transport/base.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| default Bumble transport user | `SwitchGamepad(adapter="usb:0", key_store_path=None).try_reconnect()` | `reconnect_key_store_unavailable` が記録される | default transport の永続 reconnect 不可を伝える |
| custom transport user | `SwitchGamepad(transport=fake, key_store_path=None).try_reconnect()` | `reconnect_key_store_unavailable` は記録されない | custom transport の key store 方針を `SwitchGamepad` が決め打ちしない |
| transport implementer | `list_bonded_peers()` を実装する | current reconnect candidate 0/1 件だけを返す | 複数 current は例外。historical peer は返さない |

## 2. 対象範囲

- `SwitchGamepad` が transport 注入有無を保持する。
- `reconnect_key_store_unavailable` は default Bumble transport を `SwitchGamepad` が所有する場合だけ記録する。
- `HidDeviceTransport.list_bonded_peers()` の docstring を current reconnect candidate contract に更新する。
- fake transport と既存 tests を新 contract に合わせる。
- `spec/initial` の transport / lifecycle 記述を必要最小限更新する。

## 3. 対象外

- `key_store_path` public API の再変更。
- `ConnectionResult` status の追加。
- previous peer を使った reconnect fallback。
- 実機 pairing / reconnect の再検証。
- HID report bytes、SDP、L2CAP 手順の変更。

## 4. 関連 docs

- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/complete/unit_018/KEY_STORE_TRANSPORT_BOUNDARY.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | HID report layout は変更しない |
| Bumble / transport | not applicable | implementation-fact-only | transport boundary の contract 文言と fake behavior の整理であり、Bumble 新仮定は追加しない |
| OS / driver / adapter | not applicable | not applicable | adapter open や driver 挙動は変更しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| default transport no key store | default Bumble transport + `key_store_path=None` | `reconnect_key_store_unavailable` を記録 | `try_reconnect()` は `no_bond` |
| injected transport no key store | injected transport + `key_store_path=None` | `reconnect_key_store_unavailable` を記録しない | custom transport の内部 storage は不問 |
| current candidate 0 件 | `list_bonded_peers()` | `()` | reconnect は `no_bond` |
| current candidate 1 件 | `list_bonded_peers()` | `(BondedPeer(...),)` | reconnect attempt へ進む |
| current candidate 複数 | fake / custom transport | `InvalidKeyStoreError` | 複数 `BondedPeer` を返さない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | injected transport + `key_store_path=None` では `reconnect_key_store_unavailable` を出さない | regression | integration | no | fake transport |
| green | default Bumble transport + `key_store_path=None` では `reconnect_key_store_unavailable` を出す | regression | unit | no | monkeypatch default transport |
| green | `HidDeviceTransport.list_bonded_peers()` docstring が current reconnect candidate contract を明示する | regression | unit | no | public API docstring |
| green | fake transport は複数 current candidate を `InvalidKeyStoreError` とする | edge | integration | no | `try_reconnect()` は例外を受ける |

status は `todo`、`red`、`green`、`refactor-done`、`refactor-skipped`、`deferred` を使う。

## 8. 設計メモ

- `SwitchGamepad` は constructor で `transport is not None` を記録する。後から default transport を生成した場合は injected ではない。
- `list_bonded_peers()` の名前は変更しない。今回の変更は contract 明文化と fake behavior の整合にとどめる。
- `SwitchGamepad.try_reconnect()` 側の `len(peers) > 1` guard は defensive check として残す。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | injected transport 判定と diagnostics 条件 |
| `src/swbt/transport/base.py` | modify | `list_bonded_peers()` docstring |
| `src/swbt/transport/fake.py` | modify | 複数 current candidate を例外化 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | diagnostics と fake transport contract regression |
| `tests/unit/test_public_api_boundary.py` | modify | default transport diagnostics と docstring contract |
| `spec/initial/*.md` | modify | public transport contract を追記 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 41 packages checked |
| `uv run ruff format --check .` | pass | 50 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 147 passed |
| `uv run pytest tests\integration -q` | pass | 55 passed |
| `uv run pytest --collect-only tests\hardware -q` | pass | 12 tests collected。実機は実行していない |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。この unit では fake transport と unit tests で diagnostics / contract を固定する |
| adapter | 実機未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test を行う場合は別途明示承認、対象 adapter、command、cleanup plan を確認する |
| log / artifact | unit / integration test output |
| cleanup | なし |

## 12. 先送り事項

- none

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
