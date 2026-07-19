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
| Bluetooth Core | BR/EDR の BD_ADDR は IEEE 802 universal EUI-48 とし、予約 LAP を使わない | https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-61/out/en/br-edr-controller/baseband-specification.html#UUID-6c866fc7-2884-01bc-03f5-7e5a90ec76a6 |
| IEEE guideline | EUI-48 の先頭 octet bit 1 は universal / local administration を示す | https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf |
| PyPI / latest source | 最新 Bumble は 0.0.233。CSR vendor module と CSR Vendor Event command completion は追加されていない | https://pypi.org/project/bumble/, Bumble 0.0.233 wheel source |
| hardware observation | `usb:0` / `0a12:0001` / CSR8510 A10 / WinUSB、BD_ADDR `00:1B:DC:F9:9F:7D` | `spec/hardware-test-log.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | BD_ADDR と volatile / persistent | BlueZ と同じ write/reset bytes を得る | adapter を開かない |
| hardware operator | read-only probe | manufacturer、現在値、Vendor Event 経路を確認する | HCI Reset 後に pass。standard HCI と CSR PSKEY の address が一致 |
| hardware operator | 後続 volatile rewrite | PSRAM write / read-back を先に確認し、別実験で reset 後の active address と再挿入後の復帰を確認する | 各 write と復旧手順に個別承認が必要 |

### 1.4 Intent Delta

- 2026-07-19: Bumble 0.0.233 への version bump は取りやめ、現行の `0.0.230` で CSR 実機検証を継続する。0.0.233 との source / unit test 比較は、upgrade が CSR 経路の必須条件ではない根拠として残す。
- 2026-07-20: controller-reported active BD_ADDR と物理復旧が確認できたため、`02:1B:DC:F9:9F:7D`、次いで `00:11:22:33:44:55` を使う短時間の Switch-facing characterization を対象に加える。前者は local bit を持ち BR/EDR の universal address 要件に適合しない。後者も割り当てを受けた address ではない。どちらも製品設定ではなく、専用 dongle、Switch 1 台、新規 key store、試験後の物理 power cycle に限定する。

## 2. 対象範囲

- BlueZ CSR command layout の監査。
- CSR write/reset command の純粋な byte builder と Vendor Event status parser。
- adapter を開かない dry-run command。
- 承認済み `usb:0` での HCI Reset、standard identity read、CSR `PSKEY_BDADDR GETREQ`、clean close。
- warm reset を送らない PSRAM SETREQ / GETREQ / 元値 restore probe の準備。
- PSRAM sentinel を確認して CSR warm reset を enqueue し、USB 再列挙後の identity read を別プロセスへ分離する probe の準備。
- active address を preflight と Bumble `power_on()` 後の二段階で照合し、一致した場合だけ Switch pairing を開始する probe。
- local address `02:1B:DC:F9:9F:7D`、次いで dummy address `00:11:22:33:44:55` を使う Switch 登録 identity の characterization。
- Bumble 0.0.230 と最新版で不足する送受信経路の比較。

## 3. 対象外

- persistent store への PSKEY 書き込み。
- public API への BD_ADDR 設定追加。
- CSR 以外の vendor command、複数 controller の同時接続保証。
- address の規格適合性、割り当ての正当性、Switch firmware 間の同一挙動、一般利用可能性の保証。

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
| OS / driver / adapter | required | done for target | Windows / WinUSB / 対象 `usb:0` で CSR GETREQ、PSRAM SETREQ / read-back、CSR warm reset / USB 再列挙、別プロセス active identity read が pass |
| CSR write bytes | required | done | BlueZ 5.7 `csr_write_bd_addr()` / `csr_reset_device()` を固定 |
| BCCMD response type | required | done | GETREQ `0x0000` / SETREQ `0x0002` の server-to-client response は GETRESP `0x0001`。BlueZ HCI 経路は response type を検査せず channel と status を扱う |
| 対象個体の書き換え可否 | required | done for volatile controller identity | PSRAM SETREQ status `0`、sentinel read-back、warm reset 後の standard HCI / CSR default-store sentinel 一致が pass。persistent store と on-air identity は未検証 |
| lab sentinel address | required | inference | `02:1B:DC:F9:9F:7D` は local bit を立てた非 universal address。Switch-facing 実験は規格適合性の確認ではなく、対象 Switch の受理挙動だけを観測する |
| dummy address | required | unverified hypothesis | `00:11:22:33:44:55` は universal bit の形式だが、この実験用に割り当てられた address ではない。同一 address の別機器が存在しない閉じた試験条件に限定する |
| power-on address guard | required | implementation fact | Bumble `power_on()` 後、connectable / discoverable を有効にする前に controller の public address を expected value と比較し、不一致なら pairing へ進まない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| persistent plan | `01:23:45:67:89:AB` | BlueZ の opcode / address packing と一致 | 実送信なし |
| volatile plan | 同じ address、volatile | write/reset selector が volatile 値になる | 最初の実機候補 |
| invalid address | 6 octet colon notation 以外 | `ValueError` | address 割り当ては別途検討 |
| response parse | `0xC2` Vendor Event | byte 9-10 の status を返す | BlueZ と同じ判定 |
| dry-run CLI | address と store | raw packet と `adapter_opened=false` を JSON 出力 | USB I/O なし |
| PSRAM-only probe | original と lab sentinel | warm reset なしで SETREQ / GETREQ / restore / GETREQ を行い、active standard address が不変であることを確認する | persistent write、RF 動作なし |
| staged warm-reset probe | original と lab sentinel | PSRAM read-back 後に warm reset を enqueue し、再列挙後の identity read を別プロセスで行う | automatic restore なし、物理 power cycle 必須、RF 動作なし |
| guarded Switch pairing | active address と expected address | read-only preflight と Bumble `power_on()` 後の双方が一致した場合だけ advertising / pairing を開始する | 新規 key store 必須、neutral report のみ、終了後に物理 power cycle |
| identity comparison | local address、次いで dummy address | Switch 上の登録表示、再接続先、既存登録との分離を人間が観測する | address ごとに key store / trace / result artifact を分離 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | persistent plan が BlueZ layout と一致する | characterization | unit | no | import error の red 後に実装 |
| green | volatile plan が selector を変える | new | unit | no | persistent を既定にしない |
| green | 不正な BD_ADDR 表記を拒否する | edge | unit | no | 6 octet colon notation |
| green | Vendor Event status を parse する | characterization | unit | no | non-CSR / short event も拒否 |
| green | Bumble Host で read-only CSR probe の Vendor Event を受ける | characterization | bumble | yes | company identifier `10`、CSR status `0`、standard HCI / PSKEY address 一致、clean close |
| green | volatile apply / restore plan が persistent selector を選べない | new | unit | no | apply / restore とも PSRAM selector、同一 address は拒否 |
| partial | volatile write/reset/read-back/replug rollback | characterization | bumble | yes | 初回は apply 中 timeout。同一 process 再 open 失敗、別 process で元 address を確認。write 適用は inconclusive |
| partial | warm reset なしの PSRAM SETREQ / GETREQ / restore roundtrip | characterization | bumble | yes | 修正版で apply / read-back / active address 不変は pass。same-session restore 確認は status `0x0008`。power cycle 後の元 identity read は再度 pass |
| green | staged warm-reset probe の dry-run が process boundary と physical recovery を示す | new | unit | no | adapter open false、automatic restore false、persistent / RF false |
| green | warm reset 後の別プロセス identity read | characterization | bumble | yes | standard HCI / CSR default-store が sentinel `02:1B:DC:F9:9F:7D` で一致、clean close |
| green | expected address 不一致時は可視化前に pairing を拒否する | safety | unit | no | Bumble `power_on()` は実行するが connectable / discoverable は設定しない |
| green | Switch pairing probe の dry-run は adapter を開かない | safety | unit | no | fresh key store、二段階 address guard、cleanup sequence を出力 |
| green | 接続後5秒の観測窓を維持する | new | unit | no | 既定 `observation_seconds=5.0`、neutral report loop のまま保持してから close |
| green | 明示指定時だけ同一 identity の key store を再利用できる | safety | unit | no | `--reuse-key-store` は既存ファイル必須。fresh / reuse の不整合は adapter open 前に拒否 |
| green | local address で Switch pairing が成立する | characterization | hardware | yes | `02:1B:DC:F9:9F:7D`、fresh key store、Classic pairing / HID connected / clean close が pass。別登録の目視は実施できず unobserved |
| planned | dummy address が local address / original と別 device として登録される | characterization | hardware | yes | `00:11:22:33:44:55`、別 key store、local 試験の復旧確認後だけ実行 |

## 8. 文書検証計画

公開文書は変更しない。探索結果はこの仕様、実機結果は `spec/hardware-test-log.md` で管理する。

## 9. 設計メモ

- CSR 経路は opcode `0xFC00` を使い、Vendor Event `0xFF` を待つ。
- Bumble 0.0.230 と 0.0.233 の通常 command 完了経路は CSR 応答形式と一致しない。command semaphore、`vendor_event` listener、timeout cleanup をまとめた内部経路が必要になる。
- 0.0.233 への upgrade はこの機能を直接提供しない。対象 Bumble unit tests 61 件は依存ファイルを変更しない隔離環境で通ったが、version bump は取りやめ、現行 0.0.230 で実験を続ける。
- `DeviceConfiguration.address` は LE random/static address 用であり、Classic public BD_ADDR の上書きではない。
- 最初の write は volatile のみとする。不揮発書き込みは真正 CSR8510 の確認、元 BD_ADDR の記録、再挿入による復旧確認まで実行しない。
- 最初の lab sentinel は `02:1B:DC:F9:9F:7D` とする。これは Bluetooth Core が要求する universal EUI-48 ではない。adapter 内部の write / read-back / restore を確認した後、ユーザ承認下の短時間 Switch-facing characterization に限って使い、一般利用可能な address とは扱わない。
- CSR warm reset は対象 `usb:0` を USB 再列挙させ、同一 Python process の libusb handle では再 open できなかった。次は warm reset なしの PSRAM SETREQ / GETREQ / restore で write 応答を切り分ける。active address の変更は、その結果を得た後に process boundary を分けて観測する。
- PSRAM-only probe は各 SETREQ / GETREQ に別の sequence number を使い、応答の GETRESP type `0x0001`、sequence number、VARID を照合する。BCCMD に server-to-client の SETRESP type はなく、SETREQ に request type `0x0002` が返ると仮定してはいけない。timeout 後の遅延応答を次 stage の成功応答として扱わない。
- 対象 CSR8510 A10 は warm reset なしで PSRAM BD_ADDR SETREQ を受理し、GETREQ で sentinel を返す。active standard HCI address は warm reset 前には変化しない。元値 restore SETREQ は status `0` だったが、その後の PSRAM GETREQ は status `0x0008` であり、same-session restore 成否は確定できない。
- BlueZ HCI 経路は CSR warm reset に対して応答を待たず command を送る。Bumble 0.0.230 の USB sink は `Host.send_hci_packet()` を queue に積んで非同期 transfer するため、staged probe は reset enqueue 後 0.5 秒待って close する。transfer 完了は直接判定せず、USB 再列挙と別プロセス read を実機の判定根拠にする。
- staged probe は同一 session restore を行わない。warm reset 後の観測に成功しても失敗しても物理 power cycle を必須とし、その後の read-only probe で元 identity を確認する。
- 対象 CSR8510 A10 は PSRAM write + CSR warm reset 後、別プロセスの standard HCI Read BD_ADDR と CSR default-store GETREQ の双方で sentinel を返した。これは controller-reported active BD_ADDR の一時変更が可能という hardware observation であり、on-air identity や Switch の登録分離までは示さない。
- sentinel active identity の観測後に dongle を物理 power cycle すると、standard HCI / CSR default-store の双方が元の `00:1B:DC:F9:9F:7D` へ復帰した。対象個体では volatile change と physical recovery の一連を observed-pass とする。
- Switch-facing probe は raw HCI の standard / CSR address 一致を確認して adapter を閉じ、Bumble transport を開き直す。Bumble `power_on()` 後にも address を再取得し、一致しなければ connectable / discoverable を有効にしない。preflight 後の HCI Reset による address 変化もこの二段目の guard で遮断する。
- identity ごとに存在しない key store path を要求する。既存 key store がある場合は adapter を開かず失敗する。これにより元 address、local address、dummy address の link key を混在させない。
- 初回 pairing は fresh key store を要求する。同じ expected address の目視再試験に限り `--reuse-key-store` で既存 key store を明示再利用できる。reuse 指定時にファイルがなければ adapter を開かない。
- pairing probe は `connected` 直後に閉じず、既定5秒の観測窓を維持する。この間の periodic input は neutral のみとする。
- 対象 Switch は local address `02:1B:DC:F9:9F:7D` を Classic pairing と HID connection まで受理した。Bumble `power_on()` 後の address、Device Info address ともに local address であり、fresh key store 保存と neutral input report 送信後に clean close した。元 address の登録と別 device に見えたかは目視確認を逃したため unobserved である。
- local-address pairing 後に dongle を物理 power cycleすると、2回の read-only recovery probe で standard HCI / CSR default-store の双方が元の `00:1B:DC:F9:9F:7D` へ復帰していた。対象個体では Switch-facing pairing 後も volatile identity の physical recovery が observed-pass である。
- BlueZ の CSR 対応は source fact だが、VID:PID `0a12:0001` の全個体が受理することは未検証仮説である。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_csr_bd_addr.py` | new | command plan と response parser。I/O なし |
| `tools/csr_bd_addr_plan.py` | new | adapter を開かない dry-run |
| `tools/csr_bd_addr_probe.py` | new | standard HCI identity read と CSR GETREQ の承認済み実機 probe |
| `tools/csr_bd_addr_volatile_probe.py` | new | dry-run 既定、warm reset なし、自動 restore 必須の PSRAM SETREQ / GETREQ probe |
| `tools/csr_bd_addr_warm_reset_probe.py` | new | dry-run 既定、PSRAM apply / warm reset enqueue と別プロセス read を分離する probe |
| `tools/csr_bd_addr_switch_pair_probe.py` | new | fresh key store と二段階 address guard を持つ Switch pairing probe |
| `tests/unit/test_csr_bd_addr_experiment.py` | new | BlueZ layout の characterization |
| `tests/unit/test_csr_bd_addr_switch_pair_probe.py` | new | pairing probe の dry-run と既存 key store 拒否 |
| `src/swbt/transport/bumble.py` | update | power-on 後、可視化前の expected local address guard |
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
| `uv run pytest tests/unit/test_csr_bd_addr_experiment.py -q` | pass | GETREQ / SETREQ に対する GETRESP と遅延応答拒否を追加後 15 passed |
| `uv run python tools/csr_bd_addr_volatile_probe.py --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D` | pass | `adapter_opened=false`、apply / restore とも volatile、persistent write false |
| 同 command に `--execute` と artifact options を追加 | inconclusive | baseline pass。apply 中 timeout、USB device address `11` から `16` へ再列挙。同一 process restore は失敗。別 process read-only probe で元 address と clean close を確認 |
| warm reset なしの PSRAM-only tool へ変更後、同 dry-run command | pass | `adapter_opened=false`、`warm_reset=false`、PSRAM SETREQ / GETREQ / restore / GETREQ / close の順序を出力 |
| PSRAM-only tool 変更後の `uv run ruff format --check .` / `ruff check .` / `ty check --no-progress` | pass | 92 files formatted、lint / type check pass |
| `uv run pytest tests/unit -q -p no:cacheprovider --basetemp=tmp/pytest-unit-csr-getresp-20260719` | pass | response type 修正後 425 passed |
| 承認済み PSRAM-only command | harness fail / hardware inconclusive | baseline pass、apply / best-effort restore timeout、adapter close pass。SETREQ response type filter の誤りを確認したため、write 適用可否の根拠にはしない。後続 power-cycle read は pass |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-post-psram-power-cycle.json` | pass | 抜き差し後、standard HCI / CSR default-store address `00:1B:DC:F9:9F:7D`、CSR status `0`、一致、clean close |
| 修正版の承認済み PSRAM-only retry command | partial | apply SETREQ / PSRAM sentinel read-back / active standard address 不変は pass。restore SETREQ status `0` 後の GETREQ と best-effort restore は status `0x0008`、adapter close pass。後続 power-cycle read は pass |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-post-psram-retry-power-cycle.json` | pass | 抜き差し後、standard HCI / CSR default-store address `00:1B:DC:F9:9F:7D`、CSR status `0`、一致、clean close。PSRAM volatile 復帰を再確認 |
| `uv run python tools/csr_bd_addr_warm_reset_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D` | pass | dry-run。`adapter_opened=false`、persistent / advertising / Switch-facing false、automatic restore false、physical power cycle 必須、process boundary を出力 |
| staged warm-reset tool 追加後の standard gate | pass | 93 files formatted、ruff / ty pass、425 unit tests pass |
| 承認済み staged warm-reset apply command | pass | baseline / PSRAM apply / sentinel read-back pass、warm reset enqueue 後 USB transfer status `4`、process exit `0`。後続の別プロセス read で active sentinel を確認 |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-warm-reset-active-read.json` | pass | HCI Reset なし。standard HCI / CSR default-store address が sentinel `02:1B:DC:F9:9F:7D`、status `0`、一致、clean close |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-post-warm-reset-recovery.json` | pass | power cycle 後、standard HCI / CSR default-store address が元の `00:1B:DC:F9:9F:7D`、status `0`、一致、clean close |
| `uv run pytest tests/unit/test_csr_bd_addr_switch_pair_probe.py tests/unit/test_bumble_transport.py -q` | pass | 45 passed。power-on address 不一致時は可視化前に拒否し、dry-run / fresh key store guard を確認 |
| `uv run pytest tests/unit -q -p no:cacheprovider --basetemp=tmp/pytest-unit-csr-switch-pair-final` | pass | 428 passed。並列 basetemp 競合の修正後に直列再実行 |
| `uv run pytest tests/integration -q -p no:cacheprovider --basetemp=tmp/pytest-integration-csr-switch-pair-final` | pass | 125 passed。unit と別 basetemp で直列実行 |
| local address の承認済み warm-reset + guarded pairing probe | pass / visual pending | standard HCI / CSR / Bumble power-on address が `02:1B:DC:F9:9F:7D` で一致。Classic pairing、fresh key store、HID connected、neutral `0x30`、clean close。別登録の目視は未確認 |
| `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/local-address-post-pair-recovery.json` | pass | power cycle 後、standard HCI / CSR default-store が元の `00:1B:DC:F9:9F:7D` で一致、clean close |
| 同 read-only recovery command の `local-address-post-pair-recovery-recheck.json` 再確認 | pass | 2回目も standard HCI / CSR default-store が元 address で一致、clean close |
| 観測窓 / key store reuse 追加前の対象 test | red | dry-run に `observation_seconds` がなく1 failed。`--reuse-key-store` 未実装で1 failed |
| `uv run pytest tests/unit/test_csr_bd_addr_switch_pair_probe.py tests/unit/test_bumble_transport.py -q -p no:cacheprovider --basetemp=tmp/pytest-csr-observation-reuse-green` | pass | 46 passed。既定5秒、明示 reuse、address guard の非実機 contract を確認 |
| `uv run pytest tests/unit -q -p no:cacheprovider --basetemp=tmp/pytest-unit-csr-observation-final` | pass | 429 passed |
| local address 5秒再試験 command の dry-run | pass | `adapter_opened=false`、`key_store_mode=reuse`、`observation_seconds=5.0`、RF / Switch-facing false |
| Bumble / hardware pytest | not run | 今回は専用 probe command のみ承認範囲として実行 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | dry-run は不要。read-only probe 以降は必要 |
| 承認範囲 | adapter、command、read-only / volatile / persistent、Switch-facing 動作、cleanup plan |
| adapter | 候補は専用 `usb:0` / CSR8510 A10 / `0a12:0001` / WinUSB。実行直前に再確認する |
| 実行遮断 | 環境変数ではなく、会話上の明示承認で管理する |
| log / artifact | raw HCI trace、前後の BD_ADDR、manufacturer/version、USB 再列挙を保存する |
| cleanup | Switch-facing probe は controller context で discoverable / connectable を解除して adapter を閉じる。各 address 試験後に物理 power cycle と read-only recovery check を必須にし、復旧確認前に次 address を試さない |

## 13. 先送り事項

- volatile selector が対象個体で address を一時変更できるか。
- volatile selector が対象個体で再挿入後に復帰するか。
- restore SETREQ status `0` 後に PSRAM GETREQ が status `0x0008` となる意味と、same-session restore の扱い。
- SETREQ 成功確認後、warm reset と USB transfer loss を別 stage / process で観測する。
- controller-reported active BD_ADDR の変更が on-air BD_ADDR に反映されるか。
- Switch-facing 検証に使える正規割り当て済み universal EUI-48 の確保。
- BD_ADDR ごとの key store path の公開 API / CLI での導出。
- Switch が同一ドングルの複数 BD_ADDR を独立登録できるか。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] dry-run の根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] Bumble 最新版との比較を記録した
- [x] format / lint / type gate を記録した
