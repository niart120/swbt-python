# swbt-python リアーキテクチャ文書セット

この文書セットは、Joy-Con 対応後に膨らんだ `swbt-python` の public API、runtime、profile、transport seam を整理するための設計資料である。対象は `spec/rearchitecture/` 配下の設計ノートであり、実装 PR に渡せる判断、移行方針、検証観点を分割して記述する。

## 完了後の更新

この文書セットで計画した初回リアーキテクチャは完了している。Issue #118 / `unit_074` は、その後の不要な実装階層整理として、runtime を知らない純粋 interface と private `_RuntimeBackedGamepad` の分離を上書きした。現行の `SwitchGamepad` は直接生成できない公開共通型であると同時に、共通 public method と `ControllerRuntime` への委譲を所有する。stateful owner は引き続き `ControllerRuntime` とする。

`01`〜`05`に残るmilestone順序や移行途中のclass名は、初回リアーキテクチャの判断履歴として読む。現行構造と競合する場合は、`spec/initial/`と`spec/complete/unit_074/`を優先する。

## Scope

対象に含めるもの:

- `SwitchGamepad` を直接生成できない public abstract common type に変更する。
- `ProController`、`JoyConL`、`JoyConR` を public concrete controller にする。
- `JoyCon(side="left" | "right")`、`SwitchGamepadConfig(profile=...)`、public `transport=` を削除する。
- Runtime lifecycle を `ControllerRuntime` に移す。
- Profile selection を concrete controller class 内部に閉じる。
- Test transport injection を internal factory または test helper に隠す。
- README、usage docs、examples、hardware verification matrix を新 API に揃える。

対象外にするもの:

- `JoyConPair` の実装。
- 外部利用者向け backend extension API。
- 実機検証が済んでいない Joy-Con behavior の保証。

## 読む順番

1. `01-design-change-overview.md`
   - 設計変更の要約
   - 確定判断
   - 目標 public usage
   - 採用しない代替案

2. `02-as-is-to-be.md`
   - 現状構造
   - 目標構造
   - 責務分割
   - 依存方向
   - 境界ルール

3. `03-public-api-config-profile.md`
   - public API
   - constructor policy
   - profile / config policy
   - root export policy
   - migration guide

4. `04-runtime-profile-transport-details.md`
   - `SwitchGamepad` / `ControllerRuntime` の責務
   - runtime behavior preservation
   - transport factory
   - profile module split
   - architecture guardrails

5. `05-milestones-implementation.md`
   - M0〜M6 の実装順
   - acceptance gate
   - implementation checklist
   - reviewer checklist
   - risk register
   - open questions

`mkdocs-nav-snippet.yml` は、この設計資料を MkDocs に載せる場合の nav 断片である。利用者向け docs と混ぜない場合は使わない。

## 中核判断

- `SwitchGamepad` は直接生成しない public abstract common type にする。
- `ProController`、`JoyConL`、`JoyConR` を public concrete controller にする。
- `JoyCon(side="left" | "right")` は削除する。
- `SwitchGamepadConfig(profile=...)` は public API から削除する。
- public constructor から `profile`、`kind`、`device_name`、`device_type`、HID descriptor、SDP policy、button map、`transport` を削除する。
- `ControllerProfile` と具象 profile class は内部実装詳細にする。`ControllerColors` は public のまま残す。
- test transport injection は内部 factory または test helper に隠す。public constructor には出さない。
- この変更は breaking change とする。`JoyCon = JoyConL` や `SwitchGamepad = ProController` のような root-level alias は残さない。
- `JoyConPair` は本設計の範囲外にする。将来、`JoyConL` / `JoyConR` を束ねる上位 orchestration layer として扱う。

中核ルールは次の 1 文に集約する。

> Public class が controller identity を選ぶ。Public constructor は resource と利用者向け option だけを受け取る。

## 実装順の要約

1. M0 で target boundary tests と設計判断を固定する。
2. M1 で public API を変えずに runtime を `ControllerRuntime` へ移す。
3. M2 で public controller API を `ProController` / `JoyConL` / `JoyConR` へ切り替える。
4. M3 で public profile injection と `SwitchGamepadConfig` を消す。
5. M4 で public `transport=` を消し、internal transport factory に寄せる。
6. M5 で profile module を分割し、`ControllerKind` 分岐を局所化する。
7. M6 で docs、examples、hardware verification matrix、release notes を更新する。
