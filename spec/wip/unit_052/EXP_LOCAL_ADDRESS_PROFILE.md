# EXP_LOCAL_ADDRESS_PROFILE 仕様書

## 1. 概要

### 1.1 目的

`ProController` に、利用者が管理する `exp_local_address` と Switch pairing key を一つの profile JSON へ保存し、その profile で CSR8510 A10 の volatile BD_ADDR を準備して接続する経路を追加する。

通常の `ProController(adapter=...)` は adapter 本来の BD_ADDR を使い、既存の接続経路を維持する。`profile_path` を明示した場合だけ exp local identity 経路を使う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #89 | 接続情報と `exp_local_address` 切替を統合した公開 API | `https://github.com/niart120/swbt-python/issues/89` |
| CSR 実験の完了仕様 | CSR8510 A10 の volatile write、warm reset、通常 close 後の保持、USB dongle 抜き差し後の復帰 | `spec/complete/unit_051/CSR_BD_ADDR_REWRITE_EXPERIMENT.md` |
| 初期 transport 設計 | Bumble transport と local BD_ADDR の既存境界 | `spec/initial/transport-bumble.md` |
| 初期公開 API | `ProController` の constructor / pairing lifecycle | `spec/initial/api.md` |
| Bluetooth Core 6.1 | BD_ADDR の reserved LAP `0x9E8B00`〜`0x9E8B3F` | `https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core-61/out/en/br-edr-controller/baseband-specification.html` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| profile 作成者 | 新規 `profile_path`、local / individual `exp_local_address` | profile を作成し、その identity で初回 pairing できる | CSR8510 A10 の既知構成だけを実機完了対象にする |
| profile 利用者 | 既存 `profile_path` | target が current BD_ADDR と一致すれば書換なしで reconnect / pairing を試みる | profile JSON は swbt envelope に限る |
| 通常利用者 | `profile_path` なし | adapter 本来の identity で従来どおり利用できる | CSR vendor command を送らない |
| write 結果不明の呼び出し側 | write 送信後の timeout、reset 不成立、read-back 不能 | `ExpLocalAddressRecoveryRequired` を受け取り、USB dongle を抜き差しする | profile へ recovery 状態を書かない |

## 2. 対象範囲

- `ProController` の `profile_path` と `create_profile()` 公開経路。
- swbt 所有 profile envelope の parse、validation、atomic save。
- envelope の `key_store.namespaces` を Bumble KeyStore interface へ渡す内部 adapter。
- CSR8510 A10 volatile preparation、warm reset 後の再列挙待機、read-back、Bumble power-on 後 guard。
- `ExpLocalAddressRecoveryRequired` 例外と失敗 diagnostics。
- unit / fake transport test と、既知構成での必須手動実機 gate。
- 実装完了時の `spec/initial/api.md`、`transport-bumble.md`、`lifecycle.md`、`risks.md` の Intent Delta 反映。

## 3. 対象外

- 正規 EUI-48 の調達、所有、割当、または global uniqueness の保証。
- universal 形式の固定 dummy address の提供。
- 既存 raw Bumble key-store JSON の読込・自動移行。
- CSR8510 A10 以外の chipset / driver / OS への対応検知または互換保証。
- Joy-Con、Direct controller、複数 controller への公開 profile 経路の展開。
- persistent BD_ADDR write、factory address の読出し、profile への adapter 固有復旧情報の保存。
- read-only recovery probe の公開 API。
- USB dongle の物理的な給電断をライブラリが行うこと。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/risks.md`
- `spec/initial/testing.md`
- `spec/complete/unit_051/CSR_BD_ADDR_REWRITE_EXPERIMENT.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | identity profile は HID report layout を変更しない |
| Bumble / transport | required | done for existing behavior | Bumble 0.0.230 の `JsonKeyStore` root namespace 規則、`power_on()` 後の public address guard、unit_051 の raw CSR session を参照する |
| CSR command / reset | required | done for target hardware only | BlueZ-compatible BCCMD layout と CSR8510 A10 / WinUSB の unit_051 hardware observation を再利用する。persistent write は行わない |
| `exp_local_address` validation | required | done | 6 octet、individual、locally administered、reserved LAP `9E:8B:00`〜`9E:8B:3F` 拒否。Bluetooth Core 6.1 の source fact |
| OS / driver / adapter | required | done for target hardware only | Windows 11 / CSR8510 A10 / WinUSB / `usb:0` / Bumble 0.0.230 だけを手動 gate 対象にする |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| 通常起動 | `profile_path=None` | native BD_ADDR で既存 Bumble transport を開く | CSR preparation を実行しない |
| profile parse | 既存 `profile_path` | `format="swbt.profile"`、schema version 1、identity、namespace map を検査する | legacy raw Bumble JSON、未知 version、不正 schema、`controller_kind != "pro"` は adapter open 前に失敗 |
| address validation | `exp_local_address` | 6 octet、individual、local、非予約 LAP の値だけを受理する | user-managed local identity であり規格適合の universal BD_ADDR を主張しない |
| profile 作成 | 未存在 path と有効 address | `controller_kind="pro"` を含む empty envelope を atomic に保存し、volatile preparation と pairing を行う | 既存 path は上書きしない。pairing 失敗後も profile は残る |
| current = target | raw read が target と一致 | write / warm reset を省略し、Bumble open へ進む | 同じ target の継続利用 |
| current != target | raw read が target と異なる | volatile write、warm reset、再列挙、read-back の順に target を確認する | raw session と Bumble transport は同時に adapter を開かない |
| power-on guard | Bumble `power_on()` 後の address が target と不一致 | advertising、pairing、reconnect を開始しない | identity 不一致の可視化を防ぐ |
| write 前の失敗 | validation、raw read、対応外 CSR で失敗 | preparation failure として失敗する | USB dongle の抜き差しを要求しない |
| write 後の結果不明 | write 送信後の timeout、reset / read-back 不能 | `ExpLocalAddressRecoveryRequired` を送出する | USB dongle を抜き差しする。profile へ状態保存しない |
| pairing / 接続失敗 | address guard 通過後に pairing / reconnect が失敗 | 通常の connection failure を返す | 同じ profile の再試行を許可する |
| 通常 close | connected / opened controller | transport を閉じる | volatile address を戻さず、次回の同 profile 利用を妨げない |

### 6.1 profile envelope version 1

```json
{
  "format": "swbt.profile",
  "schema_version": 1,
  "identity": {
    "kind": "exp-local-address",
    "address": "02:12:34:56:78:9A"
  },
  "controller_kind": "pro",
  "key_store": {
    "namespaces": {
      "02:12:34:56:78:9A": {},
      "swbt.previous::02:12:34:56:78:9A": {}
    }
  }
}
```

Bumble `JsonKeyStore` へ envelope 全体を渡さない。pairing key は `key_store.namespaces` のみを内部 KeyStore adapter で読み書きし、envelope 全体を atomic に保存する。

### 6.2 API 草案

```python
pad = await ProController.create_profile(
    adapter="usb:0",
    profile_path="profiles/lab-pad.json",
    exp_local_address="02:12:34:56:78:9A",
    pair_timeout=60.0,
)

pad = ProController(adapter="usb:0", profile_path="profiles/lab-pad.json")
await pad.connect(allow_pairing=False)
```

`create_profile()` は既存 path を上書きしない。`profile_path` を渡した通常 constructor は profile の target を読み、caller に address の再指定を求めない。既存 `key_store_path` はこの public exp profile 経路に受け付けない。

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | profile なしの `ProController` は CSR preparation を呼ばず native transport を作る | regression | unit | no | 52 targeted tests pass。native factory への既存引数を維持し追加 refactor なし |
| refactor-skipped | malformed / unknown schema / legacy raw Bumble JSON は adapter open 前に拒否する | edge | unit | no | 16 tests pass。codec は adapter 非依存で責務が閉じており追加 refactor なし |
| refactor-skipped | group、universal、reserved LAP の address は profile 作成前に拒否する | edge | unit | no | 8 tests pass。immutable value object で責務が閉じており追加 refactor なし |
| refactor-done | 新規 profile は `controller_kind="pro"` を含む envelope を atomic に保存し、既存 path を上書きしない | new | unit | no | 18 tests pass。一時ファイルの完全書込と payload 生成を分離 |
| refactor-skipped | current = target なら volatile write と warm reset を省略する | new | unit | no | 1 test pass。比較結果を immutable result に閉じており追加 refactor なし |
| refactor-done | current != target では write、reset、再列挙後 read-back を順に要求する | new | unit | no | 2 tests pass。CSR 初期化と再列挙 retry を helper へ分離 |
| refactor-done | write 後の結果不明は `ExpLocalAddressRecoveryRequired` となり pairing を始めない | edge | unit | no | 5 targeted tests pass。stage state と runtime preparation を分離 |
| refactor-done | Bumble power-on 後の address 不一致は advertising / pairing / reconnect を開始しない | regression | unit | no | 51 tests pass。advertising / reconnect の照合を共通 helper へ統合 |
| refactor-done | pairing key 保存後も envelope identity と namespace map が保持される | new | integration | no | 53 targeted tests pass。profile envelope の一時ファイル保存を共通化 |
| refactor-skipped | pairing 失敗後、同じ profile で pairing を再試行できる | regression | integration | no | 61 targeted tests pass。作成済み profile を残して controller 資源だけを閉じる単一責務のため追加 refactor なし |
| todo | `close()` 後に target が残る profile を次の controller が再利用できる | characterization | bumble | yes | known CSR8510 A10 の実機 gate と結ぶ |
| todo | fresh profile 作成、pairing、通常 close 後の同 profile 再利用を確認する | characterization | hardware | yes | 完了必須の手動 gate |

## 8. 文書検証計画

実装完了時に公開 API と transport 前提を更新する。自然言語要件を固定語句で検査しない。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `spec/initial/api.md` | profile の作成と再利用 | 本仕様 §6.2 | link / code example の構文確認 | todo | 実装 API 確定後に `docs-quality-review` |
| `spec/initial/transport-bumble.md` | CSR target 限定と guard | 本仕様 §5、§6 | link 確認 | todo | 実機 gate 後に確認済み範囲を記録 |
| `spec/initial/lifecycle.md` | `close()` と recovery-required | 本仕様 §6 | link 確認 | todo | public lifecycle との整合 |
| `spec/initial/risks.md` | local identity / recovery のリスク | 本仕様 §2、§3 | link 確認 | todo | obsolete な EUI-48 前提を置換 |

## 9. 設計メモ

- P-007 の主な懸念は CSR warm reset 後の USB 再列挙である。unit_051 では旧 libusb handle を同一 Python process で再 open できなかった。preparation は raw session を閉じ、adapter が再び開けるまで待ってから read-back と Bumble transport 作成を行う。
- 再列挙待機の timeout、adapter を再 open できない場合の exception、write 済みか確定できない境界は実装前に内部 state machine と unit test で固定する。write 送信後に target 状態を確定できない経路は `ExpLocalAddressRecoveryRequired` に畳み込む。
- `close()` は controller resource の終了であり、USB dongle の抜き差しや volatile address の復旧を行わない。抜き差し後の read-only probe は内部 diagnostics だけに残し、公開 API にしない。
- profile は adapter 固有情報や factory / baseline BD_ADDR を保存しない。`controller_kind="pro"` は後続の Joy-Con / Direct profile との取り違えを防ぐ swbt 側 contract である。同じ local identity を同時に複数 adapter で使わないことは利用者の責任とする。
- CSR8510 A10 以外で成功することは未検証である。対応可否を事前検知しようとせず、preparation 実行時の失敗として報告する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad/core.py` | modify | `ProController` の `profile_path` と `create_profile()` |
| `src/swbt/gamepad/transport_factory.py` | modify | profile-aware Bumble transport の組立 |
| `src/swbt/transport/bumble.py` | modify | target address guard と profile KeyStore adapter の接続 |
| `src/swbt/transport/_exp_local_address.py` | new | typed address、envelope codec、preparation state / error |
| `src/swbt/transport/_exp_local_identity.py` | new | raw CSR session、warm reset 再列挙、read-back handoff |
| `src/swbt/transport/_bumble_key_store.py` | modify | envelope namespace view の KeyStore adapter |
| `tests/unit/test_exp_local_address.py` | new | validation、codec、failure classification |
| `tests/unit/test_exp_local_identity.py` | new | preparation sequence と guard |
| `tests/integration/test_exp_local_profile.py` | new | pairing key persistence と retry lifecycle |
| `spec/initial/api.md` | modify | 完了時に `profile_path` / `create_profile()` を正本へ反映 |
| `spec/initial/transport-bumble.md` | modify | CSR target 限定と transport handoff |
| `spec/initial/lifecycle.md` | modify | close と recovery-required |
| `spec/initial/risks.md` | modify | local identity の制約と未検証範囲 |
| `spec/hardware-test-log.md` | modify | 手動実機 gate の実行時だけ観測を追記 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run ruff format --check .` | not run | 実装前 |
| `uv run ruff check .` | not run | 実装前 |
| `uv run ty check --no-progress` | not run | 実装前 |
| `uv run pytest tests/unit` | not run | 実装前 |
| `uv run pytest tests/integration` | not run | integration tree を追加 / 変更した場合に実行 |
| 手動 CSR8510 A10 gate | not run | 実装・unit / integration gate 後、明示承認が必要 |
| `uv run pytest tests/unit/test_exp_local_address.py -q` | pass | address validation cycle: 8 passed |
| `uv run ruff check src/swbt/transport/_exp_local_address.py tests/unit/test_exp_local_address.py` | pass | address validation cycle |
| `uv run pytest tests/unit/test_exp_local_address.py -q` | pass | profile codec cycle: 16 passed |
| `uv run ruff format --check src/swbt/transport/_exp_local_address.py src/swbt/errors.py src/swbt/__init__.py tests/unit/test_exp_local_address.py` | pass | profile codec cycle |
| `uv run ruff check src/swbt/transport/_exp_local_address.py src/swbt/errors.py src/swbt/__init__.py tests/unit/test_exp_local_address.py` | pass | profile codec cycle |
| `uv run ty check --no-progress` | pass | address validation cycle |
| `uv run pytest tests/unit/test_public_api_boundary.py tests/unit/test_gamepad_transport_factory.py tests/unit/test_probe_cli.py -q` | pass | profile-less native transport cycle: 52 passed |
| `uv run ruff check src/swbt/gamepad/_config.py src/swbt/gamepad/runtime.py src/swbt/gamepad/core.py src/swbt/probe.py tests/unit/test_public_api_boundary.py tests/unit/test_probe_cli.py tests/hardware/test_input_operations.py tests/hardware/test_reconnect_keystore.py` | pass | profile-less native transport cycle |
| `uv run ty check --no-progress` | pass | profile-less native transport cycle |
| `uv run pytest tests/unit/test_exp_local_address.py -q` | pass | atomic profile creation cycle: 18 passed |
| `uv run ruff check src/swbt/transport/_exp_local_address.py tests/unit/test_exp_local_address.py` | pass | atomic profile creation cycle |
| `uv run ty check --no-progress` | pass | atomic profile creation cycle |
| `uv run pytest tests/unit/test_exp_local_identity.py -q` | pass | already-active preparation cycle: 1 passed |
| `uv run ruff check src/swbt/transport/_exp_local_identity.py tests/unit/test_exp_local_identity.py` | pass | already-active preparation cycle |
| `uv run ty check --no-progress` | pass | already-active preparation cycle |
| `uv run pytest tests/unit/test_exp_local_identity.py -q` | pass | rewrite / re-enumeration cycle: 2 passed |
| `uv run ruff check src/swbt/transport/_exp_local_identity.py tests/unit/test_exp_local_identity.py` | pass | rewrite / re-enumeration cycle |
| `uv run ty check --no-progress` | pass | rewrite / re-enumeration cycle |
| `uv run pytest tests/unit/test_exp_local_identity.py tests/unit/test_exp_local_profile_runtime.py -q` | pass | recovery-required runtime cycle: 5 passed |
| `uv run pytest tests/unit/test_exp_local_identity.py tests/unit/test_exp_local_profile_runtime.py tests/unit/test_gamepad_transport_factory.py tests/unit/test_public_api_boundary.py tests/unit/test_exp_local_address.py -q` | pass | recovery-required surrounding regression: 68 passed |
| `uv run ruff check src/swbt/errors.py src/swbt/__init__.py src/swbt/transport/_exp_local_identity.py src/swbt/gamepad/transport_factory.py src/swbt/gamepad/runtime.py tests/unit/test_exp_local_identity.py tests/unit/test_exp_local_profile_runtime.py` | pass | recovery-required runtime cycle |
| `uv run ty check --no-progress` | pass | recovery-required runtime cycle |
| `uv run pytest tests/unit/test_bumble_transport.py tests/unit/test_exp_local_profile_runtime.py tests/unit/test_gamepad_transport_factory.py -q` | pass | Bumble power-on guard cycle: 51 passed |
| `uv run ruff check src/swbt/transport/bumble.py tests/unit/test_bumble_transport.py tests/unit/test_exp_local_profile_runtime.py` | pass | Bumble power-on guard cycle |
| `uv run ty check --no-progress` | pass | Bumble power-on guard cycle |
| `uv run pytest tests/integration/test_exp_local_profile.py tests/unit/test_exp_local_profile_runtime.py tests/unit/test_gamepad_transport_factory.py tests/unit/test_bumble_transport.py -q` | pass | profile key-store cycle: 53 passed |
| `uv run ruff check src/swbt/transport/_exp_local_address.py src/swbt/transport/_bumble_key_store.py src/swbt/transport/bumble.py src/swbt/gamepad/runtime.py src/swbt/gamepad/transport_factory.py tests/unit/test_exp_local_profile_runtime.py tests/unit/test_bumble_transport.py tests/integration/test_exp_local_profile.py` | pass | profile key-store cycle |
| `uv run ty check --no-progress` | pass | profile key-store cycle |
| `git diff --check` | pass | profile key-store cycle |
| `uv run pytest -p no:cacheprovider --basetemp <temp> tests/integration/test_exp_local_profile.py tests/unit/test_public_api_boundary.py tests/unit/test_exp_local_address.py -q` | pass | pairing retry cycle: 61 passed。repo 内 pytest temp の権限不整合を避けるため OS temp を指定 |
| `uv run ruff check src/swbt/gamepad/core.py tests/integration/test_exp_local_profile.py` | pass | pairing retry cycle |
| `uv run ty check --no-progress` | pass | pairing retry cycle |
| `git diff --check` | pass | pairing retry cycle |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for completion |
| 承認範囲 | USB adapter open、CSR volatile write、warm reset、Bumble HID advertising、Switch pairing / reconnect、neutral report、close。実行時に command ごとに明示承認を得る |
| adapter | 専用 `usb:0` / CSR8510 A10 / `0a12:0001` / WinUSB。実行直前に再確認する |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md` に OS、driver、dongle、Python、Bumble、Switch model / firmware、command、result、trace、cleanup を記録する |
| cleanup | `close()` 後の target 保持を許容する。USB dongle の抜き差しと内部 read-only probe は利用者が必要と判断した場合だけ実行する |

## 13. 先送り事項

- Joy-Con、Direct controller、複数 controller への exp profile 展開は、本 unit の ProController 実機 gate 後に別 unit で扱う。
- CSR8510 A10 以外の adapter 対応は、chipset ごとの根拠と実機観測なしに追加しない。
- factory / baseline address の永続化と公開 recovery probe は、必要性が生じた場合に別 Issue として扱う。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [ ] 実装と unit / integration gate を完了した
- [ ] 明示承認下の手動実機 gate を完了した
- [ ] 初期設計と公開文書の Intent Delta を反映した
- [ ] 検証結果または未実行理由を更新した