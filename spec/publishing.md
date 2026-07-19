# PyPI 公開手順

この文書は `swbt-python` を PyPI / TestPyPI へ公開するための内部運用手順である。
公開 package は `swbt-python`、import package は `swbt`、公開 CLI は `swbt-probe` である。

production publish は GitHub Actions の `Publish` workflow と PyPI Trusted Publishing で行う。
workflow は PyPI 公開前に draft GitHub Release を作り、同じ wheel / sdist を添付する。
PyPI 公開に成功した場合だけ GitHub Release を公開状態にする。
手元の `twine upload` は使わない。`v*` tag を作るだけでは公開されない。

## 1. PyPI 側の事前設定

PyPI と TestPyPI の Trusted Publisher は、次の値で登録する。

| 項目 | 値 |
|---|---|
| project | `swbt-python` |
| owner | `niart120` |
| repository | `swbt-python` |
| workflow | `publish.yml` |
| environment | `pypi` または `testpypi` |

GitHub repository 側では `pypi` と `testpypi` environment を作る。
environment の手動承認ルールは必須にしない。production publish の承認境界は、
tag push と `target=pypi` workflow 実行前に同じ会話 turn で得る明示確認とする。

## 2. 公開前の確認

release 実行前に、次を確認する。

```console
git status --short --branch
git fetch --prune --tags origin
git tag --list "v*" --sort=-version:refname
```

候補 version が PyPI に存在しないことを version-specific endpoint で確認する。

```text
https://pypi.org/pypi/swbt-python/X.Y.Z/json
https://test.pypi.org/pypi/swbt-python/X.Y.Z/json
```

local gate は次を実行する。

```console
uv sync --dev
uv lock --check
uv run ruff format --check .
uv run ruff check .
uv run ty check --no-progress
uv run pytest tests/unit
uv run pytest tests/integration
uv build
```

docs を変更した release では、docs gate も実行する。

```console
uv sync --group docs
uv run --group docs mkdocs build --strict
```

`bumble` marker と `hardware` marker の test は CI 必須にしない。
実行する場合は、adapter、Switch-facing 動作、cleanup plan を明示して承認を得る。

## 3. Release PR

1. `release/vX.Y.Z` branch を作る。
2. `pyproject.toml` の `project.version` を `X.Y.Z` に更新する。
3. `uv lock` で `uv.lock` を同期する。
4. README、docs、spec に version や公開状態の矛盾があれば更新する。
5. local gate と CI を通す。
6. PR merge と branch cleanup は `pr-merge-cleanup` に委譲する。

古い build artifact が残っている場合は `dist/.gitignore` だけを残し、`swbt_python-*.whl` と `swbt_python-*.tar.gz` を削除してから build する。
wheel / sdist の確認では candidate version の exact path を使う。

```console
uv build
uvx --from twine twine check --strict dist\swbt_python-X.Y.Z-py3-none-any.whl dist\swbt_python-X.Y.Z.tar.gz
```

## 4. TestPyPI

TestPyPI publish は `Publish` workflow を `target=testpypi` で手動実行する。
同じ version を TestPyPI に再公開することはできないため、実行前に version-specific endpoint を確認する。

```console
gh workflow run publish.yml --ref release/vX.Y.Z -f target=testpypi
gh run list --workflow publish.yml --limit 5
gh run watch <run-id> --exit-status
```

TestPyPI smoke では、依存を本番 PyPI から入れ、`swbt-python` wheel だけを TestPyPI から取得する。

```console
uv venv .tmp-testpypi-smoke
uv pip install --python .tmp-testpypi-smoke\Scripts\python.exe "bumble>=0.0.230,<0.0.231"
uv pip install --python .tmp-testpypi-smoke\Scripts\python.exe --no-deps --index-url https://test.pypi.org/simple/ swbt-python==X.Y.Z
.tmp-testpypi-smoke\Scripts\python.exe -c "import importlib.metadata, swbt; print(importlib.metadata.version('swbt-python')); print(swbt.__name__)"
.tmp-testpypi-smoke\Scripts\swbt-probe.exe --help
```

smoke 後の `.tmp-testpypi-smoke` は削除してよい。

## 5. Production PyPI

production publish は release PR merge 後、local default branch が `origin/main` と同期している状態で行う。
tag push と `target=pypi` workflow 実行は、同じ会話 turn で明示確認を得てから行う。

```console
git switch main
git pull --ff-only origin main
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
gh workflow run publish.yml --ref vX.Y.Z -f target=pypi
gh run list --workflow publish.yml --limit 5
gh run watch <run-id> --exit-status
```

`Publish` workflow は `target=pypi` が `v*` tag ref 以外で実行された場合に失敗する。
tag push だけでは publish job は実行されない。

workflow は build 済みの wheel / sdist を draft GitHub Release に添付してから、同じ
Actions artifact を PyPI へ公開する。PyPI job が成功すると draft を公開状態へ変更する。
既に公開済みの同名 GitHub Release がある場合は、成果物を上書きせず停止する。

PyPI 公開前に workflow が失敗した場合、draft GitHub Release は再実行時に再利用される。
PyPI 公開後の GitHub Release 公開処理だけが失敗した場合は、次の command で failed job を
再実行する。PyPI への重複 upload は行わない。

```console
gh run rerun <run-id> --failed
gh run watch <run-id> --exit-status
```

## 6. 公開後の確認

GitHub Release が draft ではなく、wheel / sdist が添付されていることを確認する。

```console
gh release view vX.Y.Z --json isDraft,assets,url
```

PyPI は version-specific endpoint を先に確認する。
generic latest endpoint は反映が遅れる場合がある。

```text
https://pypi.org/pypi/swbt-python/X.Y.Z/json
```

公開済み package は version を固定して確認する。

```console
uvx --from swbt-python==X.Y.Z python -c "import importlib.metadata, swbt; print(importlib.metadata.version('swbt-python')); print(swbt.__name__)"
uvx --from swbt-python==X.Y.Z swbt-probe --help
```

GitHub Release の本文には GitHub の自動生成 release notes を使う。PyPI URL、workflow run、local gate、smoke 結果、既知の制約は release 実行結果として報告する。

## 7. 中断条件

次の状態では公開を止める。

- worktree が dirty。
- local default branch が `origin/main` と同期していない。
- candidate version が PyPI または TestPyPI に存在する。
- local または remote に release tag が既に存在する。
- 同じ tag の GitHub Release が既に公開されている。
- `pyproject.toml` と `uv.lock` の version が一致しない。
- Trusted Publisher 設定が project、owner、repository、workflow、environment と一致しない。
- CI、local gate、publish workflow が失敗している。
- production publish の明示確認がない。
- 実機 smoke が必要だが、adapter、Switch-facing 動作、cleanup plan の承認がない。
