---
name: dev-journal
description: "swbt-python の実装中に見つかった小さい設計観測、未解決事項、先送り判断、Bumble や Switch HID の未検証仮説を spec/dev-journal.md に記録する skill。ユーザがジャーナル、メモ、dev-journal、バックログ、後で拾う記録を依頼したとき、または spec/dev-journal.md を読み書きするときに使う。"
---

# 開発ジャーナル

仕様書にするほど固まっていない観測や先送り判断を `spec/dev-journal.md` に時系列で残す。

## 記録先

- `spec/dev-journal.md` に集約する。
- ファイルがなければ初期テンプレートで作る。
- 作業単位として扱える粒度になったら `spec-format` で `spec/wip/unit_XXX` に昇格する。

## Entry

```markdown
## YYYY-MM-DD: {タイトル}

### 現状

### 観察

### 方針
```

- 新しい entry は末尾に追記する。
- 同一テーマの続きは、新しい entry として前回日付を本文冒頭に書く。
- entry 全体は短く保つ。議論の経緯ではなく、後続で使える判断と根拠を書く。

## 記録するもの

- Bumble adapter、OS driver、Bluetooth dongle の未確定観測。
- Switch firmware、pairing、L2CAP、subcommand sequence の未検証仮説。
- `spec/initial` に反映する前の小さい設計判断。
- TDD 中に見つかったが今の item には混ぜない振る舞い。
- 実機検証前に残したい安全上の注意。

## 書かないもの

- 実装手順の細かい TODO。
- command log 全文。
- 仕様書へ昇格済みの内容の重複。

## 初期テンプレート

```markdown
# Dev Journal

swbt-python の設計観測、未解決事項、先送り判断の記録。
```
