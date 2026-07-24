# transport Protocol 前提の防御分岐整理

## 概要

`HidDeviceTransport` が必須とする `local_bluetooth_address()` を runtime が直接利用し、default transport と Bumble constructor の重複分岐を削除する。

## 起点

| source | 内容 |
|---|---|
| GitHub Issue #132 | 内部 Protocol 準拠を前提に防御分岐を削減する |
| `src/swbt/transport/base.py` | address method を必須 member として定義する |

## 対象範囲

- runtime の address member 存在確認を直接呼出しへ置換する。
- runtime と factory の default transport constructor call を各1経路にする。
- test fake を内部 Protocol と constructor 契約へ合わせる。

## 対象外

- Bumble object の version 差を吸収する動的処理、Protocol の公開 export、expected address validation、Bumble dependency、実機操作の変更。

## 根拠監査

| 項目 | 状態 | 根拠 |
|---|---|---|
| internal transport Protocol | done | `HidDeviceTransport`、Fake、Bumble 実装と test fake を照合した |
| Device Info address | implementation fact | 既存 source-audit fixture と address integration test を維持した |
| Bumble / adapter / hardware | not applicable | constructor 引数と lifecycle を変えず、実機操作しない |

## TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | Fake transport の address を Device Info に反映する | characterization | integration | no | existing address test を維持した |
| refactor-done | default transport が profile 各 variant の引数で1経路から作られる | regression | unit / integration | no | constructor contract を test fake へ反映した |
| refactor-done | public import が Bumble を解決しない | regression | unit | no | full unit gate で確認した |

この unit は既存契約を変えない構造変更である。既存 test を characterization baseline とし、Protocol を満たさない test fake は production fallback を増やさず修正した。

## 実機実行条件

not required。adapter、Bumble open、pairing、advertising は実行しない。

## 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_gamepad_transport_factory.py tests/unit/test_public_api_boundary.py -q` | pass | 31 passed |
| `uv run pytest tests/integration/test_switch_gamepad_fake_transport.py -q -k "bluetooth_address or profile_path"` | pass | 3 passed |
| `uv run ruff format --check .` | pass | 103 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit` | pass | 440 passed |
| `uv run pytest tests/integration` | pass | 154 passed |
| `git diff --check` | pass | whitespace error なし |

## 先送り事項

- none
