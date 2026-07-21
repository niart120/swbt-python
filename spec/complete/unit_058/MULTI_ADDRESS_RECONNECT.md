# 複数 BD_ADDR 登録の往復再接続

## 1. 概要

### 1.1 目的

二つの locally administered address と pairing profile を Switch に登録した後、A→B→A→B を再ペアリングなしで実行し、登録が BD_ADDR 単位で分離されるかを実機確認する。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub issue #88 | 複数 BD_ADDR 登録の往復再接続 | https://github.com/niart120/swbt-python/issues/88 |
| unit_052 | 単一 profile の pairing と active reconnect は確認済み | `spec/complete/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md` |

## 2. 対象範囲

- 専用 CSR8510 A10 adapter の volatile address A/B 切替。
- A/B それぞれの fresh profile pairing。
- profile A/B を A→B→A→B の順で active reconnect。
- pairing / advertising / key-store update が reconnect 時に発生しないことの trace 確認。
- Switch UI 上で両登録が残ることの利用者目視確認。

## 3. 対象外

- CSR persistent write。
- 正規 EUI-48 の取得や重複回避の保証。
- Switch 画面から BD_ADDR を直接読み取ること。

## 4. 関連 docs

- `spec/complete/unit_051/CSR_BD_ADDR_REWRITE_EXPERIMENT.md`
- `spec/complete/unit_052/EXP_LOCAL_ADDRESS_PROFILE.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 入力値ではなく pairing / reconnect の identity を確認する |
| Bumble / transport | required | done | unit_052 の profile-aware transport と address guard を使用する |
| OS / driver / adapter | required | done | Windows 11、専用 `usb:0`、CSR8510 A10、WinUSB、Bumble 0.0.230 を実機ログへ記録した |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| A/B を登録する | fresh profile A、fresh profile B | 両方が Switch に登録される | UI の確認は手動記録 |
| A/B を往復再接続する | 保存済み profile、A→B→A→B | 各回 connected、pairing fallback なし | profile bytes 不変 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | A/B を fresh pairing し、A→B→A→B を active reconnect する | characterization | hardware | yes | `tests/hardware/test_multi_address_reconnect.py` |

## 8. 文書検証計画

not applicable。公開文書は変更しない。

## 9. 設計メモ

現行 unit_052 の単一 profile test を再利用し、二つ目の address は `--swbt-local-address-b` で明示する。実機テストは同一 artifact directory 内で A/B の profile と各 trace を保持する。

## 10. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `tests/conftest.py` | modify | B 用 address option / fixture |
| `tests/hardware/test_multi_address_reconnect.py` | new | A/B 往復 hardware gate |
| `spec/complete/unit_058/MULTI_ADDRESS_RECONNECT.md` | new | Issue #88 完了仕様 |
| `spec/hardware-test-log.md` | modify | 実機結果 |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run ruff format --check tests/conftest.py tests/hardware/test_multi_address_reconnect.py` | pass | 2 files already formatted |
| `uv run ruff check tests/conftest.py tests/hardware/test_multi_address_reconnect.py` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| hardware pytest command | pass | `1 passed, 1 warning in 22.71s`。A/B pairing と A→B→A→B reconnect、profile bytes 不変、reconnect 時の pairing / advertising / key-store update なしを確認 |
| observation-window hardware pytest | pass | `1 passed in 18.06s`。A、B を各1回 reconnect し、各5秒待機後に neutral close。profile bytes 不変、pairing / advertising / key-store update なし |
| post-run read-only probe | pass | 通常 close / HCI Reset 後は B address が保持されたが、physical power cycle 後は元 address へ復帰 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | required |
| 承認範囲 | 専用 adapter open、CSR volatile write、warm reset、HID advertising、A/B pairing、A→B→A→B reconnect、neutral close |
| adapter | `usb:0` / CSR8510 A10 / WinUSB。実行直前に確認 |
| log / artifact | `tmp/hardware/unit_058/issue-88-round-trip` と `spec/hardware-test-log.md` |
| cleanup | 各 session は neutral close。最後に dongle 抜き差しと read-only probe で元 address を確認 |

## 13. 先送り事項

- Switch UI から A/B の BD_ADDR を直接識別する手段は未確定。ただし今回の UI 目視では A/B 両登録と接続成功を確認した。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果を記録した
