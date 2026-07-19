---
name: pr-merge-cleanup
description: "swbt-python の作業ブランチを GitHub プラグイン経由の PR と merge commit で default branch に取り込み、ローカル同期と branch cleanup まで行う skill。ユーザが PR 作成、マージ、ブランチ後片付け、main/master へ入れる、PR cleanup を依頼したときに使う。remote 未設定、default branch 上、dirty worktree、required check 失敗では停止する。"
---

# PR Merge Cleanup

作業ブランチの変更を GitHub プラグイン経由の PR で default branch に取り込み、local sync と branch cleanup まで行う。

GitHub の PR 作成、状態確認、チェック確認、マージは GitHub プラグインを主経路とする。ローカルの `gh` が Windows keyring や実行環境の隔離によって認証できなくても、プラグインの接続が有効なら作業を止めない。

## Preconditions

- `origin` remote が設定済み。
- default branch を確認できる。
- 作業ブランチ上である。
- `git status --short` が clean。
- 必要な commit が完了している。
- GitHub プラグインから対象 repository の `push` と `admin`、または PR merge 権限を確認できる。

remote 未設定の現段階では stop condition として扱い、push や PR 作成を試みない。

## Workflow

1. `git branch --show-current` を確認する。
2. `git remote get-url origin` を確認し、GitHub プラグインで repository と default branch、書き込み権限を確認する。
3. default branch 上なら停止する。
4. `git status --short` が空であることを確認する。
5. `git log --oneline <default>..HEAD` で commit log を作る。
6. `agentic-self-review` の結果、実行 gate、hardware 未実行理由を PR 本文へ反映する。
7. `git push -u origin <branch>` で push する。
8. GitHub プラグインで PR を作成する。PR 本文には下記の必須項目をすべて含める。
9. GitHub プラグインで PR の mergeable state と、head commit に紐づく required check を確認する。
10. check が通ったら、GitHub プラグインで `merge` を指定して merge commit する。勝手に squash や rebase へ変えない。
11. default branch へ戻り、`git pull --ff-only origin <default>` で同期する。
12. local branch を `git branch -d <branch>`、remote branch を `git push origin --delete <branch>` で削除する。
13. PR 番号、URL、merge commit、削除 branch、gate、hardware 状態を報告する。

## 補助経路

- GitHub プラグインに該当する操作がない場合だけ、`gh` または Git の remote 操作を使う。
- `gh auth status` の失敗だけでは停止しない。プラグイン経由で repository の権限確認、PR 作成、チェック確認、マージができるかを優先して確認する。
- GitHub プラグインに remote branch 削除の操作がない場合は、`git push origin --delete <branch>` を使う。

## Stop Conditions

- `origin` remote がない。
- default branch 上にいる。
- dirty worktree がある。
- GitHub プラグインから repository または必要な書き込み権限を確認できない。
- required check が未完了または失敗。
- mergeable state が blocked / dirty / unknown。
- 実機 command が必要だが承認がない。
- PR 本文に hardware / gate の必須情報が不足している。

## PR Body

- Summary: 変更目的を 1-3 行で書く。
- Related: spec、docs、issue、作業指示元。
- Changes: file list ではなく論理単位。
- Commit Log: `<default>..HEAD`。
- Testing: command と結果。未実行 gate は理由。
- Hardware: 実機未使用なら `not run` と理由。
- Review Notes: 根拠監査、scope drift、先送り事項。
