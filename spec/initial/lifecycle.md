# 接続ライフサイクル

この文書では、`SwitchGamepad` の open から close までの状態遷移、neutral fail-safe、例外時の後始末、reconnect の扱いを定義する。

## 1. 状態一覧

`SwitchGamepad` は内部状態として次を持つ。

| 状態 | 意味 |
|---|---|
| `closed` | transport が開かれていない |
| `opening` | transport 初期化中 |
| `opened` | transport と内部 resource は開いているが、Bluetooth 上の接続開始処理はしていない |
| `advertising` | Switch から発見・接続可能な状態 |
| `pairing` | pairing または初回接続処理中 |
| `connected` | HID control / interrupt channel が利用可能 |
| `disconnecting` | close または disconnect 処理中 |
| `failed` | 継続不能な例外が発生した状態 |

状態は diagnostics に記録する。public API では `status()` から読めるようにする。

## 2. 基本遷移

```text
closed
  ↓ open()
opening
  ↓ transport open complete
opened
  ↓ pair() / connect(allow_pairing=True)
advertising
  ↓ host connection started
pairing
  ↓ HID channels ready
connected
  ↓ close() / disconnect
 disconnecting
  ↓ cleanup complete
closed
```

失敗時は次のように遷移する。

```text
opening / opened / advertising / pairing / connected
  ↓ unrecoverable error
failed
  ↓ close()
closed
```

## 3. `open()` 処理

`open()` は次の順序で処理する。

1. 現在状態を確認する
2. `closed` でなければ適切に扱う
3. diagnostics を初期化する
4. transport callback を登録する
5. transport を open する
6. protocol と report loop を初期化する
7. `opened` 状態に入る
8. `ReportLoop` task を起動可能な状態にする

`open()` は Switch との接続完了を待たず、HID advertising も開始しない。Bluetooth 上で外部から見える接続開始は `pair()`、`connect()`、`reconnect()` が担当する。

## 4. 接続開始 API

`SwitchGamepad` は resource open と Bluetooth 接続戦略を分ける。

| API | 主な用途 | Bluetooth 上の動作 |
|---|---|---|
| `pair(timeout=...)` | 初回 pairing | HID advertising / connectable を開始し、incoming 接続を待つ |
| `reconnect(timeout=...)` | 保存済み bond だけを使う再接続 | 保存済み peer address / link key を使って active bond reuse reconnect を試行する |
| `connect(timeout=..., allow_pairing=False)` | 通常利用 | bond があれば `reconnect()` を優先する。bond がなく、`allow_pairing=True` の場合だけ `pair()` へ進む |

`connect()` は失敗時に自動 advertising recovery や retry loop を開始しない。失敗理由は diagnostics に記録し、呼び出し側が明示的に `pair()` へ戻る。

## 5. `wait_connected()` 処理

```python
await pad.wait_connected(timeout=30.0)
```

`wait_connected()` は状態が `connected` になるまで待つ。timeout が指定され、時間内に接続しない場合は `ConnectionTimeoutError` を投げる。

`wait_connected()` は複数 task から呼ばれてもよい。同じ接続完了 event を待つだけにする。

## 6. 接続完了時の処理

transport から connected callback を受けたら、次を行う。

1. 状態を `connected` にする
2. connection metadata を diagnostics に記録する
3. `ReportLoop` を開始する
4. neutral `InputState` を送信対象にする

HID control / interrupt channel の両方が必要な場合、transport 側で両 channel が利用可能になった時点を connected とする。

## 7. 入力送信中の処理

`connected` 状態では、`ReportLoop` が一定周期で送信する。

- reply queue に `0x21` がある場合はそれを優先送信する
- reply queue が空なら `InputStateStore` の snapshot から `0x30` を生成して送る
- 送信失敗は diagnostics に記録する
- 継続不能な送信失敗では状態を `failed` にする

## 8. `neutral()` 処理

`neutral()` は現在入力を neutral state へ戻す。

```python
await pad.neutral()
```

`neutral()` は次を保証する。

- `InputStateStore` の現在入力を neutral にする
- 接続中であれば、次 tick 以降に neutral report が送られる
- 即時送信が必要な場合は、内部 helper として trailing neutral report を送る

public API としては、`neutral()` が「状態を neutral に戻す」ことを意味する。wire 上で何回送るかは内部実装に閉じる。

## 9. `close()` 処理

```python
await pad.close(neutral=True)
```

`close()` は冪等にする。処理順序は次の通り。

1. 状態を `disconnecting` にする
2. `neutral=True` かつ接続中であれば neutral report を送る
3. `ReportLoop` を停止する
4. transport を close する
5. callback を解除する
6. 状態を `closed` にする

close 中に neutral report 送信が失敗した場合、例外を優先して外へ出すか、diagnostics 記録に留めるかは実装時に判断する。初期実装では、close 全体の完了を優先し、失敗は diagnostics に記録する。

## 10. neutral fail-safe

次の場合は、可能な範囲で neutral へ戻す。

- `close(neutral=True)` が呼ばれた
- `async with` を抜けた
- 利用者 task が cancel された
- disconnect callback を受けた
- heartbeat / timeout に相当する異常を検出した
- 送信 loop が例外で停止した

fail-safe は最善努力とする。Bluetooth link が切断済みの場合、wire 上に neutral report を送れないことがある。この場合でも、内部 `InputStateStore` は neutral へ戻す。

## 11. disconnect 処理

Switch 側から切断された場合、transport は disconnected callback を発火する。

処理は次の通り。

1. disconnect reason を diagnostics に記録する
2. `ReportLoop` を停止する
3. `InputStateStore` を neutral に戻す
4. bond reuse reconnect の対象であれば、M6 の作業仕様に従い active / incoming のどちらで扱うかを判定する
5. reconnect が無効、または reconnect 失敗時は clean close し、`closed` または `failed` へ遷移する

初期実装では reconnect を既定で無効にする。

## 12. reconnect

reconnect は M6 で扱う。初期実装では次だけを考慮する。

- `key_store_path` を設定できる
- pairing 情報の保存有無を diagnostics に記録する
- reconnect を public API として保証しない

M6 では次を追加する。

- bond reuse reconnect の可否を active / incoming に分けて検証する
- reconnect 失敗時は failure diagnostics を残して clean close する
- reconnect 失敗後の自動 advertising recovery と retry loop は M6 に含めない
- link key なしの再 pairing と pairing-free reconnect を区別する

## 13. cancellation

利用者 task が cancel された場合でも、`async with` の `__aexit__` から `close(neutral=True)` を呼ぶ。

内部 task の cancel は次の順序で扱う。

1. `ReportLoop` に停止要求を出す
2. 一定時間待つ
3. 残っていれば task を cancel する
4. cancel 結果を diagnostics に記録する
5. transport close を実行する

## 14. concurrency

同時操作の方針は次の通り。

- `set_input()`、`press()`、`release()`、`neutral()` は `InputStateStore` の lock で保護する
- `open()` と `close()` は lifecycle lock で直列化する
- `tap()` は途中で他 task の `set_input()` と競合する可能性があるため、documented behavior を明確にする

初期実装では、同一 `SwitchGamepad` に対する複雑な同時 macro 実行は保証しない。必要になった場合は、上位に macro scheduler を追加する。
