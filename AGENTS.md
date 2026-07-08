# swbt-python Agent Guide

## 対話

- ユーザとの対話は日本語で行う。
- 技術文書と回答は事実ベースで簡潔に書く。
- 事実、仮説、提案、未検証事項を分けて扱う。
- 実機未検証、Bumble の挙動未確認、Bluetooth adapter や Switch firmware に依存する観測は明示する。

## プロジェクト概要

`swbt-python` は、Python から Nintendo Switch 向けの仮想入力デバイスを扱うためのライブラリである。

主な前提は次の通り。

| 種別 | 名称 |
|---|---|
| 公開 package | `swbt-python` |
| Python module root | `swbt` |
| 主要公開 class | `SwitchGamepad` |
| 主な利用面 | Python object API |

初期設計の正本は `spec/initial/` に置く。実装や仕様を変更する場合は、関連する設計文書との整合を確認する。

## 初期対象

- 単一の仮想 Switch 入力デバイス。
- Pro Controller 相当の HID report。
- button、stick、neutral 入力。
- Switch からの主要 subcommand への応答。
- fake transport を使う実機なしの protocol / API 検証。
- Bumble を使う Bluetooth Classic HID Device transport。
- 実機接続時の diagnostics と trace。

初期対象外:

- 常駐 daemon の再実装。
- 既存 JSON Lines IPC の完全互換。
- 複数 controller 同時接続。
- amiibo、NFC、IR camera の意味的実装。
- 高水準 rumble API。
- GUI。
- Switch 以外の host 対応。

## アーキテクチャ境界

- Public API は `SwitchGamepad` に集約する。
- 入力状態は immutable な `InputState` として扱う。
- periodic report 送信は `ReportLoop` が担当する。
- Switch HID report の生成と parse は protocol 層が担当する。
- Bumble 依存は `swbt.transport.bumble` に閉じ込める。
- protocol core は Bumble、Bluetooth adapter、Switch 実機なしで単体テストできるようにする。
- public API に Bumble の object 型や callback 型を露出しない。

参照すべき設計文書:

- `spec/initial/README.md`
- `spec/initial/architecture.md`
- `spec/initial/api.md`
- `spec/initial/protocol.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/roadmap.md`
- `spec/initial/risks.md`
- `spec/initial/naming.md`

## Spec / Work Tracking

この repo は `spec/wip` 型を基本にしつつ、作業単位、根拠監査、TDD 状態、実機条件を仕様書内で追跡する。

| 目的 | path |
|---|---|
| 着手中の作業仕様 | `spec/wip/unit_XXX/FEATURE_NAME.md` |
| 完了した作業仕様 | `spec/complete/unit_XXX/FEATURE_NAME.md` |
| 小さな観測と先送り判断 | `spec/dev-journal.md` |
| 実機観測 | `spec/hardware-test-log.md` |
| 初期設計 | `spec/initial/` |

作業仕様には、対象範囲、対象外、関連 docs、根拠監査、TDD Test List、検証、実機実行条件、先送り事項、チェックリストを含める。

複数の作業仕様から参照する安定した判断は、既存の `spec/initial/` を更新するか、必要に応じて `spec/` 配下へ分ける。未確定の観測は `spec/dev-journal.md` に置く。

## Agent Skills

repo-local skill は `.agents/skills` を正本として管理する。`.github/skills` には重複配置しない。

主な skill:

- `agentic-sdd`: `spec/initial` と `spec/wip` から次の作業単位を選び、plan、実装、gate へ進める。
- `agentic-self-review`: 仕様変更、実装、PR 前に gate 結果と未検証リスクを整理する。
- `spec-format`: `spec/wip` / `spec/complete` の作業仕様を作成、更新、完了移動する。
- `dev-journal`: 小さい設計観測や先送り事項を `spec/dev-journal.md` に記録する。
- `docs-wording`: README、docs、release notes の文言整理で、swbt-python 固有の訳語と残す英語表記をそろえる。
- `source-audit`: Switch HID、Bumble、既存実装、実機ログ由来の値を根拠分類して記録する。
- `hardware-harness`: Bumble adapter、Bluetooth dongle、Switch 実機を使う検証の承認境界と記録項目を確認する。
- `tdd-workflow`: TDD Test List から red / green / refactor を進める。
- `tdd-test-list`: 振る舞いベースの TDD Test List を作成、更新する。
- `tdd-one-cycle`: TDD Test List の 1 項目だけを red / green / refactor で進める。
- `refactor-after-green`: green 後に観測可能な振る舞いを変えず構造を整える。
- `tidy-first`: 振る舞い変更と構造変更を分ける。
- `test-desiderata-review`: Test Desiderata に基づきテスト価値と trade-off を確認する。
- `pr-merge-cleanup`: remote 設定後に PR 作成、merge、default branch 同期、branch cleanup を行う。
- `pypi-release`: PyPI / TestPyPI 公開、version bump、release PR、publish workflow、公開後 smoke check を扱う。publish workflow / runbook が未整備の場合は release 実行前に停止する。

## Python

- Python 実行と依存管理は `uv` 経由に統一する。
- Python script は `python ...` ではなく `uv run python ...` で実行する。
- 依存追加は `uv add <package>`、開発依存は `uv add --dev <package>` を使う。
- 型注釈は Python 3.12+ の構文を使う。
- ランタイムに不要な型 import は `if TYPE_CHECKING:` に置く。
- `from __future__ import annotations` は、実行時評価を遅延する必要がある場合だけ使う。

## テストと検証

標準 gate は次を基本にする。

```console
uv sync --dev
uv run ruff format --check .
uv run ruff check .
uv run ty check --no-progress
uv run pytest tests/unit
```

対象となる integration test tree がある変更では、`uv run pytest tests/integration` も実行する。対象 tree がまだない場合、該当 gate は未実行理由を報告する。

pytest marker:

- `@pytest.mark.bumble`: USB Bluetooth dongle と Bumble adapter open が必要な検証。
- `@pytest.mark.hardware`: Nintendo Switch 実機、pairing、HID advertising、report loop が必要な検証。

CI で必須にする対象は、static type check、lint、unit tests、fake transport integration tests とする。Bumble adapter tests と hardware tests は CI 必須にしない。

## 実機安全境界

次は人間の明示承認なしに実行しない。

- USB Bluetooth dongle を Bumble から開く処理。
- Switch pairing。
- HID Device advertising。
- periodic input report loop。
- Switch-facing output report / subcommand handling。
- `bumble` または `hardware` marker のテスト。

実機または dongle を使う command について、環境変数による実行遮断は採用しない。承認境界は、会話上の明示承認、対象 adapter、実行する command、Switch-facing 動作の範囲、cleanup plan を確認することで管理する。

実機観測には OS、driver、dongle identity、adapter string、Bumble version、Python version、Switch model / firmware、command、result、cleanup を記録する。

## 根拠監査

次を追加または変更する前に `source-audit` を使う。

- HID descriptor bytes。
- input / output report ID と byte layout。
- button bit、stick packing、IMU frame。
- subcommand ID と reply payload。
- SPI flash address と返却 data。
- rumble packet layout。
- report period の default。
- Bumble HID Device / SDP / L2CAP に関する仮定。
- WinUSB / libusb / OS driver に関する仮定。

根拠は、source fact、implementation fact、hardware observation、inference、unverified hypothesis に分ける。

## Git / PR

- 変更を伴う作業では開始時に branch と `git status --short` を確認する。
- default branch への直接 commit は、ユーザの明示指示がある場合を除き避ける。
- Conventional Commits に準拠する。

```text
<type>(<scope>): <subject>
```

type は `feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `build` / `ci` / `chore` / `revert` を使う。subject は日本語で記述し、末尾句点は付けない。
