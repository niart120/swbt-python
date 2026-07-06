# Rearchitecture Docs Release Matrix 仕様書

## 1. 概要

### 1.1 目的

リアーキテクチャ後の user-facing docs、examples、agent brief、hardware verification matrix、release note を新 API に揃える。未検証 Joy-Con behavior を保証済みのように見せず、Pro Controller / Joy-Con L / Joy-Con R の検証状態と key store 分離を明記する。

この unit は release 可能な破壊的変更の仕上げを扱う。実機検証を新たに実施する場合は、会話上の明示承認を得る。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| design note | M6 docs / hardware matrix / release cleanup | `spec/rearchitecture/05-milestones-implementation.md` |
| current docs | 現行 docs は `SwitchGamepad`, `JoyCon(side)`, `SwitchGamepadConfig`, public `transport=` を案内している | `README.md`, `docs/api.md`, `docs/usage.md`, `docs/agent-brief.md` |
| hardware record | Joy-Con behavior は検証済み構成と未検証構成を分ける必要がある | `spec/hardware-test-log.md`, `spec/complete/unit_036/JOYCON_SDP_IDENTITY_POLICY.md`, `spec/complete/unit_037/JOYCON_DEFAULT_CONTROLLER_COLORS.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| new user | README / usage docs を読む | `ProController`, `JoyConL`, `JoyConR` で始められる | old API は migration section に限定 |
| maintainer | release note を作る | breaking change と移行表が明示される | 互換 alias を案内しない |
| hardware reviewer | hardware matrix を読む | Pro / Joy-Con L / Joy-Con R の検証状態が分かれる | 未検証を確認済みと書かない |

## 2. 対象範囲

- README examples の更新。
- `docs/api.md` の public API 更新。
- `docs/usage.md` の usage 更新。
- `docs/agent-brief.md` の agent-facing API 更新。
- examples の更新。
- old API から new API への migration note。
- hardware verification matrix の追加または更新。
- Joy-Con L/R の検証状態の分離。
- `JoyConPair` を未実装の上位 API として別扱いにする記述。
- Pro Controller / Joy-Con L / Joy-Con R は別々の `key_store_path` を使うことの明記。
- changelog / release note と package version update。
- docs site 更新。rearchitecture docs を公開 docs に載せるかの判断。

## 3. 対象外

- public API model の実装。
- runtime extraction。
- profile module split。
- 未承認の hardware / bumble marker tests。
- Joy-ConPair 実装。

## 4. 関連 docs

- `spec/rearchitecture/README.md`
- `spec/rearchitecture/05-milestones-implementation.md`
- `README.md`
- `docs/api.md`
- `docs/usage.md`
- `docs/agent-brief.md`
- `docs/hardware-guide.md`
- `spec/hardware-test-log.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | docs / release matrix を扱い、新しい byte layout は追加しない |
| Bumble / transport | not applicable | not applicable | docs 上で verification state を整理する。実機検証を追加する場合は hardware-harness を使う |
| OS / driver / adapter | required | pending | hardware matrix に OS / driver / adapter / Switch firmware の検証状態を書く必要がある |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| normal docs | README / usage / API docs | `SwitchGamepad(`, `JoyCon("left"`, `JoyCon("right"`, `SwitchGamepadConfig`, `transport=FakeHidTransport` を通常説明に含めない | migration section は例外 |
| migration docs | old API examples | old -> new mapping が明示される | old API を推奨しない |
| agent brief | agent-facing docs | `ProController`, `JoyConL`, `JoyConR` を案内する | `SwitchGamepad` は型として説明 |
| hardware matrix | docs / spec | 検証済み構成と未検証構成が分かれている | user observation と automated pass を混同しない |
| release note | changelog / release notes | breaking change が明記される | package version target を決める |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| todo | README の通常説明が new controller API を使う | regression | docs | no | old API は migration section のみ |
| todo | API docs が `SwitchGamepad` を型として説明する | new | docs | no | direct construction しない |
| todo | usage / examples が `ProController`, `JoyConL`, `JoyConR` を使う | regression | docs / integration | no | examples smoke |
| todo | hardware matrix が Pro / Joy-Con L / Joy-Con R を分ける | new | docs | no | verified / unverified 明記 |
| todo | release note に breaking change と migration table がある | new | docs | no | package version target も記録 |
| deferred | 新 API で実機接続を確認する | characterization | hardware | yes | 実機承認後に別 command と artifact を記録 |

## 8. 設計メモ

rearchitecture docs は maintainer 向け設計資料であり、利用者向け docs と混ぜる必要はない。MkDocs に載せる場合は `spec/rearchitecture/mkdocs-nav-snippet.yml` を参考にするが、現時点の推奨は internal architecture note として管理すること。

hardware matrix は「未検証」を明確に見せるための資料である。Joy-Con L/R の spec が存在しても、実機確認がない構成は保証済みと書かない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `README.md` | modify | new API examples / migration |
| `docs/api.md` | modify | API reference |
| `docs/usage.md` | modify | usage guide |
| `docs/agent-brief.md` | modify | agent-facing summary |
| `docs/hardware-guide.md` | modify | hardware verification matrix |
| `examples/` | modify | new API examples |
| `spec/hardware-test-log.md` | modify | verified / unverified state |
| `CHANGELOG.md` or release note file | add / modify | breaking change note |
| `pyproject.toml` | modify | version bump if release scope includes package version |
| `mkdocs.yml` | modify / optional | rearchitecture docs publication decision |
| `spec/wip/unit_044/REARCHITECTURE_DOCS_RELEASE_MATRIX.md` | add | 作業仕様 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run ruff format --check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ruff check .` | not run | 作業仕様作成時点では未実装 |
| `uv run ty check --no-progress` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/unit` | not run | 作業仕様作成時点では未実装 |
| `uv run pytest tests/integration` | not run | 作業仕様作成時点では未実装 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required for docs-only matrix update。検証済み状態を増やす場合は required |
| 承認範囲 | 実機検証を追加する場合は、対象 adapter、controller class、Switch-facing command、cleanup plan を会話で確認する |
| adapter | 未定 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | 実機検証時は `spec/hardware-test-log.md` と artifact path を記録する |
| cleanup | 実機検証時は neutral、disconnect request、transport close、adapter release を記録する |

## 12. 先送り事項

- actual hardware verification は docs-only matrix update とは分けて、承認後に実施する。
- rearchitecture docs を MkDocs 公開対象にするかは release docs 作業時に決める。

## 13. チェックリスト

- [ ] 対象範囲と対象外を確認した
- [ ] TDD Test List を更新した
- [ ] 必要な根拠監査を記録した
- [ ] 実機実行条件を記録した
- [ ] 検証結果または未実行理由を記録した
