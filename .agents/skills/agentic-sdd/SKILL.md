---
name: agentic-sdd
description: "swbt-python の Agentic Spec-Driven Development を開始、継続する入口 skill。ユーザが Agentic SDD、次の作業単位、spec/initial からの実装、spec/wip の plan/tasks/implement/gate loop、Intent Delta、TDD と gate を含む進行を求めるときに使う。"
---

# Agentic SDD

`AGENTS.md`、`spec/initial/*.md`、対象の `spec/wip` を Constitution として読み、次の作業単位を 1 つだけ選んで進める。

## Bootstrap

1. `AGENTS.md` を読む。
2. 関連する `spec/initial/*.md` を読む。
3. 既存 `spec/wip/unit_*` と `spec/complete/unit_*` を確認する。
4. 変更を伴う作業では branch と `git status --short` を確認する。
5. ユーザ入力から Intent Delta を抽出する。なければ `none`。
6. 実装済み範囲と既存 test を確認する。
7. 次の作業単位を 1 つだけ選ぶ。

開始時は短く提示する。

```text
Agentic SDD bootstrap:
- Constitution: AGENTS.md, spec/initial/*
- Git Context:
- Intent Delta:
- Selected Work:
- Non-goals:
- Gates:
- Hardware:
```

## Work Selection

| 候補 | 選択条件 |
|---|---|
| roadmap milestone | `spec/initial/roadmap.md` の M0-M7 に沿う作業。 |
| spec TDD item | `spec/wip` の TDD Test List にある小さい振る舞い。 |
| source audit item | report bytes、subcommand、Bumble、driver 仮定の根拠が必要。 |
| hardware-gated item | Bumble adapter または Switch 実機が必要。 |

- 選択していない milestone、daemon、GUI、複数 controller、amiibo、NFC、IR camera は実装しない。
- 大きい作業は TDD item へ分割する。
- 実機や dongle を使う command は `hardware-harness` の承認まで実行しない。
- protocol 値や driver 仮定は `source-audit` を通す。

## Implementation Loop

1. 作業仕様がなければ `spec-format` で `spec/wip` を作る。
2. TDD が適する場合は `tdd-workflow` を使う。
3. red の理由が期待した失敗であることを確認する。
4. green を作る。
5. green 後に必要な構造変更だけ `tidy-first` と `refactor-after-green` で分ける。
6. gate 失敗時は、Spec、Plan、Tasks、Source audit、Implement のどこへ戻るか決める。
7. 終了時は `agentic-self-review` で gate と未検証リスクを整理する。

## Git Context

- read-only 調査では branch 作成は不要。
- 作業 branch 上で clean ならそのまま進める。
- default branch 上で clean なら、変更前に作業 branch を作るかユーザ指示を確認する。
- dirty worktree では既存変更を読み、ユーザ変更を破棄しない。
- remote 未設定なら `pr-merge-cleanup` は PR 作成前に止まる。
