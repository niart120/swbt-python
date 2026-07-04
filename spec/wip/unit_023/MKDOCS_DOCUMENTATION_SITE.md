# MkDocs Documentation Site 仕様書

## 1. 概要

### 1.1 目的

`docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` を、README から個別 Markdown へリンクするだけでなく、MkDocs の最小サイトとしてローカル閲覧でき、GitHub Pages で公開できるようにする。

この unit は GitHub Issue #30 に対応する。本文 docs の作成は `unit_022` の範囲であり、この unit では MkDocs 設定、docs index、依存関係、ローカル確認手順、README からの導線、GitHub Pages 公開 workflow を扱う。

GitHub Pages 公開は Issue #30 では非対象だったが、2026-07-04 のユーザ指示により今回の実装対象に含める。完了条件には、`main` 反映後に Pages deployment が成功し、公開 URL で docs site を確認できることを含める。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #30 | MkDocs 設定、`docs/index.md`、依存関係、ローカル確認コマンド、README 導線 | https://github.com/niart120/swbt-python/issues/30 |
| user instruction | GitHub Pages を今回の実装対象に含め、Pages 公開までを完了条件にする | 2026-07-04 conversation |
| repository state | Pages site は未設定。`gh api repos/niart120/swbt-python/pages` は 404 | GitHub API |
| prerequisite unit | docs 本文 `api.md` / `usage.md` / `hardware.md` / `agent-brief.md` | `spec/complete/unit_022/PUBLIC_API_USAGE_HARDWARE_DOCS.md` |
| package config | `uv`、`pyproject.toml`、dependency groups、build backend | `pyproject.toml` |
| CI | 現行 CI は `uv sync --locked --dev`、format、lint、type、unit、integration、build を実行する | `.github/workflows/ci.yml` |
| README | 現在は個別 docs と `docs/hardware-test-log.md` への導線がある。MkDocs site と Pages への導線は未整備 | `README.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | docs をローカルで読みたい | `uv sync --group docs` と `uv run mkdocs serve` で閲覧できる | Poetry 前提を書かない |
| maintainer | docs link を確認したい | `uv run mkdocs build --strict` が通る | docs 本文が unit_022 で存在すること |
| reviewer | README から詳細 docs へ辿る | docs site と個別 Markdown の入口が分かる | README に本文を重複させない |
| contributor | docs 依存を入れる | `pyproject.toml` の dependency group に従う | runtime dependency に MkDocs を混ぜない |
| site reader | 公開 docs を読む | GitHub Pages URL から `docs/index.md` 由来のサイトを閲覧できる | 公開 URL は初回 deployment 後に確認する |
| maintainer | `main` 反映後に公開状態を確認する | Pages deployment が成功し、公開 URL が応答する | PR 上では deploy 完了を確認できない |

## 2. 対象範囲

- `mkdocs.yml` を追加し、最小 navigation を定義する。
- `docs/index.md` を追加し、docs site の入口にする。
- `docs/index.md` に docs の目的、README との役割分担、各文書の短い説明、実機情報は `hardware.md` を参照することを書く。
- MkDocs 依存を `pyproject.toml` の dependency group に追加する。
- この unit では独立した `docs` dependency group を採用する。
- `uv.lock` を更新する。
- ローカル確認手順を README または docs に書く。
- `uv run mkdocs build --strict` 相当の確認を実行し、結果をこの仕様へ記録する。
- GitHub Actions に docs build / Pages deploy workflow を追加する。
- pull request では `uv run mkdocs build --strict` を実行し、Pages deploy は行わない。
- `main` push では strict build 後に GitHub Pages へ deploy する。
- Pages deploy workflow は deploy に必要な権限を持つ。Python matrix の CI workflow へ広い権限を混ぜない。
- README にローカル閲覧手順と GitHub Pages 公開先への導線を書く。
- `main` 反映後に Pages deployment と公開 URL を確認し、結果をこの仕様へ記録する。

## 3. 対象外

- `docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` の本文完成。これは `unit_022`。
- custom domain。
- branch-based `gh-pages` 公開。
- versioned docs。
- 自動 API reference 生成。
- Material for MkDocs などの追加 theme。
- API 仕様変更。
- 実機検証。

## 4. 関連 docs

- `spec/complete/unit_022/PUBLIC_API_USAGE_HARDWARE_DOCS.md`
- `README.md`
- `pyproject.toml`
- `.github/workflows/ci.yml`
- `.github/workflows/docs.yml`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | docs site 構成であり、protocol 値は変更しない |
| Bumble / transport | not applicable | not applicable | MkDocs 導入は runtime transport behavior に触れない |
| OS / driver / adapter | not applicable | not applicable | 実機や adapter を使わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| mkdocs config | `mkdocs.yml` | `site_name: swbt-python` と docs navigation が定義されている | theme は MkDocs 標準 |
| docs navigation | nav | Home、API Reference、Usage Guide、Hardware Guide、Agent Brief が辿れる | label は実装時に日本語化してもよいが、リンク先は固定 |
| docs index | `docs/index.md` | README との役割分担と各 docs の短い説明がある | 実機情報は `hardware.md` へ誘導 |
| docs dependency group | `pyproject.toml` | `[dependency-groups] docs = ["mkdocs>=1.6"]` 相当がある | runtime dependency へ入れない |
| local sync command | README / docs | `uv sync --group docs` を案内する | `--dev` が必要な場合は実際の構成に合わせる |
| local serve command | README / docs | `uv run mkdocs serve` を案内する | Windows PowerShell で実行できる形 |
| strict build | local command | `uv run mkdocs build --strict` が通る | docs link と nav を確認する |
| README docs link | README | docs site / docs index への導線がある | README は詳細本文を重複させない |
| docs workflow build | `.github/workflows/docs.yml` | pull request と `main` push で `uv run mkdocs build --strict` が実行される | 実機不要の docs gate |
| Pages deploy condition | `.github/workflows/docs.yml` | `main` push の build 成功後だけ Pages deploy を実行する | pull request では公開しない |
| Pages permissions | `.github/workflows/docs.yml` | deploy job が `contents: read`、`pages: write`、`id-token: write` を持つ | Python CI workflow へ deploy 権限を入れない |
| Pages artifact | GitHub Actions | MkDocs build output が Pages artifact として upload される | `site/` を repo に commit しない |
| public docs link | README | GitHub Pages の公開先へ辿れる | 初回 deploy までは想定 URL と未確認状態を分ける |
| Pages verification | GitHub Actions / public URL | `main` 反映後に deployment 成功と公開 URL 応答を確認する | 完了条件に含める |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `mkdocs.yml` に `docs/index.md`、`docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` の nav がある | new | unit / docs | no | Python unit test か strict build で固定 |
| todo | `docs/index.md` が docs の目的、README との役割分担、各 docs の説明を含む | new | unit / docs | no | text drift test を検討 |
| todo | `pyproject.toml` に docs dependency group と `mkdocs>=1.6` がある | new | unit | no | `tomllib` test を追加可能 |
| todo | README に docs のローカル閲覧手順がある | regression | unit | no | `tests/unit/test_readme_docs.py` |
| todo | Poetry 前提の docs command が残っていない | regression | unit | no | text scan |
| todo | `uv run mkdocs build --strict` が通る | new | docs | no | 実装後に実行結果を記録 |
| todo | docs workflow が pull request と `main` push で docs group を使い strict build する | regression | ci | no | workflow YAML test と remote Actions で確認 |
| todo | docs workflow が `main` push だけで GitHub Pages deploy を行う | new | ci / docs | no | PR では deploy しない |
| todo | Pages deploy job が `pages: write` と `id-token: write` を持つ | new | ci | no | deploy 権限を CI matrix へ混ぜない |
| todo | README にローカル docs と公開 docs の導線がある | regression | unit | no | 初回 deploy 前後の表現を確認 |
| todo | `main` 反映後に GitHub Pages deployment が成功し、公開 URL で docs site を確認できる | new | remote docs | no | 完了条件。merge 後に実行結果を記録 |
| deferred | Material for MkDocs を導入する | deferred | docs | no | 標準 theme で開始する |

## 8. 設計メモ

- docs 依存は runtime dependency に入れない。利用者が `swbt-python` を install するだけで MkDocs が入る状態にはしない。
- `docs` dependency group を分ける。既存 `dev` group は test / lint / type check の標準 gate に使われているため、docs site 専用 dependency は分離する。
- README には、詳細 docs への導線とローカル確認 command だけを書く。docs 本文を README へ戻さない。
- `unit_022` は完了済みの前提として扱う。`mkdocs build --strict` が本文リンク不足で失敗した場合は、この unit の link / nav 側の不整合として扱う。
- docs build / deploy workflow は `.github/workflows/docs.yml` として分ける。既存の Python CI matrix は `contents: read` のまま維持する。
- Pages deploy は `main` 反映後にしか公開状態を確認できない。完了移動は deployment 成功と公開 URL 確認を記録した後に行う。
- 公開 URL は `https://niart120.github.io/swbt-python/` を想定する。ただし初回 deployment 前は未確認として扱い、確認済みのように書かない。
- docs gate は実機不要の gate として扱い、`bumble` / `hardware` marker は実行しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `mkdocs.yml` | new | MkDocs site name と navigation |
| `docs/index.md` | new | docs site の入口 |
| `pyproject.toml` | modify | docs dependency group |
| `uv.lock` | modify | MkDocs 依存の lock 更新 |
| `README.md` | modify | docs への導線とローカル閲覧手順 |
| `.github/workflows/docs.yml` | new | docs strict build と GitHub Pages deploy |
| `.github/PULL_REQUEST_TEMPLATE.md` | modify / optional | docs gate を標準 Testing 例へ追加する場合だけ変更 |
| `tests/unit/test_readme_docs.py` | modify | README docs 手順と link の確認 |
| `tests/unit/test_package_metadata.py` | modify | docs dependency group の確認を追加可能 |
| `tests/unit/test_docs_workflow.py` | new | docs workflow の trigger、build command、Pages deploy 権限を確認 |
| `spec/wip/unit_023/MKDOCS_DOCUMENTATION_SITE.md` | new / modify | この作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --group docs` | not run | 実装後に docs dependency group を確認する |
| `uv run mkdocs build --strict` | not run | 実装後に docs site を確認する |
| `uv run pytest tests\unit\test_readme_docs.py tests\unit\test_package_metadata.py tests\unit\test_docs_workflow.py -q` | not run | docs command / dependency group / Pages workflow の drift test |
| `uv run ruff format --check .` | not run | 実装後の標準 gate |
| `uv run ruff check .` | not run | 実装後の標準 gate |
| `uv run ty check --no-progress` | not run | 実装後の標準 gate |
| `uv run pytest tests\unit` | not run | docs metadata test を含めて確認する |
| GitHub Actions docs workflow on pull request | not run | PR 上で strict build を確認する |
| GitHub Pages deployment after merge to `main` | not run | 完了条件。deployment 成功と公開 URL 応答を確認する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。MkDocs build は実機、adapter、Switch-facing 動作を含まない |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test とは別の docs build として扱う |
| log / artifact | MkDocs build output、unit test output、GitHub Actions docs workflow、Pages deployment URL |
| cleanup | なし |

## 12. 先送り事項

- versioned docs。
- 自動 API reference 生成。
- Material for MkDocs など追加 theme。
- docs 本文の完成。これは `unit_022`。
- custom domain。
- branch-based `gh-pages` 公開。

## 13. チェックリスト

このチェックリストは unit_023 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] Issue #30 を起点として対象範囲と対象外を整理した
- [x] TDD Test List の初期案を作成した
- [x] 根拠監査と実機実行条件を記録した
- [ ] `mkdocs.yml` と `docs/index.md` を追加した
- [ ] docs dependency group と lockfile を更新した
- [ ] README に docs のローカル閲覧手順を追加した
- [ ] GitHub Pages 用の docs workflow を追加した
- [ ] pull request で docs strict build が通ることを確認した
- [ ] `main` 反映後に Pages deployment 成功を確認した
- [ ] 公開 URL で docs site を確認した
- [ ] `uv run mkdocs build --strict` の結果を記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
