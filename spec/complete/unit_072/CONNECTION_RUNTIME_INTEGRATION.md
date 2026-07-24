# Connection Runtime 統合 仕様書

## 1. 概要

### 1.1 目的

`ConnectionWorkflow` が runtime 所有の状態と操作を callback として再包装している経路を削除し、active reconnect と pairing fallback を `ControllerRuntime` に集約する。transport の current bonded peer は 0 件または 1 件であるため、内部境界を `str | None` で表す。公開の接続結果と例外契約は変更しない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | ConnectionWorkflow の runtime 統合と bonded peer contract の単純化 | `https://github.com/niart120/swbt-python/issues/117` |
| 親 Issue | runtime の不要な間接層を段階的に削除する | `https://github.com/niart120/swbt-python/issues/114` |
| 依存 Issue | controller 構築経路の統合 | `spec/complete/unit_071/CONTROLLER_CONSTRUCTION_PATH.md` |
| 初期設計 | lifecycle と reconnect の公開契約 | `spec/initial/lifecycle.md`, `spec/initial/api.md` |
| 初期設計 | transport の current peer 契約 | `spec/initial/transport-bumble.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| public API 利用者 | `try_reconnect()` | no bond、成功、timeout、transport failure を `ConnectionResult` で得る | multiple peer は `InvalidKeyStoreError` |
| public API 利用者 | `try_connect(allow_pairing=True)` | no bond の場合だけ pairing fallback を実行する | reconnect 成功・失敗・timeout は fallback しない |
| transport | key store の current peer | address または `None` を返す | multiple current peer は transport で拒否する |
| runtime | reconnect 中の callback、timeout、cancellation | protocol-ready 後だけ connected とし、既存 diagnostics を維持する | 新しい manager / strategy は追加しない |

## 2. 対象範囲

- `ConnectionWorkflow.try_reconnect()` と `try_connect()` の処理を `ControllerRuntime` へ移す。
- `ConnectionWorkflow` と callback type alias 群を削除する。
- callback 適合だけの runtime helper を削除する。
- `HidDeviceTransport.bonded_peer_address()` を `str | None` の 0/1 current peer 境界として導入する。
- `BondedPeer` value object と `list_bonded_peers()` を削除する。
- Bumble / fake transport と test fixture を新しい bonded peer 境界へ更新する。
- `ConnectionResult`、`ConnectionRoute`、`ConnectionStatus`、公開 reconnect / connect 契約を維持する。

## 3. 対象外

- lifecycle state machine の全面再設計。
- protocol、pairing profile schema、CSR identity preparation、HID report、diagnostics event 名または主要 field の変更。
- Bumble adapter open、Switch pairing、advertising、実機 test の実行。
- 新しい connection manager / strategy object の追加。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/transport-bumble.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | report builder、parser、subcommand を変更しない |
| Bumble / transport | required | done | existing `BumbleHidTransport`、`FakeHidTransport`、key-store tests の current peer 意味を `str | None` に表現するだけで、adapter / L2CAP / SDP の挙動は変更しない |
| OS / driver / adapter | not applicable | not applicable | adapter を開かず、driver や identity preparation の仮定を追加しない |

### 5.1 監査結果

| 項目 | 値 | 根拠分類 | source | status |
|---|---|---|---|---|
| current peer | 0 件は no bond、1 件は active reconnect、複数は invalid key store | implementation fact | `src/swbt/transport/{base,fake,bumble}.py`、connection integration tests | 維持 |
| reconnect completion | transport connect 後、protocol-ready まで待って connected とする | implementation fact | `src/swbt/gamepad/runtime.py`、fake transport integration tests | 維持 |
| cancellation | 外側 task cancellation は再送出し、transport 由来 `CancelledError` は failed result にする | implementation fact | `src/swbt/gamepad/connection.py`、integration tests | 維持 |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| no bond | `bonded_peer_address()` が `None` | active reconnect は `no_bond` | no advertising |
| bonded reconnect | address がある | transport connect と protocol-ready 後に `connected` | route と peer address を維持 |
| timeout / transport error | reconnect が完了しない、または例外 | `timeout` / `failed`、neutral close、diagnostics を維持 | 外側 cancellation は再送出 |
| multiple peer | key store に複数 current peer | transport が `InvalidKeyStoreError` を送出 | runtime は結果へ畳み込まない |
| pairing fallback | reconnect が no bond かつ allow pairing | pairing の結果を route `pairing` で返す | no bond 以外では実行しない |
| structure | source inspection | `ConnectionWorkflow` と callback adapter helper がない | runtime が接続分岐を所有 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | production source に `ConnectionWorkflow` と callback adapter helper が存在しない | regression | unit | no | red を確認後、runtime ownership boundary test をgreen |
| refactor-done | transport は current peer address または `None` を返し、multiple peer は `InvalidKeyStoreError` にする | characterization | unit | no | Bumble / fake transport contract をgreen |
| refactor-done | no bond、reconnect 成功、timeout、transport failure、cancellation が既存の result / cleanup を維持する | regression | integration | no | fake transport integration 139 passed |
| refactor-done | no bond の `try_connect(allow_pairing=True)` だけが pairing fallback を実行する | regression | integration | no | fake transport integration 139 passed |
| refactor-done | `ConnectionResult`、route、status、public exception を維持する | characterization | unit / integration | no | public API boundary と full gate green |

## 8. 文書検証計画

公開 docs site は変更しない。`spec/initial` の transport current peer と runtime 所有の説明を、実装、public API、fake transport integration test と照合する。

## 9. 設計メモ

- `ConnectionResult`、`ConnectionRoute`、`ConnectionStatus` は `gamepad.connection` に残す。callback と workflow は残さない。
- runtime は `open()`、`_ensure_transport()`、connection state、protocol-ready wait、`pair()`、`close()` を直接使う。
- `raise_if_connection_failed()` は runtime に private helper として置くか、connection module の小さい純粋 helper として残す。重複させない。
- `bonded_peer_address()` は current peer の不在を `None` で表す。multiple peer の検出は transport 実装で行う。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/connection.py` | modify | public result typesだけを残し workflow を削除 |
| `src/swbt/gamepad/runtime.py` | modify | reconnect と pairing fallback を直接所有 |
| `src/swbt/transport/base.py` | modify | bonded peer address の0/1境界 |
| `src/swbt/transport/fake.py` | modify | fake peer contract を更新 |
| `src/swbt/transport/bumble.py` | modify | key store peer contract を更新 |
| `tests/unit/test_gamepad_connection_workflow.py` | modify | workflow 単体ではなく削除・runtime boundary を検証 |
| `tests/unit/test_public_api_boundary.py` | modify | transport boundary を更新 |
| `tests/unit/test_bumble_transport.py` | modify | Bumble current peer contract を更新 |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | reconnect / fallback contract を維持 |
| `spec/initial/{architecture,transport-bumble}.md` | modify | 現行責務と peer contract を記録 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_gamepad_connection_workflow.py -q` | red / green | red は `ConnectionWorkflow` が残るため失敗、green は削除後に成功 |
| `uv run pytest tests/unit/test_bumble_transport.py tests/unit/test_gamepad_connection_workflow.py -q` | pass | 39 passed |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 139 passed |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 102 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 469 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `git diff --check` | pass | whitespace error なし |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | adapter / Switch-facing command を実行しない |
| adapter | none |
| 実行遮断 | 環境変数による遮断は採用しない。`bumble` / `hardware` marker を実行対象から除外する |
| log / artifact | local unit / integration / CI output |
| cleanup | none |

## 13. 先送り事項

- none

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
