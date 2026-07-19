# CSR BD_ADDR 書き換え探索仕様書

## 1. 概要

### 1.1 目的

同じ USB Bluetooth ドングルで controller profile ごとに異なる Bluetooth Classic device identity を持てるか調べる。最初の対象は確認済み構成の CSR8510 A10 とする。

この unit では CSR vendor command を再現し、実機 I/O なしの byte 検査から承認済み adapter での段階的な characterization まで進める。read-only probe は完了済みであり、BD_ADDR の変更と Switch pairing は別の明示承認を必要とする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | `key_store_path` では分離できない Bluetooth identity の探索 | conversation, 2026-07-19 |
| Bumble source | `power_on()` が `HCI_Read_BD_ADDR` を `public_address` に設定する | Bumble 0.0.230 `device.py` |
| BlueZ source | CSR に opcode `0xFC00` の BCCMD を送る | https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/5.7/tools/bdaddr.c |
| BlueZ docs | CSR は一時変更、不揮発変更、soft reset を区別する | https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/refs/tags/5.66/tools/bdaddr.rst |
| vendor document | CSR8510 A10 は full HCI mode と external EEPROM interface を持つ | https://docs.qualcomm.com/bundle/publicresource/80-CT903-1_REV_AC_CSR8510_A10_Product_Brief.pdf |
| PyPI / latest source | 最新 Bumble は 0.0.233。CSR vendor module と CSR Vendor Event command completion は追加されていない | https://pypi.org/project/bumble/, Bumble 0.0.233 wheel source |
| hardware observation | `usb:0` / `0a12:0001` / CSR8510 A10 / WinUSB、BD_ADDR `00:1B:DC:F9:9F:7D` | `spec/hardware-test-log.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | BD_ADDR と volatile / persistent | BlueZ と同じ write/reset bytes を得る | adapter を開かない |
| hardware operator | read-only probe | manufacturer、現在値、Vendor Event 経路を確認する | HCI Reset 後に pass。standard HCI と CSR PSKEY の address が一致 |
| hardware operator | 後続 volatile rewrite | reset 後の変更と再挿入後の復帰を確認する | 復旧手順まで承認が必要 |

### 1.4 Intent Delta

- 2026-07-19: Bumble 0.0.233 への version bump は取りやめ、現行の `0.0.230` で CSR 実機検証を継続する。0.0.233 との source / unit test 比較は、upgrade が CSR 経路の必須条件ではない根拠として残す。

## 2. 対象範囲

- BlueZ CSR command layout の監査。
- CSR write/reset command の純粋な byte builder と Vendor Event status parser。
- adapter を開かない dry-run command。
- 承認済み `usb:0` での HCI Reset、standard identity read、CSR `PSKEY_BDADDR GETREQ`、clean close。
- Bumble 0.0.230 と最新版で不足する送受信経路の比較。

## 3. 対象外

- persistent store への PSKEY 書き込み。
- HID advertising、Switch pairing、report loop。
- public API への BD_ADDR 設定追加。
- CSR 以外の vendor command、複数 controller の同時接続保証。

## 4. 関連 docs

- `spec/initial/transport-bumble.md`
- `spec/initial/risks.md`
- `spec/complete/unit_035/JOYCON_DEVICE_INFO_ADDRESS_WIRING.md`
- `spec/complete/unit_046/HARDWARE_PROFILE_TEST_SCENARIOS.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | HID report は変更しない |
| Bumble / transport | required | done for dry-run | 0.0.230 と 0.0.233 のどちらにも CSR vendor module はない。通常 command は Command Complete / Status を待つため、CSR Vendor Event には専用経路が必要 |
| OS / driver / adapter | required | partial | Windows / WinUSB / 対象 `usb:0` で CSR GETREQ は受理された。volatile SETREQ と CSR warm reset は未検証 |
| CSR write bytes | required | done | BlueZ 5.7 `csr_write_bd_addr()` / `csr_reset_device()` を固定 |
| 対象個体の書き換え可否 | required | todo | product brief だけでは対象個体の PSKEY 書き込み可否を確定できない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| persistent plan | `01:23:45:67:89:AB` | BlueZ の opcode / address packing と一致 | 実送信なし |
| volatile plan | 同じ address、volatile | write/reset selector が volatile 値になる | 最初の実機候補 |
| invalid address | 6 octet colon notation 以外 | `ValueError` | address 割り当ては別途検討 |
| response parse | `0xC2` Vendor Event | byte 9-10 の status を返す | BlueZ と同じ判定 |
| dry-run CLI | address と store | raw packet と `adapter_opened=false` を JSON 出力 | USB I/O なし |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | persistent plan が BlueZ layout と一致する | characterization | unit | no | import error の red 後に実装 |
| green | volatile plan が selector を変える | new | unit | no | persistent を既定にしない |
| green | 不正な BD_ADDR 表記を拒否する | edge | unit | no | 6 octet colon notation |
| green | Vendor Event status を parse する | characterization | unit | no | non-CSR / short event も拒否 |
| green | Bumble Host で read-only CSR probe の Vendor Event を受ける | characterization | bumble | yes | company identifier `10`、CSR status `0`、standard HCI / PSKEY address 一致、clean close |
| deferred | volatile write/reset/read-back/replug rollback | characterization | bumble | yes | read-only probe 後 |
| deferred | BD_ADDR ごとに Switch が別 device として登録する | characterization | hardware | yes | volatile write 成功後 |

## 8. 文書検証計画

公開文書は変更しない。探索結果はこの仕様、実機結果は `spec/hardware-test-log.md` で管理する。

## 9. 設計メモ

- CSR 経路は opcode `0xFC00` を使い、Vendor Event `0xFF` を待つ。
- Bumble 0.0.230 と 0.0.233 の通常 command 完了経路は CSR 応答形式と一致しない。command semaphore、`vendor_event` listener、timeout cleanup をまとめた内部経路が必要になる。
- 0.0.233 への upgrade はこの機能を直接提供しない。対象 Bumble unit tests 61 件は依存ファイルを変更しない隔離環境で通ったが、version bump は取りやめ、現行 0.0.230 で実験を続ける。
- `DeviceConfiguration.address` は LE random/static address 用であり、Classic public BD_ADDR の上書きではない。
- 最初の write は volatile のみとする。不揮発書き込みは真正 CSR8510 の確認、元 BD_ADDR の記録、再挿入による復旧確認まで実行しない。
- BlueZ の CSR 対応は source fact だが、VID:PID `0a12:0001` の全個体が受理することは未検証仮説である。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_csr_bd_addr.py` | new | command plan と response parser。I/O なし |
| `tools/csr_bd_addr_plan.py` | new | adapter を開かない dry-run |
| `tools/csr_bd_addr_probe.py` | new | standard HCI identity read と CSR GETREQ の承認済み実機 probe |
| `tests/unit/test_csr_bd_addr_experiment.py` | new | BlueZ layout の characterization |
| `spec/wip/unit_051/CSR_BD_ADDR_REWRITE_EXPERIMENT.md` | new | 根拠、実機境界、探索結果 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_csr_bd_addr_experiment.py -q` | red | module 未実装の `ModuleNotFoundError` |
| 同 command | pass | write plan 追加時 8 passed、read GETREQ 追加後 11 passed |
| `uv run python tools/csr_bd_addr_plan.py 01:23:45:67:89:AB` | pass | `adapter_opened=false`、volatile plan を出力 |
| Bumble 0.0.233 隔離環境で対象 unit tests | pass | 61 passed。初回は共有 basetemp の権限競合、固有 basetemp で再実行 |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run ruff format --check .` | pass | 91 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run pytest tests/unit -q -p no:cacheprovider --basetemp=tmp/pytest-unit-csr-hardware-final-20260719` | pass | 421 passed |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-read-probe.json` | probe bug | `Host.ready=False` のため Reset 以外の応答を Bumble が破棄。controller capability の失敗根拠にはしない |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-read-probe-success.json` | pass | company identifier `10`、standard HCI / CSR PSKEY address `00:1B:DC:F9:9F:7D`、CSR status `0`、clean close |
| Bumble / hardware pytest | not run | 今回は専用 probe command のみ承認範囲として実行 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | dry-run は不要。read-only probe 以降は必要 |
| 承認範囲 | adapter、command、read-only / volatile / persistent、Switch-facing 動作、cleanup plan |
| adapter | 候補は専用 `usb:0` / CSR8510 A10 / `0a12:0001` / WinUSB。実行直前に再確認する |
| 実行遮断 | 環境変数ではなく、会話上の明示承認で管理する |
| log / artifact | raw HCI trace、前後の BD_ADDR、manufacturer/version、USB 再列挙を保存する |
| cleanup | advertising なし。volatile 実験は read-back、close、再挿入、元 BD_ADDR read-backまで行う |

## 13. 先送り事項

- volatile selector が対象個体で address を一時変更できるか。
- volatile selector が対象個体で再挿入後に復帰するか。
- 衝突しない実験用 address の割り当て。
- BD_ADDR ごとの key store path 導出。
- Switch が同一ドングルの複数 BD_ADDR を独立登録できるか。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] dry-run の根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] Bumble 最新版との比較を記録した
- [x] format / lint / type gate を記録した
