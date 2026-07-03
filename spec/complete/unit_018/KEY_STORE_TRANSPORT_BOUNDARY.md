# Key Store Transport Boundary 仕様書

## 1. 概要

### 1.1 目的

`unit_017` で `key_store_path` を接続メソッドの一時引数へ移したが、レビュー指摘により方針を戻す。`key_store_path` は 1 つの仮想 Pro Controller の pairing storage を定義する構成値であり、接続試行ごとに差し替える値ではない。

この unit では、`key_store_path` を `SwitchGamepad` / `SwitchGamepadConfig` へ戻し、transport を作成時設定で固定する。あわせて current / previous key store の current peer を 1 件に正規化し、複数 current peer を含む旧形式 key store は不正形式として扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user review input | `key_store_path` は構成値へ戻す。`configure_key_store_path()` 削除。`ambiguous_bond` 削除。current peer は 1 件に正規化。旧形式複数 peer は自動移行しない | conversation, 2026-07-03 |
| completed unit | unit_016 は current / previous key store を導入したが、別 peer pairing 時の current 正規化が不足している | `spec/complete/unit_016/JSON_KEY_STORE_CURRENT_PREVIOUS.md` |
| completed unit | unit_017 は成功必須 API と try API を導入したが、`key_store_path` を接続時引数へ移した | `spec/complete/unit_017/SWITCH_GAMEPAD_API_HARDENING.md` |
| implementation-before | 接続メソッドに `key_store_path` 引数が残り、`HidDeviceTransport.configure_key_store_path()` がある | `src/swbt/gamepad.py`, `src/swbt/transport/base.py` |
| implementation-before | `_CurrentPreviousJsonKeyStore.update()` は同一 peer のみ previous へ退避し、別 peer の current entry を残す | `src/swbt/transport/bumble.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json")` | その仮想 controller の pairing storage として固定される | 接続メソッドで差し替えない |
| diagnostic user | `try_reconnect()` | current peer が 0 件なら `no_bond`、1 件なら reconnect 試行、複数なら key store 不正例外 | `ambiguous_bond` は返さない |
| transport implementer | custom transport を注入する | `SwitchGamepad` から transport の key store 設定を mutate されない | key store は custom transport 自身の責務 |
| existing user | 旧形式 key store に複数 peer がある | 自動移行せず `InvalidKeyStoreError` で落ちる | JSON 順序や推定で current を選ばない |

## 2. 対象範囲

- `SwitchGamepad` constructor と `SwitchGamepadConfig` に `key_store_path` を戻す。
- `pair()` / `reconnect()` / `try_reconnect()` / `connect()` / `try_connect()` から `key_store_path` 引数を削除する。
- `HidDeviceTransport.configure_key_store_path()`、`SwitchGamepad._configure_connection_key_store_path()`、fake transport の同等 hook を削除する。
- default `BumbleHidTransport` は constructor の `key_store_path` を lifetime 中の固定設定として使う。
- `InvalidKeyStoreError` を追加し、top-level export する。
- `ambiguous_bond` を `ConnectionStatus`、diagnostics、tests、spec から削除する。
- `_CurrentPreviousJsonKeyStore.update()` は pairing 後の peer を current 1 件にし、旧 current entries を previous namespace に退避する。
- current namespace に複数 peer がある場合、`get_all()` / `list_bonded_peers()` は `InvalidKeyStoreError` を投げる。
- README と `spec/initial` に破壊的変更、旧形式 key store の再作成、Switch ごとの key store 分離を明記する。

## 3. 対象外

- 旧形式 key store の自動移行。
- previous peer を使った reconnect fallback。
- 複数 controller 同時接続。
- 実機 pairing / reconnect の再検証。
- HID report bytes、SDP、L2CAP 接続手順の変更。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/complete/unit_016/JSON_KEY_STORE_CURRENT_PREVIOUS.md`
- `spec/complete/unit_017/SWITCH_GAMEPAD_API_HARDENING.md`
- `README.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | HID report layout は変更しない |
| Bumble / transport | not applicable | implementation-fact-only | Bumble の新仮定は追加しない。既存 `device.keystore` hook の使い方を constructor 固定へ戻す |
| OS / driver / adapter | not applicable | not applicable | adapter open や driver 挙動は変更しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| constructor key store | `SwitchGamepad(key_store_path=...)` | config と run metadata に保持する | default transport 生成へ渡す |
| config key store | `SwitchGamepadConfig(key_store_path=...)` | `from_config()` 経由でも同じ値を使う | resource 構成値 |
| method signature | `pair()` / `connect()` / `try_*()` | `key_store_path` 引数を持たない | 差し替え API を消す |
| injected transport | `SwitchGamepad(transport=fake, key_store_path=...)` | metadata には記録するが transport を mutate しない | custom transport の設定は transport 側 |
| transport protocol | `HidDeviceTransport` | `configure_key_store_path()` を持たない | public extension point は維持 |
| status literal | `ConnectionStatus` | `ambiguous_bond` を含まない | invalid key store は例外 |
| current normalization | A で pair 後 B で pair | current は B のみ、previous は A | 同一 peer 再 pairing でも旧 key を previous へ退避 |
| invalid current | current namespace に 2 peer 以上 | `InvalidKeyStoreError` | 自動移行しない |
| reconnect selection | current 0 / 1 / 2+ | 0 は `no_bond`、1 は selected、2+ は例外 | `ambiguous` diagnostics は出さない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | connect / pair / reconnect / try_* に `key_store_path` 引数が存在しない | regression | unit | no | `inspect.signature` |
| green | `SwitchGamepadConfig` と `SwitchGamepad` constructor が `key_store_path` を持つ | regression | unit | no | public API boundary |
| green | `BumbleHidTransport` constructor に config の `key_store_path` が渡る | regression | unit | no | monkeypatch default transport |
| green | `HidDeviceTransport.configure_key_store_path()` が存在しない | regression | unit | no | public extension point |
| green | injected transport は `SwitchGamepad` から key store 再設定されない | regression | integration | no | fake transport |
| green | `ConnectionStatus` に `ambiguous_bond` が含まれない | regression | unit | no | typing args |
| green | try reconnect は複数 fake bonded peer を `ConnectionResult` にせず例外にする | edge | integration | no | fake transport の invalid shape |
| green | pair / update で current が 1 peer に正規化され、旧 current は previous へ退避される | edge | unit | no | `_CurrentPreviousJsonKeyStore` |
| green | 同一 peer 再 pairing でも旧 key が previous へ退避される | edge | unit | no | `_CurrentPreviousJsonKeyStore` |
| green | current namespace に複数 peer がある旧形式 store は `InvalidKeyStoreError` | edge | unit | no | 自動移行なし |
| green | `try_reconnect()` は invalid key store を `ConnectionResult` ではなく例外にする | edge | unit / integration | no | Bumble transport |
| green | README / spec に旧形式 key store 再作成と Switch ごとの key store 分離を記録する | docs | docs | no | 破壊的変更 |

status は `todo`、`red`、`green`、`refactor-done`、`refactor-skipped`、`deferred` を使う。

## 8. 設計メモ

- `key_store_path=None` は永続 bond を持たない一時 controller として扱う。pairing は可能だが、プロセス終了後の reconnect は期待しない。
- `SwitchGamepadConfig.key_store_path` は default Bumble transport の構築と diagnostics metadata に使う。
- custom transport が key store を必要とする場合、その transport の constructor で受ける。`SwitchGamepad` は injected transport を後から再設定しない。
- current peer は自動 reconnect 対象の 1 件のみ。previous peer は自動 reconnect 対象にしない。
- 複数 current peer を含む key store は旧形式または不正形式として扱い、JSON entry の順序や最終更新推定で current を選ばない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | `key_store_path` を config へ戻す。接続メソッド引数と ambiguous handling を削除 |
| `src/swbt/errors.py` | modify | `InvalidKeyStoreError` |
| `src/swbt/__init__.py` | modify | top-level export |
| `src/swbt/transport/base.py` | modify | `configure_key_store_path()` 削除 |
| `src/swbt/transport/bumble.py` | modify | current 1 peer 正規化、invalid key store 検出 |
| `src/swbt/transport/fake.py` | modify | key store mutation hook 削除 |
| `src/swbt/probe.py` | modify | constructor key store へ戻す |
| `examples/*.py` | modify | constructor key store へ戻す |
| `tests/unit/*` | modify | public API / key store tests |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | connection API / injected transport regression |
| `tests/hardware/test_reconnect_keystore.py` | modify | 新 API に追従。実行はしない |
| `README.md` | modify | 破壊的変更と再 pairing 導線 |
| `spec/initial/*.md` | modify | 正本更新 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | 41 packages checked |
| `uv run ruff format --check .` | pass | 50 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 145 passed |
| `uv run pytest tests\integration -q` | pass | 55 passed |
| `uv run pytest --collect-only tests\hardware -q` | pass | 12 tests collected。実機は実行していない |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。この unit では fake transport と unit tests で API / key store shape を固定する |
| adapter | 実機未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test を行う場合は別途明示承認、対象 adapter、command、cleanup plan を確認する |
| log / artifact | unit / integration test output |
| cleanup | なし |

## 12. 先送り事項

- previous peer を使った reconnect fallback は扱わない。必要になった場合は別 unit で、選択規則と実機観測を分けて設計する。
- 旧形式 key store の自動移行はしない。利用者には key store 削除と再 pairing を要求する。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
