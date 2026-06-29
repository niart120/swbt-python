---
name: test-desiderata-review
description: "swbt-python のテスト設計を Kent Beck の Test Desiderata 観点で見直す skill。protocol byte fixture、fake transport integration、Bumble adapter test、hardware test、flaky risk、assertion 粒度、単体テストと実機テストの分担に迷うときに使う。"
---

# Test Desiderata Review

テストの価値と trade-off を明示する。すべての性質を同時に最大化しようとしない。

## 観点

- isolated: 実機、Bumble、OS driver に依存しないか。
- deterministic: clock、scheduler、adapter state に左右されないか。
- fast: 通常 gate に入れられる速さか。
- precise: 失敗時に protocol、state、transport のどこが悪いか分かるか。
- representative: Switch-facing behavior を十分に表しているか。
- maintainable: fixture が report layout の意味を読ませているか。

## swbt-python 方針

- M0/M1 は unit / fake transport integration を厚くする。
- report bytes は fixture と意味の両方で確認する。
- 実時間に依存する `ReportLoop` は fake clock を優先する。
- Bumble adapter tests は CI 必須にしない。
- Hardware tests は承認制にし、trace と cleanup を重視する。
- 実機でしか分からない項目を unit test で証明したように書かない。

## Output

```markdown
### Test Desiderata Review

| test | value | trade-off | decision |
|---|---|---|---|

### Gaps

- ...
```
