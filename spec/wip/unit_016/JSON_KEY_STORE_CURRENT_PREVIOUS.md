# JsonKeyStore Current / Previous 世代管理 仕様書

## 1. 概要

### 1.1 目的

Bumble `JsonKeyStore` を使う pairing key 保存に、`current` / `previous` の世代概念を導入する。

現状の `key_store_path` は Bumble の `JsonKeyStore:<path>` に直結しており、同じ peer address の `update()` は保存済み key set を上書きする。unit_007 の実機観測では、controller search / change grip order screen からの incoming run が `classic_pairing` と `key_store_update` を発生させた。これは route 分離の根拠にはなるが、pairing-free incoming bond reuse の根拠にはならない。

この unit では、再 pairing や incoming 側の再登録で最新 key が書かれても、直前の key set を失わない保存形式と diagnostics を固定する。`previous` を自動 reconnect fallback として使うかは、実装と実機観測で分けて判断する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | `JsonKeyStore` の拡張として current / previous 概念を導入する | conversation, 2026-07-03 |
| completed unit | M6 reconnect / key store / diagnostics の完了仕様。active reconnect 成功、incoming route 分離、incoming 側の再 pairing 観測を記録済み | `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` |
| dev journal | incoming 側の既存 bond 再利用条件は未解決。Change Grip/Order 画面の run は pairing-free bond reuse と扱わない | `spec/dev-journal.md` |
| lifecycle | `connect()` は bond があれば `reconnect()` を優先し、失敗時に自動 advertising recovery や retry loop を開始しない | `spec/initial/lifecycle.md` |
| api | `key_store_path` は pairing / reconnect 情報の保存先として public API に存在する | `spec/initial/api.md` |
| risks | key store 破損や reconnect 失敗時には復旧手順が必要になる | `spec/initial/risks.md` |
| Bumble source | `JsonKeyStore` は JSON file の top-level namespace 配下に peer address -> `PairingKeys` を保存し、`update()` は同じ peer の dict を更新して保存する | `.venv/Lib/site-packages/bumble/keys.py` |
| implementation | swbt は `_bumble_key_store_config(key_store_path)` で `JsonKeyStore:<path>` を設定し、diagnostics wrapper で `key_store_update` を記録する | `src/swbt/transport/bumble.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | 既存の `key_store_path` を指定する | 既存 API の意味は変わらず、最新 key set が current として保存される | Bumble 型や key material は public API に出さない |
| transport | 同じ peer address に新しい key set が書かれる | 直前の current key set が previous として退避され、新しい key set が current になる | 初回書き込みでは previous を作らない |
| developer | diagnostics trace を読む | key material を含めず、current update と previous 退避の成否を判別できる | link key 値、IRK、CSRK は記録しない |
| reconnect | 保存済み current key set がある | unit_007 の active reconnect 経路は current を使い続ける | previous の自動 fallback は初期挙動にしない |
| recovery | current が再 pairing で更新された後に問題が起きる | previous の存在を diagnostics と file structure から確認できる | previous を current へ戻す操作はこの unit では public helper にしない |

## 2. 対象範囲

- `key_store_path` の既存 public contract を current store として保つ。
- Bumble `JsonKeyStore` と互換の current namespace を維持する。
- 同じ peer address の上書き時に直前の current key set を previous namespace へ退避する。
- current / previous の保存結果を key material なしで diagnostics に記録する。
- `get()` / `get_all()` の通常経路は current だけを返す。
- active reconnect は unit_007 で固定した current key store 経路を使い続ける。
- previous が存在する状態を unit test と fake integration test で固定する。
- 実機での再 pairing / incoming run による key store 世代更新は、承認後の characterization として扱う。

## 3. 対象外

- previous key set を使う自動 reconnect fallback の既定有効化。
- previous を current に戻す public CLI / API。
- key material の暗号化、マスキング付き出力、外部 secret store 連携。
- Bumble upstream の `JsonKeyStore` そのものへの patch。
- 複数 controller 同時接続の世代選択。
- pairing-free incoming bond reuse の成功条件探索。これは `spec/dev-journal.md` の後続観測に残す。
- reconnect 失敗後の automatic advertising recovery と retry loop。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `spec/complete/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/dev-journal.md`
- `docs/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | この unit は key store persistence の保存形式と diagnostics を扱う。HID report byte layout は変更しない |
| Bumble / transport | required | source-audited-for-planning | Bumble 0.0.230 の `JsonKeyStore` は top-level namespace ごとに peer map を持つ。`load()` は一致 namespace を優先し、`update()` は current namespace の peer dict を更新して file を保存する。swbt の現行実装は `DeviceConfiguration.keystore = "JsonKeyStore:<path>"` で Bumble に key store 生成を任せている |
| OS / driver / adapter | required-for-hardware | pending | current / previous 保存形式の unit test には不要。実機で incoming 再登録時の世代退避を確認する場合は Windows / driver / dongle / Bumble / Switch firmware を記録する |

### 根拠分類

| 項目 | 値 | 根拠分類 | source | status |
|---|---:|---|---|---|
| Bumble `JsonKeyStore` の保存単位 | top-level namespace -> peer address -> `PairingKeys` dict | source fact | `.venv/Lib/site-packages/bumble/keys.py` | current |
| `JsonKeyStore.update()` の同一 peer 処理 | `key_map.setdefault(name, {}).update(keys.to_dict())` 後に save | source fact | `.venv/Lib/site-packages/bumble/keys.py` | current |
| swbt の current key store 接続 | `key_store_path` から `JsonKeyStore:<path>` を作る | implementation fact | `src/swbt/transport/bumble.py` | current |
| incoming Change Grip/Order run | `incoming_connection route=incoming` と同じ trace に `classic_pairing` / `key_store_update` が出た | hardware observation | `docs/hardware-test-log.md`, `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` | current |
| previous key set が active reconnect fallback として有効か | 未確認 | unverified hypothesis | none | pending |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| current write | peer address が未保存 | current namespace に key set を保存する | previous は作らない |
| current overwrite | peer address の current が保存済み | 既存 current を previous namespace に退避し、新しい key set を current に保存する | key material は diagnostics に出さない |
| repeated overwrite | current と previous が保存済み | previous は直前の current に置き換わる | previous は履歴配列ではなく 1 世代だけ |
| current read | Bumble または swbt が `get()` / `get_all()` を呼ぶ | current namespace の key set だけを返す | 既存 reconnect 挙動を変えない |
| namespace layout | current namespace が `<current_namespace>` | previous namespace は同じ JSON file 内の `swbt.previous::<current_namespace>` にする | current namespace は Bumble-compatible に残す |
| previous metadata | previous が作成済み | diagnostics で previous availability を確認できる | peer address までは記録可。secret は不可 |
| write failure | current write または previous 退避が失敗 | 失敗 event を記録し、呼び出し元へ例外を伝える | current だけ更新され previous 退避だけ失敗する中間状態を避ける |
| legacy file | 既存 Bumble `JsonKeyStore` file を読む | 既存 namespace を current として扱う | migration command は作らない |
| active reconnect | current が 1 peer だけ存在する | unit_007 と同じ active reconnect selection を行う | previous は候補に混ぜない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | 初回 `update(peer, keys)` は current だけを保存し previous を作らない | new | unit | no | JSON file の namespace と peer count を固定する |
| todo | 同じ peer の 2 回目 `update()` は旧 current を previous に退避して新 current を保存する | new | unit | no | old/new を区別できる fake `PairingKeys` fixture を使う |
| todo | 3 回目以降の `update()` は previous を直前 current に置き換え、履歴を増やさない | edge | unit | no | JSON file が 1 世代 previous だけを持つことを固定する |
| todo | `get(peer)` と `get_all()` は current のみを返し previous を通常 reconnect 候補に混ぜない | regression | unit | no | Bumble-compatible `KeyStore` interface の互換性を守る |
| todo | previous 退避または current 保存の失敗は key material を出さず diagnostics に記録される | edge | unit | no | `link_key` など secret field が trace に出ないことを確認する |
| todo | `BumbleHidTransport` は `key_store_path` 指定時に current / previous 対応 key store を使う | new | unit | no | public API に Bumble 型を出さない |
| todo | `SwitchGamepad(key_store_path=...)` の run metadata は current path と previous availability を secret なしで記録する | new | integration | no | `key_store_exists` の既存 contract を壊さない |
| todo | active reconnect は previous が存在しても current の 1 peer だけを選択する | regression | integration | no | unit_007 の reconnect 挙動を守る |
| todo | legacy Bumble JSON file は current として読める | regression | unit | no | 既存 user file を破壊しない |
| todo | 実機 incoming 再登録で current / previous 退避 event が trace に残るか確認する | characterization | hardware | yes | controller search / change grip order screen 条件では pairing-free bond reuse と扱わない |

status は `todo`、`red`、`green`、`refactor-done`、`refactor-skipped`、`deferred` を使う。

## 8. 設計メモ

- `current` は既存 `key_store_path` の意味を引き継ぐ。利用者が `SwitchGamepad(key_store_path="switch-bond.json")` と書いた場合、active reconnect は current を使う。
- `previous` は同じ peer address の直前 key set を保持する。目的は、再 pairing や incoming 側の再登録で直前の working key を即時に失わないことにある。
- 保存形式は Bumble の namespace 構造を利用する。current namespace は Bumble が使う namespace のままにし、previous は同じ JSON file 内の `swbt.previous::<current_namespace>` に保存する。
- `previous` を reconnect fallback として自動使用する挙動は、この unit の初期成功条件にしない。Bluetooth authentication failure 後に別 key set で再試行してよいかは、Switch / Bumble / dongle の実機挙動に依存する。
- `key_store_update` diagnostics は既存 event 名を維持し、世代情報を field として足す。event 名を分ける必要がある場合は `spec/complete/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md` との整合を取る。
- key material は trace、例外 message、test assertion output に出さない。peer address、generation、status、error type までに留める。
- Bumble upstream の `JsonKeyStore` class を monkey patch しない。swbt の transport 境界で Bumble-compatible `KeyStore` を用意するか、`device.keystore` 差し替えで閉じ込める。
- source-audit 上、previous key set が active reconnect fallback として有効かは未検証仮説である。public guarantee に含めない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/bumble.py` | modify | current / previous 対応 key store の組み込み、diagnostics wrapper との接続 |
| `src/swbt/transport/` | new / modify | Bumble-compatible key store helper を分離する場合の置き場 |
| `src/swbt/diagnostics.py` | modify | run metadata または event field に previous availability を追加 |
| `tests/unit/test_bumble_transport.py` | modify | transport が current / previous 対応 key store を使うことを固定 |
| `tests/unit/` | new / modify | current / previous key store behavior の unit tests |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | `key_store_path` metadata と reconnect selection の回帰確認 |
| `tests/hardware/test_reconnect_keystore.py` | modify | 実機 characterization を行う場合の trace 確認 |
| `docs/hardware-test-log.md` | modify | 実機で世代退避を確認した場合に記録 |
| `spec/wip/unit_016/JSON_KEY_STORE_CURRENT_PREVIOUS.md` | modify | TDD 状態、検証、実機条件を更新 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests\unit -q` | not run | 仕様作成時点では未実行。実装後の標準 unit gate |
| `uv run pytest tests\integration -q` | not run | 仕様作成時点では未実行。`key_store_path` metadata と active reconnect selection の回帰確認に使う |
| `uv run pytest --collect-only tests\hardware\test_reconnect_keystore.py -q` | not run | 実機を使わない収集確認。hardware test を変更した場合に実行する |
| `uv run ruff format --check .` | not run | 実装後の標準 gate |
| `uv run ruff check .` | not run | 実装後の標準 gate |
| `uv run ty check --no-progress` | not run | 実装後の標準 gate |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for hardware characterization only |
| 承認範囲 | USB Bluetooth dongle open、Classic HID Device initialization、HID advertising、初回 pairing、incoming 再登録または active reconnect、key store update、Switch-facing output report / subcommand handling、periodic report loop、close cleanup |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、debug log、key store file path。key material は記録しない |
| cleanup | neutral、report loop 停止、disconnect request、transport close、adapter release。必要なら test 用 key store file を削除する |

## 12. 先送り事項

- previous を使う自動 reconnect fallback は、authentication failure 後の再試行が Switch / Bumble / dongle 上で安全に扱える根拠が揃うまで別 unit に送る。
- previous を current へ戻す CLI / API は、実際の復旧手順が必要になった段階で別 unit に送る。
- incoming 側の pairing-free bond reuse 条件探索は `spec/dev-journal.md` の既存項目に残す。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
