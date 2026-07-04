# Dev Journal

swbt-python の設計観測、未解決事項、先送り判断の記録。

## 2026-07-03: incoming 側の既存 bond 再利用条件

### 現状

unit_007 M6 では、HOME / 通常画面条件の active reconnect で保存済み key store を使った再接続を確認した。trace は `connection_authentication`、`connection_encryption_change`、HID control / interrupt L2CAP open、`connected`、`active_reconnect_result status=connected` を記録し、active reconnect trace には `classic_pairing` と `key_store_update` が出ていない。

incoming 側は controller search / change grip order screen 条件で `incoming_connection route=incoming` と active reconnect event 不在を確認した。ただし同じ trace に `classic_pairing`、`link_key_available`、`key_store_update status=succeeded` が出たため、既存 bond だけを使った Switch 側操作なし reconnect の証拠にはしない。

### 観察

`持ち方/順番を変える` 画面は incoming 経路の確認には使えるが、既存登録済み controller としての再接続確認には向かない可能性が高い。この画面からの接続を「pairing なしの既存 bond 再利用」と期待するのは、現時点の実機観測に合わない。

incoming 側で `classic_pairing` と `key_store_update` が出ないことを検証するには、Switch が登録画面ではなく既存 controller の再接続として接続してくる操作条件が必要になる。通常画面待機、sleep / resume 前後、controller disconnect 後の自動復帰などが候補だが、どれで Switch が incoming 接続を開始するかは未確認。

### 方針

unit_007 は active reconnect の key store 再利用成功を完了根拠とし、incoming 側の既存 bond 再利用条件探索は後続へ送る。後続で扱う場合の成功条件は、`incoming_connection route=incoming`、HID control / interrupt L2CAP open、`connected`、かつ `classic_pairing` と `key_store_update` が出ないこととする。

controller search / change grip order screen からの incoming run は、route 分離の根拠としてだけ扱う。Switch 側操作なし reconnect の根拠としては使わない。
