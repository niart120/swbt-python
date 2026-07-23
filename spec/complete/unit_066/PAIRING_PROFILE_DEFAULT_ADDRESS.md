# pairing profile の adapter 既定アドレス対応 仕様書

## 1. 概要

### 1.1 目的

pairing key を永続化する `profile_path` と、利用者管理のローカル Bluetooth アドレスを分離可能にする。`create_profile(local_address=None)` では adapter identity の volatile 書き込みを行わず、Bumble の `power_on()` 後に adapter が報告した current default address を key-store namespace として使う。

これにより、専用のローカルアドレスを必要としない通常の adapter identity でも pairing profile と再接続を利用できるようにする。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | pairing profile の `local_address` に `None` を許容し、volatile 領域へ書き込まず adapter の既定値を使う | conversation, 2026-07-23 |
| pairing profile の既存契約 | 利用者管理のローカルアドレス、pairing key namespace、volatile identity preparation | `spec/complete/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md` |
| 公開 API の正本 | `create_profile()`、`profile_path`、pairing / reconnect lifecycle | `spec/initial/api.md` |
| transport の正本 | Bumble device、key store、local BD_ADDR の境界 | `spec/initial/transport-bumble.md` |
| Bumble 0.0.230 source fact | `Device.power_on()` は HCI Read BD_ADDR の結果を `public_address` に設定してから、未設定の key store を生成する | `.venv/Lib/site-packages/bumble/device.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| 通常の profile 利用者 | 新規 `profile_path`、`local_address=None` | volatile address を書き込まず、adapter が報告したアドレスで pairing key を保存する | adapter open、pairing、advertising は従来どおり明示操作で開始する |
| profile 再利用者 | `local_address=None` の既存 profile、同じ current default address | 保存済み namespace から bond を読み、active reconnect を試行できる | unit_066 の実機 gate で fresh pairing と続く reconnect を確認する |
| local identity 利用者 | 新規または既存の explicit `local_address` profile | 従来どおり volatile preparation と power-on guard を行う | 既存 profile との互換性を維持する |
| adapter address が変わった利用者 | `local_address=None` profile、前回と異なる current default address | 新しい address の namespace を選び、以前の namespace を暗黙移行しない | 給電断前の volatile 値も current default になり得る |

## 2. 対象範囲

- `PairingProfile.local_address` の `None` 対応と profile envelope の adapter-default identity variant。
- 全 concrete controller の `create_profile(local_address=None)` 公開経路。
- runtime での adapter identity preparation 省略と、profile path の transport への引き渡し。
- Bumble `power_on()` 後の current default address を使う遅延 key-store namespace 解決。
- adapter-default profile で public address が取得できない場合の advertising / active reconnect 前ガード。
- explicit local address profile の既存 validation、volatile preparation、power-on guard の回帰維持。
- unit / integration / hardware test、関連する初期設計文書、公開 API 文書の更新。

## 3. 対象外

- factory / baseline address の読出し、保存、復旧。
- adapter address の自動生成、重複回避、永続書き込み。
- adapter default address が変わった場合の pairing key namespace 自動移行または削除。
- profile schema の旧実装への forward compatibility 保証。
- `profile_path=None` の一時 controller 経路の変更。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/complete/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md`
- `spec/complete/unit_058/MULTI_ADDRESS_RECONNECT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | HID report layout と subcommand を変更しない |
| Bumble / transport | required | done for source | Bumble 0.0.230 `Device.power_on()` は HCI Read BD_ADDR 後に key store を生成する。profile 用 key store は non-`None` の proxy として先に設定し、最初の key-store operation で更新済み `public_address` を namespace に解決できる |
| OS / driver / adapter | required | done for one hardware configuration | current default address の取得は Bumble の HCI Read BD_ADDR に依存する。Windows 11 / CSR8510 A10 / WinUSB / Bumble 0.0.230 の `usb:0` で fresh pairing と active reconnect を確認した。別 adapter / OS は未検証 |
| profile representation | required | implementation fact | 既存 schema version 1 は `identity.kind="exp-local-address"` と address を持つ。新 variant は `identity.kind="adapter-default"` とし address を保存しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| adapter-default profile 作成 | 未存在 path、`local_address=None` | controller kind、adapter-default identity、空 namespace map を atomic に保存する | path は上書きしない |
| adapter preparation | adapter-default profile を open | profile validation と controller kind guard は行うが、raw CSR session と volatile write を開始しない | preparation diagnostics event も記録しない |
| transport 作成 | adapter-default profile の validation 後 | `profile_path` を Bumble transport へ渡し、expected local address は `None` にする | profile なしの経路とは異なり key store は永続化する |
| namespace 解決 | Bumble `power_on()` 後、adapter が有効な public address を報告 | その uppercase address を current namespace として profile key store を読み書きする | factory address であることは要求・主張しない |
| namespace 未確定 | `power_on()` 後も public address が未取得または zero | `InvalidKeyStoreError` とし、connectable / discoverable の有効化や active reconnect を開始しない | `__DEFAULT__` や zero address へ保存しない |
| default address 変更 | 同じ profile を別の current default address で開く | 新 address の current / previous namespace を使用し、既存 namespace は保持する | 自動 migration なし |
| explicit local address | 有効な `local_address` | 既存 envelope、volatile preparation、expected-address guard、固定 namespace を維持する | 既存 profile 読込を含む |
| profile なし | `profile_path=None` | 永続 key store を持たない一時 controller のまま | 既存通常経路を変更しない |

### 6.1 adapter-default profile envelope

```json
{
  "format": "swbt.profile",
  "schema_version": 1,
  "identity": {
    "kind": "adapter-default"
  },
  "controller_kind": "pro",
  "key_store": {
    "namespaces": {}
  }
}
```

`adapter-default` は factory address を意味しない。Bumble `power_on()` 後に HCI controller が報告した current public address を使用する。以前の volatile write が給電断まで残っている場合、その値が選ばれることがある。

### 6.2 API

```python
pad = await ProController.create_profile(
    adapter="usb:0",
    profile_path="profiles/switch-pro.json",
    local_address=None,
    pair_timeout=60.0,
)
```

`local_address` の既定値も `None` とし、省略時は adapter-default profile を作成する。明示的な文字列を渡した場合だけ利用者管理のローカルアドレスを検査し、volatile preparation を行う。

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-skipped | `local_address=None` で adapter-default profile envelope を作成・再読込できる | new | unit | no | schema 1 の tagged identity variant と empty namespaces。codec の責務が閉じており追加整理なし |
| refactor-skipped | adapter-default profile の open は volatile identity preparation を呼ばず profile path を transport へ渡す | new | unit | no | expected local address は `None`。既存 runtime 分岐への最小追加 |
| refactor-done | adapter-default profile key store は `power_on()` 後の device public address を namespace として更新・再読込できる | new | unit / integration | no | namespace resolver を key-store operation 時に評価し、address 変更時は旧 namespace を保持 |
| refactor-skipped | public address 未確定時は profile key store が fail closed になる | edge | unit | no | zero / unavailable を保存しない。resolver の単一 guard で完結 |
| refactor-skipped | adapter-default profile は public address 未確定時に advertising / active reconnect の前で fail closed になる | edge | unit | no | profile なし経路は変更せず、profile path と expected address の組み合わせだけで availability guard を有効化 |
| refactor-skipped | 全 concrete controller の `create_profile()` は `local_address` 省略または `None` を受理し、pairing retry 用 profile を残す | new | integration | no | Pro / Joy-Con L/R、Periodic / Direct の6 classで確認 |
| refactor-skipped | explicit local address profile の codec、preparation、guard、key-store namespace を維持する | regression | unit / integration | no | unit 467件、integration 137件で既存経路を確認 |
| observed-pass | adapter-default profile で fresh pairing と active reconnect が成功する | characterization | hardware | yes | fresh `1 passed in 2.98s`、reconnect `1 passed in 4.52s`。同じ current address namespace、profile bytes 不変、reconnect 時の advertising / pairing / key update なし |

## 8. 文書検証計画

README、公開 API / usage / hardware / release notes と初期設計の正本を更新する。自然言語の固定語句 assertion は追加せず、実装、Bumble source、既存 hardware log と照合する。

| document | audience / task | source of truth | mechanical check | review result | unresolved |
|---|---|---|---|---|---|
| `README.md`, `docs/api.md`, `docs/usage.md` | profile 作成者が adapter-default と explicit address を選ぶ | 公開 signature、本仕様 §6 | `mkdocs build --strict` | done | `InvalidKeyStoreError` の public-address 未取得条件を追記し、未解決 must-fix なし |
| `docs/hardware.md`, `docs/release-notes.md` | 揮発書換、安全境界、確認済み / 未検証範囲を確認する | 実装、本仕様 §5-6、`spec/hardware-test-log.md` | `mkdocs build --strict` | done | fresh close の neutral report 未確認と、別環境の未検証範囲を明記 |
| `spec/initial/api.md` | profile 作成者が `None` と explicit address を選ぶ | 本仕様 §6 | `mkdocs build --strict` | done | none |
| `spec/initial/transport-bumble.md` | adapter preparation と namespace 解決順序 | Bumble 0.0.230 source、本仕様 §5-6、unit_066 hardware trace | `mkdocs build --strict` | done | 別 adapter / OS、給電断後の address 変更、Joy-Con は未検証 |
| `spec/initial/lifecycle.md`, `spec/initial/risks.md` | open / power-on / close と address 変更リスク | 本仕様 §6 | `mkdocs build --strict` | done | none |

## 9. 設計メモ

- `PairingProfile.local_address` は `LocalAddress | None` とする。`None` は identity 不在ではなく adapter-default identity variant を表す。
- profile 用 key store は Bumble `Device.power_on()` より前に device へ設定する。namespace は固定文字列または device public address の resolver とし、key-store operation の時点で解決する。これにより Bumble が profile key store を `MemoryKeyStore` へ置き換えることを防ぐ。
- adapter-default profile の namespace guard は、任意 namespace を無条件に許すのではなく、resolver が返した現在の device public address と profile operation の namespace を一致させる。
- `profile_path=None` と `profile.local_address=None` は別の状態である。前者は永続 storage なし、後者は adapter-default address に紐づく永続 storage あり。
- schema version は 1 を維持し、identity を tagged variant として拡張する。既存 `exp-local-address` profile は同じ payload と挙動を維持する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/transport/_pairing_profile.py` | modify | adapter-default identity variant、optional local address、codec |
| `src/swbt/transport/_bumble_key_store.py` | modify | device public address の遅延 namespace 解決 |
| `src/swbt/transport/bumble.py` | modify | profile identity に応じた key-store namespace 構成 |
| `src/swbt/gamepad/runtime.py` | modify | `None` profile の identity preparation 省略 |
| `src/swbt/gamepad/core.py` | modify | 全 concrete controller の optional `local_address` API |
| `tests/unit/test_pairing_profile.py` | modify | adapter-default codec |
| `tests/unit/test_pairing_profile_runtime.py` | modify | preparation 省略と transport handoff |
| `tests/unit/test_bumble_transport.py` | modify | 遅延 namespace 解決と fail-closed |
| `tests/integration/test_pairing_profile.py` | modify | profile 作成 / retry、key generation |
| `tests/hardware/test_pairing_profile.py` | modify | adapter-default fresh pairing / active reconnect |
| `spec/initial/api.md` | modify | optional local address contract |
| `spec/initial/transport-bumble.md` | modify | current default address と key-store sequence |
| `spec/initial/lifecycle.md` | modify | adapter-default profile の open / close |
| `spec/initial/risks.md` | modify | current address 変更と namespace 選択リスク |
| `README.md`, `docs/api.md`, `docs/usage.md` | modify | adapter-default を通常の profile 作成経路として説明 |
| `docs/hardware.md`, `docs/release-notes.md` | modify | explicit-address の揮発書換と adapter-default の未検証範囲を分離 |
| `docs/agent-brief.md` | modify | agent 向け profile 作成例と安全境界を同期 |
| `spec/hardware-test-log.md` | modify | unit_066 実機条件、結果、artifact、cleanup |

## 11. 検証

| command | result | notes |
|---|---|---|
| profile codec targeted test | red, expected -> pass | 既存 codec は `None` を文字列 address として保存して再読込に失敗。adapter-default variant 実装後に pass |
| runtime handoff targeted test | red, expected -> pass | 既存 runtime は `target=None` で identity preparation を呼んだ。省略実装後に pass |
| Bumble namespace targeted test | red, expected -> pass | 既存 key store は namespace `"None"` へ保存。遅延 resolver 実装後に pass |
| advertising guard targeted test | red, expected -> pass | 既存実装は public address が `None` でも visibility を有効化。availability guard 実装後は `InvalidKeyStoreError` となり connectable / discoverable は未変更 |
| `uv run pytest tests/unit/test_bumble_transport.py -q` | pass | 37 passed。adapter-default の advertising / active reconnect 前ガードを含む |
| adapter-default hardware tests `--collect-only` | pass | fresh pairing と active reconnect の 2 node を収集。adapter は開いていない |
| `uv run swbt-probe adapters --json` | pass, no-open | `usb:0`、CSR8510 A10、VID:PID `0A12:0001`、bus 6、device 91、port 9.1。Bumble transport は開いていない |
| `uv sync --dev` | pass | 53 packages resolved、41 packages checked |
| `uv run ruff format --check .` | pass | 99 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 467 passed |
| `uv run pytest tests/integration` | pass | 137 passed |
| `uv sync --dev --group docs` | pass | docs dependencies installed |
| `uv run mkdocs build --strict` | pass | strict build completed |
| `git diff --check` | pass | whitespace error なし |
| `uv run pytest tests/hardware/test_pairing_profile.py::test_switch_adapter_default_profile_fresh_pairing_and_close ...` | hardware-pass | `1 passed in 2.98s`。current address `0E:08:71:C0:B4:5C` の namespace に fresh key を保存し、identity preparation なしで pairing / connected / transport close |
| `uv run pytest tests/hardware/test_pairing_profile.py::test_switch_adapter_default_profile_reuses_address_after_normal_close ...` | hardware-pass | `1 passed in 4.52s`。profile bytes 不変、active reconnect connected、identity preparation / advertising / pairing / key update なし、transport close |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required for adapter-default fresh pairing / active reconnect characterization |
| 承認範囲 | approved and executed。下記 2 command、`usb:0`、Switch-facing pairing / reconnect / neutral report loop、cleanup |
| adapter | no-open 列挙時の `usb:0`: CSR8510 A10、VID:PID `0A12:0001`、bus 6 / device 91 / port 9.1、Bumble 0.0.230、Windows 11、Python 3.13.5 |
| fresh pairing command | `uv run pytest tests/hardware/test_pairing_profile.py::test_switch_adapter_default_profile_fresh_pairing_and_close -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build/hardware/unit_066/adapter-default-20260723 --log-file build/hardware/unit_066/adapter-default-20260723/fresh-pairing-pytest-debug.log --log-file-level=DEBUG -q -s` |
| active reconnect command | `uv run pytest tests/hardware/test_pairing_profile.py::test_switch_adapter_default_profile_reuses_address_after_normal_close -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build/hardware/unit_066/adapter-default-20260723 --log-file build/hardware/unit_066/adapter-default-20260723/reconnect-pytest-debug.log --log-file-level=DEBUG -q -s` |
| Switch-facing scope | fresh: 持ちかた/順番を変える画面で Classic HID pairing、neutral periodic report。reconnect: HOME / 通常画面で保存 bond への active reconnect、neutral periodic report。non-neutral input は送らない |
| log / artifact | `build/hardware/unit_066/adapter-default-20260723` と `spec/hardware-test-log.md` |
| cleanup | 各 test の `finally` で `close(neutral=True)` を実行し、connection / advertising を停止して adapter を解放する。失敗時も同じ cleanup を行う |
| 結果 | fresh / reconnect とも pass。両 trace に `transport_close_complete`。fresh close は `ClosedError: Bumble interrupt channel is not connected` を1件記録したため、終了時 neutral report の到達は未確認。non-neutral input は未送信 |

## 13. 先送り事項

- fresh pairing の `close(neutral=True)` では interrupt channel 未接続の `ClosedError` を記録した。transport close と adapter 解放は完了し、non-neutral input は送っていない。終了時 neutral report の到達確認は、close lifecycle を扱う後続作業の source とする。
- adapter-default profile の別 adapter / OS、給電断後に current address が変わる場合、Joy-Con、Direct / Periodic 間の profile 再利用は未検証。
- schema version 2 への移行は、identity variant 以外の非互換変更が必要になった時点で別 unit として扱う。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を作成した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 実装と local gate を完了した
- [x] 初期設計と公開文書へ Intent Delta を反映した
- [x] 承認範囲内で hardware gate を実行し、結果と cleanup を記録した
