# Usage

この文書は目的別の利用例です。API の詳細な引数と例外は `docs/api.md` を参照してください。実機接続には専用 USB Bluetooth dongle、Bumble、対象機器側の pairing / reconnect 操作が必要です。

## Minimal Example

初回実行では `allow_pairing=True` を付け、対象機器を controller pairing / search 画面に置きます。

```python
import asyncio
from swbt import Button, SwitchGamepad


async def main() -> None:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        await pad.tap(Button.A)
        await pad.neutral()


asyncio.run(main())
```

`async with` は終了時に `close(neutral=True)` 相当で閉じます。`neutral()` は state update API であり、即時送信を保証しません。接続中は後続の periodic report で反映されます。

## Connection

### First-Run Pairing Or Reconnect Fallback

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.connect(timeout=30.0, allow_pairing=True)
```

`connect()` は保存済み bond があれば reconnect を先に試します。bond がない場合、`allow_pairing=True` のときだけ pairing へ進みます。

### Pairing Only

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.pair(timeout=30.0)
```

`pair()` は対象機器が controller pairing / search 画面にいるときだけ使います。

### Reconnect Only

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    await pad.reconnect(timeout=10.0)
```

`reconnect()` は key store に current bonded peer が 1 件ある状態だけを扱います。pairing fallback はしません。

### Handling Result Values

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    result = await pad.try_connect(timeout=30.0, allow_pairing=True)
    if result.status != "connected":
        print(result.status, result.route, result.peer_count)
```

```python
async with SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-bond.json",
) as pad:
    result = await pad.try_reconnect(timeout=10.0)
    if result.status == "no_bond":
        print("pairing is required")
```

`try_connect()` / `try_reconnect()` は接続戦略の結果を `ConnectionResult` で返します。key store の形式不一致や複数 current peers は `InvalidKeyStoreError` として扱います。

### Separate Key Stores By Target Device

```python
first = SwitchGamepad(
    adapter="usb:0",
    key_store_path="switch-2-fw-22-1-0.json",
)
second = SwitchGamepad(
    adapter="usb:0",
    key_store_path="other-switch.json",
)
```

1 つの key store に複数の current peer を混ぜないでください。別の対象機器へ pairing したい場合は、対象機器ごとに別の `key_store_path` を使います。

## Button Input

### Tap A

```python
await pad.tap(Button.A)
```

`tap()` は action API です。接続済みを要求し、押下と release の input report を即時送信します。

### Hold ZL And Tap A

```python
await pad.press(Button.ZL)
await pad.tap(Button.A)
await pad.release(Button.ZL)
```

`tap(Button.A)` は A だけを release します。事前に `press(Button.ZL)` した ZL は維持されます。

### Hold L+R Then Release

```python
import asyncio
from swbt import Button

await pad.press(Button.L, Button.R)
await asyncio.sleep(0.5)
await pad.release(Button.L, Button.R)
await pad.neutral()
```

`press()` / `release()` は state update API です。接続を要求せず、即時送信を保証しません。

## Stick Input

### Tilt The Left Stick

```python
from swbt import Stick

await pad.sticks(left=Stick.normalized(x=0.0, y=1.0))
```

`sticks()` は `Stick` だけを受けます。tuple や raw tuple は受けません。

### Press B And Tilt The Left Stick

複数の state update API 呼び出しは、同一 HID report に入る保証はありません。

```python
await pad.press(Button.B)
await pad.sticks(left=Stick.normalized(x=0.0, y=1.0))
```

完全同時入力が必要な場合は、complete `InputState` を作って `apply()` します。

```python
from swbt import Button, InputState, Stick

state = InputState.neutral().with_buttons([Button.B]).with_sticks(
    left_stick=Stick.normalized(x=0.0, y=1.0),
)
await pad.apply(state)
```

`apply()` は現在入力全体を置き換えます。差分適用ではありません。

## Neutral And Close

```python
await pad.neutral()
```

`neutral()` は local state を neutral に戻します。即時送信を保証しません。

```python
await pad.close(neutral=True)
```

`close(neutral=True)` は接続中なら trailing neutral を試みてから transport を閉じます。`async with` を使う場合は、通常は明示的に呼ぶ必要はありません。

## Diagnostics

```python
from pathlib import Path
from swbt import DiagnosticsConfig, SwitchGamepad

with Path("trace.jsonl").open("w", encoding="utf-8") as trace:
    async with SwitchGamepad(
        adapter="usb:0",
        key_store_path="switch-bond.json",
        diagnostics=DiagnosticsConfig(trace_writer=trace),
    ) as pad:
        await pad.connect(timeout=30.0, allow_pairing=True)
        status = pad.status()
        print(status.connection_state)
```

`DiagnosticsConfig(trace_writer=trace)` は JSON Lines trace を出します。`pad.status()` は connection state、report counter、last subcommand、raw rumble、last error を返します。

## Scope

初期 public API には duration 付き保持入力、入力列 runner、公開の現在入力送信 API、fluent builder API はありません。入力列や macro runner が必要になった場合は、利用者側で `asyncio` と公開 API を組み合わせてください。
