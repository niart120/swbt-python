---
name: pypi-release
description: "swbt-python の PyPI release を計画・実行する workflow skill。ユーザが PyPI / TestPyPI 公開、バージョン更新、release PR、v* tag、GitHub Actions publish、公開後 smoke check、release 手順確認を依頼したときに使う。"
---

# PyPI Release

`spec/publishing.md` を release runbook の正本として使う。手順詳細を skill に重複させない。

## 手順

1. release 計画または実行前に `spec/publishing.md` を読む。
2. `.github/workflows/publish.yml`、`pyproject.toml`、`uv.lock`、git 状態を確認する。
3. 必要な場合だけ追加文書を読む。
   - `spec/complete/unit_012/INITIAL_RELEASE_GATE.md`: release gate の範囲。
   - `spec/initial/naming.md`: package / import / CLI 名。
   - `spec/hardware-test-log.md`: hardware evidence または smoke 判断。
4. release PR 作成、merge、default branch 同期、branch cleanup は `pr-merge-cleanup` に委譲する。

## 停止条件

- local `twine upload` は使わない。
- current turn の明示確認なしに production tag push や `target=pypi` workflow を実行しない。
- 明示承認なしに Bumble adapter、hardware、pairing、advertising、report loop、Switch-facing smoke command を実行しない。
- `spec/publishing.md` または `.github/workflows/publish.yml` がなければ停止する。
- candidate version、tag、Trusted Publisher 設定、local gate、CI、publish workflow が runbook と矛盾する場合は停止する。

## 報告

version、release branch / PR、tag、workflow run、PyPI / TestPyPI URL、gate、smoke、hardware status、停止条件を報告する。
