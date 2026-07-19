---
name: agentic-self-review
description: "swbt-python の仕様変更、実装、TDD cycle、PR 前に品質 gate、未実行テスト、根拠監査、Bumble/実機未検証リスク、Subagent 指摘の採否を整理する self-review skill。作業完了前、handoff、PR 本文準備、gate 結果報告で使う。"
---

# Agentic Self Review

完了宣言ではなく、何が確認済みで何が未検証かを人間が判断できる形に圧縮する。

## Process

1. 対象の `spec/wip`、Intent Delta、non-goals を確認する。
2. diff と仕様の明示要件を照合する。
3. 実行した command、validator、test、hook を evidence として記録する。
4. 未実行 gate は `not run`、対象外は `not applicable` と書く。
5. `source-audit`、`hardware-harness`、Subagent review の有無を分ける。
6. 公開文書を変更した場合は `docs-quality-review` の対象、正本、findings、未解決事項を確認する。
7. 問題がある場合は findings を先に出す。
8. 問題がない場合も、残る test gap と実機未検証を明記する。

## Gates

| Gate | Evidence |
|---|---|
| Requirements | `AGENTS.md`、`spec/initial`、対象 spec との照合。 |
| Scope | 対象範囲、対象外、先送り事項。 |
| Source Audit | protocol / Bumble / driver 値の根拠、または該当なし。 |
| TDD / Tests | red / green 履歴、pytest 結果、未実行理由。 |
| Documentation Review | 公開文書の対象、正本、`docs-quality-review` の findings と採否。 |
| Static | ruff format、ruff check、ty check、skill validation。 |
| Hardware | 実機使用有無、承認有無、adapter identity、artifact。 |
| Integration Review | diff、scope drift、指摘の採否。 |

## Report

```markdown
## Agentic SDD Report

### Work
- spec:
- intent delta:
- non-goals:

### Findings
| severity | finding | evidence | disposition |
|---|---|---|---|

### Gates
| gate | result | evidence |
|---|---|---|

### Source / Hardware
- source audit:
- hardware used:
- approval:

### Next
- deferred:
- next candidate:
```

## Rules

- evidence が弱い項目を pass にしない。
- docs / skill のみ変更では Python test を省略できるが、skill validation と residue check は実行する。
- 公開文書を変更した場合、未解決の `must-fix` がある状態を pass としない。修正しない場合は人間の判断と理由を記録する。
- 実機 gate は承認がなければ `not run` とする。
