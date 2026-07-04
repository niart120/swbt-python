# MkDocs Documentation Site 仕様書

## 1. 概要

### 1.1 目的

`docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` を、README から個別 Markdown へリンクするだけでなく、MkDocs の最小サイトとして閲覧できるようにする。

この unit は GitHub Issue #30 に対応する。本文 docs の作成は `unit_022` の範囲であり、この unit では MkDocs 設定、docs index、依存関係、ローカル確認手順、README からの導線を扱う。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| GitHub Issue #30 | MkDocs 設定、`docs/index.md`、依存関係、ローカル確認コマンド、README 導線 | https://github.com/niart120/swbt-python/issues/30 |
| prerequisite unit | docs 本文 `api.md` / `usage.md` / `hardware.md` / `agent-brief.md` | `spec/complete/unit_022/PUBLIC_API_USAGE_HARDWARE_DOCS.md` |
| package config | `uv`、`pyproject.toml`、dependency groups、build backend | `pyproject.toml` |
| CI | 現行 CI は `uv sync --locked --dev`、format、lint、type、unit、integration、build を実行する | `.github/workflows/ci.yml` |
| README | 現在は `docs/hardware-test-log.md` への導線のみ | `README.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | docs をローカルで読みたい | `uv sync --group docs` と `uv run mkdocs serve` で閲覧できる | Poetry 前提を書かない |
| maintainer | docs link を確認したい | `uv run mkdocs build --strict` が通る | docs 本文が unit_022 で存在すること |
| reviewer | README から詳細 docs へ辿る | docs site と個別 Markdown の入口が分かる | GitHub Pages 公開は必須にしない |
| contributor | docs 依存を入れる | `pyproject.toml` の dependency group に従う | runtime dependency に MkDocs を混ぜない |

## 2. 対象範囲

- `mkdocs.yml` を追加し、最小 navigation を定義する。
- `docs/index.md` を追加し、docs site の入口にする。
- `docs/index.md` に docs の目的、README との役割分担、各文書の短い説明、実機情報は `hardware.md` を参照することを書く。
- MkDocs 依存を `pyproject.toml` の dependency group に追加する。
- この unit では独立した `docs` dependency group を採用する。
- `uv.lock` を更新する。
- ローカル確認手順を README または docs に書く。
- `uv run mkdocs build --strict` 相当の確認を実行し、結果をこの仕様へ記録する。
- CI への docs build 追加は、既存 workflow に自然に入る場合に行う。追加する場合は `bumble` / `hardware` marker と同じく実機不要の docs gate として扱う。

## 3. 対象外

- `docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` の本文完成。これは `unit_022`。
- GitHub Pages 公開。
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
| CI docs build | `.github/workflows/ci.yml` | 追加する場合は `uv run mkdocs build --strict` が pull request で確認される | 必須条件ではないが、自然なら実施 |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | `mkdocs.yml` に `docs/index.md`、`docs/api.md`、`docs/usage.md`、`docs/hardware.md`、`docs/agent-brief.md` の nav がある | new | unit / docs | no | Python unit test か strict build で固定 |
| todo | `docs/index.md` が docs の目的、README との役割分担、各 docs の説明を含む | new | unit / docs | no | text drift test を検討 |
| todo | `pyproject.toml` に docs dependency group と `mkdocs>=1.6` がある | new | unit | no | `tomllib` test を追加可能 |
| todo | README に docs のローカル閲覧手順がある | regression | unit | no | `tests/unit/test_readme_docs.py` |
| todo | Poetry 前提の docs command が残っていない | regression | unit | no | text scan |
| todo | `uv run mkdocs build --strict` が通る | new | docs | no | 実装後に実行結果を記録 |
| todo | CI に docs build を追加した場合、workflow が docs group を使う | regression | ci | no | 追加しない場合は未実行理由を書く |
| deferred | GitHub Pages 公開を行う | deferred | docs | no | この unit では扱わない |
| deferred | Material for MkDocs を導入する | deferred | docs | no | 標準 theme で開始する |

## 8. 設計メモ

- docs 依存は runtime dependency に入れない。利用者が `swbt-python` を install するだけで MkDocs が入る状態にはしない。
- `docs` dependency group を分ける。既存 `dev` group は test / lint / type check の標準 gate に使われているため、docs site 専用 dependency は分離する。
- README には、詳細 docs への導線とローカル確認 command だけを書く。docs 本文を README へ戻さない。
- `unit_022` は完了済みの前提として扱う。`mkdocs build --strict` が本文リンク不足で失敗した場合は、この unit の link / nav 側の不整合として扱う。
- CI 追加は任意だが、追加するなら実機不要の docs gate として扱い、`bumble` / `hardware` marker は実行しない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `mkdocs.yml` | new | MkDocs site name と navigation |
| `docs/index.md` | new | docs site の入口 |
| `pyproject.toml` | modify | docs dependency group |
| `uv.lock` | modify | MkDocs 依存の lock 更新 |
| `README.md` | modify | docs への導線とローカル閲覧手順 |
| `.github/workflows/ci.yml` | modify / optional | docs build を追加する場合だけ変更 |
| `tests/unit/test_readme_docs.py` | modify | README docs 手順と link の確認 |
| `tests/unit/test_package_metadata.py` | modify | docs dependency group の確認を追加可能 |
| `spec/wip/unit_023/MKDOCS_DOCUMENTATION_SITE.md` | new / modify | この作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --group docs` | not run | 実装後に docs dependency group を確認する |
| `uv run mkdocs build --strict` | not run | 実装後に docs site を確認する |
| `uv run pytest tests\unit\test_readme_docs.py tests\unit\test_package_metadata.py -q` | not run | docs command / dependency group の drift test |
| `uv run ruff format --check .` | not run | 実装後の標準 gate |
| `uv run ruff check .` | not run | 実装後の標準 gate |
| `uv run ty check --no-progress` | not run | 実装後の標準 gate |
| `uv run pytest tests\unit` | not run | docs metadata test を含めて確認する |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。MkDocs build は実機、adapter、Switch-facing 動作を含まない |
| adapter | 未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test とは別の docs build として扱う |
| log / artifact | MkDocs build output、unit test output |
| cleanup | なし |

## 12. 先送り事項

- GitHub Pages 公開。
- versioned docs。
- 自動 API reference 生成。
- Material for MkDocs など追加 theme。
- docs 本文の完成。これは `unit_022`。

## 13. チェックリスト

このチェックリストは unit_023 の作業完了状態を示す。仕様書の初期作成だけで完了扱いにしない。

- [x] Issue #30 を起点として対象範囲と対象外を整理した
- [x] TDD Test List の初期案を作成した
- [x] 根拠監査と実機実行条件を記録した
- [ ] `mkdocs.yml` と `docs/index.md` を追加した
- [ ] docs dependency group と lockfile を更新した
- [ ] README に docs のローカル閲覧手順を追加した
- [ ] `uv run mkdocs build --strict` の結果を記録した
- [ ] 完了条件を満たしたら `spec/complete` へ移動する
