---
name: tdd-test-list
description: "swbt-python の仕様、roadmap、use case から振る舞いベースの TDD Test List を作成または更新する skill。ユーザがテストリスト、TDD item、red/green/refactor の候補、M0/M1 などの milestone を TDD に落とす依頼をしたとき、または spec/wip の TDD Test List を扱うときに使う。"
---

# TDD Test List

実装前に、観測可能な振る舞いを小さい test item に分ける。

## Input

- `AGENTS.md`
- 関連する `spec/initial/*.md`
- 対象の `spec/wip/unit_XXX/FEATURE_NAME.md`
- 既存 test と実装状態

## Rules

- item は外部から観測できる入力、状態、期待結果で書く。
- 実装順、file list、内部 helper 名だけを item にしない。
- protocol core と fake transport は、Bumble や実機なしで先に固定する。
- Bumble adapter と Switch 実機が必要な item は `hardware=yes` にし、`hardware-harness` の承認条件へつなぐ。
- 新しく見つけた振る舞いは、今の red/green に混ぜず list へ追加する。

## Item Table

```markdown
| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo |  | new / regression / edge / characterization | unit / integration / bumble / hardware | no / yes |  |
```

status:

- `todo`
- `red`
- `green`
- `refactor-done`
- `refactor-skipped`
- `deferred`

## Priority

1. `spec/initial/roadmap.md` の milestone 順を尊重する。
2. M0 protocol core と M1 fake transport を優先する。
3. 未監査の byte layout や subcommand は `source-audit` を先に通す。
4. 実機依存 item は local automated item が尽きるまで後段に置く。ただし adapter bring-up 自体が目的の milestone では `hardware-harness` を使って扱う。
