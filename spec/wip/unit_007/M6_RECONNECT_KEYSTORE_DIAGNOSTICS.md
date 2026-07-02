# M6 Bond Reuse Reconnect / Keystore / Diagnostics 仕様書

## 1. 概要

### 1.1 目的

pairing 情報の保存、保存済み bond を使う reconnect、diagnostics 拡充、hardware run metadata を扱う。M6 の中心は、daemon restart 後の再接続要求と同じく、Switch 側の追加操作なしに保存済み link key を使って接続を戻せるかを確認することである。

この仕様では reconnect を次の 3 種類に分ける。

| 用語 | 意味 | M6 での扱い |
|---|---|---|
| active bond reuse reconnect | 保存済み peer address / link key を使い、swbt-python 側から Switch へ Classic 接続を開始する | 主対象 |
| incoming bond reuse | swbt-python 側が connectable で待ち、Switch 側から既知 device として接続要求が来る | 補助観測 |
| advertising recovery | 失敗後に自動で discoverable / connectable へ戻して待つ | 対象外 |

M6 は全 dongle での reconnect 保証を目標にしない。観測条件を明確にし、release 時に保証できる範囲を分ける。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| roadmap | M6 の対象範囲、非対象範囲、完了条件 | `spec/initial/roadmap.md` |
| lifecycle | reconnect 方針、key_store_path、disconnect 処理。M6 で active / incoming / advertising recovery へ再分類する | `spec/initial/lifecycle.md` |
| api | `key_store_path`、`status()` | `spec/initial/api.md` |
| testing | hardware test の reconnect 項目 | `spec/initial/testing.md` |
| risks | reconnect、dongle、OS / driver 差分。`active reconnect / incoming reconnect` は Bumble と OS / dongle に依存する | `spec/initial/risks.md` |
| completed M5 | Button A / neutral は確認済み。pairing_complete / authentication event と reconnect は未確認 | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| daemon reconnect reference | link-key DB open、link key request response、no `pairing complete`、L2CAP open、Button A smoke は daemon 側で observed | `spec/complete/unit_006/M5_INPUT_OPERATION_API.md` |
| hardware log | full handshake と Button A は observed-pass。Switch model / firmware、reconnect、key store は未記録 | `docs/hardware-test-log.md` |
| close cleanup prerequisite | reconnect 前に connected close / disconnect cleanup contract を固定する。unit_014 は automated contract と hardware characterization まで完了済み | `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md` |
| context manager prerequisite | `async with` を resource scope に寄せ、HID advertising / pairing / reconnect を明示 API へ移す | `spec/complete/unit_015/CONTEXT_MANAGER_RESOURCE_SCOPE.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `SwitchGamepad(key_store_path=...)` | pairing 情報の保存先が設定される | 保存形式は Bumble と実装で確認 |
| developer | 初回 pairing 後 | key store 書き込み有無が diagnostics に残る | secret 値はログに出さない |
| library user | 保存済み bond があり、daemon restart 相当の再起動後に再接続する | Switch 側の追加操作なしで active bond reuse reconnect を試行し、結果を記録する | peer address の取得方法と複数 bond 時の扱いは実装で固定 |
| developer | incoming bond reuse を観測する | Switch 側から既知 device への接続要求が来たか、active reconnect と区別して記録する | incoming 成功は「Switch 側操作なし」の証明にはしない |
| developer | reconnect 失敗 | failure reason と cleanup を記録する | 自動 advertising recovery はしない |
| lifecycle | reconnect 前の close cleanup | 前回 connected close が neutral、disconnect request terminal state、transport close まで説明できる | `unit_014` の完了済み仕様と hardware evidence を前提に M6 へ入る |

## 2. 対象範囲

- `key_store_path` の設定と diagnostics 記録。
- pairing 情報保存の確認。
- active bond reuse reconnect の成功 / 失敗の区別。
- incoming bond reuse と active bond reuse reconnect の trace 上の区別。
- reconnect 失敗時の clean close と failure diagnostics。
- hardware run metadata の trace 追加。
- trace schema の安定化。
- hardware matrix の更新。
- `unit_014` で固定した close / disconnect cleanup contract を reconnect 前提として参照する。

## 3. 対象外

- 全 dongle での reconnect 保証。
- 複数 controller 同時 reconnect。
- daemon mode。
- link key の secret 値のログ出力。
- OS 標準 Bluetooth stack との併用。
- reconnect 失敗後の自動 advertising recovery。
- reconnect 失敗後の自動 retry loop。
- incoming bond reuse だけで「Switch 側操作なし reconnect」を満たしたと扱うこと。
- connected close / remote close request / bounded disconnect wait の設計。これは `unit_014`。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_011/HARDWARE_TEST_LOG_MATRIX.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | required | todo | active bond reuse reconnect 後の初期 output report sequence が初回 pairing と異なる可能性がある |
| Bumble / transport | required | todo | `JsonKeyStore`、link key request / update、active Classic connection、incoming connection event、HID channel open は Bumble 挙動に依存する |
| OS / driver / adapter | required | todo | active reconnect と incoming reconnect の成否は dongle、driver、Switch firmware 条件付きで記録する |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| key store configured | `key_store_path` 指定 | path と存在確認結果を diagnostics に記録する | secret 内容は記録しない |
| pairing saved | 初回 pairing 後 | 保存成功 / 失敗が trace に残る | Bumble API 確認が必要 |
| saved bond discovered | key store に保存済み peer がある | peer address の候補数、選択結果、曖昧さを trace に残す | link key 値は出さない |
| active reconnect attempt | 保存済み peer address / link key あり | active attempt start / result を記録する | Bumble の active Classic connection API を監査してから固定 |
| active reconnect success | active attempt 後に HID channel ready | state が connected になる | 再 pairing event がないことを観測対象に含める |
| active reconnect failure | timeout / error | failure reason を記録し clean close する | 自動 advertising recovery はしない |
| incoming bond reuse | connectable 中に Switch から接続要求が来る | incoming として attempt / result を記録する | Switch 側操作なし reconnect の証明にはしない |
| key store reset | user deletes key store | 再 pairing 手順を docs に残す | CLI 化は M7 |
| trace metadata | hardware run | OS、driver、dongle、Bumble、Python、Switch model / firmware を含む | unit_010 と整合 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `key_store_path` 指定が diagnostics metadata に残る | new | unit | no | secret は出さない |
| todo | `key_store_path` が Bumble `JsonKeyStore` の保存先として設定される | new | unit | no | public API に Bumble 型を出さない |
| todo | key store 書き込み失敗が diagnostics に残り、例外の扱いが明確になる | edge | unit | no | filesystem failure mock |
| todo | key store に保存済み peer が 0 件、1 件、複数件ある場合の active reconnect 入口が trace で区別される | new | unit | no | 複数 peer の自動選択はしない |
| todo | disconnect 後に reconnect disabled なら closed / failed の定義通りに遷移する | regression | integration | no | M1-M5 の保証維持 |
| todo | active reconnect failure が failure reason を記録し、automatic advertising recovery を開始しない | new | integration | no | fake transport event |
| todo | incoming bond reuse と active reconnect の trace event が混ざらない | new | integration | no | fake transport event |
| todo | trace event が schema に従い metadata を含む | regression | integration | no | unit_010 |
| todo | key store ありで active bond reuse reconnect 成功 / 失敗を実機で記録する | new | hardware | yes | 成功保証ではなく観測 |
| todo | active reconnect run で新規 pairing event の有無、authentication、encryption、HID channel open を記録する | characterization | hardware | yes | daemon 側の pairing-free reconnect 観測と突き合わせる |
| todo | incoming bond reuse を実機で観測する場合は Switch 側操作の有無を記録する | characterization | hardware | yes | active reconnect success とは分ける |
| todo | hardware matrix に reconnect 結果が反映される | new | hardware | yes | unit_011 |
| todo | public config の `key_store_path` が `SwitchGamepad` から Bumble transport 生成へ渡る | new | unit | no | 現状は public config に存在するが、transport bridge へ未接続 |
| todo | `pairing_complete` / `connection_authentication` diagnostics が実機 trace に出るか確認する | characterization | hardware | yes | unit_006 では `link_key_available` と `connection_encryption_change` は出たが、この 2 event は未記録 |
| done | `unit_014` の close / disconnect cleanup contract が完了していることを M6 の前提として確認する | regression | docs | no | unit_014 は connected close ordering、Classic scan cleanup、full observed handshake 後の A exit / close path を hardware evidence 付きで完了済み |

## 8. 設計メモ

- reconnect は初期 release の保証対象に含めるか未決である。実装しても README では確認済み構成と未確認構成を分ける。
- M6 では `reconnect` を裸の用語として扱わない。active bond reuse reconnect、incoming bond reuse、advertising recovery を分ける。
- active bond reuse reconnect を主経路にする前に、`async with` / `open()` が暗黙に advertising へ入る現状を unit_015 で整理する。M6 は resource scope 化後の `connect()` / `reconnect()` を前提にする。
- daemon restart 後に Switch 側の追加操作なしで戻る要件に近いのは active bond reuse reconnect である。incoming bond reuse は Switch 側が接続要求を出す必要があるため、主成功条件にはしない。
- advertising recovery は以前の pre-host-connection timeout と同じ失敗面を再発させる可能性がある。M6 では failure diagnostics と clean close までに留め、自動復帰や retry は別 unit に送る。
- key store の secret 値は diagnostics に出さない。path、存在、読み書き結果、例外型に留める。
- active reconnect 失敗時は利用者が再 pairing へ戻れる状態を優先する。ただし自動で discoverable / connectable へ戻す挙動はここに含めない。
- trace schema は M2 以降の実機 run で破綻しないよう、unit_010 で先に安定させる。
- `unit_006` の post-handshake run は Button A と neutral を完了したが、Bumble の `pairing_complete` / `connection_authentication` event は実機 trace に出ていない。M6 では、Bumble callback が出ないのか、bonding / reconnect 条件でだけ出るのかを分ける。
- `SwitchGamepadConfig.key_store_path` は public surface にある。M6 では、この値が Bumble の link key 保存へ接続されているかを最初に確認する。
- disconnect 競合時の trailing neutral、remote close request、closed event / timeout は `unit_014` で決める。M6 ではその terminal state を reconnect 前提として読み、reconnect failure と close cleanup failure を混ぜない。unit_014 は Switch 実機での close request ordering まで確認済みとして扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | active reconnect option、lifecycle |
| `src/swbt/transport/base.py` | modify | active reconnect transport boundary |
| `src/swbt/transport/fake.py` | modify | fake active / incoming reconnect events |
| `src/swbt/transport/bumble.py` | modify | key store / active reconnect bridge |
| `src/swbt/diagnostics.py` | modify | metadata と reconnect events |
| `src/swbt/errors.py` | modify | reconnect / keystore error |
| `tests/unit/` | modify | key store metadata tests |
| `tests/integration/` | modify | fake active / incoming reconnect lifecycle tests |
| `tests/hardware/` | modify | reconnect characterization tests |
| `docs/hardware-test-log.md` | modify | reconnect 観測 |
| `README.md` | modify | reconnect の保証範囲 |
| `spec/wip/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` | modify | unit_006 から送った reconnect / diagnostics deferred item |
| `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md` | reference | reconnect 前提となる close / disconnect cleanup contract |

## 10. 検証

この表は M6 実装時に実行する gate を示す。仕様書作成時点の実行結果ではない。

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit tests/integration` | pending | M6 実装後に local automated gate として実行する |
| `uv run pytest -m hardware` | pending-approval | reconnect 実機検証の明示承認後に実行する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for reconnect observation |
| 承認範囲 | adapter open、Classic HID Device initialization、discoverable / connectable / HID advertising、初回 pairing、key store 書き込み、disconnect、active reconnect request、HID control / interrupt channel open、Switch-facing output report / subcommand handling、periodic report loop、必要時の incoming bond reuse 観測、再 pairing、close |
| adapter | 例: `usb:0`。専用 USB Bluetooth dongle であること |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | diagnostics trace、hardware test log、key store path metadata |
| cleanup | neutral、report loop 停止、transport close、adapter release。必要なら key store 削除手順を記録 |

## 12. 先送り事項

- 複数 dongle / 複数 Switch firmware の網羅は初期 release 後の matrix 拡張に送る。
- daemon mode の reconnect 制御は初期対象外。
- reconnect 失敗後の automatic advertising recovery と retry loop は別 unit に送る。M6 では失敗理由と cleanup を記録する。
- 複数 peer が key store にある場合の自動選択 UI / CLI は M7 以降に送る。M6 では曖昧さを diagnostics に出す。
- CLI からの key store reset helper は M7 の `swbt-probe` で必要性を判断する。
- L+R / stick の追加 semantic input reflection は `unit_013`。M6 では扱わない。
- connected close / remote close request / bounded disconnect wait は `unit_014`。M6 では再設計しない。

## 13. チェックリスト

このチェックリストは M6 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] 対象範囲と対象外を初期設計から切り出した
- [x] TDD Test List の初期案を作成した
- [x] active bond reuse reconnect、incoming bond reuse、advertising recovery の意味を分けた
- [ ] reconnect / key store / diagnostics の根拠監査を実施し、状態を更新した
- [ ] M6 の local automated gate を実行し、検証欄を結果で更新した
- [ ] 実機 reconnect 観測は承認、command、cleanup、結果を `docs/hardware-test-log.md` に記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
