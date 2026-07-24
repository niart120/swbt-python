# 接続ライフサイクル

この文書では、Periodic / Direct 両方の `SwitchGamepad` の open から close までの状態遷移、neutral fail-safe、例外時の後始末、reconnect の扱いを定義する。

## 1. 状態一覧

`SwitchGamepad` は内部状態として次を持つ。

| 状態 | 意味 |
|---|---|
| `closed` | transport が開かれていない |
| `opening` | transport 初期化中 |
| `opened` | transport と内部 resource は開いているが、Bluetooth 上の接続開始処理はしていない |
| `advertising` | Switch から発見・接続可能な状態 |
| `pairing` | pairing または初回接続処理中 |
| `initializing` | HID control / interrupt channel は利用可能だが、初期 subcommand 応答と player assignment が未完了 |
| `connected` | supported report mode と 0 以外の player lights が同じ session で揃い、対応 reply の送信が完了した |
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
initializing
  ↓ protocol ready
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
4. `profile_path` がある場合は profile を検証し、CSR volatile identity を準備する
5. preparation 完了後に Bumble transport を構築し、callback を登録する
6. transport を open し、power-on 後の local address guard を通す
7. host要求状態とIMU encoding stateが初期値の`SwitchHidSession`、protocol、共通 sender を初期化する
8. `opened` 状態に入る
9. Periodic だけ `ReportLoop` task を起動可能な状態にする。Direct は周期 task を作らない

profile の validation、raw read、volatile write、warm reset、再列挙、read-back は HID advertising より前に完了する。current address が target と一致する場合は write と reset を省略する。write 開始後の状態を確定できない場合は `AdapterIdentityRecoveryRequired` を送出し、transport 構築と pairing へ進まない。

`open()` は Switch との接続完了を待たず、HID advertising も開始しない。Bluetooth 上で外部から見える接続開始は `pair()`、`connect()`、`reconnect()` が担当する。

adapter-default profile では、`pair()` / `reconnect()` が Bumble device を `power_on()` した後、public address を取得できない場合は `InvalidKeyStoreError` とする。discoverable / connectable の有効化と active reconnect は開始しない。`profile_path=None` の一時 controller 経路にはこの profile 用 guard を適用しない。

## 4. 接続開始 API

`SwitchGamepad` は resource open と Bluetooth 接続戦略を分ける。

| API | 主な用途 | Bluetooth 上の動作 |
|---|---|---|
| `pair(timeout=...)` | 初回 pairing | HID advertising / connectable を開始し、incoming 接続を待つ |
| `reconnect(timeout=...)` | 保存済み bond だけを使う再接続 | current peer の address / link key を使って active bond reuse reconnect を試行する |
| `try_reconnect(timeout=...)` | 再接続診断 | `ConnectionResult` で `no_bond`、`timeout`、`failed` を返す |
| `connect(timeout=..., allow_pairing=False)` | 通常利用 | bond があれば `reconnect()` を優先する。bond がなく、`allow_pairing=True` の場合だけ `pair()` へ進む |
| `try_connect(timeout=..., allow_pairing=False)` | 接続診断 | `ConnectionResult` で reconnect / pairing fallback の結果を返す |

`connect()` と `reconnect()` は成功した場合だけ戻る。失敗時に自動 advertising recovery や retry loop は開始しない。失敗理由は diagnostics に記録し、呼び出し側は例外または `try_` 系の `ConnectionResult` を見て次の操作を選ぶ。

current namespace に複数 peer がある key store は旧形式または不正形式として扱う。この場合は `InvalidKeyStoreError` を投げ、`ConnectionResult` には変換しない。

## 5. 接続完了時の処理

transport から connected callback を受けたら、次を行う。

1. 状態を `initializing` にする
2. link 接続と接続 route を diagnostics に記録する
3. host output report を受信し、subcommand reply を送れる状態にする
4. supported `0x03 30` と 0 以外の `0x30` player lights が同じ session で揃うまで待つ
5. predicate を成立させた reply の transport 送信後に状態を `connected` にする
6. Periodic は `ReportLoop` を開始する。Direct は周期送信を開始しない

HID control / interrupt channel の両方が利用可能になった時点は link connected であり、
public な接続完了ではない。`0x30 00` は初期化途中として記録し、成功条件にしない。
初期化中の Periodic 入力レポートは開始せず、subcommand reply の入力 prefix は neutral
state を使う。

接続待ちの timeout は、`pair()` / `connect()` / `reconnect()` の呼び出し単位で 1 個の
deadline として扱い、advertising または active reconnect から protocol ready までを
含める。時間内に `connected` へ到達しない場合は `ConnectionTimeoutError`、reply
送信失敗や ready 前 disconnect は `ConnectionFailedError` とし、half-ready 接続を
cleanup する。`try_connect()` / `try_reconnect()` は対応する `timeout` / `failed` を返す。

## 6. 入力送信中の処理

`connected` 状態では reporting type ごとに入力レポートの送信契機が異なる。

- Periodic は `ReportLoop` が単調時計上の固定 deadline ごとに `InputStateStore` の snapshot から `0x30` を生成する。snapshot、report build、transport enqueue の処理時間は次の待機時間から差し引く
- Periodic の処理が周期を超えた場合は過去 deadline を飛ばし、現在時刻以上の最初の deadline まで待つ。遅延 tick の burst 追送や古い state の queue は行わない
- Direct は `send()` または意味的入力操作ごとに候補 state の `0x30` を1件送る
- Direct は transport が入力レポートを受理した場合だけ候補 state を commit する。受理は controller flow-control completion や Switch への反映完了を意味しない
- host output report の `0x21` reply は reporting type に関係なく自動送信する
- `0x30` と `0x21` は共通 sender lock、timer、IMU encoding state を使う
- 送信失敗は diagnostics に記録する
- 継続不能な送信失敗では状態を `failed` にする

## 7. `neutral()` 処理

`neutral()` は現在入力を neutral state へ戻す。

```python
await pad.neutral()
```

Periodic の `neutral()` は次を保証する。

- `InputStateStore` の現在入力を neutral にする
- 接続中であれば、次 tick 以降に neutral report が送られる
- 即時送信が必要な場合は、内部 helper として trailing neutral report を送る

Direct の `neutral()` は接続済みを要求し、ニュートラル入力レポートを1件 transport に受理させてから current state を確定する。受理前の失敗では最後に受理された state を維持する。

## 8. `close()` 処理

```python
await pad.close(neutral=True)
```

`close()` は冪等にする。処理順序は次の通り。

1. 状態を `disconnecting` にする
2. `neutral=True` かつ接続中であれば neutral report を送る
3. Periodic の場合は `ReportLoop` を停止する
4. transport に切断を要求する。Bumble transport は保留中の interrupt ACL queue を drain してから L2CAP channel を切断する
5. transport を close する
6. callback を解除する
7. 状態を `closed` にする

close 中に neutral report 送信が失敗した場合、close 全体の完了を優先し、失敗は recoverable な diagnostics error として記録する。

pairing profile を使った場合も `close()` の責務は controller resource と接続を閉じることに限る。明示 address profile では volatile address を元へ戻さず、USB ドングルの抜き差しや read-only probe を要求しない。次の controller が同じ profile を開くときに current address が target なら、そのまま接続処理を続行する。adapter-default profile は open / close のどちらでも address を書き換えず、次回 `power_on()` 後に報告された current address の namespace を選ぶ。

## 9. neutral fail-safe

次の場合は、可能な範囲で neutral へ戻す。

- `close(neutral=True)` が呼ばれた
- `async with` を抜けた
- 利用者 task が cancel された
- disconnect callback を受けた
- heartbeat / timeout に相当する異常を検出した
- 送信 loop が例外で停止した

fail-safe は最善努力とする。Bluetooth link が切断済みの場合、wire 上に neutral report を送れないことがある。この場合でも、内部 `InputStateStore` は neutral へ戻す。

## 10. disconnect 処理

Switch 側から切断された場合、transport は disconnected callback を発火する。

処理は次の通り。

1. disconnect reason を diagnostics に記録する
2. Periodic の場合は `ReportLoop` を停止する
3. `InputStateStore` を neutral に戻す
4. bond reuse reconnect の対象であれば、M6 の作業仕様に従い active / incoming のどちらで扱うかを判定する
5. reconnect が無効、または reconnect 失敗時は clean close し、`closed` または `failed` へ遷移する

初期実装では reconnect を既定で無効にする。

## 11. reconnect

reconnect は M6 で扱う。初期実装では次だけを考慮する。

- Periodic / Direct の全 concrete controller は `profile_path` 内の namespace map を reconnect storage として使う
- default Bumble transport で `profile_path=None` の場合は、永続 bond を持たない一時的な仮想 controller として扱う
- injected transport では、`SwitchGamepad.profile_path is None` だけを根拠に reconnect 用 storage の有無を判断しない
- pairing 情報の保存有無を diagnostics に記録する
- current peer は自動 reconnect 対象の 1 件だけに正規化する
- pair 成功時、その peer を current にし、旧 current peer は previous generation へ退避する
- previous peer は自動 reconnect 対象にしない
- 複数 current peer を含む key store は自動移行せず、再作成と再 pairing を要求する

M6 では次を追加する。

- bond reuse reconnect の可否を active / incoming に分けて検証する
- reconnect 失敗時は failure diagnostics を残して clean close する
- reconnect 失敗後の自動 advertising recovery と retry loop は M6 に含めない
- link key なしの再 pairing と pairing-free reconnect を区別する

## 12. cancellation

利用者 task が cancel された場合でも、`async with` の `__aexit__` から `close(neutral=True)` を呼ぶ。

内部 task の cancel は次の順序で扱う。

1. Periodic の場合は `ReportLoop` に停止要求を出す
2. 一定時間待つ
3. 残っていれば task を cancel する
4. cancel 結果を diagnostics に記録する
5. transport close を実行する

## 13. concurrency

同時操作の方針は次の通り。

- Periodic の `apply()` と意味的入力操作は `InputStateStore` の lock で保護する
- Direct の `send()`、意味的入力操作、`tap()` は input operation lock で直列化し、transport 受理後の commit まで同じ operation とする
- `open()` と `close()` は lifecycle lock で直列化する
- subcommand による session 遷移、`0x21` ACK 送信、Periodic / Direct の `0x30` 生成は共通 sender lock で直列化する
- close / disconnect後の次の`open()`では新しい`SwitchHidSession`を作り、前回接続のreport mode、IMU mode、vibration状態、quaternion状態を引き継がない
- Direct の `tap()` は押下から解放まで input operation lock を保持する。解放送信に失敗した場合は最後に正常送信した押下 state を維持する

初期実装では、同一 `SwitchGamepad` に対する複雑な同時 macro 実行は保証しない。必要になった場合は、上位に macro scheduler を追加する。
