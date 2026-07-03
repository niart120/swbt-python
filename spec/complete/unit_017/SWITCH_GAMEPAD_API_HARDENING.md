# SwitchGamepad API Hardening 仕様書

## 1. 概要

### 1.1 目的

`SwitchGamepad` の公開 API を、通常利用だけでなく、複数 Switch / 複数 bond / 接続失敗 / 入力送信失敗の視点で整理する。

今回のレビューで問題になった中心は、接続戦略の戻り値と例外が混在していること、`key_store_path` が constructor 状態として固定されていること、入力状態の fail-safe が一部弱いこと、公開 API と top-level export が一致していないことである。

この unit では、利用者向けの成功必須 API と、診断向けの結果返却 API を分ける。あわせて、入力 validation、`tap()` / `close()` の後始末、`from_config()`、主要例外と transport 型の top-level export をまとめて扱う。非同期エラー通知の追加は対象外にし、`status().last_error` の改善とは別 unit に送る。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user review input | ChatGPT-5.5 review と人間コメント。`key_store_path` の接続時引数化、`try_` API、`tap()` / `close()` fail-safe、`from_config()`、例外 export、validation、adapter 明示化を扱う | conversation, 2026-07-03 |
| api design | `SwitchGamepad`、`SwitchGamepadConfig`、`connect()` / `reconnect()` / `pair()`、入力操作、例外設計 | `spec/initial/api.md` |
| lifecycle | resource open と接続開始 API、close、neutral fail-safe、reconnect failure diagnostics | `spec/initial/lifecycle.md` |
| testing | fake transport integration、neutral fail-safe、callback 例外、reconnect tests | `spec/initial/testing.md` |
| risks | reconnect の不確実性、OS / adapter 差分、report period / scheduler jitter | `spec/initial/risks.md` |
| completed unit | context manager は resource scope であり、`open()` は advertising / pairing / reconnect を開始しない | `spec/complete/unit_015/CONTEXT_MANAGER_RESOURCE_SCOPE.md` |
| completed unit | close / disconnect cleanup contract。trailing neutral、disconnect request、transport close の順序を固定済み | `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md` |
| completed unit | reconnect / key store / diagnostics。`ConnectionResult` と active reconnect status の現状 | `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md` |
| implementation-before | 実装前の `SwitchGamepad` は constructor に `adapter="usb:0"` と `key_store_path` を持ち、`connect()` / `reconnect()` は `ConnectionResult` を返していた | `src/swbt/gamepad.py` |
| implementation-before | 実装前は `Stick.raw()` / `normalized()` は validation するが dataclass 直接生成では validation が走らなかった。`IMUFrame` も範囲 validation がなかった | `src/swbt/input.py` |
| implementation-before | 実装前の `swbt.__all__` は主要例外と `HidDeviceTransport` を top-level export していなかった | `src/swbt/__init__.py` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| library user | `await pad.connect(...)` | 接続できた場合だけ戻る。失敗は例外で分かる | 詳細 status が必要なら `try_connect()` を使う |
| diagnostic user | `await pad.try_connect(...)` / `await pad.try_reconnect(...)` | `ConnectionResult` で `no_bond`、`ambiguous_bond`、`timeout`、`failed` を読める | automatic advertising recovery はしない |
| library user | `key_store_path` を接続時に渡す | 接続試行単位で key store を選べる | constructor の内部状態として固定しない |
| library user | `await pad.tap(Button.A)` が送信途中で失敗する | 内部 button state が押下のまま残らない | cancellation は握りつぶさない |
| library user | `async with` を抜けるときに neutral 送信が失敗する | close cleanup は可能な範囲で最後まで進む | neutral 送信失敗は diagnostics に残す |
| library user | `Stick(x=-1, y=999999)` や過大な `IMUFrame` を直接作る | 生成時に `InvalidInputError` で落ちる | report loop で後から壊さない |
| library user | 複数 adapter / 複数 Switch を扱う | adapter を明示し、trace metadata が誤読されない | 初期対象は 1 adapter = 1 virtual controller = 1 host connection |

## 2. 対象範囲

- `connect()` / `reconnect()` を成功しなければ例外に寄せる。
- `try_connect()` / `try_reconnect()` を追加し、現行の `ConnectionResult` 返却経路を移す。
- `key_store_path` を `connect()` / `try_connect()` / `reconnect()` / `try_reconnect()` / `pair()` の接続時入力として扱う。
- `key_store_path=None` で reconnect できないことを diagnostics event で明示する。
- `SwitchGamepad.from_config()` を追加する。
- `adapter="usb:0"` の暗黙 default を廃止し、default transport では adapter 指定を必須にする。
- custom transport 指定時の run metadata が `usb:0` と誤記録されないようにする。
- `ClosedError`、`ConnectionFailedError`、`ConnectionTimeoutError`、`TransportOpenError`、`InvalidInputError`、`SwbtError`、`HidDeviceTransport`、`DisconnectRequestResult`、`BondedPeer` を top-level export する。
- `press()` / `release()` docstring に即時送信ではないことを明記する。
- `tap()` は接続済み確認を先に行い、送信失敗時も内部 state を戻す。
- `close(neutral=True)` の neutral 送信を best-effort にし、後続 cleanup を継続する。
- `Stick`、`IMUFrame`、`report_period_us` の validation を constructor / `__post_init__` に寄せる。
- README / API docs / docstring tests を公開 API 変更に合わせて更新する。

## 3. 対象外

- `wait_failed()`、`raise_if_failed()`、`on_error` callback などの非同期エラー通知 API。
- previous key set を使う reconnect fallback。これは `unit_016` 以降の key store 世代管理で扱う。
- 複数 controller 同時接続の実装。
- automatic advertising recovery と retry loop。
- Switch HID report byte、subcommand reply、SDP / HID descriptor の変更。
- 実機 reconnect の再検証。API contract の自動 test を先に固定する。

## 4. 関連 docs

- `spec/initial/api.md`
- `spec/initial/lifecycle.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_007/M6_RECONNECT_KEYSTORE_DIAGNOSTICS.md`
- `spec/complete/unit_014/DEVICE_CLOSE_GRACEFUL_DISCONNECT.md`
- `spec/complete/unit_015/CONTEXT_MANAGER_RESOURCE_SCOPE.md`
- `README.md`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | 公開 API と入力 validation の変更であり、report byte layout は変更しない |
| Bumble / transport | not applicable | implementation-fact-only | default transport の adapter / key store 設定の渡し方は変えるが、Bumble の HID Device / L2CAP / SDP 仮定は追加しない。Bumble 型は引き続き public API に露出しない |
| OS / driver / adapter | not applicable | implementation-fact-only | adapter の暗黙 default を廃止し、trace metadata の誤読を減らす。adapter open や driver 挙動の新規実機観測は行わない |

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| required adapter | default transport で `adapter` 未指定 | `InvalidInputError` を投げる | custom transport 指定時は adapter なしを許す |
| config construction | `SwitchGamepad.from_config(config)` | `SwitchGamepadConfig` の値で gamepad を生成する | config は resource 設定に寄せる |
| connection key store | `connect(key_store_path=...)` | その接続試行の key store として使う | constructor 固定値より接続時入力を優先する |
| missing key store reconnect | `try_reconnect(key_store_path=None)` | `ConnectionResult(status="no_bond")` と diagnostics event を返す | 次回も reconnect できないことが trace から分かる |
| success API | `connect()` / `reconnect()` が接続できない | `ConnectionTimeoutError` または接続失敗系例外を投げる | 戻り値と例外の混在を避ける |
| try API | `try_connect()` / `try_reconnect()` が接続できない | 例外ではなく `ConnectionResult` を返す | cancellation は伝播させる |
| pairing timeout | `connect(allow_pairing=True)` の pairing fallback が timeout | `ConnectionTimeoutError` を投げる | `try_connect()` では `ConnectionResult(status="timeout")` |
| ambiguous bond | 複数 bond がある | `connect()` は接続失敗系例外、`try_connect()` は `ambiguous_bond` | 自動選択しない |
| tap precondition | 未接続で `tap()` | state を変更せず `ClosedError` | 押下 state が残らない |
| tap send failure | press 送信後に失敗 | `release()` または `neutral()` 相当で内部 state を戻す | release report 送信は best-effort |
| press / release docs | `press()` / `release()` を呼ぶ | state 更新のみ。即時送信ではない | 次の periodic report または内部送信で反映 |
| close neutral failure | trailing neutral 送信が失敗 | recoverable error を diagnostics に記録し、report loop stop、disconnect request、transport close へ進む | close の主目的は後始末 |
| stick validation | `Stick(...)` 直接生成 | raw range 外なら `InvalidInputError` | factory と直接 constructor の差をなくす |
| IMU validation | `IMUFrame(...)` 直接生成 | 16-bit signed range 外なら `InvalidInputError` | report loop の `OverflowError` を防ぐ |
| report period validation | `report_period_us <= 0` | `InvalidInputError` | 下限値は設けない |
| top-level export | `from swbt import ConnectionFailedError, ConnectionTimeoutError, HidDeviceTransport` | import できる | public constructor に現れる型と例外を取得可能にする |
| custom transport metadata | `SwitchGamepad(transport=fake)` | diagnostics は custom transport と分かる内容を記録し、未指定 adapter を `usb:0` と記録しない | test / extension 用 escape hatch |

## 7. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | default transport で adapter 未指定なら `InvalidInputError` になる | new | unit | no | `tests/unit/test_public_api_boundary.py` |
| green | custom transport 指定時は adapter 未指定でも使え、run metadata が `usb:0` と誤記録されない | regression | integration | no | fake transport で `adapter="custom"` を確認 |
| green | `SwitchGamepad.from_config()` が config 値を default transport 生成へ渡す | new | unit | no | `adapter`、`device_name`、`report_period_us` を固定 |
| green | `connect()` は `try_reconnect()` の `no_bond` / `ambiguous_bond` / `timeout` / `failed` を成功扱いしない | new | integration | no | `connect()` / `reconnect()` は失敗時に例外 |
| green | `try_connect()` / `try_reconnect()` は現行 `ConnectionResult` 相当の詳細 status を返す | new | integration | no | diagnostic use case を残した |
| green | `connect(key_store_path=...)` / `pair(key_store_path=...)` が接続時 key store として記録される | new | integration | no | constructor 固定値ではなく接続時入力を使う |
| green | `key_store_path=None` で reconnect 不可能な場合に diagnostics event が出る | new | integration | no | `reconnect_key_store_unavailable` |
| green | open 済み gamepad で別 `key_store_path` へ差し替えようとすると `InvalidInputError` になる | edge | integration | no | Bumble runtime の曖昧な差し替えを避ける |
| green | `tap()` は未接続時に state を変更せず `ClosedError` を投げる | edge | integration | no | snapshot に Button が残らないことを確認 |
| green | `tap()` の press 側送信失敗でも内部 state が neutral または release 済みになる | edge | integration | no | fake transport の send failure で固定 |
| green | `close(neutral=True)` の trailing neutral 送信が失敗しても transport close まで進む | edge | integration | no | diagnostics は recoverable error を記録する |
| green | `press()` / `release()` docstring が即時送信ではないことを説明する | regression | unit | no | public API docstring test |
| green | `Stick(...)` 直接生成が raw range 外を拒否する | edge | unit | no | factory と同じ `InvalidInputError` |
| green | `IMUFrame(...)` 直接生成が 16-bit signed range 外を拒否する | edge | unit | no | report build 時の `OverflowError` を前倒しする |
| green | `report_period_us <= 0` は constructor / `from_config()` で拒否される | edge | unit | no | 下限値は設けない |
| green | 主要例外と `HidDeviceTransport` 関連型が top-level import できる | regression | unit | no | `swbt.__all__` と import surface を固定 |
| deferred | `status().last_error` 以外の非同期エラー通知 API を設計する | deferred | docs | no | この unit では実装しない |

status は `todo`、`red`、`green`、`refactor-done`、`refactor-skipped`、`deferred` を使う。

## 8. 設計メモ

- `connect()` / `reconnect()` は利用者向けの「接続できたら戻る」API にする。接続できなかった理由を分岐したい場合は `try_connect()` / `try_reconnect()` を使う。
- `ConnectionResult` は削除しない。route、status、peer address、peer count を読む用途は diagnostics と分岐制御に残る。
- `pair()` は初回 pairing の明示入口であり、成功時は値を返さない。`try_connect(allow_pairing=True)` は pairing fallback の結果を `ConnectionResult(route="pairing", status="connected")` として返せる。
- `key_store_path` は接続時の入力として扱う。`async with SwitchGamepad(adapter="usb:0") as pad: await pad.connect(key_store_path="switch-bond.json")` を主要導線にする。
- `open()` が context manager resource scope であることは維持する。ただし接続時 key store を扱うため、default transport の key store 設定は `pair()` / `reconnect()` 前に反映できる構造へ寄せる。既に open 済みで異なる key store を指定された場合は、黙って無視せず `InvalidInputError` にする。
- `SwitchGamepadConfig` は resource 設定へ寄せる。`adapter`、`report_period_us`、`device_name` は config に残し、connection-specific な `key_store_path` は接続 method の引数へ移す。
- `adapter` の暗黙 default は複数 adapter / 複数 Switch の誤用を招く。default transport では明示指定を必須にする。custom transport を渡す test では adapter を要求しない。
- `HidDeviceTransport` は Bumble 型ではなく repo-local Protocol である。constructor が `transport` を受ける以上、top-level export しても Bumble 依存は漏れない。
- `tap()` の `try/finally` は入力操作の安全性を優先する。性能面の影響は `tap()` が短時間 helper であることと、既に即時送信を行っていることから受け入れる。高頻度入力は `press()` / `release()` と periodic report loop を使う。
- `close()` は cleanup API として扱う。neutral 送信失敗は diagnostics に残すが、report loop stop、disconnect request、transport close を止めない。
- `report_period_us` の下限は設けない。0 以下だけを拒否する。
- unsupported subcommand 後の通知 API は先送りにする。現状の `status().last_error` は残し、能動的 notification は別 unit で扱う。

## 9. 対象ファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/gamepad.py` | modify | `try_connect()` / `try_reconnect()`、成功必須 `connect()` / `reconnect()`、接続時 `key_store_path`、`from_config()`、adapter validation、tap / close fail-safe |
| `src/swbt/input.py` | modify | `Stick.__post_init__`、`IMUFrame.__post_init__` validation |
| `src/swbt/errors.py` | modify | 接続失敗系例外を追加する場合の置き場 |
| `src/swbt/__init__.py` | modify | 主要例外と transport boundary 型の top-level export |
| `src/swbt/diagnostics.py` | modify | missing key store / custom transport metadata を必要に応じて記録 |
| `src/swbt/transport/base.py` | modify | top-level export 対象として docstring / public surface を確認 |
| `tests/unit/test_public_api_boundary.py` | modify | top-level export、Bumble 非露出、adapter validation、from_config |
| `tests/unit/test_public_api_docstrings.py` | modify | `press()` / `release()` の非即時送信説明、try API docstring |
| `tests/unit/test_input_state.py` | modify | direct constructor validation |
| `tests/integration/test_switch_gamepad_fake_transport.py` | modify | try API、connect exception、tap fail-safe、close best-effort、metadata |
| `tests/unit/test_probe_cli.py` | modify | `swbt-probe pair` が接続時 key store を渡すことを固定 |
| `tests/hardware/test_reconnect_keystore.py` | modify | 実機 characterize test を新 API に追従。実行はしない |
| `src/swbt/probe.py` | modify | `pair(key_store_path=...)` を使う |
| `examples/*.py` | modify | constructor 固定 key store を廃止 |
| `README.md` | modify | adapter 明示、connection-time key store、try API の使い分け |
| `spec/initial/api.md` | modify | 公開 API 正本の更新 |
| `spec/initial/lifecycle.md` | modify | 接続失敗と close best-effort の整理 |
| `spec/initial/transport-bumble.md` | modify | transport Protocol 例を現行境界へ更新 |
| `spec/complete/unit_017/SWITCH_GAMEPAD_API_HARDENING.md` | move / modify | TDD 状態、検証、先送り事項を更新 |

## 10. 検証

| command | result | notes |
|---|---|---|
| `uv sync --dev` | pass | Resolved / Checked 41 packages |
| `uv run ruff format --check .` | pass | 50 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests\unit -q` | pass | 137 passed |
| `uv run pytest tests\integration -q` | pass | 56 passed |
| `uv run pytest --collect-only tests\hardware -q` | pass | 12 tests collected。実機は未実行 |

## 11. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | not required |
| 承認範囲 | なし。この unit は public API と fake transport integration の自動 test で固定する |
| adapter | 実機未使用。docs では adapter 明示を扱う |
| 実行遮断 | 環境変数による遮断は採用しない。実機 test を追加する場合は別途明示承認、対象 adapter、command、cleanup plan を確認する |
| log / artifact | unit / integration test output。実機 trace は不要 |
| cleanup | なし |

## 12. 先送り事項

- `wait_failed()`、`raise_if_failed()`、`on_error` callback などの非同期エラー通知 API は別 unit に送る。
- previous key set を使う reconnect fallback は `unit_016` の current / previous 世代管理後に判断する。
- 複数 controller 同時接続は初期対象外のままにする。今回の範囲では adapter 明示と trace metadata の誤読防止までに留める。
- `press(send=True)`、`send()`、`hold()` などの即時送信 API 追加は採用しない。今回の範囲では docstring に即時送信ではないことを明記する。

## 13. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] TDD Test List を更新した
- [x] 必要な根拠監査を記録した
- [x] 実機実行条件を記録した
- [x] 検証結果または未実行理由を記録した
