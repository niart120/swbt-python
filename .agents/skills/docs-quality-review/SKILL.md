---
name: docs-quality-review
description: "swbt-python の README、利用者向け docs、公開 API docstring、release notes の追加・更新・レビューで、対象読者が迷わず利用できる説明、根拠、未検証範囲、表現を確認する skill。ユーザが README、利用者向け docs、公開 API 説明、release notes の品質、読みやすさ、説明順、利用手順の見直しを依頼したとき、または公開文書を変更するときに使う。"
---

# Docs Quality Review

公開文書を、対象読者が必要な情報を見つけ、理解し、次の操作を選べる状態に整える。読みやすさ、説明順、言葉選びを主に見直し、事実性、安全境界、未検証範囲を変更できない制約として正本と照合する。

## 対象と対象外

| 対象 | 役割 | 主な正本 |
|---|---|---|
| `README.md` | 利用開始の入口と公開 docs への導線 | package metadata、公開 docs |
| `docs/index.md` | 公開 docs の入口 | `mkdocs.yml`、各公開 docs |
| `docs/api.md` と public API docstring | 公開 API 契約 | `src/swbt/__init__.py`、公開 class / method の signature |
| `docs/usage.md` | 利用者が API 操作を完了する手順 | 公開 API、例外、状態契約 |
| `docs/hardware.md` | adapter、pairing、実機確認範囲の説明 | `spec/hardware-test-log.md`、関連する初期設計 |
| `docs/release-notes.md` | 利用者への変更影響と移行 | 実装差分、公開 API、package metadata |

`docs/agent-brief.md`、`spec/`、`AGENTS.md`、skill、PR 本文は対象外とする。

## Review Rules

- 最初に対象読者と、読者が完了すべき作業を一文で定める。読者が最初に必要とする結論を先に置き、同じ説明を複数箇所へ複製しない。長い段落、曖昧な指示、説明順の飛躍、用語の揺れは改善候補にする。
- 手順では、前提、操作、成功の確認方法、失敗時の次の行動、必要なら終了後の復帰手順を確認する。文書の役割に不要な実装詳細、開発経緯、agent 運用などは公開面に残さない。
- API 名、引数、例外、状態変化、対応範囲は正本と照合する。既存の test 成功だけを文書の事実性の根拠にしない。
- 実機、OS、driver、adapter、Switch firmware に依存する説明は、確認済み条件と未検証条件を分ける。記録がない互換性を断定しない。
- 日本語の用語、残す英語表記、実機条件の表現を変更する場合は `docs-wording` を併用する。
- 自然言語の意味要件を固定語句の存在・不在 assertion に置き換えない。正しい言い換えを落とす検査、または誤った説明を通す検査は追加しない。

## Workflow

1. `git diff --name-only` と依頼内容から対象文書を列挙する。対象外だけならこの skill を使わない。
2. 文書ごとに対象読者、達成タスク、正本を決める。正本が不足する場合は推測で補わず finding にする。
3. 対象文書と正本を読み、事実性、安全境界、利用手順、説明順、読みやすさを確認する。
4. docs 変更を実装中なら、根拠がある修正必須事項と改善提案を自分で反映する。単独 review ではファイルを変更せず findings を返す。
5. 変更範囲に対応する既存の機械的検証だけを実行する。公開 docs site を変更した場合は site build を確認する。
6. 未解決の修正必須事項は、根拠とともに人間へ判断を委ねる。解決済みの改善提案と未実行検証も report に残す。

## Findings

| level | 扱い |
|---|---|
| `must-fix` | 正本との矛盾、安全な前提または復帰手順の欠落、読者が手順を完了できない欠落、未検証事項の過剰な断定。修正または人間による先送り判断が必要。 |
| `improvement` | 読みやすさ、用語、説明順、重複、見出し、導線を改善できる箇所。根拠を示し、実装中なら安全な範囲で反映する。 |

## Checks

最低限、対象ファイルを読んだうえで次を確認する。

```powershell
git diff --name-only
git diff --check
```

公開 docs site または `mkdocs.yml` を変更した場合だけ実行する。

```powershell
uv run mkdocs build --strict
```

リンク、参照先、front matter、schema などの機械的契約に対応する repo-local command がある場合は実行する。プレースホルダや特定の誤記が懸念されるときは、対象を定めた文字列検索を補助として使える。ただし、検索結果を文書品質の合否にせず、存在しない検査を文字列検索で代用しない。Bumble adapter、pairing、HID advertising、report loop はこの review のために実行しない。

## Report

```markdown
### Docs Quality Review

- audience / task:
- documents:
- sources checked:

| level | target | finding | evidence | disposition |
|---|---|---|---|---|

verification:
- command / result:
- not run:

remaining risk:
- （なし）
```
