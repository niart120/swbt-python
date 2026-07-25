# Pairing profile schema v2: current key only

## 1. 概要

### 1.1 目的

pairing profile schema を v2 に上げ、現在選択中の Bluetooth address namespace だけへ pairing key を保存する。v1 profile は runtime で読み替えず、adapter を開く前に再ペアリングを案内する `InvalidProfileError` で拒否する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #143 | previous pairing key 世代の廃止、schema v2、破壊的変更の利用者案内 | `https://github.com/niart120/swbt-python/issues/143` |
| 実装事実 | v1 は current key 更新時に `swbt.previous::` namespace を書き込む | `src/swbt/transport/_pairing_profile.py`, `src/swbt/transport/_bumble_key_store.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 新規 explicit profile 利用者 | locally administered address を指定して profile を作成 | schema v2 と当該 address の空 namespace だけを保存する | previous namespace を作らない |
| adapter-default profile 利用者 | profile 作成後、power-on で current address が解決する | 解決済み address の current namespace だけを key 更新する | profile 作成時は空 map |
| v1 profile 利用者 | `profile_path` を runtime へ渡す | adapter open 前に v2 profile の作成と再ペアリングを示す `InvalidProfileError` | compatibility load / migration を提供しない |

## 2. 対象範囲

- schema version を 2 にする。
- new profile、key update、diagnostics から previous 世代を除く。
- current namespace の key lookup、複数 peer 拒否、atomic save、identity guard を維持する。
- fake transport の pairing / reconnect と explicit / adapter-default variant を確認する。
- 公開 docs と release notes に破壊的変更と再ペアリング手順を記載する。

## 3. 対象外

- BD_ADDR 切替、identity kind、CSR identity preparation の変更。
- previous key fallback、復元 API / CLI、v1 互換読込、自動または in-place migration。
- 実機 pairing / reconnect の実行。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `docs/usage.md`
- `docs/release-notes.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report format、subcommand、input timing を変更しない。 |
| Bumble / transport | not applicable | not applicable | Bumble API / SDP / L2CAP の仮定を追加せず、既存 key-store adapter の保存世代だけを変更する。 |
| OS / driver / adapter | not applicable | not applicable | adapter open や driver 操作を変更しない。 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| v2 profile creation | explicit address | current address namespace だけを持つ schema v2 JSON | atomic create を維持 |
| v1 early rejection | schema v1 JSON | adapter open 前に v2 と再ペアリングを案内する `InvalidProfileError` | migration しない |
| current-only update | current key を新しい peer key で更新 | current namespace は新しい 1 peer だけ、previous namespace は作成しない | active lookup は current のみ |
| diagnostics | key update 成功 / 失敗 | status、peer_address、失敗時 error_type/message だけを記録 | key material、generation、previous_saved は出さない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | explicit address の新規 profile は schema v2 と current namespace だけを保存する | regression | unit | no | `test_pairing_profile_create_new_atomically_saves_schema_v2_current_only_pro_envelope` が red から green。構造整理なし。 |
| refactor-skipped | schema v1 profile は adapter open 前に再作成・再ペアリングを案内して拒否する | regression | unit | no | loader と runtime の両方で v1 を拒否し、transport creation 前の停止を確認。構造整理なし。 |
| refactor-skipped | current key 更新は previous namespace を作らず、current key だけを置換する | regression | integration | no | `_PairingProfileKeyStore.update()` の 2 回更新を確認。構造整理なし。 |
| refactor-skipped | adapter-default profile は power-on 後に解決した current namespace だけを更新する | regression | unit / integration | no | existing Bumble fake device test で遅延 namespace 選択を確認。構造整理なし。 |
| refactor-skipped | key_store_update diagnostics は generation / previous_saved を記録しない | regression | unit | no | 成功・失敗 event の両方を確認。構造整理なし。 |
| refactor-skipped | v2 profile は fake transport pairing と active reconnect で current key を利用する | regression | integration | no | integration suite の fake transport pairing / reconnect と profile key-store update を通過。構造整理なし。 |

## 8. 文書検証計画

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `docs/usage.md` | v1 profile の利用者が v2 profile を作り直して再ペアリングする | Issue #143 と profile loader | `uv run --group docs mkdocs build --strict` | done | none |
| `docs/release-notes.md` | 破壊的変更と compatibility / migration 非提供を把握する | Issue #143 | `uv run --group docs mkdocs build --strict` | done | none |

## 9. 設計メモ

これは behavior change である。green 後の構造整理は、current-only 保存を変えない範囲に分離する。v1 error は loader に置き、adapter の生成・open より前に失敗させる。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_pairing_profile.py` | modify | v2 envelope creation と v1 rejection message |
| `src/swbt/transport/_bumble_key_store.py` | modify | previous generation を除く current-only update と diagnostics |
| `tests/unit/test_pairing_profile.py` | modify | v2 / v1 early rejection |
| `tests/unit/test_bumble_transport.py` | modify | diagnostics と adapter-default current namespace |
| `tests/integration/test_pairing_profile.py` | modify | fake transport pairing / reconnect の保存契約 |
| `docs/usage.md` | modify | v1 profile の再作成・再ペアリング |
| `docs/release-notes.md` | modify | breaking change |
| `spec/initial/lifecycle.md` | modify | current-only key store と v1 非互換の設計判断 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit -q --basetemp tmp/issue143-unit` | passed, 448 passed | profile loader、runtime、Bumble fake device、diagnostics を含む |
| `uv run pytest tests/integration -q --basetemp tmp/issue143-integration-all` | passed, 154 passed | fake transport pairing / reconnect と profile key-store update を含む |
| `uv run ruff format --check .` | passed | 106 files formatted |
| `uv run ruff check .` | passed | lint passed |
| `uv run ty check --no-progress` | passed | type check passed |
| `uv run --group docs mkdocs build --strict` | passed | public docs build passed |
| `uv build` | passed | `swbt_python-0.5.2.tar.gz` と `swbt_python-0.5.2-py3-none-any.whl` を作成 |
| `pytest -m bumble` / `pytest -m hardware` | not run | adapter / Switch 操作の明示承認がない。Issue の必須条件ではない。 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | 実機確認は Issue 完了条件に含めない。実行する場合は別途明示承認を得る。 |
| adapter | not applicable |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実行時のみ `spec/hardware-test-log.md` に記録する |
| cleanup | 実機未実行 |

## 13. 先送り事項

- none

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
