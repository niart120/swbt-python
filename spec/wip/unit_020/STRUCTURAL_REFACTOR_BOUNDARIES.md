# Structural Refactor Boundaries 仕様書

## 1. 概要

### 1.1 目的

`gamepad.py`、`transport/bumble.py`、Bumble / fake transport 周辺のテスト肥大化を、観測可能な挙動を変えずに整理する。

この unit は機能追加ではない。公開 API、HID report bytes、diagnostics event 名、close / reconnect の状態遷移、Bumble 0.0.230 向けの実機観測済み補正を維持したまま、責務境界を読みやすい単位へ分ける。

内部 module 名、private helper、test fake、fixture helper の互換は維持条件にしない。既存 tests と必要な regression tests を信頼し、内部 interface は壊してよい。壊した箇所は同じ change set で tests と仕様を更新する。

`diagnostics.py` が key store の `swbt.previous::` 保存形式を直接読んでいる点は、先に漏れ出た原因を分析したうえで、この unit 内で key store metadata owner へ寄せる。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | `gamepad.py` と `transport/bumble.py` の肥大化、周辺の tidying 余地を unit_020 に落とす。`diagnostics.py` の key store 実装知識漏れは原因分析を先に行う | conversation, 2026-07-04 |
| user request | 内部 interface の互換は優先せず、テストを信頼してある程度破壊的にきれいにする | conversation, 2026-07-04 |
| implementation fact | `BumbleHidTransport` は public transport、Bumble runtime protocol、current / previous key store、diagnostics wrapper、callback bridge、SDP builder、Bumble 0.0.230 workaround を同じ file に持つ | `src/swbt/transport/bumble.py` |
| implementation fact | `SwitchGamepad` は public API、active reconnect strategy、close ordering、output report dispatch、diagnostics event 組み立てを同じ class に持つ | `src/swbt/gamepad.py` |
| implementation fact | `tests/unit/test_bumble_transport.py` と `tests/integration/test_switch_gamepad_fake_transport.py` は fake runtime / fixture と behavior assertion が同じ file に集まっている | `tests/unit/test_bumble_transport.py`, `tests/integration/test_switch_gamepad_fake_transport.py` |
| completed unit | close ordering、disconnect request、Bumble connection request warning workaround は実機観測済み contract として維持する | `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md` |
| completed unit | current / previous key store、active reconnect、injected transport の reconnect boundary は維持する | `spec/complete/unit_016/JSON_KEY_STORE_CURRENT_PREVIOUS.md`, `spec/complete/unit_018/KEY_STORE_TRANSPORT_BOUNDARY.md`, `spec/complete/unit_019/TRANSPORT_RECONNECT_CONTRACT.md` |
| web doc | refactoring は観測可能な振る舞いを変えず内部構造を変える作業として扱う | https://refactoring.com/ |
| web doc | Python module は file 単位の名前空間を持ち、top-level import は module 初回 import 時に実行される | https://docs.python.org/3/tutorial/modules.html |
| web doc | package は dotted module names で module namespace を構造化する仕組みである | https://docs.python.org/3/tutorial/modules.html#packages |
| web doc | `Protocol` は構造的部分型を静的型検査へ表現するために使える | https://docs.python.org/3/library/typing.html#typing.Protocol |
| web doc | pytest fixture は状態変更と teardown を小さい単位へ分けるのが安全である | https://docs.pytest.org/en/stable/how-to/fixtures.html#safe-fixture-structure |
| web doc | tests を application code の外に置く layout と `src` layout は、package と test helper の混入を避ける判断材料になる | https://docs.pytest.org/en/stable/explanation/goodpractices.html, https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/ |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| maintainer | Bumble transport 実装を読む | transport 本体、key store、SDP / HID helper、callback bridge の変更理由を分けて追える | 内部 import path は変更可。利用者向け API と観測結果を維持する |
| maintainer | `SwitchGamepad.try_reconnect()` と output report handling を読む | 接続戦略と protocol dispatch の責務を個別に確認できる | public method signature と diagnostics は変えない |
| test author | Bumble unit test を読む | fake runtime fixture と behavior test の位置関係が分かる | production 分割の安全網を弱めない |
| release reviewer | refactor 後の gate を確認する | unit / integration / public API boundary が通り、hardware-gated test は未実行理由が明確 | 実機挙動の再主張はしない |
| maintainer | `diagnostics.py` の key store knowledge を見る | なぜ保存形式を diagnostics が読む形になったか、どの boundary が不足していたかを説明できる | 原因分析なしに単純移動しない |

## 2. 対象範囲

- `transport/bumble.py` の責務分割方針を決め、Bumble 依存を `swbt.transport.bumble` 配下に閉じたまま file / module を分ける。
- `BumbleHidTransport` の import 互換は public API ではないため必須条件にしない。ただし `swbt.transport.bumble.BumbleHidTransport` を低コストで維持できる場合は残す。
- current / previous key store helper と diagnostics wrapper を transport 内部の独立した責務として扱う。
- SDP / HID service record builder と HIDP output report decode / ACL drain などの helper を、transport 本体から分離する。
- connection request bridge、L2CAP lifecycle bridge、connection diagnostics registration を transport 本体から分離するか判断する。
- `diagnostics.py` の key store 保存形式知識を、key store metadata owner へ移す。`run_metadata` の field は維持する。
- `transport/bumble.py` の file-to-package 変換を許容する。互換維持のための薄い facade を残すか、test / docs 側の import を更新するかは、実装差分の小ささではなく最終構造の読みやすさで決める。
- `SwitchGamepad.try_reconnect()` の peer selection、attempt、result recording、cleanup を分ける。
- `SwitchGamepad._handle_output_report_data()` の parse、diagnostics、subcommand reply enqueue を分ける。
- `SwitchGamepad` は公開入口として維持し、内部の接続戦略、output report dispatch、既定 transport 生成を別 module / 内部部品へ切り出す案を扱う。
- `SwitchGamepad.close()` は unit_014 の実機観測済み contract が重いため、最初の外部切り出し対象にはしない。既存の切り出しが green の後、`CloseCoordinator` 相当へ分けるかを判断する。
- `tests/unit/test_bumble_transport.py` の fake runtime fixture と test 群を、production 分割後に責務別へ整理する。
- `tests/integration/test_switch_gamepad_fake_transport.py` は必要に応じて connection / close / report / reconnect の grouping を整理する。
- `diagnostics.py` の key store 保存形式漏れについて、原因、既存制約、修正候補、修正をこの unit に含めるかを分析して記録する。

## 3. 対象外

- public API の追加、削除、引数変更。
- `from swbt import ...` で公開している利用者向け API の破壊。
- HID report bytes、subcommand reply payload、SDP record 内容、HID descriptor 内容の変更。
- close / disconnect / reconnect の状態遷移や diagnostics event 名の変更。
- Bumble 0.0.230 の source fact を再解釈する変更。
- previous peer を使う reconnect fallback。
- key store file の自動移行、復旧 CLI、secret store 対応。
- Bumble adapter test、hardware test の実行。必要になった場合は明示承認を取る。

## 4. 関連 docs

- `spec/initial/architecture.md`
- `spec/initial/lifecycle.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/complete/unit_010/DIAGNOSTICS_TRACE_SCHEMA.md`
- `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md`
- `spec/complete/unit_016/JSON_KEY_STORE_CURRENT_PREVIOUS.md`
- `spec/complete/unit_018/KEY_STORE_TRANSPORT_BOUNDARY.md`
- `spec/complete/unit_019/TRANSPORT_RECONNECT_CONTRACT.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 構造整理のみ。byte layout、subcommand payload、report timer semantics は変更しない |
| Bumble / transport | required | done-for-existing-contract / todo-for-refactor | 既存の Bumble 0.0.230 補正、L2CAP close、connection request bridge、ACL drain を移動するだけなら新しい source fact は不要。helper の意味を変える場合は `source-audit` を使う |
| OS / driver / adapter | not applicable | not applicable | adapter open、driver、Switch 実機挙動は変更しない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| public import | `from swbt import SwitchGamepad` | Bumble import を発生させない | `test_public_api_import_does_not_import_bumble` を維持 |
| default transport import | default transport factory が Bumble transport を生成する | `SwitchGamepad(adapter=...)` と `from_config()` の観測結果が変わらない | `swbt.transport.bumble.BumbleHidTransport` の import 互換は任意 |
| close ordering | connected `close(neutral=True)` | trailing neutral、report loop stop、disconnect request、closed wait or timeout、transport close の順を維持 | unit_014 contract |
| reconnect strategy | current peer 0 / 1 / invalid | `no_bond`、active reconnect、`InvalidKeyStoreError` の既存挙動を維持 | unit_018 / unit_019 contract |
| output report handling | fake transport から `0x01` / `0x10` を注入 | `output_report_rx`、`subcommand_rx`、`subcommand_reply_tx`、rumble status が従来通り | 実装分割だけを行う |
| key store diagnostics | key store path と previous namespace がある | `run_metadata` の `key_store_previous_exists` が従来通り | 原因分析後に移動可否を判断 |
| key store metadata owner | key store path と previous namespace がある | diagnostics は `swbt.previous::` を直接読まず、plain bool を受け取って従来通り記録する | storage format knowledge を transport key store 側へ戻す |
| Bumble helper split | SDP builder、HIDP output report decode、ACL drain を移動 | 既存 unit tests の expected bytes / event / drain behavior が変わらない | source fact の再解釈はしない |
| Bumble callback bridge split | connection request bridge、L2CAP lifecycle bridge を移動 | deprecation warning avoidance、connected/disconnected callback 発火条件、diagnostics event が変わらない | unit_014 / unit_005 contract |
| test fixture split | fake Bumble runtime を別 helper へ移す | assertion の意味と test count は維持 | 最初に production behavior を変えない |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| refactor-done | default Bumble transport の module 再配置後も `SwitchGamepad(adapter=...)` と `from_config()` の default transport 生成結果が変わらない | regression | unit | no | `create_default_transport()` に resource config 受け渡しを移し、public API import boundary を維持 |
| green | public API import が Bumble を解決しない | regression | unit | no | `tests/unit/test_public_api_boundary.py` で再確認 |
| refactor-done | Bumble key store current / previous tests が分割後も current のみを reconnect candidate にする | regression | unit | no | `_CurrentPreviousJsonKeyStore` と `_DiagnosticKeyStore` を `_bumble_key_store.py` に移し、既存 unit tests で current-only candidate を確認 |
| refactor-done | `run_metadata` の key store fields は metadata owner 経由へ移しても `key_store_exists` / `key_store_previous_exists` が変わらない | regression | unit / integration | no | `src/swbt/transport/_bumble_key_store.py` が storage format を読み、`diagnostics.py` は plain bool を記録する |
| refactor-done | SDP builder 分割後も service record bytes / attributes が既存 reference と一致する | regression | unit | no | `_bumble_sdp.py` に移し、reference HID attributes を確認 |
| refactor-done | HIDP output report decode 分割後も interrupt / control / set report callback が従来通り output report payload を転送する | regression | unit | no | `_bumble_hidp.py` に移し、HID data / SET_REPORT callback tests を確認 |
| refactor-done | ACL queue drain 分割後も connection queue、host fallback queue、no-progress stop が従来通り | regression | unit | no | `_bumble_acl.py` に移し、queue drain tests を確認 |
| green | Bumble request disconnect、connection request bridge、ACL queue drain の既存 unit tests が通る | regression | unit | no | unit_014 / unit_005 contract を `tests/unit/test_bumble_transport.py` で再確認 |
| refactor-done | connection diagnostics registration 分割後も pairing / authentication / encryption / mode change events の field が変わらない | regression | unit | no | `_bumble_lifecycle.py` に移し、connection diagnostics unit と Bumble transport unit で確認 |
| refactor-done | output report dispatch 分割後も output report trace、subcommand reply、raw rumble status が変わらない | regression | unit / integration | no | `OutputReportDispatcher` に parse、diagnostics、reply enqueue を移し、fake transport integration で trace と status を確認 |
| refactor-done | unsupported subcommand が分割後も復旧不能エラーとして記録され、`connection_state="failed"` になる | regression | integration | no | `OutputReportDispatcher` 化後も fake transport integration で確認 |
| refactor-done | default transport 生成を分割後も public API import は Bumble を解決せず、`SwitchGamepad.from_config()` は既定 transport へ resource config を渡す | regression | unit | no | `_gamepad_transport.py` は Bumble import を factory 関数内部に閉じる |
| refactor-done | `SwitchGamepad.try_reconnect()` 分割後も no bond / connected / timeout / failed / invalid key store の結果が変わらない | regression | unit / integration | no | `ConnectionWorkflow` に移し、fake transport integration で reconnect 結果を確認 |
| refactor-done | `try_connect(allow_pairing=True)` 分割後も no bond のときだけ pairing fallback を行い、bond がある場合は advertising しない | regression | integration | no | `ConnectionWorkflow.try_connect()` に移し、fake transport integration で pairing fallback を確認 |
| refactor-done | active reconnect の `CancelledError` は分割後も外側へ伝播し、transport error として畳み込まない | regression | integration | no | cancellation handling を workflow に移し、既存 cancellation test を確認 |
| todo | close / host disconnect race tests が分割後も通る | regression | integration | no | close ordering を触らない確認 |
| todo | test fixture 分割後に `tests/unit` と `tests/integration` の全件が通る | regression | unit / integration | no | fixture 移動の安全確認 |
| green | `diagnostics.py` の key store knowledge leak について、原因分析と修正方針が仕様内に記録されている | characterization | docs | no | unit_020 の最初に完了した分析項目 |

status は `todo`、`red`、`green`、`refactor-done`、`refactor-skipped`、`deferred` を使う。

## 8. 設計メモ

### 8.1 Tidy decision

Tidy decision:
- classification: structure
- action: split
- reason: 対象は責務分割と test fixture 整理であり、利用者向け API、wire bytes、状態遷移、diagnostics event 名を変えない。内部 interface の互換は維持条件にしない
- verification: `uv run ruff format --check .`、`uv run ruff check .`、`uv run ty check --no-progress`、`uv run pytest tests/unit tests/integration -q`

### 8.2 推奨する着手順

1. [x] `diagnostics.py` の key store knowledge leak を分析し、修正範囲をこの unit に含めるか判定する。
2. [x] key store metadata reader を `src/swbt/transport/_bumble_key_store.py` に置き、`diagnostics.py` の previous namespace 直読みを外す。
3. [x] `gamepad.py` の output report dispatch を `_gamepad_output.py` 相当へ切り出す。parser、rumble 記録、subcommand diagnostics、reply enqueue を `OutputReportDispatcher` が扱い、`SwitchGamepad` は callback 入口だけを残す。
4. [x] `gamepad.py` の既定 transport 生成を `_gamepad_transport.py` 相当へ切り出す。Bumble import は関数内部に閉じ込め、public API import が Bumble を解決しない contract を維持する。
5. [x] `gamepad.py` の reconnect / connect workflow を `_gamepad_connection.py` 相当へ切り出す。`SwitchGamepad.reconnect()` / `connect()` は成功必須 API の薄い wrapper として残す。
6. [ ] `SwitchGamepad.close()` は外部切り出し済み箇所が green になった後に再評価する。unit_014 の close ordering、disconnect request terminal、host disconnect race の回帰 test があるため、最初の整理では動かさない。
7. [x] `transport/bumble.py` から key store と diagnostics wrapper を key store module へ分ける。package 化する場合は `swbt.transport.bumble.key_store`、しない場合は `swbt.transport._bumble_key_store` とする。
8. [ ] `transport/bumble.py` を `src/swbt/transport/bumble/` package へ変換するか判断する。package 化する場合は `__init__.py` を transport 本体の入口にし、内部 module は package private に寄せる。
9. [x] SDP / HID service record builder を `swbt.transport.bumble.sdp` または `swbt.transport._bumble_sdp.py` 相当へ分ける。
10. [x] HIDP output report decode と ACL queue drain を `swbt.transport.bumble.hidp` / `acl` または `_bumble_hidp.py` / `_bumble_acl.py` 相当へ分ける。
11. [x] connection request bridge、L2CAP lifecycle bridge、connection diagnostics registration を callback / lifecycle module へ分ける。callback state と diagnostics field が散る場合も、tests を更新して最終構造を優先する。
12. [ ] production 分割後に test fixture を責務別へ移す。fake runtime は `tests` 配下に置き、`src` 配下へ入れない。

### 8.3 `diagnostics.py` に key store 実装知識が漏れた原因

事実:
- `DiagnosticsRecorder.record_run_metadata()` は adapter、OS、Python、package version などの実行メタデータを集める責務を持つ。
- unit_016 で current / previous key store が導入され、`key_store_previous_exists` を `run_metadata` に追加した。
- `SwitchGamepad` が持っていた入力は `key_store_path` だけで、current / previous の保存形式を読む public helper は存在しなかった。
- `_CurrentPreviousJsonKeyStore` は `transport/bumble.py` 内部に閉じており、`diagnostics.py` から参照できる安定した boundary ではなかった。
- その結果、`DiagnosticsRecorder` が JSON file を直接読み、`swbt.previous::` prefix を探す形になった。

推論:
- 漏れの直接原因は、diagnostics metadata と key store persistence metadata の境界が未定義だったことにある。
- unit_016 では「trace に secret を出さず previous の存在を見せる」ことが優先され、key store 保存形式の問い合わせ API までは作らなかった。
- `run_metadata` が path を受け取る設計だったため、file system を読む処理を diagnostics 側へ足すのが最短経路になった。
- `transport.bumble` が単一 file だったため、key store helper を transport 内部実装として閉じる判断と、diagnostics から previous availability を読む要求が衝突した。

修正候補:
- key store metadata reader を `swbt.transport.bumble` 配下の key store module に置き、`SwitchGamepad` か default transport factory が `DiagnosticsRecorder.record_run_metadata()` に plain metadata を渡す。
- Bumble 非依存の `swbt.key_store_metadata` のような module を作る。ただし default Bumble store の保存形式を一般名で扱うため、抽象化の名前が過剰になりやすい。
- `DiagnosticsRecorder` は file path を読まず、`RunMetadata` 相当の値を受け取るだけにする。これはきれいだが `SwitchGamepad.open()` の準備処理が少し増える。

現時点の判断:
- 単純に `_key_store_previous_exists()` を移すだけでは、なぜ diagnostics が storage format を知ったかという設計欠落を直せない。
- 先に key store metadata の owner を決める。その owner は secret を返さず、`key_store_exists` と `key_store_previous_exists` のような plain bool だけを返す。
- この unit では root-cause の切り分けに留めず、`key_store_previous_exists` を owner API 経由で渡す実装整理まで含める。

### 8.4 item 4 の原因分析結果

- `diagnostics.py` 側で `swbt.previous::` 判定が読めるのは、`_CurrentPreviousJsonKeyStore` が `transport/bumble.py` に内包され、`DiagnosticsRecorder` が代替の所有者を取得する API を受け取れなかったため。
- いまの時点では「`key_store_previous_exists` を所有者 API 経由で渡す」という設計整理をこの unit に含める。diagnostics の storage format 直読みは取り除く。

### 8.5 `SwitchGamepad` の外部切り出し方針

`SwitchGamepad` の肥大化は、公開 API の数そのものよりも、内部方針が同じ class に集まっていることが原因である。利用者が触る入口は `SwitchGamepad` に集約したまま、次の内部部品へ寄せる。

| 責務 | 現状 | 切り出し候補 | 判断 | 主要な回帰確認 |
|---|---|---|---|---|
| output report dispatch | `_handle_output_report_data()` が parse、rumble 記録、subcommand diagnostics、reply enqueue、復旧不能エラー記録をまとめて持つ | `src/swbt/_gamepad_output.py` の `OutputReportDispatcher` | 最初に切り出す。transport lifecycle への依存が薄く、protocol dispatch の責務として独立しやすい | `output_report_rx`、`subcommand_reply_tx`、raw rumble、unsupported subcommand tests |
| 既定 transport 生成 | `_ensure_transport()` が `BumbleHidTransport` 遅延 import と config 受け渡しを持つ | `src/swbt/_gamepad_transport.py` の `create_default_transport()` | 早めに切り出す。Bumble import を関数内部に閉じることが条件 | public API import boundary、`from_config()` resource config tests |
| reconnect / connect workflow | `try_reconnect()` が peer discovery、invalid key store、attempt、timeout、transport error cleanup、result recording をまとめて持つ | `src/swbt/_gamepad_connection.py` の `ConnectionWorkflow` | output dispatch の後に切り出す。`open()`、`pair()`、`close()`、connection state への接点を小さい context に閉じる | reconnect selection、no bond、timeout、failed、cancellation、pairing fallback tests |
| close workflow | `close()` が trailing neutral、report loop stop、disconnect request、terminal wait、transport close を持つ | `CloseCoordinator` 相当 | deferred。unit_014 の実機観測済み contract に近く、先に動かす理由が弱い | close ordering、disconnect request terminal、host disconnect race tests |
| public types | `ConnectionResult`、`SwitchGamepadConfig`、`ConnectionStatus` が `gamepad.py` にある | `src/swbt/_gamepad_types.py` | 行数削減目的では動かさない。connection workflow 切り出し時に循環 import が出る場合だけ検討する | `swbt.__all__`、docstring、`swbt.gamepad.ConnectionStatus` tests |

`SwitchGamepad` に残すもの:

- constructor / `from_config()` / async context manager。
- `open()`、`pair()`、`connect()`、`try_connect()`、`reconnect()`、`try_reconnect()`、`close()` の public method signature。
- 入力操作 `press()`、`release()`、`set_input()`、`neutral()`、`tap()`。
- `status()`、`snapshot()`。
- diagnostics 上の connection state 変更と public error への変換。ただし変換処理の実体は内部部品に委譲してよい。

内部部品へ渡してよいもの:

- `DiagnosticsRecorder`、`InputStateStore`、`ReportLoop` 参照または取得関数。
- `HidDeviceTransport` 参照または取得関数。
- `connected_event` / `disconnect_event` の待機。
- connection state 更新関数。文字列状態を内部部品側で直接ばらまく場合は、後続で `ConnectionState` 型別名へ寄せる。

禁止すること:

- `SwitchGamepad` の public method 名、引数、返り値を変える。
- `from swbt import SwitchGamepad` や `from swbt.gamepad import ConnectionStatus` の互換を壊す。
- `swbt` import 時に Bumble を import する。
- close / reconnect / output report の diagnostics event 名や payload field を変える。
- 内部部品から Bumble 固有型を public API に露出する。

### 8.6 Web docs からの判断

確認した外部文書は、公式 docs または refactoring の一次説明に限った。

| source | 確認した要点 | この unit での使い方 |
|---|---|---|
| Refactoring.com | refactoring は観測可能な振る舞いを変えず、理解しやすく変更しやすい内部構造へ変える作業 | diagnostics event、public API、wire bytes、状態遷移を固定したまま、内部 module と test fixture だけを動かす |
| Python docs / Modules | program が大きくなると複数 file へ分けられる。module は private namespace を持ち、top-level import は初回 import 時に実行される | Bumble 依存の import timing を test で固定する。内部 module 名は変えてよい |
| Python docs / Packages | package は dotted module names で module namespace を構造化する | `transport/bumble.py` の package 化を許容する。内部互換より、責務ごとの package structure を優先する |
| Python docs / `typing.Protocol` | `Protocol` は明示継承なしで構造的部分型を静的に表せる | Bumble fake runtime と production runtime の境界は `Protocol` を維持する。Bumble の具象型を public API や `SwitchGamepad` へ出さない |
| pytest docs / safe fixture structure | 状態変更と teardown を小さい fixture へ束ねると、失敗時に test environment を戻しやすい | fake runtime fixture は巨大な一括 setup にしない。handle、device、hid device、ACL queue、connection request bridge を分ける |
| pytest docs / good practices, PyPA src layout | tests を application code の外へ置く layout と `src` layout は、package へ入る code と test helper を分ける判断材料になる | fake Bumble runtime は `src` へ移さない。production helper は `src/swbt/transport/bumble/` または `src/swbt/transport/_bumble_*` へ置く |

### 8.7 `transport/bumble.py` の再考結果

内部 interface の互換を維持条件にしないため、`transport/bumble.py` の package 化を有力候補に戻す。Python docs の module / package の説明を踏まえると、Bumble transport は単一 module より package 配下で責務を分けるほうが読みやすい。

推奨案:

- `src/swbt/transport/bumble/__init__.py`: `BumbleHidTransport` の入口。低コストなら `from swbt.transport.bumble import BumbleHidTransport` は残すが、必須ではない。
- `src/swbt/transport/bumble/transport.py`: transport 本体。
- `src/swbt/transport/bumble/key_store.py`: current / previous key store、diagnostic wrapper、metadata reader。
- `src/swbt/transport/bumble/sdp.py`: SDP / HID service record builder。
- `src/swbt/transport/bumble/hidp.py`: HIDP output report decode、PSM 表示。
- `src/swbt/transport/bumble/acl.py`: ACL queue drain。
- `src/swbt/transport/bumble/lifecycle.py`: connection request bridge、L2CAP lifecycle bridge、connection diagnostics registration。

代替案:

- package 化の差分が大きすぎる場合だけ、`src/swbt/transport/_bumble_*.py` へ抽出する。

1. key store module
   - `_CurrentPreviousJsonKeyStore`、`_DiagnosticKeyStore`、previous namespace 判定、key store metadata reader を置く。
   - `diagnostics.py` は JSON file を読まず、`SwitchGamepad.open()` または default transport factory から渡された plain metadata を `run_metadata` に記録する。
   - secret material は返さない。返してよい値は `key_store_exists`、`key_store_previous_exists`、必要なら `key_store_path` まで。

2. SDP module
   - `_build_hid_service_records()` と SDP/HID service record 定数を置く。
   - HID descriptor bytes、SDP attributes、record handle は値を変えない。値の意味を変える場合だけ `source-audit` を使う。

3. HIDP / ACL module
   - `_decode_hidp_output_report()`、`_drain_bumble_acl_queue()`、PSM 表示 helper を分ける。
   - queue drain は unit_005 の hardware oracle に近いので、connection queue、host fallback queue、no-progress stop の tests を先に green にしてから移す。

4. lifecycle module
   - connection request bridge、L2CAP lifecycle bridge、connection diagnostics registration は責務として分けたい。
   - `_l2cap_connected_emitted`、`_disconnected_callback_emitted`、diagnostics recording、callback dispatch が絡む。内部互換は捨ててよいが、observable diagnostics と connected/disconnected callback 発火条件は tests で固定する。

5. `BumbleHidTransport` に残すもの
   - public transport methods: `open()`、`start_advertising()`、`close()`、`request_disconnect()`、`list_bonded_peers()`、`connect_bonded_peer()`、`send_interrupt()`、`send_control()`、callback registration。
   - runtime ownership: handle、runtime、close lock、connected/disconnected emission state。
   - default transport factory から生成できること。`from swbt.transport.bumble import BumbleHidTransport` は任意互換。

### 8.8 tests の再考結果

`tests/unit/test_bumble_transport.py` は fake runtime 定義と behavior assertion が混在している。pytest docs の fixture 方針に合わせ、production 分割が green になった後で次の順に整理する。

1. fake class を `tests/unit/_bumble_fakes.py` 相当へ移す。
   - `FakeBumbleHandle`、`FakeBumbleDevice`、`FakeHidDevice`、`FakeConnection`、ACL queue fakes を移す。
   - production code から import しない。

2. fixture は状態変更単位で分ける。
   - open 済み runtime、advertising 済み runtime、L2CAP channel open、connection request bridge などを一括 fixture にしない。
   - teardown が必要な実リソースはこの unit の通常 tests では扱わない。

3. behavior tests は責務ごとに分ける。
   - key store tests、SDP tests、HIDP callback tests、ACL drain tests、L2CAP lifecycle tests、connection diagnostics tests。
   - test file 分割は最後に行う。先に fake helper を分けるだけでも読みやすさは改善する。

4. pytest import mode 変更は対象外。
   - 現在の `pyproject.toml` は `--strict-config --strict-markers` を使うが、`--import-mode=importlib` は採用していない。
   - import mode 変更は test collection 全体の挙動を変えるため、この unit では扱わない。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | reconnect strategy と output report dispatch を小さく分ける |
| `src/swbt/_gamepad_output.py` | new | output report parse、diagnostics、subcommand reply enqueue の内部部品 |
| `src/swbt/_gamepad_connection.py` | new | reconnect / connect workflow の内部部品 |
| `src/swbt/_gamepad_transport.py` | new | 既定 Bumble transport の遅延生成関数。public import 時に Bumble を解決しない |
| `src/swbt/transport/bumble.py` | delete / move / split | package 化する場合は `src/swbt/transport/bumble/` へ移す。内部 import path 互換は不要 |
| `src/swbt/transport/bumble/` | new / candidate | package 化した場合の transport 本体、key store、callback bridge、SDP / helper の置き場 |
| `src/swbt/transport/_bumble_*.py` | new / fallback | package 化しない場合の内部 helper 置き場 |
| `src/swbt/transport/_bumble_key_store.py` | new / modify | key store metadata reader、current / previous store、diagnostic wrapper、previous namespace prefix owner |
| `src/swbt/transport/_bumble_sdp.py` | new | Classic HID SDP service record builder |
| `src/swbt/transport/_bumble_hidp.py` | new | HIDP output report decode、SET_REPORT status constants、PSM display helper |
| `src/swbt/transport/_bumble_acl.py` | new | Bumble ACL packet queue drain |
| `src/swbt/transport/_bumble_lifecycle.py` | new | connection request bridge、L2CAP lifecycle bridge、connection diagnostics registration |
| `src/swbt/diagnostics.py` | modify | key store storage format knowledge を外へ出し、plain metadata を記録するだけにする |
| `tests/unit/test_bumble_key_store_metadata.py` | new | key store metadata reader の current / previous 判定を固定する |
| `tests/unit/test_gamepad_output_dispatcher.py` | new | output report dispatcher の trace と reply enqueue を単体で固定する |
| `tests/unit/test_gamepad_transport_factory.py` | new | default transport factory の resource config 受け渡しを単体で固定する |
| `tests/unit/test_gamepad_connection_workflow.py` | new | reconnect workflow の no-bond trace を単体で固定する |
| `tests/unit/test_bumble_sdp.py` | new | SDP builder の reference HID attributes を単体で固定する |
| `tests/unit/test_bumble_hidp.py` | new | HIDP output report decode を単体で固定する |
| `tests/unit/test_bumble_acl.py` | new | ACL queue drain の host fallback を単体で固定する |
| `tests/unit/test_bumble_lifecycle.py` | new | connection diagnostics registration の主要 event field を単体で固定する |
| `tests/unit/test_bumble_transport.py` | modify / split | fake runtime fixture と behavior tests を整理する |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify / split | connection / close / report / reconnect tests の grouping を整理する |
| `spec/wip/unit_020/STRUCTURAL_REFACTOR_BOUNDARIES.md` | new / modify | 作業範囲、原因分析、検証結果を記録する |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_diagnostics.py -q` | expected fail | red: `record_run_metadata()` が caller supplied key store metadata をまだ受け取れなかった |
| `uv run pytest tests/unit/test_diagnostics.py tests/unit/test_bumble_key_store_metadata.py tests/integration/test_switch_gamepad_fake_transport.py -q` | pass | 60 passed。`run_metadata` の key store fields と fake transport integration を確認 |
| `uv run ruff format --check src\swbt\diagnostics.py src\swbt\gamepad.py src\swbt\transport\bumble.py src\swbt\transport\_bumble_key_store.py tests\unit\test_diagnostics.py tests\unit\test_bumble_key_store_metadata.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\diagnostics.py src\swbt\gamepad.py src\swbt\transport\bumble.py src\swbt\transport\_bumble_key_store.py tests\unit\test_diagnostics.py tests\unit\test_bumble_key_store_metadata.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_gamepad_output_dispatcher.py -q` | expected fail | red: `swbt._gamepad_output` module がまだ存在しなかった |
| `uv run pytest tests\unit\test_gamepad_output_dispatcher.py tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | 54 passed。dispatcher 単体と fake transport の output report trace / status を確認 |
| `uv run ruff format --check src\swbt\_gamepad_output.py src\swbt\gamepad.py tests\unit\test_gamepad_output_dispatcher.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\_gamepad_output.py src\swbt\gamepad.py tests\unit\test_gamepad_output_dispatcher.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_gamepad_transport_factory.py -q` | expected fail | red: `swbt._gamepad_transport` module がまだ存在しなかった |
| `uv run pytest tests\unit\test_gamepad_transport_factory.py tests\unit\test_public_api_boundary.py -q` | pass | 16 passed。factory と public API import boundary を確認 |
| `uv run ruff format --check src\swbt\_gamepad_transport.py src\swbt\gamepad.py tests\unit\test_gamepad_transport_factory.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\_gamepad_transport.py src\swbt\gamepad.py tests\unit\test_gamepad_transport_factory.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_gamepad_connection_workflow.py -q` | expected fail | red: `swbt._gamepad_connection` module がまだ存在しなかった |
| `uv run pytest tests\unit\test_gamepad_connection_workflow.py tests\integration\test_switch_gamepad_fake_transport.py -q` | pass | 54 passed。workflow 単体と fake transport の reconnect / connect / cancellation を確認 |
| `uv run ruff format --check src\swbt\_gamepad_connection.py src\swbt\gamepad.py tests\unit\test_gamepad_connection_workflow.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\_gamepad_connection.py src\swbt\gamepad.py tests\unit\test_gamepad_connection_workflow.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_bumble_key_store_metadata.py -q` | expected fail | red: key store owner module に `_CurrentPreviousJsonKeyStore` / `_DiagnosticKeyStore` がまだ存在しなかった |
| `uv run pytest tests\unit\test_bumble_key_store_metadata.py tests\unit\test_bumble_transport.py -q` | pass | 42 passed。key store module と既存 Bumble transport behavior を確認 |
| `uv run ruff format --check src\swbt\transport\_bumble_key_store.py src\swbt\transport\bumble.py tests\unit\test_bumble_key_store_metadata.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\transport\_bumble_key_store.py src\swbt\transport\bumble.py tests\unit\test_bumble_key_store_metadata.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_bumble_sdp.py -q` | expected fail | red: `swbt.transport._bumble_sdp` module がまだ存在しなかった |
| `uv run pytest tests\unit\test_bumble_sdp.py tests\unit\test_bumble_transport.py -q` | pass | 39 passed。SDP builder と既存 Bumble transport behavior を確認 |
| `uv run ruff format --check src\swbt\transport\_bumble_sdp.py src\swbt\transport\bumble.py tests\unit\test_bumble_sdp.py tests\unit\test_bumble_transport.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\transport\_bumble_sdp.py src\swbt\transport\bumble.py tests\unit\test_bumble_sdp.py tests\unit\test_bumble_transport.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_bumble_hidp.py tests\unit\test_bumble_acl.py -q` | expected fail | red: `_bumble_hidp.py` と `_bumble_acl.py` がまだ存在しなかった |
| `uv run pytest tests\unit\test_bumble_hidp.py tests\unit\test_bumble_acl.py tests\unit\test_bumble_transport.py tests\unit\test_bumble_sdp.py -q` | pass | 42 passed。HIDP decode、SET_REPORT、ACL drain behavior を確認 |
| `uv run ruff format --check src\swbt\transport\_bumble_hidp.py src\swbt\transport\_bumble_acl.py src\swbt\transport\_bumble_sdp.py src\swbt\transport\bumble.py tests\unit\test_bumble_hidp.py tests\unit\test_bumble_acl.py tests\unit\test_bumble_transport.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\transport\_bumble_hidp.py src\swbt\transport\_bumble_acl.py src\swbt\transport\_bumble_sdp.py src\swbt\transport\bumble.py tests\unit\test_bumble_hidp.py tests\unit\test_bumble_acl.py tests\unit\test_bumble_transport.py` | pass | 対象変更の lint 確認 |
| `uv run pytest tests\unit\test_bumble_lifecycle.py -q` | expected fail | red: `swbt.transport._bumble_lifecycle` module がまだ存在しなかった |
| `uv run pytest tests\unit\test_bumble_lifecycle.py tests\unit\test_bumble_transport.py -q` | pass | 39 passed。connection diagnostics registration と transport behavior を確認 |
| `uv run ruff format --check src\swbt\transport\bumble.py src\swbt\transport\_bumble_lifecycle.py tests\unit\test_bumble_lifecycle.py` | pass | 対象変更の format 確認 |
| `uv run ruff check src\swbt\transport\bumble.py src\swbt\transport\_bumble_lifecycle.py tests\unit\test_bumble_lifecycle.py` | pass | 対象変更の lint 確認 |
| `uv run ruff format --check .` | pass | 66 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit tests\integration -q` | pass | 215 passed |
| `uv run pytest -m bumble` | not run | 実行には USB Bluetooth dongle open の明示承認が必要 |
| `uv run pytest -m hardware` | not run | 実行には Switch-facing 動作の明示承認が必要 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | この unit の通常作業ではなし。Bumble adapter test や hardware test を実行する場合は、対象 adapter、command、Switch-facing 動作、cleanup plan を確認する |
| adapter | 通常作業では未使用 |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | unit / integration test output。実機実行時だけ `docs/hardware-test-log.md` または該当 spec に記録する |
| cleanup | 通常作業ではなし。実機実行時は neutral、report loop stop、transport close、adapter release |

## 12. 先送り事項

- previous peer を使う reconnect fallback は扱わない。必要になった場合は、authentication failure 後の再試行可否を実機観測と分けて別 unit にする。
- key store 自動移行、復旧 CLI、secret store 対応は扱わない。
- `SwitchGamepad` の public API 再設計は扱わない。必要なら別 unit で利用者向け contract と一緒に設計する。
- `ConnectionResult` / `SwitchGamepadConfig` / `ConnectionStatus` の配置変更は、循環 import を避けるために必要になった場合だけ扱う。行数削減だけを理由に先に動かさない。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
