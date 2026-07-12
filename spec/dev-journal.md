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

## 2026-07-12: Splatoon 3 の仮想ジャイロ反映に非対称な境界がある

### 現状

unit_047 / unit_048でfactory 6-axis calibration、rad/s・G変換、Pro Controller実機reportを確認した。SwitchはSPI `0x6020`の24 bytesを取得し、IMU mode `0x02`を有効化した。ZL入力と正方向Z gyroのカメラ反映は観測できた。

### 観察

Z軸3 sampleすべてがraw `+0x0600`のとき右回転し、`+0x05FF`以下は無反応だった。1または2 sampleだけを`+0x0600`にしても無反応。3 sampleすべて`-0x0600`、またはPro相当静止加速度と`Z=-1.0 rad/s`を組み合わせると、安定した逆回転ではなく乱回転した。負値はraw `-819`、PDU `CD FC`であり、signed Int16LE encodingはunit fixtureと実機logで一致した。

8ms/15ms周期、timer step 1/3、horizontal offset、複数のuser calibration値、同値/変化sample、角速度に合わせた動的重力ベクトルを比較したが、負方向の安定化は再現しなかった。NXICは同じInt16LE配置と3 sample反復を使う。mzyy94の記事は純正Pro Controllerの約80Hz reportと初期化順を記録するが、後継nsconとjoycontrolの6軸送信は未実装であり、負方向の比較根拠にはならない。

### 方針

Issue #69/#70では、校正値共有、変換API、packing、正方向の実機反映までを扱う。`0x0600`境界と負方向乱回転はprotocol定数として実装せず、実機由来の正負IMU reportを採取して仮想reportと比較できるまで未検証仮説として残す。次の調査では純正Pro ControllerのBluetoothまたはUSB report captureを正本にし、同じ姿勢・同じ正負角速度で3 sample、timestamp、accel、gyroを比較する。
