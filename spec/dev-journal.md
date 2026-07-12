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

## 2026-07-12: NXIC既知SPI一式で正方向ジャイロ速度が安定した

### 現状

前項の続きとして、factory 6-axis calibrationだけでなく、NXICが実装する`0x603D`、`0x6080`、`0x6098`、`0x8010`、`0x8028`の既知SPI blockを同時に返す実機診断を行った。これらはNXICのimplementation factであり、純正Pro Controllerのfactory dumpや一般既定値ではない。

### 観察

Switchは5領域すべてを読み、当該handshakeでは`0x6020`を要求しなかった。15ms周期、静止加速度`(0,0,4096)`、3 sampleともZ軸raw `+0x0600`を120 report送ったところ、スプラトゥーン3のカメラが右へ中程度の速度で回転した。従来の同一raw入力では非常に速い右回転が観測されていたため、SPI応答の不足または領域間の不整合が回転速度の異常に関与した可能性がある。ただし5領域を同時に変更したため、寄与したfieldは特定できない。

### 方針

NXIC一式をproduction既定値にはしない。同一SPI応答のままZ軸raw `-0x0600`を送り、方向と速度が対称になるかを先に確認する。正負が安定した場合だけ、SPI領域を一つずつ現行値へ戻す切り分けを行う。

## 2026-07-12: NXIC既知SPIでも負方向ジャイロは安定しない

### 現状

前項の正方向診断と同じSPI応答、15ms周期、静止加速度を維持し、3 sampleともZ軸raw `-0x0600`を120 report送った。traceとdebug logは各sampleのZがsigned Int16LE `00 FA`であること、IMU mode `0x02`、neutral、transport closeを記録した。

### 観察

スプラトゥーン3では安定した左回転にならず、再び異常な回転が観測された。既知SPI一式は正方向の速度を安定させたが、負方向の非対称性は解消しなかった。従ってSPI応答の不足だけでは説明できない。負のwire値を通る経路と、校正後の負の角速度という意味のどちらに問題があるかは未確定である。

### 方針

実機テスト専用にgyro zeroを正のraw値へずらし、負方向の角速度を正のwire値で表す。これで負方向が安定すれば負のwire値経路を優先して調べ、安定しなければsigned encoding以外のreport解釈または姿勢処理へ調査対象を移す。人工的なzero biasは原因切り分けだけに使い、production校正値にはしない。

## 2026-07-12: 人工zero bias試験は校正採用の確認が不足した

### 現状

user calibrationのgyro offsetを全軸`0x4000`、scaleを全軸`0x7BE7`とし、静止rawを`0x4000`、負方向Z rawを`0x3A00`とした。Linux `hid-nintendo.c`はIMU fieldを`s16`として読み、gyro divisorを`scale - offset`、入力を`raw - offset`から計算するため、この値は同実装の計算式では差分`-0x0600`になる。

### 観察

Switchは変更した`0x8028`を読み、全report byteは非負値だったが、スプラトゥーン3では非常に速い乱回転が続いた。ただしSwitchが通常範囲から大きく外れたoffsetを有効なuser calibrationとして採用した証拠はない。試験全体の目視だけでは、人工校正が拒否された結果と、正のwire値でも負方向差分が失敗した結果を区別できない。

### 方針

人工zero biasをproductionへ反映しない。追加確認を行う場合は、負方向入力を混ぜずcalibrated rest rawだけを十分な時間送る。restだけで回転するなら人工校正診断を棄却し、restが安定するなら正のwire値による負方向差分も失敗した証拠として扱う。

## 2026-07-12: 人工zero biasの静止値はSwitchで安定した

### 現状

前項と同じgyro offset `0x4000`、scale `0x7BE7`を返し、全sampleのgyro rawを`0x4000`に固定した。負方向差分は送らず、ZL確認区間と追加120 reportの観測区間をcalibrated restだけで維持した。

### 観察

スプラトゥーン3のカメラは回転しなかった。従ってSwitchは人工offsetを少なくとも静止点として反映しており、直前の`0x3A00 - 0x4000 = -0x0600`で起きた乱回転を校正の全面拒否だけでは説明できない。ただしLinux式ではscaleとoffsetから約2.07倍の利得になるため、負方向差分試験には不要な倍率が混ざっていた。

### 方針

offsetを負方向差分より1だけ大きい`0x0601`まで下げ、scaleはNXIC既知値`0x3BE7`へ戻す。静止rawを`0x0601`、負方向rawを`0x0001`とし、wire値を非負に保ちながらLinux式の利得を約1.11へ抑えて再確認する。この値も診断専用としproductionへ反映しない。

## 2026-07-12: 非負wire rawで負方向ジャイロが安定した

### 現状

gyro offsetを全軸`0x0601`、scaleを全軸`0x3BE7`とし、静止rawを`0x0601`、負方向Z rawを`0x0001`とした。校正差分は`-0x0600`だが、SPI校正値と全IMU reportをsigned Int16LEの非負範囲に保った。

### 観察

ZL入力完了後、スプラトゥーン3のカメラが左へ安定して回転した。同じ校正差分をwire raw `-0x0600`で送った試験では乱回転していたため、このSwitch 2 / スプラトゥーン3環境では負のwire rawを跨ぐことが異常挙動に関与している。Linux `hid-nintendo.c`と既存protocol資料はIMU rawをsigned 16-bitとして扱うため、一般仕様や物理controllerの性質には拡張しない。

### 方針

production候補として採用する前に、offset `0x4000`、scale `0x7FFF`、wire差分`±0x0300`を使う対称校正を実機確認する。Linux式では見かけの差分がおおむね`±0x0600`になり、wire rawは`0x3D00`から`0x4300`の非負範囲に収まる。正方向と負方向の速度・安定性が揃った場合に限り、校正モデルとrad/s変換の仕様変更候補とする。

## 2026-07-12: scale `0x7FFF`の対称校正は乱回転した

### 現状

gyro offsetを全軸`0x4000`、scaleを全軸`0x7FFF`とし、Z raw `0x4300`、静止`0x4000`、Z raw `0x3D00`を順に送った。Linux式の校正差分は約`+1536.047`と`-1536.047`で、wire rawは非負範囲に収まっていた。

### 観察

スプラトゥーン3のカメラは非常に速く乱回転し、正負の安定回転にならなかった。`scale=0x7FFF`がSwitch側で拒否されたのか、別の内部演算で過大入力になったのかは未確認である。少なくとも、このscaleを対称なproduction校正として採用する根拠はない。

### 方針

scaleは安定左回転を確認済みの`0x3BE7`へ戻す。同じoffset `0x0601`で、正方向Z raw `0x0C01`、静止`0x0601`、負方向Z raw `0x0001`を順に送り、同一校正内の方向対称性だけを確認する。新しいscale候補は追加しない。

## 2026-07-12: minimal biasの対称入力も同方向へ回転した

### 現状

gyro offsetを全軸`0x0601`、scaleを全軸`0x3BE7`とし、正方向Z raw `0x0C01`、静止`0x0601`、負方向Z raw `0x0001`を順に送った。Linux式ではoffsetとの差分がそれぞれ`+0x0600`、`0`、`-0x0600`になる。

### 観察

スプラトゥーン3のカメラは左回転、慣性様の回転、左回転の順に動いた。正負の差分が反対方向の回転にはならなかった。中間の動きがゲーム側の慣性か、report timingや取りこぼしによるものかは目視だけでは判定できない。

### 方針

人工offsetによるLinux式校正モデルはproduction候補から外す。次の入力値を増減する前に、Switch 2でジャイロ動作実績のある実装について、Z軸の符号、値の単位、sample更新頻度、SPI応答をコード単位で監査する。

## 2026-07-12: IMU mode `0x02`はquaternion形式を要求する

### 現状

Switch 2 firmware 22.1.0はsubcommand `0x40`のpayloadに`0x02`を送り、swbt-pythonはこれをIMU有効化として受理した後も従来の3×(accel XYZ + gyro XYZ)を送っていた。MissionControlのcommit `d3941d433f15827de8aea116d61ea17bb61d0bcc`では、`0x01`を標準形式、`0x02`から`0x05`をquaternion形式として明示的に切り替えている。

### 観察

従来形式をmode `0x02`で送った実機結果は、Z rawの上位byteが`0x05`から`0x06`になる境界で無反応から高速回転へ変わり、signed negativeでは乱回転し、人工offsetでwire値を非負にしても正負差分が同じ左方向になった。これらは36 byteを標準gyroではなくpacked quaternionとして解釈した場合に整合する。ただし因果関係はquaternion形式の実機再試験が通るまでinferenceである。

### 方針

factory calibrationはzero `0`、gyro reference `0x343B`の既定値へ戻す。sessionのIMU mode `0x02`から`0x05`では36 byteのpacking mode 2を生成し、`0x01`だけ従来形式を維持する。正負Zの実機試験はquaternion対応後に同じrad/sでやり直す。

## 2026-07-12: quaternion packingで正負Zと静止が実機反映された

### 現状

production factory calibrationに戻し、Switch 2から受信したIMU mode `0x02`に対してpacking mode 2を送った。静止加速度 `(0,0,4096)`を維持し、Z角速度 `+0.5 rad/s`、静止、`-0.5 rad/s`、静止を順に120、8、120、8 reports送った。raw値はZ `+409`と`-409`である。

### 観察

スプラトゥーン3のカメラは左回転、停止、右回転、停止の順に動いた。traceはsubcommand `0x40` payload `0x02`、各入力checkpoint、最終neutral、`transport_close_complete`を記録した。正負方向と静止が入力順に一致したため、従来の36 byteをmode `0x02`で標準gyro形式として送っていたことが、閾値的な反応と乱回転の原因だったと判断する。

### 方針

人工offsetと追加SPI overlayはproductionから除外する。Pro Controllerのmode `0x02-0x05`はquaternion packingを維持し、mode `0x01`は従来形式を維持する。Joy-Conの物理軸方向は別途実機監査が必要であり、この結果から変換を追加しない。

## 2026-07-12: Joy-Conにも共通quaternion wire packingを適用する

### 現状

Joy-Con L/R profileはSwitch 2実機でIMU mode `0x02`の受信実績があるが、mode `0x03-0x05`を受理せず、Pro Controllerとprofile契約が分かれていた。protocol層のquaternion packer自体はcontroller種別に依存しない。

### 観察

MissionControlのmode分岐は`0x02-0x05`を同じpackerへ渡す。Joy-Conだけ異なる36 byte layoutを使う根拠は確認できない。Joy-Con実機で角速度の方向を観測する手段は現在ない。

### 方針

Joy-Con L/Rもmode `0x02-0x05`を受理し、Pro Controllerと同じquaternion wire packingを使う。Joy-Con固有の軸反転は追加せず、物理軸方向は実機未検証として維持する。
