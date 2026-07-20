# Native JSON Key Store API の削除

## Intent

Bumble の native JSON key-store を使う互換経路を削除し、全 concrete controller の永続ペアリング情報を swbt profile JSON に統一する。

## Scope

- `key_store_path` を public constructor、runtime config、transport factory、Bumble transport、probe から削除する。
- profile envelope 内の current / previous pairing key namespace は維持する。
- native JSON key-store 専用の metadata reader、fixture、hardware test、利用者向け説明を削除または profile 経路へ置き換える。
- diagnostics は profile path だけを実行時メタデータとして記録する。

## Non-goals

- HID descriptor、report layout、pairing protocol、Bumble adapter 操作を変更しない。
- 既存 native JSON key-store を自動移行しない。利用者は新しい profile を `create_profile()` で作る。

## Evidence

- implementation fact: 変更前の native JSON 分岐は `_CurrentPreviousJsonKeyStore` と `key_store_path` に閉じていた。削除後は profile envelope の namespace store だけを Bumble KeyStore interface に渡す。
- hardware observation: unit_052--054 で profile 経路の Pro Controller、Periodic Joy-Con、Direct controller の fresh pairing と reconnect を確認済み。
- unverified: native JSON key-store から profile への内容変換は提供しない。

## TDD Test List

| Status | Test | Classification | Environment |
|---|---|---|---|
| done | 全 concrete controller の constructor が `profile_path` を受け、`key_store_path` を受けない | API boundary | unit |
| done | runtime / factory / Bumble transport が profile path だけを受ける | boundary | unit |
| done | profile 内の pairing keys で reconnect candidate を current 1 件に制限する | regression | unit, integration |
| done | probe の pairing 実行が profile path を要求する | CLI | unit |
| done | README と API / usage / hardware docs が profile-only の手順を説明する | review | docs |

## Validation

- `uv run ruff format --check .`
- `uv run ruff check .`
- `uv run ty check --no-progress`
- `uv run pytest tests/unit`
- `uv run pytest tests/integration`
- `bumble` / `hardware` marker は既存 profile 経路の実測を根拠とし、この削除変更では実行しない。

## Completion checklist

- [x] native JSON key-store の production 分岐を削除した
- [x] public / internal API と test fixture を profile-only にした
- [x] probe と利用者向け文書を更新した
- [x] standard gate と docs-quality-review を記録した

## Verification record

- `uv run ruff format --check .`、`uv run ruff check .`、`uv run ty check --no-progress` を通過した。
- `uv run pytest tests/unit -q --basetemp <temp>` は 454 passed、`uv run pytest tests/integration -q --basetemp <temp>` は 131 passed。pytest cache は workspace のアクセス拒否により警告だけを出した。
- `uv run mkdocs build --strict` を通過した。`bumble` / `hardware` marker はこの削除変更では実行していない。

## Completion record

- source-audit: not applicable。HID descriptor、report layout、Bumble / driver の前提を追加・変更していない。
- docs-quality-review: README、API、usage、hardware、release notes を公開 API と hardware log の記録に照合し、初回 profile 作成、既存 native JSON 非対応、再接続、未検証範囲の説明を確認した。未解決の修正必須事項はない。
