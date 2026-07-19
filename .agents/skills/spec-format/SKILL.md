---
name: spec-format
description: "swbt-python の作業仕様を spec/wip/unit_XXX または spec/complete/unit_XXX に作成、更新、完了移動する skill。ユーザが仕様書、spec、設計書、作業仕様、TDD Test List、milestone 作業、spec/initial に基づく実装単位の整理を依頼したとき、または spec/ 配下を扱うときに使う。"
---

# 仕様書構成様式

`swbt-python` の作業仕様を `spec/wip` / `spec/complete` で管理する。仕様書は単なる設計文書ではなく、対象範囲、根拠監査、TDD 状態、実機条件、検証結果を束ねる作業単位でもある。

## 配置

| 状態 | path |
|---|---|
| 着手中 | `spec/wip/unit_XXX/FEATURE_NAME.md` |
| 完了済み | `spec/complete/unit_XXX/FEATURE_NAME.md` |

- `FEATURE_NAME.md` は UPPER_SNAKE_CASE にする。
- 連番は `spec/wip/unit_*` と `spec/complete/unit_*` を確認して次を選ぶ。
- 完了時は directory ごと `spec/complete` へ移す。
- `spec/initial/` は初期設計の正本として扱い、作業仕様の完了管理には使わない。

## テンプレート

新規作成時は `references/template.md` を読む。テンプレート内の guide comment は出力に残さない。

## 記述ルール

- source、use case、対象範囲、対象外を分ける。
- 事実、推論、未検証仮説を分ける。
- TDD Test List は観測可能な振る舞いで書く。実装ファイル名や内部構造だけを item にしない。公開文書だけの作業では `not applicable` とし、文書検証計画を使う。
- Switch HID、Bumble、report byte、driver、adapter、実機観測を含む場合は `source-audit` の要否を書く。
- Bumble adapter、Switch pairing、HID advertising、report loop を含む場合は `hardware-harness` の承認条件を書く。
- 検証には実行 command、結果、未実行理由を残す。
- 先送り事項には観測、先送り理由、後続の置き場を書く。何もなければ `none` と書く。

## Workflow

1. `AGENTS.md` と関連する `spec/initial/*.md` を読む。
2. 既存 `spec/wip` / `spec/complete` を確認する。
3. 新規か更新か完了移動かを決める。
4. 新規なら `references/template.md` を使って作成する。
5. TDD で進める作業では `tdd-test-list` と接続する。README、利用者向け docs、公開 API docstring、release notes だけの作業では `docs-quality-review` と文書検証計画へ接続する。
6. 根拠が必要な値は `source-audit` へ渡す。
7. 実機や dongle が関係する項目は `hardware-harness` の承認境界を記録する。
8. 実装後は検証結果と checklist を更新し、完了条件が揃った場合だけ `spec/complete` へ移す。

## 完了移動の条件

- checklist が更新されている。
- 検証 command と結果、または未実行理由がある。
- 公開文書を変更した場合は、文書検証計画と `docs-quality-review` の結果、または未解決事項の判断がある。
- 根拠監査の状態が `done`、`not applicable`、または未完了理由付きで明示されている。
- 実機状態が `not required`、`not run`、または承認範囲と結果付きで明示されている。
- 先送り事項が `none` か、後続 source として使える粒度になっている。
