# Public API

この文書は `swbt-python` の公開 API 仕様です。通常利用では `swbt` module root から import します。

```python
from swbt import Button, InputState, Stick, SwitchGamepad
```

`swbt.gamepad.*` や `swbt.transport.*` の deep import は、テスト、移行作業、custom transport 実装時だけに限定してください。`HidDeviceTransport` は custom transport 用の public extension point です。Bumble 型を public API に露出しません。

## Top-Level Exports

`swbt.__all__` の公開名は次の通りです。

| name | 用途 |
|---|---|
| `SwitchGamepad` | 利用者が操作する仮想 gamepad |
| `SwitchGamepadConfig` | `from_config()` 用の resource 設定 |
| `ConnectionResult` | `try_connect()` / `try_reconnect()` の結果 |
| `Button` | 対応ボタン |
| `Stick` | 12-bit stick 位置 |
| `IMUFrame` | IMU frame 値 |
| `InputState` | immutable な完全入力状態 |
| `DiagnosticsConfig` | diagnostics trace 設定 |
| `GamepadStatus` | `status()` の snapshot |
| `HidDeviceTransport` | custom transport の Protocol |
| `BondedPeer` | transport が返す bonded peer 候補 |
| `DisconnectRequestResult` | remote disconnect request の結果 |
| `SwbtError` | swbt 例外の基底 class |
| `TransportOpenError` | adapter / transport open 失敗 |
| `ConnectionTimeoutError` | 接続待ち timeout |
| `ConnectionFailedError` | timeout 以外の接続不成立 |
| `ClosedError` | 接続済みまたは open 済み resource が必要な操作の失敗 |
| `InvalidInputError` | 引数値や入力値の不正 |
| `InvalidKeyStoreError` | key store の未対応形式または複数 current peer |

## SwitchGamepad

### Construction

```python
pad = SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
    report_period_us=8000,
    device_name="Pro Controller",
    diagnostics=None,
)
```

`adapter` は default Bumble transport に渡す adapter moniker です。default transport を使う場合は必須です。`transport` を注入する custom transport では `adapter` を省略できます。

`key_store_path` は default Bumble transport が pairing key を保存する JSON key store path です。1 つの仮想 controller と 1 つの対象機器の組み合わせごとに分けてください。`None` は永続 bond を持たない一時的な controller を意味します。

`report_period_us` は periodic input report の送信周期です。`device_name` は HID Device として出す表示名です。

`SwitchGamepadConfig` は同じ resource 設定を値として保持します。

```python
config = SwitchGamepadConfig(
    adapter="usb:0",
    key_store_path="switch-bond.json",
    report_period_us=8000,
    device_name="Pro Controller",
)
pad = SwitchGamepad.from_config(config)
```

`SwitchGamepad.from_config(config)` は `SwitchGamepad` を返します。

### Resource Scope

```python
async with SwitchGamepad(adapter="usb:0", key_store_path="switch-bond.json") as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
    await pad.tap(Button.A)
```

`async with` は `open()` と `close(neutral=True)` の resource scope です。`__aenter__()` は advertising、pairing、reconnect を開始しません。

`open()` は transport、callback、diagnostics、report loop を準備します。HID advertising は開始しません。transport open に失敗した場合は `TransportOpenError` または lower layer の例外を返します。

`close(neutral=True)` は接続中なら trailing neutral を試み、report loop を止め、remote disconnect request を試し、transport を閉じます。複数回呼んでも未完了の後始末だけを処理します。

### Connection

| method | contract |
|---|---|
| `pair(timeout=None)` | 初回 pairing 用。HID advertising を開始し、host 接続を待つ。 |
| `reconnect(timeout=None)` | 保存済み bond が 1 件ある場合だけ active reconnect を試す。pairing fallback はしない。 |
| `try_reconnect(timeout=None)` | reconnect 結果を `ConnectionResult` として返す。 |
| `connect(timeout=None, allow_pairing=False)` | bond があれば reconnect を優先し、bond がない場合は `allow_pairing=True` のときだけ pairing へ進む。 |
| `try_connect(timeout=None, allow_pairing=False)` | `connect()` と同じ戦略を使い、結果を `ConnectionResult` として返す。 |

`connect()` / `reconnect()` は成功した場合だけ戻ります。接続できない場合は `ConnectionFailedError`、timeout は `ConnectionTimeoutError` です。current peer が複数ある key store は推測せず、`InvalidKeyStoreError` とします。

`ConnectionResult` は `route`、`status`、`peer_address`、`peer_count` を持ちます。`status` は `"connected"`、`"no_bond"`、`"timeout"`、`"failed"` のいずれかです。

### Input

入力 API は state update API、action API、complete state API に分かれます。

| method | 種別 | contract |
|---|---|---|
| `press(*buttons)` | state update API | 現在の button set に button を追加する。即時送信を保証しない。 |
| `release(*buttons)` | state update API | 現在の button set から button を取り除く。即時送信を保証しない。 |
| `sticks(left=None, right=None)` | state update API | 指定された stick だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `lstick(stick)` | state update API | left stick だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `rstick(stick)` | state update API | right stick だけを置き換える。`Stick` 以外は `InvalidInputError`。即時送信を保証しない。 |
| `neutral()` | state update API | `InputState.neutral()` 相当に戻す。即時送信を保証しない。 |
| `apply(state)` | complete state | 完成済み `InputState` で現在入力全体を置き換える。差分適用ではない。 |
| `tap(*buttons, duration=0.08)` | action API | 接続済みを要求し、押下 report と release report を即時送信する。 |

`tap()` の release は、この呼び出しで渡した button だけを解除します。事前に `press()` していた別 button は維持します。

`lstick(stick)` は `sticks(left=stick)`、`rstick(stick)` は `sticks(right=stick)` と同じ state update API です。左右を同じ状態更新で置き換える場合は `sticks(left=..., right=...)` を使います。

`press()` の直後に `lstick()`、`rstick()`、`sticks()` を呼んでも、同一 HID report に入る保証はありません。button と stick を完全な同時入力として扱う場合は complete state を作り、`apply(state)` に渡してください。

```python
state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.up(),
)
await pad.apply(state)
```

### Observation

`snapshot()` は現在の `InputState` を返します。`status()` は `GamepadStatus` を返します。

`GamepadStatus` は `connection_state`、`report_counters`、`last_subcommand_id`、`raw_rumble`、`last_error` を持ちます。状態監視や diagnostics の確認用であり、高頻度 control path には使いません。

## Input Model

`Button` は `A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`LEFT_STICK`、`RIGHT_STICK`、`DPAD_UP`、`DPAD_DOWN`、`DPAD_LEFT`、`DPAD_RIGHT` を持ちます。

`Stick.center()` は中央位置を返します。`Stick.raw(x=..., y=...)` は `0..4095` の raw 値を受けます。`Stick.normalized(x=..., y=...)` は `-1.0..1.0` を raw 値へ変換します。

`Stick.tilt(x, y)` は `Stick.normalized(x=x, y=y)` と同じ正規化座標を使う短い生成 API です。`Stick.up(amount=1.0)`、`Stick.down(amount=1.0)`、`Stick.left(amount=1.0)`、`Stick.right(amount=1.0)` は単一方向の倒し込み量を `0.0..1.0` で受けます。`amount=0.0` は中央、`amount=1.0` は全倒しです。`Stick.tilt(1.0, 1.0)` は x/y を個別に検証する既存の矩形座標モデルとして許可します。

`IMUFrame.neutral()` は移動なしの IMU frame を返します。`InputState.neutral()` は button なし、左右 stick 中央、neutral IMU frame の状態を返します。`InputState.with_buttons(...)` と `InputState.with_sticks(...)` は新しい immutable state を返します。

## Errors And Diagnostics

例外は `SwbtError` を基底にします。利用者入力の不正は `InvalidInputError`、transport open 失敗は `TransportOpenError`、接続 timeout は `ConnectionTimeoutError`、接続不成立は `ConnectionFailedError`、key store 形式不一致は `InvalidKeyStoreError` です。

`DiagnosticsConfig(trace_writer=...)` を渡すと JSON Lines trace を記録します。raw link key などの secret material は記録しません。

## Transport Extension Point

custom transport は `HidDeviceTransport` を満たす object として `SwitchGamepad(transport=...)` に渡します。`open()`、`start_advertising()`、`close()`、interrupt/control send、callback registration、bonded peer listing、active reconnect を transport 側で実装します。

`SwitchGamepad` は injected transport に `adapter` や `key_store_path` を後から設定しません。key store が必要な custom transport は、その constructor で設定を受けてください。
