# 03. 公開 API、設定、プロファイルの方針

## 公開 API

コントローラーは具象クラスで作成する。`SwitchGamepad` は任意のコントローラーを受け取る型と共通操作の基底であり、直接作成しない。

```python
from swbt import JoyConL, ProController, SwitchGamepad


pro = ProController(adapter="usb:0", profile_path="profiles/pro-controller.json")
left = JoyConL(adapter="usb:0", profile_path="profiles/joy-con-left.json")


async def accept_any_controller(pad: SwitchGamepad) -> None:
    await pad.connect(timeout=30.0, allow_pairing=True)
```

周期送信型は `ProController`、`JoyConL`、`JoyConR`、直接送信型は `DirectProController`、`DirectJoyConL`、`DirectJoyConR` を使う。

## コンストラクターの方針

すべての具象コントローラーは `adapter`、`profile_path`、`controller_colors`、`diagnostics` を受け取る。周期送信型だけは `report_period_us` も受け取る。`report_period_us=None` はコントローラーのプロファイルの既定値を使う。

`profile`、`device_name`、`transport` は公開引数にしない。コントローラー形状と Bluetooth 識別情報は具象クラスが固定し、下位通信実装の差し替えは repository 内のテストに限る。

`ControllerColors` は公開設定として残す。色はコントローラー形状ではなく、プロファイルが応答する SPI データの表示設定である。

## ペアリングプロファイルの方針

`profile_path` は、Bluetooth アドレスの選択方法とペアリングキーを保存する swbt プロファイルを指す。新しい保存先は各具象クラスの `create_profile()` で作成し、コントローラー形状と接続先ごとに分ける。

`local_address` を省略した `create_profile()` は、Bumble が起動後に報告する現在の Bluetooth アドレスを使い、アダプタの揮発領域を書き換えない。利用者管理のアドレスを指定する場合だけ `local_address` を渡す。この経路は CSR8510 A10 の揮発領域を書き換えるため、生成、重複回避、管理は利用者が担う。

## 公開する名前

`swbt` モジュール直下は具象コントローラー、`SwitchGamepad`、`PeriodicSwitchGamepad`、`DirectSwitchGamepad`、入力型、トレース出力の設定型、接続結果、アダプタ列挙 API を公開する。プロファイル型と下位通信実装の型は公開しない。

公開 API の完全な引数、例外、入力操作は `spec/initial/api.md` と `docs/api.md` を正本とする。
