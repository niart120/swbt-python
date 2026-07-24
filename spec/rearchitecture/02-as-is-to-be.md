# 02. 現在の構造

## 公開生成経路

```text
swbt.ProController(...)       ┐
swbt.JoyConL(...)             ├─ 具象クラスが固定のプロファイルを選ぶ
swbt.JoyConR(...)             │
swbt.DirectProController(...) │
swbt.DirectJoyConL(...)       │
swbt.DirectJoyConR(...)       ┘
        │
        └─ SwitchGamepad の共通公開操作
             └─ ControllerRuntime が実行状態を所有
```

`SwitchGamepad` は直接生成できない公開共通型であり、ライフサイクル、接続、入力操作、状態取得を一度だけ実装する。具象コントローラーはコントローラー形状、送信方式、公開コンストラクターを定義する。状態を持つ処理は `ControllerRuntime` が所有する。

```text
SwitchGamepad
  ├─ PeriodicSwitchGamepad
  │   ├─ ProController
  │   ├─ JoyConL
  │   └─ JoyConR
  └─ DirectSwitchGamepad
      ├─ DirectProController
      ├─ DirectJoyConL
      └─ DirectJoyConR
```

## モジュールの責務

```text
src/swbt/gamepad/
  __init__.py          # 公開 gamepad export
  interface.py         # 公開抽象型と共通の実行状態への委譲
  controllers.py       # 6 個の公開具象クラス
  runtime.py           # 内部 ControllerRuntime
  _config.py           # 正規化済みの内部 gamepad 設定
  connection.py        # 接続処理
  output.py            # 出力レポートの振り分け
  transport_factory.py # 既定の下位通信実装の生成
```

具象コントローラーは `controllers.py`、共通公開操作は `interface.py` に置く。責務を表さない単一モジュールへ再集約しない。

## Boundary rules

### コントローラー形状

`ProController`、`JoyConL`、`JoyConR` とそれぞれの直接送信型は、対応する profile を class 属性として固定する。`profile` と `device_name` は公開コンストラクターで受け取らない。

### 利用者が指定する設定

利用者が指定できる値は `adapter`、`profile_path`、`report_period_us`、`controller_colors`、`diagnostics` である。`profile_path` は Bluetooth アドレスの選択方法とペアリングキーを保存する swbt プロファイルへのパスであり、コントローラー形状と接続先ごとに分ける。

### 下位通信実装の境界

Bluetooth の下位通信実装は内部実装である。公開コンストラクターに `transport` はなく、通常経路では実行状態が `create_default_transport()` を呼ぶ。リポジトリ内のテストだけが `tests/gamepad_factory.py` から `ControllerRuntime` のコンストラクターを差し替える。配布パッケージにテスト用の生成処理やコンストラクターを介さない生成経路は置かない。

### 依存方向

```text
swbt.__init__
  └─ swbt.gamepad.controllers
      └─ swbt.gamepad.interface
          └─ swbt.gamepad.runtime
              ├─ swbt.protocol.*
              ├─ swbt.report_loop
              ├─ swbt.gamepad.connection
              ├─ swbt.gamepad.output
              └─ swbt.gamepad.transport_factory
```

`swbt.protocol.*` は `swbt.gamepad.*` に依存しない。`swbt` モジュール直下から `ControllerProfile` や `HidDeviceTransport` を公開しない。`ControllerKind` による分岐はプロファイル生成とテストに局所化し、実行状態、レポート、下位通信実装へ広げない。
