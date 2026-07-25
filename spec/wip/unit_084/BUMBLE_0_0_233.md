# Bumble 0.0.233 への固定と transport 互換分岐の整理

## 1. 概要

### 1.1 目的

Bumble の正式対応を `0.0.233` だけに固定し、transport 実装を同版の API shape に合わせる。旧版を許容する動的分岐を削除し、最新 Bumble による nonblocking canary CI で将来の差分を検知する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue | Bumble 0.0.233 への固定、互換分岐整理、canary CI の完了条件 | `https://github.com/niart120/swbt-python/issues/144` |
| 初期設計 | Bumble 依存を transport 境界内に閉じる | `spec/initial/transport-bumble.md` |
| 初期設計 | fake transport と Bumble / hardware test の分離 | `spec/initial/testing.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| ライブラリ利用者 | `swbt` を import | Bumble を import / 解決しない | lazy import 境界を維持する |
| CI | lock に固定された dependency | Bumble 0.0.233 で unit / integration が通る | adapter は開かない |
| 保守者 | schedule / 手動の canary workflow | 最新 Bumble の失敗を通常 CI と独立して観測できる | required check にしない |

## 2. 対象範囲

- `bumble==0.0.233` への dependency と lock の更新。
- Bumble 0.0.233 source に照合した transport の不要な互換分岐と専用 test の削除。
- remaining workaround の理由を本仕様へ記録。
- latest Bumble で unit / integration を実行する nonblocking canary workflow。

## 3. 対象外

- 複数 Bumble version の同時対応と runtime version check。
- 明示承認なしの Bumble adapter、Switch pairing、HID advertising、report loop の実行。
- HID report、subcommand、SPI、SDP 値、report timing の変更。
- BD_ADDR 切替機能の縮小。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | protocol 値を変更しない |
| Bumble / transport | required | done | 0.0.230 と 0.0.233 の installed source を照合した |
| OS / driver / adapter | required | partial | dedicated `usb:0` / CSR8510 A10 / WinUSB と Switch 2 firmware 22.5.0 は利用者が既存実験から不変と確認した。driver assignment の再照会は今回未実行 |

### 根拠監査の結果

| 項目 | 値 / 判断 | 根拠分類 | source | status |
|---|---|---|---|---|
| HID SET_REPORT callback | `hid.Device.register_set_report_cb()` は 0.0.233 に存在するため、存在確認 fallback を削除する | source fact | `.venv/Lib/site-packages/bumble/hid.py:470-473` | done |
| connection event | `Connection` の diagnostics event 定数は 0.0.233 に存在するため、event 名文字列 fallback を削除する | source fact | `.venv/Lib/site-packages/bumble/device.py:1729-1760` | done |
| ACL queue | `connection.device.host.get_data_packet_queue(handle)` と `DataPacketQueue.drain(handle)` は 0.0.233 の正式経路である | source fact | `.venv/Lib/site-packages/bumble/host.py:182-186,882-885` | done |
| address | `hci.Address.to_string(False)` は 0.0.233 に存在するため、文字列化 fallback を削除する | source fact | `.venv/Lib/site-packages/bumble/hci.py:2226-2320` | done |
| incoming BR/EDR request | `Device.on_connection_request()` は 0.0.233 でも deprecated `host.send_command_sync()` を呼ぶ。host の一時 bridge はこの upstream 挙動だけを回避する | source fact | `.venv/Lib/site-packages/bumble/device.py:6069-6125` | retained |
| public accept alternative | `Device.accept()` は request より前に待機する coroutine であり、継続 accept loop と close 時の task 管理が必要になる | source fact | `.venv/Lib/site-packages/bumble/device.py:4138-4270` | deferred |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| 正式 dependency | project install | Bumble が `0.0.233` に固定される | lock と一致する |
| transport callback | Bumble 0.0.233 の HID / connection object | 固定 API を使い、旧 API fallback を使わない | diagnostics 用 optional field は残せる |
| close | explicit disconnect | pending ACL queue だけを drain する | 通常 report では待たない |
| canary | schedule / 手動実行 | 最新 Bumble で unit / integration を実行する | `continue-on-error: true` |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | 0.0.233 の固定 API で HID callback と connection listener を登録できる | characterization | unit | no | fixture を fixed API shape に更新し focused test で確認 |
| refactor-done | explicit disconnect で 0.0.233 の ACL queue を drain する | regression | unit | no | host 経由の正式取得経路で focused test を確認 |
| refactor-done | 旧 API fallback 専用の test を削除しても transport の既存契約を保つ | regression | unit / integration | no | source に残る deprecated sync workaround は維持する |
| refactor-done | latest Bumble canary が schedule / 手動実行で unit / integration を起動する | new | CI config | no | YAML parse により trigger、nonblocking、両 test tree を確認 |
| done | Switch 2 fresh pairing 後に Button A input report を送り、neutral close する | regression | hardware | yes | 0.3 s Periodic case が pytest と利用者の画面観測で成功 |
| deferred | Pro Controller active reconnect と normal close を Bumble adapter で確認する | regression | bumble / hardware | yes | 明示承認後にだけ実行する |

## 8. 文書検証計画

not applicable。公開利用者向け文書は変更しない。

## 9. 設計メモ

- `getattr()` を一律に削除しない。診断用 optional field と source 上で欠落し得る値だけは残す。
- Bumble source にない fallback は、0.0.233 固定後に互換性のため保持しない。
- `Device.on_connection_request()` の deprecated sync helper は 0.0.233 に残る。public `Device.accept()` への移行には accept loop と lifecycle task の設計変更が必要なため、本 unit では既存の狭い bridge を維持する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `pyproject.toml` | modify | Bumble exact pin |
| `uv.lock` | modify | dependency lock |
| `src/swbt/transport/**` | modify | 0.0.233 API に合わせた分岐整理 |
| `tests/unit/**` | modify | obsolete fallback test の削除と fixed-API fixture |
| `.github/workflows/**` | new / modify | latest Bumble canary |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv lock --check` | passed | Bumble 0.0.233 lock と一致 |
| `uv run ruff format --check .` | passed | 106 files already formatted |
| `uv run ruff check .` | passed | All checks passed |
| `uv run ty check --no-progress` | passed | All checks passed |
| `uv run pytest tests/unit` | passed | 448 passed |
| `uv run pytest tests/integration` | passed | 154 passed |
| `uv run --group docs mkdocs build --strict` | passed | strict build succeeded |
| `uv build` | passed | sdist と wheel を build |
| `uv run python -c "...yaml.safe_load(...)..."` | passed | canary の trigger、nonblocking、unit / integration command を確認 |
| `uv run pytest tests/hardware/test_context_manager_resource_scope.py -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir tmp/hardware/unit_084/bumble-open-only` | passed | 1 passed。advertising / host connection なし、transport close complete を trace で確認 |
| `uv run pytest "tests/hardware/test_reply_holdoff.py::test_switch_reply_holdoff_variant_fresh_pairing_characterizes_readiness_and_a_input[0.3-True]" -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir tmp/hardware/unit_084/fresh-a-switch2-20260725` | passed | 1 passed in 10.34s。fresh pairing、Button A の input report、neutral close を trace で確認し、利用者が Switch 2 UI への反映を確認 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | Bumble adapter open-only と Switch 2 fresh pairing / Button A は完了。active reconnect と normal close は未実行 |
| 承認範囲 | `usb:0` の open-only Bumble marker に加え、Switch 2 の fresh pairing、HID advertising、Button A、neutral close、adapter release を実行済み。active reconnect は未承認 |
| adapter | `usb:0` |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md`、`tmp/hardware/unit_084/bumble-open-only/resource-open-only.jsonl`、`tmp/hardware/unit_084/fresh-a-switch2-20260725/reply-holdoff-fresh-periodic-0_300.jsonl` |
| cleanup | open-only と Switch 2 fresh pairing の両方で `transport_close_complete` を確認。Switch 2 run では disconnect terminal `closed` と neutral close も記録 |

## 13. 先送り事項

- adapter を使う active reconnect と normal close の実機確認は、利用者の明示承認後に実行する。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List または文書検証計画を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
