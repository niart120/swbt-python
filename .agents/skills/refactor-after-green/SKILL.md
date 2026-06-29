---
name: refactor-after-green
description: "swbt-python の TDD green 後に、観測可能な振る舞いを変えずに小さな構造変更を行う skill。red/green 後の refactor phase、protocol builder/parser、state store、report loop、transport boundary、test fixture の重複整理や命名改善、refactor-done / refactor-skipped 判断で使う。"
---

# Refactor After Green

green になった item の振る舞いを保ったまま構造を整える。

## Preconditions

- green baseline の command と結果が分かっている。
- 対象 item が 1 つに絞られている。
- 観測可能な振る舞いを変えない。
- behavior change と structure change の分類に迷う場合は `tidy-first` を使う。

## Review Points

- 同じ byte packing、parse 分岐、fixture setup が重複していないか。
- test 名、関数名、変数名が確定した振る舞いを表しているか。
- protocol、state store、report loop、transport、diagnostics の責務が混ざっていないか。
- Bumble import が transport 層外へ漏れていないか。
- test が実装構造ではなく観測可能な振る舞いを読ませているか。
- `source-audit` や `hardware-harness` が必要な値へ触れていないか。

## Decision

- `refactor-done`: 構造変更を行い、同じ command が green。
- `refactor-skipped`: 見直したが、今の item で行う構造変更がない。
- `deferred`: 必要な整理はあるが今の cycle を超える。

## Output

```text
Refactor status:
- decision: refactor-done | refactor-skipped | deferred
- change:
- unchanged behavior:
- verification:
- notes:
```
