---
name: tdd-workflow
description: "swbt-python の spec/wip、spec/initial、TDD Test List から Canon TDD を進める orchestration skill。ユーザが TDD、テストリスト、red/green/refactor、仕様から実装への進行、M0/M1 protocol core や fake transport の TDD 実装を求めるときに使う。"
---

# TDD Workflow

`spec-format`、`tdd-test-list`、`tdd-one-cycle`、`refactor-after-green` を接続する。

## Git Context

- 変更前に branch と `git status --short` を確認する。
- default branch への直接 commit はユーザの明示指示がある場合を除き避ける。
- dirty worktree では既存変更を読んで、ユーザ変更を破棄しない。

## Workflow

1. 関連する `spec/initial/*.md` と `spec/wip` を読む。
2. 作業仕様がなければ `spec-format` で作る。
3. `tdd-test-list` で振る舞いベースの item に分ける。
4. 次に扱う item を 1 つだけ選ぶ。
5. `tdd-one-cycle` で red / green / refactor を進める。
6. green 後の構造変更は `refactor-after-green` と `tidy-first` で behavior change と分ける。
7. test quality に迷う場合は `test-desiderata-review` を使う。
8. spec の TDD Test List、検証、先送り事項を更新する。

## swbt-python Priority

- M0 protocol core と M1 fake transport では、実機なしの unit / integration test を優先する。
- Bumble import は transport 層に閉じる。
- `0x30` input report、`0x01` / `0x10` output report、`0x21` reply、SPI flash、subcommand などの値は `source-audit` を通す。
- `bumble` / `hardware` marker の item は `hardware-harness` の承認まで実行しない。

## Rules

- red から green の途中で見つけた別の振る舞いは list に追加し、今の item に混ぜない。
- refactor は green 後に行う。
- formatter / linter だけを refactor と呼ばない。
- 実機未検証を pass にしない。
