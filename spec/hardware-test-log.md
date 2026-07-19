# Hardware Test Log

Bumble adapter と対象機器に依存する観測を記録する正本である。

実機観測は、OS、driver、dongle、adapter string、Bumble version、Python version、Switch model / firmware に依存する。ここに記録した結果は、その条件での観測であり、別構成での保証には使わない。

## Current Status

- CSR BD_ADDR read-only probe: 2026-07-19 に `experiment/bd-addr-rewrite` branch、`usb:0`、CSR8510 A10 / WinUSB、Bumble 0.0.230、Python 3.13.5 で pass。HCI Reset 後、standard HCI と CSR `PSKEY_BDADDR GETREQ` の双方が `00:1B:DC:F9:9F:7D` を返し、CSR status `0`、`matches_standard_hci=true` を記録した。company identifier は CSR の `10`。PSKEY write、advertising、Switch-facing command は送信していない
- CSR BD_ADDR volatile probe attempt: 2026-07-19 に lab sentinel `02:1B:DC:F9:9F:7D` への PSRAM SETREQ、warm reset、read-back、元 address restore を承認範囲として実行した。baseline は pass したが apply 中に timeout し、同一 process の best-effort restore は libusb transfer error で再 open できなかった。no-open 列挙では USB device address が `11` から `16` へ変わり、別 process の read-only probe では元の `00:1B:DC:F9:9F:7D` と clean close を確認した。write 適用の有無は切り分けられず inconclusive。persistent write、advertising、Switch-facing command は未実行
- CSR BD_ADDR PSRAM-only probe attempt: 2026-07-19 に warm reset なしで lab sentinel への SETREQ / GETREQ / restore を承認範囲として実行した。baseline は元 address で pass したが、apply と best-effort restore は timeout。adapter close は成功した。実装が SETREQ に対する GETRESP type `0x0001` を拒否する誤りを後から確認したため、write 適用と restore 適用は inconclusive。PSRAM 状態を確定せず、物理 power cycle まで追加の adapter open / write / reset を停止した
- CSR BD_ADDR post-PSRAM power-cycle read: 2026-07-19 にユーザが専用 dongle を抜き差しした後、承認済み read-only probe が pass。standard HCI / CSR default-store address はともに元の `00:1B:DC:F9:9F:7D`、CSR status `0`、`matches_standard_hci=true`、`adapter_closed`。前回の未確定 PSRAM 状態は power cycle で解消した
- CSR BD_ADDR PSRAM-only retry: 2026-07-19 に response matcher 修正後の probe を実行。lab sentinel への PSRAM SETREQ status `0`、GETREQ で `02:1B:DC:F9:9F:7D` を read-back し、active standard HCI address は元のままと確認した。元値 restore SETREQ も status `0` だったが、restore 後 GETREQ と best-effort restore は status `0x0008` で失敗。adapter close は成功した。対象個体の PSRAM write capability は observed-pass、同一 session restore は observed-fail とし、物理 power cycle まで追加操作を停止した
- CSR BD_ADDR post-retry power-cycle read: 2026-07-20 にユーザが専用 dongle を抜き差しした後、read-only probe が pass。standard HCI / CSR default-store address は元の `00:1B:DC:F9:9F:7D`、CSR status `0`、一致、`adapter_closed`。PSRAM sentinel は power cycle 後に残らないことを再確認した
- CSR BD_ADDR staged warm-reset apply: 2026-07-20 に専用 `usb:0` へ PSRAM sentinel を設定して read-back 後、CSR warm reset を enqueue した。SETREQ status `0`、PSRAM GETREQ は `02:1B:DC:F9:9F:7D`、warm reset 前の active address は元値。reset enqueue 後に USB OUT / IN transfer status `4` を観測し、再列挙と整合する。後続の別プロセス read で active sentinel を確認済み。persistent write、advertising、Switch-facing 動作は未実行
- CSR BD_ADDR post-warm-reset active read: 2026-07-20 に HCI Reset なしの別プロセス read-only probe が pass。standard HCI / CSR default-store address はともに sentinel `02:1B:DC:F9:9F:7D`、CSR status `0`、一致、`adapter_closed`。対象 CSR8510 A10 では PSRAM write + CSR warm reset により controller が報告する active BD_ADDR を一時変更できることを observed-pass とした。RF / Switch-facing identity は未検証
- CSR BD_ADDR post-warm-reset recovery: 2026-07-20 にユーザが専用 dongle を抜き差しした後、read-only recovery probe が pass。standard HCI / CSR default-store address は元の `00:1B:DC:F9:9F:7D`、CSR status `0`、一致、`adapter_closed`。PSRAM + warm reset による active BD_ADDR 変更が power cycle で復帰することを observed-pass とした
- CSR BD_ADDR unintended read-only preflight: 2026-07-20 に unit / integration pytest を同じ `tmp/pytest` へ並列実行したため、integration 側の basetemp cleanup が unit test の既存 key store fixture を削除した。unit subprocess は拒否条件を失って `usb:0` の read-only identity preflight を開始し、pairing probe 自体は `identity_preflight_rejected` で終了した。advertising / Switch-facing 動作には進んでいない。result artifact は pytest cleanup で残らず、個別 read 値と cleanup field は未確認。テスト adapter を `invalid:test-adapter` へ変更し、以後 pytest gate は固有 basetemp で直列実行する
- CSR BD_ADDR local-address Switch pairing: 2026-07-20 に専用 `usb:0` の volatile address を `02:1B:DC:F9:9F:7D` へ変更し、二段階 address guard 付き pairing probe を実行した。初回は Classic pairing、fresh key store 保存、HID connected、clean close が pass したがユーザ目視は unobserved。元 identity への復旧後、同じ local address と key store を再適用し、接続後5秒の観測窓を持つ rerun も pass。rerun は `classic_pairing`、`previous_saved=true` の key store 更新、periodic `0x30` 107件、終了時 neutral、clean close を記録し、ユーザは Switch UI で登録されたことを目視確認した。local address が対象 Switch の登録経路に受理されることを observed-pass とする。元登録を削除していない条件から別 identity と扱われた可能性は強いが、UI は BD_ADDR を表示しないため inference とする
- CSR BD_ADDR local-address post-pair recovery: 2026-07-20 にユーザが dongle を抜き差しした後、HCI Reset を含む read-only recovery probe が2回連続で pass。standard HCI / CSR default-store は2回とも元の `00:1B:DC:F9:9F:7D`、CSR status `0`、一致、`adapter_closed`。local-address pairing 後も物理 power cycle で元 identity へ復帰することを observed-pass とした
- CSR BD_ADDR dummy-address Switch pairing: 2026-07-20 に local-address rerun 後の物理復旧を確認し、`00:11:22:33:44:55` をvolatile適用した。fresh key storeの初回runはprotocol pairing / HID / full initial subcommand列 / clean closeがpassしたが、Switch UIは反応なし。close後のreuse attemptはpreflightで元addressを検出し、advertising前に安全停止した。dummy addressを再適用したreuse rerunはprotocol passし、ユーザがSwitch UIで登録されたことを目視確認した。dummy addressが対象Switchの登録経路に受理されることをobserved-passとする。warm reset直後のUSB transfer警告は再列挙と整合し、後続のstandard HCI / CSR / Bumble address一致により適用成功を判定した
- IMU calibration / gyro reflection run: 2026-07-12 に `fix/issue-69-gyro-calibration` branch、`usb:0`、CSR8510 A10 / WinUSB、Bumble 0.0.230、Python 3.13.5 で Pro Controller の active reconnect 回帰を実行した。Switchはfactory 6-axis calibration 24 bytesを取得し、`imu_enabled=true`となった。スプラトゥーン3ではZ軸3 sampleすべてがraw `+0x0600`のとき右回転を目視した一方、`+0x05FF`以下、1～2 sampleだけ`+0x0600`、3 sampleすべて`-0x0600`では対称な反映にならなかった。packingと正方向ジャイロ入力経路はobserved-pass、低速・負方向の意味的挙動はobserved-partialとする
- Hardware run: 2026-07-01 に CSR8510 A10 / WinUSB / `usb:0` で M2 advertising smoke と M3 pairing / L2CAP pass
- Bumble adapter run: adapter open、Bumble Device 初期化、Classic HID 初期化、SDP / HID descriptor 登録、discoverable / connectable、close を記録済み
- Pairing run: 2026-07-01 に `Pro Controller` / Class of Device `0x002508` で M3 pairing / L2CAP pass。`classic_pairing`、HID control / interrupt channel open、`connected` を記録済み
- Subcommand run: 2026-07-02 に Classic default link policy `0x0005` のみを残した最小実装で M4 subcommand sequence が pass。続く observation window run では Bumble ACL queue drain 後、5 秒以上の実機観測で `0x02` 1 件と `0x08` 8 件を受信し、全件に `0x21` reply を送信した。trace は `classic_link_policy_configured`、Switch からの `0x01` output report、`subcommand_rx`、`subcommand_reply_tx`、`report_tx` reason `subcommand_reply` 9 件を記録し、`unsupported_subcommand` と `error` は 0 件だった。debug log は `packets in flight` backlog 行 0 件だった。link policy 反映前の試行では、HIDP DATA header 除去、SET_REPORT callback、control channel output report、HID SDP policy、service name / language base、daemon-aligned `0x8e` / `0x80` prefix、HID L2CAP local MTU `100` を反映しても `output_report_rx` 未観測のまま Switch 側 reason 19 で切断されていた
- H1 open-only smoke: 2026-07-07 に `test/hardware-test-scenarios` branch で H1 を実行した。pytest は `1 passed in 0.32s`。trace は `transport_open_complete`、`disconnect_request status=unavailable reason=channels_not_connected`、`transport_close_complete` を記録し、`advertising_start` / `host_connection` は 0 件だった。これは `open()` だけでは HID advertising / Switch pairing / report loop が始まらないことの Bumble adapter smoke である。ユーザは Switch 側も反応なしと目視確認した。H1 は pass として扱う
- H2 advertising smoke: 2026-07-07 に `test/hardware-test-scenarios` branch で H2 を実行した。pytest は `1 passed in 0.52s`。trace は `transport_open_complete`、`local_bluetooth_address_configured address=001bdcf99f7d`、`classic_link_policy_configured settings=0x0005`、`advertising_start`、`transport_close_complete` を記録した。`connection_request` / `host_connection` / `classic_pairing` / `error` は 0 件だった。ユーザは Switch 側も接続反応なしと目視確認した。H2 は pass として扱う
- Profile regression run: 2026-07-07 に `test/hardware-test-scenarios` branch で Pro Controller P1 / P2 / P3 / P4 / P5 / P6 / P7 を実行した。P1 pairing / L2CAP は pass。P2 subcommand observation window は当初 `0x40` Enable IMU payload `0x02` で fail した。接続情報削除後も ProCon toast / ProCon pairing 後に同じ `0x40` `0x02` が来たため、source-audit と TDD を通して ProController でも `0x02` を session state に記録して ACK するよう変更した。修正後 P2 は `1 passed in 8.05s`、trace は `imu_mode=0x02`、`0x48`、`0x21`、`transport_close_complete` を記録し、`error` / `unsupported_subcommand` は 0 件だった。P3 fresh input semantics key store 作成は `1 passed in 9.76s`、`route=pairing`、`key_store_update status=succeeded`、full handshake、`transport_close_complete` を記録した。P4 は LR split 単独 run 後、D-pad と同時に実施できると判断して LR + D-pad 統合テストへ再実装し、`1 passed in 14.09s`。P5 left stick は `1 passed in 16.83s`、P6 right stick は `1 passed in 16.87s`。どちらも hold、32 step circle、neutral、`transport_close_complete` を記録した。P7 close path は `1 passed in 7.90s` で、A exit、neutral、disconnect、post-close observation checkpoint を記録した。ユーザは P4/P5/P6/P7 とも期待値どおりの入力または UI 状態を確認した
- Joy-Con L profile regression L1: 2026-07-07 に `test/hardware-test-scenarios` branch で L1 を実行した。初回 L1 は pytest `1 passed in 24.51s` で、trace は `device_name=Joy-Con (L)`、HCI local name / EIR `Joy-Con (L)`、Device Info `controller_type=0x01`、address bytes `001bdcf99f7d`、SR+SL `000030`、neutral、`transport_close_complete` を記録した。ただしユーザ目視では初期登録 toast が Pro Controller として出て、登録自体は完了した。Switch 側の接続情報を削除して同じ L1 を別 artifact dir で再実行したところ pytest は `1 passed in 24.50s`、trace は同じ Joy-Con L discovery / Device Info / SR+SL / cleanup を記録し、ユーザは青色の Joy-Con (L) として認識され、toast も正常だったと報告した。初回の Pro toast は同一 BD_ADDR に対する Switch 側残置情報の影響が強い推論であり、cross-firmware guarantee にはしない
- Joy-Con L default-color diagnostic during L2 planning: 2026-07-07 に L2 候補として既定色 SPI test を実行し、pytest は `1 passed in 24.43s`、SPI `0x6050` bytes は `00b2ff32323200b2ff00b2ff` と一致した。ユーザ目視では L1 と同様の色だった。これは既定色の on-wire 応答確認として残すが、profile regression の L2 主シナリオとしては弱いため、L2 は利用者指定色の実機確認へ差し替える
- Joy-Con L custom-color L2: 2026-07-07 に差し替え後の L2 を実行した。pytest は `1 passed in 24.58s`。trace は Device Info `04000102001bdcf99f7d0101`、SPI `0x6050` bytes `ff00000000ffff00ffff8000`、SR+SL `000030`、neutral、`transport_close_complete` を記録した。ユーザは赤 body / 青 buttons が Switch UI に表示されたことを目視確認した。これは L2 pass として扱う
- Joy-Con L D-pad L3: 2026-07-07 に L3 用 fresh key store を `joycon-l-l3` artifact dir に作成した後、Joy-Con L active reconnect で D-pad up/right/down/left を送る hardware test を実行した。古い `joycon-l-after-clear` key store では active reconnect が `AUTHENTICATION_FAILURE_ERROR` で失敗し、non-neutral input は送っていない。fresh key store 後の初回 L3 は pytest `1 passed in 11.67s` だったが、ユーザ目視ではボタンの動作チェック画面に入れておらず、下入力が入ってそのまま終了したため observed-fail とする。最終 rerun は `1 passed in 20.67s`、trace は active reconnect、handshake、up `000002`、right `000004`、down `000001`、left `000008`、各 neutral、cleanup を記録した。ユーザは Switch UI で上右下左の順番にボタンが押されたことを目視確認した。L3 は pass として扱う
- Joy-Con L stick L4: 2026-07-07 に L3 key store を `joycon-l-l4` artifact dir へコピーし、Joy-Con L active reconnect で left stick hold / circle / neutral を送る hardware test を実行した。pytest は `1 passed in 15.62s`。trace は active reconnect、handshake、left stick hold 120 reports、32 step circle、neutral、cleanup を記録した。ユーザ目視では hold を確認したが、Switch UI は横持ち Joy-Con に対して「横持ちだと補正できません」と拒否した。これは protocol failure ではなく device/UI 制約として扱い、L4 は hold 観測までの条件付き pass とする。Joy-Con R stick scenario でも同じ制約が想定される
- Joy-Con R R1: 2026-07-07 に R1 初回を実行した。pytest は `1 failed in 24.45s`。trace は `device_name=Joy-Con (R)`、Device Info `04000202001bdcf99f7d0101`、SR+SL `300000`、neutral、UI observation hold、`transport_close_complete` を記録したが、Switch から repeated `0x22` payload first byte `0x01` を受け、`UnsupportedSubcommandError` / `error` が記録された。ユーザは赤 body / 青 buttons の Joy-Con (R) として登録されたことを目視確認した。source-audit と TDD を通して `0x22` ACK 互換処理を追加し、R1 rerun は `1 passed in 24.45s`。rerun trace は `0x22` 2 件への `0x21` reply、Device Info、SR+SL `300000`、neutral、UI observation hold、`transport_close_complete` を記録し、`unsupported_subcommand` / `error` は 0 件だった。rerun ではユーザが赤 body / グレー buttons の pairing を目視確認した。色は人間目視の観測であり、専用 SPI color scenario の pass 条件にはしない
- Joy-Con R ABXY R2: 2026-07-07 に R2 用 fresh key store を `joycon-r-r2` artifact dir に作成した後、Joy-Con R active reconnect で A entry、Y/X/B/A、各 neutral を送る hardware test を実行した。初回は pytest `1 passed in 7.80s` だったが、ユーザ目視では画面遷移に入っていなかったため UI pass ではない。`joycon-r-r2-rerun2` rerun は pytest `1 passed in 7.29s`、trace は Y `010000`、X `020000`、B `040000`、A `080000`、各 neutral、cleanup を記録した。ユーザは入力として期待どおりだったと報告した。R2 は pass として扱う
- Joy-Con R stick R3: 2026-07-07 に R2 key store を `joycon-r-r3` artifact dir へコピーし、Joy-Con R active reconnect で right stick hold / circle / neutral を送る hardware test を実行した。pytest は `1 passed in 10.38s`。trace は active reconnect、handshake、right stick hold 120 reports、32 step circle、neutral、cleanup を記録した。ユーザは期待どおり横持ち Joy-Con では補正が通らないことを確認した。これは protocol failure ではなく device/UI 制約として扱い、R3 は hold 観測までの条件付き pass とする
- Joy-Con R custom-color R4: 2026-07-07 に R4 として Joy-Con R custom color test を実行した。pytest は `1 passed in 24.43s`。trace は Device Info `04000202001bdcf99f7d0101`、SPI `0x6050` bytes `00ff008000ff00ffffffff00`、SR+SL `300000`、UI observation hold、cleanup を記録した。ユーザは Switch UI で body 緑 / buttons 紫を目視確認した。R4 は pass として扱う
- Input reflection run: 2026-07-02 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で M5 input operation sequence を実行した。pytest は `1 passed` だが、これは接続、subcommand reply、`0x30` report 送信、manual checkpoint、clean close を確認するだけで、Switch UI 反映を自動判定しない。初回ユーザ画面観測では Switch のデバイス登録画面が全く動かなかったため、M5 の semantic input reflection は observed-fail。debug log では A button bytes `08 00 00`、L+R button bytes `40 00 40`、neutral bytes `00 00 00` を含む `a1 30` HID interrupt send は確認済み。後続の pairing diagnostics run では `link_key_available` と `connection_encryption_change` は出たが、`pairing_complete` と `connection_authentication` は出ず、Switch は `0x02` と repeated `0x08` から進まなかった。daemon `local_037` の実機履歴では `0x21` reply timer 固定を shared input report timer に直すと repeated `0x08` から `0x10` / `0x03` へ進んだため、swbt-python でも shared timer / reply holdoff を実装した。2026-07-02 shared timer rerun では `0x02`、`0x08`、`0x10`、`0x03`、`0x04`、`0x40`、`0x30`、`0x48`、`0x21`、`0x30` まで進み、ユーザは Switch 側で pairing 完了を目視した。続く post-handshake input run では full observed handshake 後に `tap(Button.A)` を送信し、ユーザは Switch UI への A 反映と neutral 後の入力残りなしを目視した。
- Close disconnect run: 2026-07-02 の unit_014 connected close run は `connected` 後に non-neutral 入力を送らず、trailing neutral、Bumble L2CAP channel close、`disconnect_request status=requested`、`disconnect_request_terminal status=closed` まで観測した。初回は `transport_close_complete` が trace に出ず、user close 中の disconnected callback が final close を先取りする race として fake integration test で再現し、`0979bd4` で修正した。修正後の rerun では `host_connection`、control / interrupt L2CAP open、`connected`、neutral `0x30`、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete`、`manual_close_checkpoint close_complete` まで通過した。後続の visibility 調査で Bumble 0.0.230 の `power_off()` だけでは Classic scan が残ることを確認し、close cleanup に `set_discoverable(False)` / `set_connectable(False)` を追加した。修正後の close disconnect rerun は `1 passed`、final `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0` `SUCCESS` まで確認した。この run は full observed subcommand handshake 後 close ではなく、HID control / interrupt L2CAP `connected` 直後の close ordering を確認する。最後に full observed handshake 後、Button A で登録画面を抜け、neutral、disconnect、post-close UI 確認まで行う path を実行し、ユーザは登録画面脱出と接続解除を目視した。Bumble 0.0.230 の incoming Classic connection handler が deprecated `send_command_sync()` を使う警告は host listener bridge で `AsyncRunner.spawn(host.send_async_command(...))` へ差し替えて解消し、同じ path は `-W error` 付きで `1 passed in 7.85s` になった。
- Subcommand follow-up: 2026-07-02 にユーザが疎通不良を疑ったため、non-neutral 入力なしで subcommand observation window を再実行した。run は `advertising_start` まで進んだが `host_connection` が来ず、60 秒で `ConnectionTimeoutError` になった。この観測は、Switch からの output report / subcommand / `0x21` reply 疎通を確認できていない。
- Problem investigation: 2026-07-02 の L2CAP-only follow-up でも `advertising_start` まで進んだ後、`host_connection` が来ず 60 秒 timeout した。少なくともこの時点の問題は subcommand reply や input report ではなく、Switch が advertised `Pro Controller` へ接続要求を出していない段階にある。
- Problem retry: 2026-07-02 に Switch 側を接続画面へ入り直した想定で L2CAP-only check を再試行したが、再び `advertising_start` 後に `host_connection` が来ず 60 秒 timeout した。HCI debug log にも `HCI_CONNECTION_REQUEST_EVENT` はなかった。
- New pairing attempt: 2026-07-02 にユーザが Switch 側の pairing 情報削除と新規追加画面での探索を確認した状態で L2CAP-only check を再試行した。Bumble 側は `Pro Controller` / Class of Device `0x002508` / extended inquiry response を設定し、最終的な `scan_enable: 3` も成功したが、`host_connection` と HCI `HCI_CONNECTION_REQUEST_EVENT` は来ず 60 秒 timeout した。この run は pairing 失敗ではなく、pairing 開始前の discovery / connection request 未到達として扱う。
- Discovery visibility hold: 2026-07-02 に `usb:0` を `Pro Controller` として 90 秒間 discoverable / connectable に保持した。trace は `advertising_start`、`manual_advertising_hold_start duration_seconds=90`、`manual_advertising_hold_complete`、`transport_close_complete` を記録したが、`host_connection` は記録しなかった。外部 scanner から見えたかどうかはこの artifact だけでは確定できない。
- Close cleanup scan disable: 2026-07-02 に close cleanup を修正後、`usb:0` を 5 秒間だけ `Pro Controller` として advertise し、close で Classic scan を停止する診断を実行した。trace は `host_connection` を記録し、debug log は close path の `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0` が `SUCCESS` で完了したことを記録した。ユーザは iPhone 側で `Pro Controller` 表示が消えたことを目視した。
- Context manager resource scope run: 2026-07-03 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で unit_015 smoke を実行した。`open()` only smoke は `transport_open_complete` と `transport_close_complete` を記録し、`advertising_start` と `host_connection` を記録しなかった。`pair()` close smoke は `advertising_start`、`connection_request`、`host_connection`、`classic_pairing`、HID control / interrupt L2CAP open、`connected`、trailing neutral `0x30`、`disconnect_request status=requested`、`disconnect_request_terminal status=closed`、`transport_close_complete` を記録した。Button A path は full observed handshake 後に `tap(Button.A)`、neutral、close まで到達し、`manual_input_checkpoint post_handshake_tap_a_complete` と `post_handshake_neutral_complete` を記録した。この pytest は on-wire sequence と checkpoint を確認するが、Switch UI 反映は自動判定しない。
- Reconnect key store run: 2026-07-03 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で unit_007 reconnect keystore characterization を実行した。起動条件記録なしの初回 run は active reconnect の条件としては inconclusive。起動条件を trace に残す split run では、初回 pairing を controller search / change grip order screen で行い、`key_store_update status=succeeded` を記録した。2本目の active reconnect は HOME / 通常画面条件で保存済み peer 1 件を選択した。修正前は `Device.connect(..., BR_EDR)` 後に HID control の `L2CAP_CONNECTION_REQUEST` PSM `0x0011` を先に送信し、Switch 側 reason 5 `AUTHENTICATION_FAILURE_ERROR` で切断された。`Connection.authenticate()` と `Connection.encrypt(True)` を HID L2CAP 前に明示した修正後は、`connection_authentication authenticated=true`、`connection_encryption_change encryption=1`、HID control / interrupt L2CAP open、`connected`、`active_reconnect_result status=connected` を記録した。この active reconnect trace では `advertising_start`、`classic_pairing`、`key_store_update` は出ていない。3本目の incoming run は controller search / change grip order screen で `incoming_connection route=incoming` を記録し、active reconnect event を出さなかった。ただし `classic_pairing`、`link_key_available`、`key_store_update status=succeeded` も出たため、pairing-free incoming bond reuse とは扱わない。
- Packaging CLI pair probe: 2026-07-03 に unit_008 の `swbt-probe pair` を承認済み範囲で実行した。初回は `usb:0` を開き、Classic HID Device 初期化、SDP 登録、HID advertising、trace 保存まで到達したが、30 秒間 `host_connection` が来ず `ConnectionTimeoutError` で終了した。ユーザが Switch 側を接続待ちにして再実行した retry では、`connection_request`、`host_connection`、`classic_pairing`、HID control / interrupt L2CAP open、`connected`、key store write、close cleanup まで到達した。retry trace は one neutral `0x30` report と `transport_close_complete` を記録し、non-neutral input は送っていない。
- Unit 019 follow-up smoke: 2026-07-03 に `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で `test_switch_pairing_l2cap_records_diagnostics` を実行した。Switch を接続待ち画面にした状態で、`connection_request`、`host_connection`、`classic_pairing`、`link_key_available`、`key_store_update status=succeeded`、HID control / interrupt L2CAP open、`connected`、one neutral `0x30`、disconnect request、`transport_close_complete` を記録した。non-neutral input は送っていない。
- Unit 013 input semantics setup: 2026-07-04 に Switch 2 / firmware 22.1.0 / `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で fresh key store setup を実行した。Switch を controller search / change grip order screen に置き、`input-semantics-key-store.json` を作り直した。trace は `key_store_exists=false`、`active_reconnect_result status=no_bond`、`connect_pairing_fallback route=pairing`、`classic_pairing`、`link_key_available`、`key_store_update status=succeeded`、HID control / interrupt L2CAP open、`connected`、full observed subcommand handshake、`manual_input_checkpoint operation=handshake_complete`、close cleanup を記録した。non-neutral input は送っていない。これは unit_013 の後続 active reconnect 入力検証に使う前提 artifact であり、button / D-pad / stick の semantic reflection は後続 run で実行した。
- Unit 013 button check trace: 2026-07-04 に同じ artifact dir の key store を使い、Switch を「ボタンの動作チェック」選択画面直前で待機させて active reconnect button check run を実行した。trace は `key_store_exists=true`、保存済み peer 1 件、`active_reconnect_attempt`、`connection_authentication authenticated=true`、`connection_encryption_change encryption=1`、HID control / interrupt L2CAP open、`active_reconnect_result status=connected`、full observed subcommand handshake、A entry checkpoint、L+R hold checkpoint、neutral checkpoint、`transport_close_complete` を記録した。active reconnect trace には `advertising_start`、`classic_pairing`、`key_store_update` は出ていない。初回のユーザ目視では L ボタンだけが押されているように見え、L+R 同時押し表示は確認できなかった。
- Unit 013 button split diagnosis: 2026-07-04 に同じ button check screen 条件で R-only、L-only、L+R を別 checkpoint として送る再実験を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、`hold_r_only`、`hold_l_only`、`hold_lr_together`、neutral、`transport_close_complete` を記録した。debug log から抽出した `0x30` input report の button bytes は R-only `400000` が 30 件、L-only `000040` が 29 件、L+R `400040` が 30 件だった。ユーザは、Switch のボタンチェック UI は同時押しに対応しておらず片方だけしか UI に反映しないらしい、ひとまず pass 扱いでよい、と判断した。unit_013 のボタン側は、この構成で hardware-pass とする。
- Unit 013 D-pad button check: 2026-07-04 に同じ button check screen 条件で D-pad up、right、down、left を別 checkpoint として送る実験を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、`hold_dpad_up`、`hold_dpad_right`、`hold_dpad_down`、`hold_dpad_left`、各方向後の neutral、`transport_close_complete` を記録した。trace 上の expected button bytes は up `000002`、right `000004`、down `000001`、left `000008` だった。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは UI 側の反映も確認したため、D-pad 側は hardware-pass とする。
- Unit 013 left stick trace: 2026-07-04 に同じ artifact dir の key store を使い、Switch を「スティックの補正」選択画面直前で待機させて active reconnect left stick run を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、left stick hold、16-step circle、neutral、`transport_close_complete` を記録した。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは left stick の目視確認ができたと報告した。ただし、回転が速すぎたか画面遷移を考慮できていなかったため、直ぐに終わってしまったようにも見える、という留保がある。
- Unit 013 right stick trace: 2026-07-04 に同じ artifact dir の key store を使い、Switch を「スティックの補正」選択画面直前で待機させて active reconnect right stick run を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry、right stick hold、16-step circle、neutral、`transport_close_complete` を記録した。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは目視完了と報告したが、回転が速すぎて見えなかったとも報告したため、right stick semantic reflection は inconclusive とする。後続再実験では A 後の settle、hold、circle を長くする。
- Unit 013 right stick slow rerun: 2026-07-04 に同じ条件で right stick 再実験を実行した。pytest は pass。trace は active reconnect、full observed handshake、A entry 後 `settle_seconds=1.5`、right stick hold `hold_report_count=120`、32-step circle `step_seconds=0.15`、neutral、`transport_close_complete` を記録した。`advertising_start`、`classic_pairing`、`key_store_update`、`error` は出ていない。ユーザは right stick の目視確認ができたと報告した。unit_013 の stick 側は、left stick の目視確認と right stick slow rerun の目視確認により hardware-pass とする。
- macOS pairing smoke: 2026-07-05 に macOS 15.7.7 / CSR8510 A10 / `usb:0` / Bumble 0.0.230 で `swbt-probe pair` を実行した。初回は `libusb-1.0.dylib` が見つからず adapter open 前に失敗したため、Homebrew `libusb` を追加し、Intel Homebrew の libusb path を `DYLD_LIBRARY_PATH` に入れて再実行した。再実行では `transport_open_complete`、`advertising_start`、`connection_request`、`host_connection`、`classic_pairing`、`key_store_update status=succeeded`、HID control / interrupt L2CAP open、`connected`、close cleanup を記録した。non-neutral input は送っていないため、input reflection は未検証である。
- macOS active reconnect button check: 2026-07-05 に同じ macOS / CSR8510 A10 / `usb:0` / Bumble 0.0.230 構成で、前回 pairing smoke の key store を使って active reconnect button check を実行した。pytest は pass。trace は `active_reconnect_attempt`、Classic authentication / encryption、HID control / interrupt L2CAP open、`active_reconnect_result status=connected`、full observed subcommand handshake、Button A、L+R hold、neutral、`transport_close_complete` を記録した。`classic_pairing`、`key_store_update`、`advertising_start`、`error` は出ていない。ユーザは Switch UI 上の button 入力反映と neutral 後の入力残りなしを目視確認した。
- Unit 027 adapter discovery run: 2026-07-05 に Windows / CSR8510 A10 / `usb:0` / Bumble 0.0.230 で no-open discovery と open-only smoke を実行した。no-open JSON は `opens_adapter=false`、`manufacturer=null`、`serial_number=null` を返した。open-only trace は `transport_open_complete` と `transport_close_complete` を記録し、`advertising_start` と `host_connection` を記録しなかった。
- Unit 028 controller color SPI reply: 2026-07-05 に Windows 11 / `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で custom `ControllerColors(body=0x00C853, buttons=0xFFEB3B)` の probe を実行した。trace は no-bond から pairing fallback、`classic_pairing`、`key_store_update status=succeeded`、HID control / interrupt L2CAP open、`connected`、full observed subcommand sequence、`0x6050` を含む SPI read reply 2 件を記録した。`0x006050` size 13 と `0x00603d` size 25 のどちらも `controller_color_bytes=00c853ffeb3b`、`matches_expected_controller_colors=true` だった。non-neutral input は送っていない。ユーザは Switch UI で緑の body と黄色の buttons の controller 表示を目視確認した。
- Unit 028 controller grip color SPI reply: 2026-07-05 に同じ Windows / Switch 2 / firmware 22.1.0 条件で `ControllerColors(body=0x00C853, buttons=0xFFEB3B, left_grip=0x2962FF, right_grip=0xD50000)` の probe を実行した。15 秒 hold と 30 秒 hold のどちらでも、trace は `0x006050` size 13 で `controller_color_bytes=00c853ffeb3b2962ffd50000`、`matches_expected_controller_colors=true` を記録した。non-neutral input は送っていない。ユーザは Switch UI で左右 grip は青/赤に変わらず、緑のままに見えると報告した。この時点の device-info tail は daemon 由来の `01 01` 系であり、後続の `03 02` characterization で grip UI reflection の条件が切り分けられた。
- Unit 028 tracked custom controller color hardware test historical run: 2026-07-05 に同じ Windows / Switch 2 / firmware 22.1.0 条件で当時の `tests/hardware/test_controller_colors.py::test_switch_reads_custom_controller_color_profile` を実行した。pytest は `1 passed`。trace は `0x006050` size 13 で diagnostic custom profile の `controller_color_bytes=00c853ffeb3b2962ffd50000`、`matches_expected_controller_colors=true`、30 秒の `ui_observation_hold_complete`、`manual_controller_color_cleanup connection_state=closed` を記録した。ユーザは Switch UI が緑一色に見えると報告した。これは UI 表示の観測であり、SPI reply bytes の不一致ではない。現行 tracked test は sentinel profile の `test_switch_reads_sentinel_controller_color_profile` とする。
- Unit 028 tracked sentinel controller color hardware test with daemon-like tail: 2026-07-05 に同じ Windows / Switch 2 / firmware 22.1.0 条件で `tests/hardware/test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile` を実行した。pytest は `1 passed`。trace は `0x006050` size 13 で sentinel profile の `controller_color_bytes=ff00000000ffff00ffff8000`、`matches_expected_controller_colors=true`、30 秒の `ui_observation_hold_complete`、`manual_controller_color_cleanup connection_state=closed` を記録した。ユーザは Switch UI で body が赤、buttons が青、grip も赤に見えたと報告した。body/buttons は UI に反映された観測として扱い、tail `01 01` では grip が body 色に寄った観測として扱う。
- Unit 028 device-info tail characterization: 2026-07-05 に同じ Windows / Switch 2 / firmware 22.1.0 条件で sentinel profile `body=0xFF0000`, `buttons=0x0000FF`, `left_grip=0xFF00FF`, `right_grip=0xFF8000` を使い、device-info tail と SPI 周辺 byte を切り分けた。旧 tail `01 01`、nonzero device-info address だけ、SPI `0x605C=00` だけでは body/grip が赤、buttons が青のままだった。device-info tail `03 02` では left/right grip がマゼンタ/オレンジに変わり、zero BD_ADDR でも同じ表示が保持された。
- Unit 028 production default device-info tail `03 02`: 2026-07-05 に現行 `DEVICE_INFO_DATA=040003020000000000000302` で `tests/hardware/test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile` を実行した。pytest は `1 passed in 33.45s`。trace は `device_info_data=040003020000000000000302`、`controller_color_bytes=ff00000000ffff00ffff8000`、`matches_expected_controller_colors=true`、30 秒 hold、clean close を記録した。ユーザは同じように左マゼンタ、右オレンジが保持されたと報告した。
- Joy-Con L profile characterization: 2026-07-06 に Windows / `usb:0` / CSR8510 A10 / WinUSB / Bumble 0.0.230 で `JoyCon("left")` の通信上の profile 検証を実行した。修正後の pytest は `1 passed in 18.14s`。trace は `device_name=Joy-Con (L)`、`device_info_data=040001020000000000000101`、`subcommand_session_state imu_mode=0x02`、neutral `0x30` loop、`transport_close_complete` を記録した。non-neutral input は送っていない。ユーザ目視では、登録 toast は Pro Controller で、その後のコントローラーの順番画面は Joy-Con L の SR+SL 入力待ちだった。Joy-Con R は未実行。
- Joy-Con L SR+SL follow-up: 2026-07-06 に `c07fc00` で SR+SL 入力を試す hardware test を実行した。pytest は `1 passed in 19.18s` だが、ユーザ目視では pairing / controller order registration は完了しなかった。trace は `key_store_update status=succeeded`、`connected`、`device_info_data=040001020000000000000101`、`expected_button_bytes=000030`、`transport_close_complete` を記録した一方、`sr_sl_order_buttons_start` から `sr_sl_order_buttons_hold_complete` まで `report_0x30_count` は 2 のままだった。つまり test は `Button.SR` + `Button.SL` を state に入れたが、subcommand reply holdoff 中に periodic `0x30` が出ず、SR+SL の独立した input report を送れていなかった。この run は Joy-Con 登録失敗かつ test 手順不備として扱う。後続修正では `tap(Button.SR, Button.SL)` により即時 press/release の `0x30` を要求する。
- Joy-Con L immediate SR+SL follow-up: 2026-07-06 に `c225d68` の修正後 run を実行した。pytest は `1 passed in 19.31s` だが、ユーザ目視では pairing / controller order registration は完了しなかった。trace は `sr_sl_order_buttons_start report_0x30_count_before=1` 後に `report_tx reason=input report_id=0x30`、`sr_sl_order_buttons_tap_complete input_report_delta=3 input_report_delta_at_least_2=true report_0x30_count=4`、`ui_observation_hold_complete report_0x30_count=319`、`transport_close_complete` を記録した。SR+SL `0x30` 自体は送信できたが、tap は `0x08` / `0x10` / `0x03` / `0x04` / `0x40` / `0x30` / `0x48` の初期 sequence 中に発生し、UI 観測 hold 時点では neutral の periodic report に戻っていた。この run は Joy-Con 登録失敗かつ入力 timing 不備として扱う。次の run は full observed handshake 後に SR+SL を押下状態で一定数の periodic `0x30` に乗せる。
- Joy-Con L post-handshake SR+SL attempt: 2026-07-06 に `8964046` の full-handshake wait 版 run を実行した。pytest は `TimeoutError` で fail し、ユーザ目視でも状況は変わらなかった。この run は SR+SL hold まで到達していない。trace は `0x02` / `0x08` / `0x10` / `0x03` / `0x04` / `0x40` / `0x30` / `0x48` に返信し、その後 periodic neutral `0x30` を継続したが、test 側が Pro profile 用の `0x21` subcommand を必須にしていたため readiness 判定が成立しなかった。この run は Joy-Con 登録失敗かつ test readiness 判定不備として扱う。後続修正では Joy-Con の観測済み初期 sequence を readiness 条件にし、`0x21` は必須にしない。
- Joy-Con L observed-window SR+SL run: 2026-07-06 に `f249261` の readiness 修正後 run を実行した。pytest は `TimeoutError: report 0x30 count stayed at 94, expected 123` で fail したが、trace は観測済み初期 sequence 後に SR+SL `000030` の periodic `0x30` を送った。ユーザ目視では pairing 自体は完了し、登録 toast は Pro Controller のままで、コントローラーの順番画面は Joy-Con L として表示された。この run は SR+SL timing 問題を主因から外し、identity mismatch と Device Info Bluetooth address wiring の follow-up として扱う。trace の on-air local BD_ADDR は `00:1B:DC:F9:9F:7D` だが `device_info_data=040001020000000000000101` は zero address だった。
- Joy-Con L Device Info address first retest: 2026-07-06 に `21721d5` 後の first retest を実行した。pytest は `AssertionError` で fail し、trace は `bumble_device_initialized` に local address を記録せず、`device_info_data=040001020000000000000101` と zero address のままだった。debug log は on-air local BD_ADDR `00:1B:DC:F9:9F:7D/P` を記録した。ユーザ目視では登録 toast は引き続き Pro Controller だった。この run は Device Info address 修正後の toast 判定ではなく、address 注入 timing が早すぎた実装不備として扱う。後続修正では Bumble `power_on()` 後、pairing advertising 後、connection completion 後に local address を再取得する。
- Joy-Con L Device Info nonzero address retest: 2026-07-06 に `b81cce0` 後の retest を実行した。trace は `local_bluetooth_address_configured address=001bdcf99f7d` と `device_info_bluetooth_address_configured address=001bdcf99f7d` を記録し、debug log は `0x02` Device Info reply payload `04 00 01 02 00 1b dc f9 9f 7d 01 01` を送信したことを示した。ユーザ目視では Pro Controller toast が出て、Joy-Con のユーザ向け登録は完了しなかった。pytest は `device_info_reply` event 待ちで timeout したが、これは Device Info 未送信ではなく、address 更新時に `SubcommandResponder` を差し替えて hardware probe wrapper を外した計測不備として扱う。Device Info address だけでは Pro toast 問題を解消できない。
- Joy-Con L SDP policy retest: 2026-07-06 に `867a785` 後の retest を実行した。pytest は `1 passed in 24.40s`。trace は `device_name=Joy-Con (L)`、Class of Device `0x002508`、HID descriptor size `203`、Device Info reply `04 00 01 02 00 1b dc f9 9f 7d 01 01`、observed init sequence、SR+SL `000030` の `0x30` input report 147 件以上、neutral cleanup、`transport_close_complete` を記録した。Bumble debug log は SDP XML attributes を直接表示しないため、SDP policy の on-air attribute read まではこの artifact だけでは断定しない。ユーザ目視では Switch UI で Joy-Con として登録された。Joy-Con R、Joy-Con reconnect、Joy-Con 通常入力反映、別 firmware / dongle は未検証のまま扱う。
- Joy-Con L default controller color SPI retest: 2026-07-06 に `196ac6f` 後の working tree で Joy-Con L 既定 ControllerColors の hardware test を追加し、`usb:0` で実行した。pytest は `1 passed in 24.39s`。trace は `Joy-Con (L)`、Device Info reply `04000102001bdcf99f7d0101`、SPI `0x006050` size 13 の `controller_color_bytes=00b2ff32323200b2ff00b2ff`、`matches_expected_controller_colors=true`、SR+SL `000030` hold reports、neutral cleanup、`transport_close_complete` を記録した。Switch UI の色表示は pytest では自動判定しない。ユーザは Switch UI で body が青色または水色、buttons が黒色に見えると報告した。buttons byte は `0x323232` なので、この観測は濃灰が黒に見えたものとして扱う。

### 2026-07-19: CSR BD_ADDR read-only probe without HCI Reset

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、HEAD `3b82adba2c535d261280af5bec65519dfa40b09f`、unit_051 の未コミット変更あり
- adapter: `usb:0`。no-open discovery で bus `6`、device address `11`、port `9,1`、alias `usb:0A12:0001` を確認
- dongle: CSR8510 A10、VID:PID `0a12:0001`、serial / manufacturer string なし
- driver: 既存観測は WinUSB。今回の `Win32_PnPEntity` 再照会はアクセス拒否で確認できず
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `3b82adba2c535d261280af5bec65519dfa40b09f` + unit_051 working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-read-probe.json`
- approval: ユーザが Bluetooth adapter の実機検証を承認。実行時の範囲は standard HCI identity reads と CSR `PSKEY_BDADDR GETREQ` に限定し、HCI Reset、PSKEY write、advertising、Switch-facing command を除外
- result: 2 回とも adapter open 後、最初の `HCI_Read_Local_Version_Information` が `TimeoutError`。CSR Vendor Event command は未送信。observed-partial
- artifact: `tmp/hardware/unit_051/csr-bd-addr-read-probe.json`
- cleanup: 2 回とも `adapter_closed`
- notes: 後続調査で timeout は controller 応答不良ではなく、probe が `Host.ready=True` を設定せず Reset 以外の応答を Bumble に破棄させた実装不備と判明した。この entry は失敗経路の記録として残し、controller capability の失敗根拠には使わない

### 2026-07-19: CSR BD_ADDR read-only probe with HCI Reset

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、HEAD `3b82adba2c535d261280af5bec65519dfa40b09f`、unit_051 の未コミット変更あり
- adapter: `usb:0`。no-open discovery で bus `6`、device address `11`、port `9,1`、alias `usb:0A12:0001` を確認
- dongle: CSR8510 A10、VID:PID `0a12:0001`、serial / manufacturer string なし
- driver: 既存観測は WinUSB。今回の `Win32_PnPEntity` 再照会はアクセス拒否で確認できず
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `3b82adba2c535d261280af5bec65519dfa40b09f` + unit_051 working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-read-probe-success.json`
- approval: ユーザが `usb:0` への HCI Reset、version/address read、CSR GETREQ、close を承認。PSKEY write、BD_ADDR 変更、advertising、Switch-facing command は対象外
- result: pass。HCI version `6`、HCI subversion `8891`、LMP version `6`、company identifier `10`。standard HCI address と CSR PSKEY address はともに `00:1B:DC:F9:9F:7D`。CSR Vendor Event `c201000c00114703700000010004000000f9007d9fdc001b00`、status `0`、`matches_standard_hci=true`
- artifact: `tmp/hardware/unit_051/csr-bd-addr-read-probe-success.json`
- cleanup: `adapter_closed`
- notes: `Host.ready=True` を HCI Reset 完了後に設定し、Bumble `Host.reset()` と同じ受信可能状態へ遷移させた。PSKEY write、advertising、pairing、Switch-facing command は未実行

### 2026-07-19: CSR BD_ADDR volatile probe first attempt

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `84a6abe` 後の volatile probe 未コミット差分あり
- adapter: `usb:0`。実行前 bus `6`、device address `11`、port `9,1`、alias `usb:0A12:0001`。timeout 後の no-open 列挙は同じ port で device address `16`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB。今回の process 内再 open では libusb transfer status `4`
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `84a6abe` + volatile probe working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_volatile_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D --execute --timeout 2 --settle-seconds 0.5 --reopen-timeout 5 --output tmp/hardware/unit_051/csr-bd-addr-volatile-probe.json`
- approval: ユーザが HCI Reset、volatile SETREQ、CSR warm reset、read-back、volatile restore、復旧 read-back、close を承認。persistent write、advertising、Switch-facing command は対象外
- result: baseline standard HCI / CSR PSKEY は `00:1B:DC:F9:9F:7D` で一致。`apply_volatile` 中に `TimeoutError`。artifact は write response と warm reset response を分離していないため、SETREQ 適用の有無は inconclusive。同一 process の best-effort restore は USB transfer error で再 open できなかった
- artifact: `tmp/hardware/unit_051/csr-bd-addr-volatile-probe.json`、`tmp/hardware/unit_051/csr-bd-addr-post-timeout-read.json`
- cleanup: timeout 後の no-open 列挙で USB 再列挙を確認。追加 write なしの別 process read-only probe で standard HCI / CSR PSKEY とも元の `00:1B:DC:F9:9F:7D`、`adapter_closed` を確認
- notes: warm reset 後の同一 process / libusb handle 再利用を前提にできない。次の実験は warm reset を送らず、同一 session 内で PSRAM SETREQ response、PSRAM GETREQ、元値 restore を確認する。ここで SETREQ の受理を切り分けた後、active address 変更は USB 再列挙後の read / restore を別 process に分けて扱う

### 2026-07-19: CSR BD_ADDR PSRAM-only probe first attempt

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `84a6abe` 後の未コミット PSRAM-only probe 差分あり
- adapter: 専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `84a6abe` + PSRAM-only probe working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_volatile_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D --execute --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-psram-roundtrip.json`
- approval: ユーザが `usb:0` の HCI Reset / baseline read、PSRAM SETREQ / GETREQ、active address read、元値 restore / GETREQ、close を承認。warm reset、persistent write、advertising、Switch-facing 動作は対象外
- result: baseline standard HCI / CSR default-store address は `00:1B:DC:F9:9F:7D`、company identifier `10`。`apply_psram_write` と best-effort restore はともに `TimeoutError`。実行後の source audit で、listener が SETREQ `0x0002` に対して response type `0x0002` を要求していた一方、BCCMD の server-to-client response は GETRESP `0x0001` であることを確認した。正常応答を listener が破棄した可能性があるが raw unmatched event がなく、write / restore 適用は inconclusive
- artifact: `tmp/hardware/unit_051/csr-bd-addr-psram-roundtrip.json`
- cleanup: `adapter_closed`。PSRAM の元値 restore は確認できていないため、追加の adapter open / write / HCI Reset を停止し、物理 power cycle を必要条件とした
- notes: persistent write、warm reset、advertising、pairing、Switch-facing command は未実行。response matcher は GETREQ / SETREQ の双方に対する GETRESP `0x0001`、sequence number、VARID を照合するよう修正し、再実行前の unit test で固定する

### 2026-07-19: CSR BD_ADDR post-PSRAM power-cycle read

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `84a6abe` 後の未コミット response matcher 修正あり
- adapter: ユーザが抜き差しした専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `84a6abe` + PSRAM-only probe working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-post-psram-power-cycle.json`
- approval: ユーザが dongle 抜き差し後の `usb:0` に対する HCI Reset、standard identity read、CSR GETREQ、close を承認。PSKEY write、advertising、Switch-facing 動作は対象外
- result: pass。standard HCI / CSR default-store address はともに `00:1B:DC:F9:9F:7D`。company identifier `10`、CSR status `0`、`matches_standard_hci=true`
- artifact: `tmp/hardware/unit_051/csr-bd-addr-post-psram-power-cycle.json`
- cleanup: `adapter_closed`
- notes: 前回未確認だった volatile PSRAM 状態は物理 power cycle 後に元 identity へ復帰した。PSKEY write、advertising、pairing、Switch-facing command は未実行

### 2026-07-19: CSR BD_ADDR PSRAM-only retry

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `84a6abe` 後の GETRESP matcher 修正を含む未コミット差分あり
- adapter: 専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `84a6abe` + PSRAM-only probe working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_volatile_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D --execute --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-psram-roundtrip-retry.json`
- approval: ユーザが `usb:0` の HCI Reset / baseline read、PSRAM SETREQ / GETREQ、active address read、元値 restore / GETREQ、close を承認。warm reset、persistent write、advertising、Switch-facing 動作は対象外
- result: apply SETREQ Vendor Event `c201000c00114703700000010004000800f9007d9fdc001b02` / status `0`。PSRAM GETREQ は sentinel `02:1B:DC:F9:9F:7D` / status `0`。standard HCI address は `00:1B:DC:F9:9F:7D` のまま。restore SETREQ Vendor Event `c201000c00134703700000010004000800f9007d9fdc001b00` / status `0`。restore 後 PSRAM GETREQ は status `0x0008`、best-effort restore も status `0x0008` で失敗。PSRAM write / read-back は observed-pass、warm reset 前の active address 不変は observed-pass、same-session restore は observed-fail
- artifact: `tmp/hardware/unit_051/csr-bd-addr-psram-roundtrip-retry.json`
- cleanup: `adapter_closed`。restore 確認に失敗したため、追加の adapter open / write / HCI Reset を停止し、物理 power cycle を必要条件とした
- notes: persistent write、warm reset、advertising、pairing、Switch-facing command は未実行。restore SETREQ status `0` 後の GETREQ status `0x0008` の意味は未確定。power cycle 後に元 identity を read-only で再確認する

### 2026-07-20: CSR BD_ADDR post-retry power-cycle read

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `84a6abe` 後の未コミット実験差分あり
- adapter: ユーザが抜き差しした専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `84a6abe` + PSRAM-only probe working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-post-psram-retry-power-cycle.json`
- approval: ユーザが dongle 抜き差し後の `usb:0` に対する HCI Reset、standard identity read、CSR GETREQ、close を承認。PSKEY write、advertising、Switch-facing 動作は対象外
- result: pass。standard HCI / CSR default-store address はともに `00:1B:DC:F9:9F:7D`。company identifier `10`、CSR status `0`、`matches_standard_hci=true`
- artifact: `tmp/hardware/unit_051/csr-bd-addr-post-psram-retry-power-cycle.json`
- cleanup: `adapter_closed`
- notes: PSRAM sentinel は power cycle 後に残らないことを再確認した。PSKEY write、advertising、pairing、Switch-facing command は未実行

### 2026-07-20: CSR BD_ADDR staged warm-reset apply

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `6f1ac87`、実行前 clean worktree
- adapter: 専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `6f1ac87`
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_warm_reset_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D --execute --timeout 2 --settle-seconds 0.5 --output tmp/hardware/unit_051/csr-bd-addr-warm-reset-apply.json`
- approval: ユーザが baseline HCI Reset / identity read、PSRAM SETREQ / GETREQ、warm reset 前 active address read、CSR warm reset enqueue、close / USB 再列挙まで承認。persistent write、advertising、pairing、Switch-facing 動作、自動 restore は対象外
- result: baseline standard HCI / CSR default-store address は `00:1B:DC:F9:9F:7D`。apply SETREQ status `0`、PSRAM GETREQ は `02:1B:DC:F9:9F:7D`、warm reset 前 standard HCI address は元値。CSR warm reset command `c2020009000000024000000000000000000000` を enqueue 後、USB OUT transfer status `4` と IN transfer status `4` を観測。process result は `warm_reset_enqueued`。再列挙後の active identity は未確認
- artifact: `tmp/hardware/unit_051/csr-bd-addr-warm-reset-apply.json`
- cleanup: `adapter_closed_or_reenumerated`。別プロセス read 後に物理 power cycle と read-only recovery check が必須
- notes: persistent write、advertising、pairing、Switch-facing command は未実行。USB transfer status `4` は過去の CSR warm reset 再列挙時と一致するが、active identity 変更の根拠にはせず別プロセス read を待つ

### 2026-07-20: CSR BD_ADDR post-warm-reset active read

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `6f1ac87` + staged apply 実機ログの未コミット差分あり
- adapter: CSR warm reset 後に再列挙した専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `6f1ac87`
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-warm-reset-active-read.json`
- approval: ユーザが CSR warm reset / USB 再列挙後の `usb:0` に対する standard identity read、CSR GETREQ、close を承認。HCI Reset、PSKEY write、advertising、Switch-facing 動作は対象外
- result: pass。standard HCI address と CSR default-store address はともに sentinel `02:1B:DC:F9:9F:7D`。company identifier `10`、CSR status `0`、`matches_standard_hci=true`。PSRAM write + CSR warm reset による controller-reported active BD_ADDR の一時変更を observed-pass とする
- artifact: `tmp/hardware/unit_051/csr-bd-addr-warm-reset-active-read.json`
- cleanup: `adapter_closed`。sentinel active 状態のため、追加の adapter open / write / HCI Reset を停止し、物理 power cycle と read-only recovery check を必須とした
- notes: advertising、pairing、Switch-facing command は未実行。on-air BD_ADDR、Switch registration identity、別 firmware / dongle への一般化は未検証

### 2026-07-20: CSR BD_ADDR post-warm-reset recovery

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `6f1ac87` + staged warm-reset 実機ログの未コミット差分あり
- adapter: ユーザが抜き差しした専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `6f1ac87`
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/csr-bd-addr-post-warm-reset-recovery.json`
- approval: ユーザが dongle 抜き差し後の `usb:0` に対する HCI Reset、standard identity read、CSR GETREQ、close を承認。PSKEY write、advertising、Switch-facing 動作は対象外
- result: pass。standard HCI / CSR default-store address はともに `00:1B:DC:F9:9F:7D`。company identifier `10`、CSR status `0`、`matches_standard_hci=true`
- artifact: `tmp/hardware/unit_051/csr-bd-addr-post-warm-reset-recovery.json`
- cleanup: `adapter_closed`
- notes: PSRAM + CSR warm reset による sentinel active identity は物理 power cycle で元 identity へ復帰した。persistent write、advertising、pairing、Switch-facing command は未実行

### 2026-07-20: CSR BD_ADDR unintended read-only preflight during parallel pytest

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `e1cc5b1` + Switch pairing probe の未コミット差分
- adapter: `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `e1cc5b1` + working tree
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run pytest tests/unit -q` と `uv run pytest tests/integration -q` を、双方の既定 `--basetemp=tmp/pytest` のまま並列実行
- approval: この並列 gate による adapter open は意図した承認範囲ではなかった。既存 key store を検出して adapter open 前に止まる unit test の想定だった
- result: unit test subprocess は `identity_preflight_rejected` で終了し、advertising / Switch-facing 動作へ進まなかった。integration pytest の basetemp cleanup により key store fixture と result artifact が競合し、read address、CSR response、`cleanup` field は保存されなかった
- artifact: none。pytest basetemp 競合で削除済み
- cleanup: probe 実装は read-only `_probe()` の `finally` で adapter close を試行するが、result artifact が残っていないため `adapter_closed` は未確認
- notes: テスト subprocess の adapter を `invalid:test-adapter` へ変更した。再実行は `tmp/pytest-unit-csr-switch-pair` と `tmp/pytest-integration-csr-switch-pair` を分け、直列で unit `428 passed`、integration `125 passed` を確認した

### 2026-07-20: CSR BD_ADDR local-address Switch pairing

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `40c239c`、実行前 worktree clean
- adapter: 専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `40c239c63d623d0d30cc80108e206e77a1f97a44`
- Switch model: not re-confirmed in this run
- Switch firmware: not re-confirmed in this run
- report period: default `8000 us`、neutral input のみ
- command / test: `uv run python tools/csr_bd_addr_warm_reset_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D --execute --timeout 2 --settle-seconds 0.5 --output tmp/hardware/unit_051/local-address-warm-reset-apply.json`、続けて `uv run python tools/csr_bd_addr_switch_pair_probe.py --adapter usb:0 --expected-address 02:1B:DC:F9:9F:7D --key-store tmp/hardware/unit_051/local-address-switch-keys.json --trace tmp/hardware/unit_051/local-address-switch-pair.jsonl --output tmp/hardware/unit_051/local-address-switch-pair-result.json --execute --preflight-timeout 2 --pair-timeout 60`
- approval: ユーザが専用 `usb:0`、volatile PSRAM write、CSR warm reset、read-only address 照合、Bumble power-on、HID advertising、Switch pairing、L2CAP / subcommand 応答、neutral periodic report、終了時 close を明示承認。不揮発書き込み、button input、dummy address は対象外
- result: warm-reset probe は original baseline、PSRAM SETREQ status `0`、local address read-back、warm reset enqueue が pass。pairing probe の preflight は standard HCI / CSR default-store ともに `02:1B:DC:F9:9F:7D`、CSR status `0`、一致、preflight adapter close。Bumble trace は `local_bluetooth_address_configured address=021bdcf99f7d`、`advertising_start`、`connection_request`、`host_connection`、`classic_pairing`、fresh `key_store_update status=succeeded`、`connected`、neutral input `0x30` 1件を記録。process は約4秒で `status=paired`
- artifact: `tmp/hardware/unit_051/local-address-warm-reset-apply.json`、`tmp/hardware/unit_051/local-address-switch-pair-result.json`、`tmp/hardware/unit_051/local-address-switch-pair.jsonl`、`tmp/hardware/unit_051/local-address-switch-keys.json`
- cleanup: pairing probe は disconnect request、channel close、`transport_close_complete` を記録し、result は `controller_and_adapter_closed`。dongle は local address の volatile active 状態なので、物理 power cycle と read-only recovery check 前に追加 write / dummy address 実験を行わない
- notes: local address が対象 Switch の pairing / HID connection に受理されることは observed-pass。元 BD_ADDR の登録と別 device に見えたかはユーザが目視確認を逃したため unobserved であり、on-air address を別 sniffing 機器で直接観測した結果ではない

### 2026-07-20: CSR BD_ADDR local-address 5-second registration rerun

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `ca34630`、実行前 worktree clean
- adapter: 専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `ca34630a2fca05f65f12688da98e04f0cc1fcb12`
- Switch model: not re-confirmed in this run
- Switch firmware: not re-confirmed in this run
- report period: default `8000 us`、neutral input のみ、接続後 observation `5.0 s`
- command / test: `uv run python tools/csr_bd_addr_warm_reset_probe.py --adapter usb:0 --expected-original 00:1B:DC:F9:9F:7D --requested-address 02:1B:DC:F9:9F:7D --execute --timeout 2 --settle-seconds 0.5 --output tmp/hardware/unit_051/local-address-pair-rerun-warm-reset-apply.json`、続けて `uv run python tools/csr_bd_addr_switch_pair_probe.py --adapter usb:0 --expected-address 02:1B:DC:F9:9F:7D --key-store tmp/hardware/unit_051/local-address-switch-keys.json --reuse-key-store --trace tmp/hardware/unit_051/local-address-switch-pair-rerun.jsonl --output tmp/hardware/unit_051/local-address-switch-pair-rerun-result.json --execute --preflight-timeout 2 --pair-timeout 60 --observation-seconds 5`
- approval: ユーザが専用 `usb:0` への local address volatile 再適用、warm reset、既存 local-address key store 再利用、HID advertising / pairing、neutral report loop を接続後5秒維持、終了時 close を明示承認。dummy address、不揮発書き込み、button input は対象外
- result: pass。warm-reset probe は original baseline、PSRAM SETREQ status `0`、local address read-back、warm reset enqueue が pass。pairing preflight は standard HCI / CSR default-store が `02:1B:DC:F9:9F:7D` で一致。Bumble trace は power-on 後 local address、advertising、connection request、host connection、`classic_pairing`、`key_store_update previous_saved=true status=succeeded`、HID connected、subcommand reply `0x21` 16件、periodic neutral `0x30` 107件、終了時 neutral `0x30` 1件を記録。ユーザは Switch UI で登録されたことを目視確認した
- artifact: `tmp/hardware/unit_051/local-address-pair-rerun-warm-reset-apply.json`、`tmp/hardware/unit_051/local-address-switch-pair-rerun-result.json`、`tmp/hardware/unit_051/local-address-switch-pair-rerun.jsonl`
- cleanup: result は `controller_and_adapter_closed`。trace は disconnect request、control / interrupt channel close、`transport_close_complete` を記録
- notes: local address が対象 Switch の登録経路に受理されたことは hardware observation。元の BD_ADDR 登録を削除せず実行したため別 identity として扱われた可能性は強い inference だが、Switch UI は BD_ADDR を表示せず、on-air sniffing も行っていない。dongle は local address の volatile active 状態なので物理 power cycle と recovery read 前に dummy address へ進まない

### 2026-07-20: CSR BD_ADDR local-address post-pair recovery

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `40c239c` + local-address pairing 実機ログの未コミット差分
- adapter: ユーザが抜き差しした専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `40c239c63d623d0d30cc80108e206e77a1f97a44`
- Switch model: not used
- Switch firmware: not used
- report period: not applicable
- command / test: `uv run python tools/csr_bd_addr_probe.py --adapter usb:0 --hci-reset --timeout 2 --output tmp/hardware/unit_051/local-address-post-pair-recovery.json`、ユーザ依頼による再確認は出力先を `tmp/hardware/unit_051/local-address-post-pair-recovery-recheck.json` に変更して同じ read-only command を実行
- approval: ユーザが dongle 抜き差し後の元接続の復旧確認を依頼。範囲は専用 `usb:0`、HCI Reset、standard identity read、CSR GETREQ、close。PSKEY write、advertising、pairing、dummy address 操作は対象外
- result: 2回連続で pass。standard HCI / CSR default-store address は2回とも元の `00:1B:DC:F9:9F:7D`。company identifier `10`、CSR status `0`、`matches_standard_hci=true`
- artifact: `tmp/hardware/unit_051/local-address-post-pair-recovery.json`、`tmp/hardware/unit_051/local-address-post-pair-recovery-recheck.json`
- cleanup: 2回とも `adapter_closed`
- notes: local-address pairing 後の volatile identity は物理 power cycle で元 identity へ復帰した。dummy address 実験へ進める初期状態を回復した

### 2026-07-20: CSR BD_ADDR dummy-address Switch pairing

- OS: Windows 11 `10.0.26200`
- environment: branch `experiment/bd-addr-rewrite`、commit `18696ef`、実行前 worktree clean
- adapter: 専用 `usb:0`
- dongle: CSR8510 A10、VID:PID `0a12:0001`
- driver: WinUSB
- Python: `3.13.5`
- Bumble: `0.0.230`
- swbt-python: `18696ef429bebeeb132bbb9cc4cc75841d7a6155`
- Switch model: not re-confirmed in this run
- Switch firmware: not re-confirmed in this run
- report period: default `8000 us`、neutral input のみ、接続後 observation `5.0 s`
- command / test: local rerun後のrecovery read、`dummy-address-warm-reset-apply.json` へのdummy address初回適用、fresh `dummy-address-switch-keys.json` でのpairing、reuse attempt、`dummy-address-rerun-warm-reset-apply.json` への再適用、同key storeでの5秒rerunを順に実行。各完全commandは対応artifactと会話承認に記録
- approval: ユーザが専用 `usb:0` の復旧read、dummy address volatile適用、warm reset、fresh / reuse dummy key storeによるHID advertising / pairing、neutral report loopを接続後5秒維持、終了時closeを段階ごとに明示承認。不揮発書き込みとbutton inputは対象外
- result: local rerun後のrecovery readは元addressでpass。dummy初回適用はPSRAM SETREQ status `0`、read-back、warm reset enqueueがpass。fresh pairing preflightはstandard HCI / CSR default-storeが`00:11:22:33:44:55`で一致し、Classic pairing、fresh key store、HID connected、initial subcommand 16件、neutral `0x30` 116件、clean closeがpassしたが、ユーザ目視はSwitch UI反応なし。close後のreuse attemptはpreflightでstandard HCI / CSRが元addressへ戻っていることを検出し、`identity_preflight_rejected`、`advertising=false`、adapter close。dummy再適用後のreuse rerunはdummy address一致、`classic_pairing`、`key_store_update previous_saved=true`、HID connected、neutral `0x30` 106件、clean closeがpassし、ユーザがSwitch UIで登録されたことを目視確認した
- artifact: `tmp/hardware/unit_051/local-address-pair-rerun-recovery.json`、`dummy-address-warm-reset-apply.json`、`dummy-address-switch-pair-result.json`、`dummy-address-switch-pair.jsonl`、`dummy-address-switch-keys.json`、`dummy-address-switch-pair-rerun-result.json`、`dummy-address-rerun-warm-reset-apply.json`、`dummy-address-switch-pair-rerun2-result.json`、`dummy-address-switch-pair-rerun2.jsonl`
- cleanup: 各pairing processはL2CAP channel close、disconnect request、`transport_close_complete`、result `controller_and_adapter_closed`。reuse guard failureもpreflight adapter close。最後のdummy pairing後はphysical power cycle / recovery readが必要
- notes: warm reset enqueue直後の `OUT transfer not completed: status=4` とIN transfer未完了はUSB再列挙時に古いhandleで観測される警告。単独では成功根拠にせず、別processのstandard HCI / CSR / Bumble address一致で適用成功と判定した。fresh初回run後、物理抜き差しなしの次preflightで元addressへ戻ったことはhardware observation。Bumble 0.0.230 `Device.power_off()`はhost flushのみで明示HCI Resetを送らず、復帰原因はcontroller / transport close依存の未検証仮説とする

## Run Entry Template

### YYYY-MM-DD: short title

- OS:
- environment:
- adapter:
- dongle:
- driver:
- Python:
- Bumble:
- swbt-python:
- Switch model:
- Switch firmware:
- report period:
- command / test:
- approval:
- result:
- artifact:
- cleanup:
- notes:

## Hardware Matrix

| OS | Bluetooth dongle | Driver | Adapter | Switch model | Firmware | Pairing | L2CAP | Subcommands | Input reflected | Reconnect | Result source | Last updated | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Windows | CSR8510 A10 | WinUSB / libwdi 6.1.7600.16385 | `usb:0` | Switch 2 | 22.1.0 | observed-pass for Pro profile; observed-pass for Joy-Con L/R registration after SDP policy retest and R1/R4 runs | pass | pass for full observed M5 handshake sequence; unit_028 body/buttons/controller grip color SPI reply pass; tracked sentinel profile hardware test pass with device-info tail `03 02`; Joy-Con L observed init sequence, default controller color SPI reply, and `0x40` IMU mode `0x02` replied; Joy-Con R custom color SPI reply pass in R4 | observed-pass for Pro profile Button A / neutral / D-pad / left and right stick; Joy-Con L SR+SL input sent after observed init and user observed Joy-Con registration; Joy-Con L D-pad up/right/down/left observed-pass in L3; Joy-Con L left stick hold observed conditional-pass in L4; Joy-Con R ABXY observed-pass in R2; Joy-Con R right stick hold observed conditional-pass in R3 | observed-pass for Pro profile active bond reuse reconnect after explicit Classic authentication/encryption; Joy-Con L active reconnect pass in L3/L4; Joy-Con R active reconnect pass in R2/R3 | 2026-07-04 unit_013 input semantics, unit_007 active reconnect, 2026-07-05 unit_028 controller color SPI reply, 2026-07-06 Joy-Con L communication / SDP policy / default color characterization, and 2026-07-07 Joy-Con L L3/L4 plus Joy-Con R R2/R3/R4 runs | 2026-07-07 | Release gate minimum は Pro profile の pairing、L2CAP、subcommand 応答、Button A、neutral。unit_013 で Switch 2 / firmware 22.1.0 の D-pad と left / right stick 反映も確認済み。unit_028 で Switch からの `0x6050` SPI read に custom body/buttons/grip color bytes が返ることを trace で確認した。daemon-like tail `01 01` では grip が body 色に寄ったが、device-info tail `03 02` では sentinel left/right grip がマゼンタ/オレンジに反映された。Joy-Con L run は `Joy-Con (L)` device name、Device Info reply、observed init sequence、SR+SL `000030` input report、L3 D-pad up/right/down/left input report、L4 left stick hold / circle input report を記録した。Joy-Con R run は `Joy-Con (R)` device name、Device Info reply、SR+SL `300000` input report、R2 ABXY input report、R3 right stick hold / circle input report、R4 custom color SPI reply `00ff008000ff00ffffffff00` を記録した。`f249261` と `b81cce0` までの run では Pro Controller toast / Joy-Con 登録未完了だったが、`867a785` 後の SDP policy retest ではユーザ目視で Joy-Con として登録された。`196ac6f` 後の default color retest では Joy-Con L 既定 color bytes `00b2ff32323200b2ff00b2ff` を SPI `0x6050` へ返したことを確認し、ユーザは Switch UI で body が青色または水色、buttons が黒色に見えると報告した。buttons byte は `0x323232` なので濃灰の UI 目視として扱う。R4 では Joy-Con R custom color の body 緑 / buttons 紫をユーザが目視した。Bumble debug log は SDP attribute read を直接表示しないため、on-air SDP attribute そのものは自動判定していない。Joy-Con L/R stick は Switch UI が横持ち Joy-Con の補正を拒否したため hold までの条件付き pass であり、full calibration UI 完了ではない。別 firmware / dongle は未確認。UI 表示は自動判定せず、cross-firmware guarantee にしない。incoming run は route 分離と subcommand sequence を記録したが、`classic_pairing` と `key_store_update` も出たため pairing-free incoming bond reuse とは扱わない |
| Linux | 未検証 | libusb 想定 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-07-04 | experimental。手順は docs/hardware.md に整備しているが、adapter listing / open、pairing、input reflection は未確認 |
| macOS | CSR8510 A10 | libusb 1.0.30 via Homebrew, `DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib` | `usb:0` | Switch 2 | 未記録 | observed-pass | pass | pass for full observed M5 handshake sequence in active reconnect button check | observed-pass for button input and neutral | observed-pass for active bond reuse reconnect after explicit Classic authentication/encryption | 2026-07-05 macOS pairing smoke and active reconnect button check | 2026-07-05 | experimental。macOS 15.7.7 で adapter open、HID advertising、pairing、HID control / interrupt L2CAP open、active reconnect、full observed subcommand handshake、Button A / L+R / neutral report checkpoints、button input reflection、clean close を確認。D-pad、left / right stick、Switch firmware、reconnect 以外の入力は未確認 |

## Run Entries

### 2026-07-07: Joy-Con L L3 D-pad button check

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch with L3 hardware test implementation in working tree
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`
- driver: WinUSB expected from previous Windows inventory. This run did not re-enumerate driver state
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.2.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default periodic `0x30`
- command / test: `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l3 --log-file build\hardware\profile-regression-20260707\joycon-l-l3\l3-joycon-left-initial-pairing-pytest-debug.log --log-file-level=DEBUG -q -s`; then `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_left_button_check_dpad_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l3-rerun2 --log-file build\hardware\profile-regression-20260707\joycon-l-l3-rerun2\l3-joycon-left-button-check-dpad-rerun2-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested L3 execution and later approved initial pairing after active reconnect failed with the old key store. Scope included Bumble adapter open, Classic HID initialization, initial Joy-Con L pairing for L3 key store, HID channels, periodic report loop, D-pad up/right/down/left input, neutral after each direction, and close cleanup
- result: pass. Initial L3 key store pairing passed with Device Info `controller_type=0x01`, SR+SL `000030`, neutral, and cleanup. A stale-key run against `joycon-l-after-clear` failed at active reconnect authentication before any non-neutral input. A first `joycon-l-l3` D-pad run passed pytest but failed the UI precondition because the Switch was not on the button operation check screen; user observed down input and immediate exit. Final rerun passed pytest and user observed buttons pressed in order: up, right, down, left
- artifact: `build\hardware\profile-regression-20260707\joycon-l-l3\joycon-left-profile-pairing.jsonl`, `build\hardware\profile-regression-20260707\joycon-l-l3\l3-joycon-left-initial-pairing-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-l-l3-rerun2\joycon-left-button-check-dpad.jsonl`, `build\hardware\profile-regression-20260707\joycon-l-l3-rerun2\l3-joycon-left-button-check-dpad-rerun2-pytest-debug.log`
- cleanup: initial pairing and final L3 run both executed `pad.close(neutral=True)`; traces recorded neutral after each direction and `transport_close_complete`
- notes: The final test order was up `000002`, neutral, right `000004`, neutral, down `000001`, neutral, left `000008`, neutral. Joy-Con L has no Button A in this profile, so the button operation check screen entry is a human setup condition, not an automated step. The temporary post-reconnect wait used during one retry was removed from the tracked test after the user confirmed it was unnecessary

### 2026-07-07: Joy-Con L L4 left stick hold conditional pass

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch with L4 hardware test implementation in working tree
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`
- driver: WinUSB expected from previous Windows inventory. This run did not re-enumerate driver state
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.2.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default periodic `0x30`
- command / test: copied the L3 key store with `Copy-Item -Path build\hardware\profile-regression-20260707\joycon-l-l3\joycon-left-profile-key-store.json -Destination build\hardware\profile-regression-20260707\joycon-l-l4\joycon-left-profile-key-store.json -Force`; then ran `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_left_stick_calibration_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l4 --log-file build\hardware\profile-regression-20260707\joycon-l-l4\l4-joycon-left-stick-calibration-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user stated the Switch was waiting on the stick input validation screen and requested continuing. Scope included Bumble adapter open, active reconnect from the Joy-Con L key store, HID channels, periodic report loop, left stick hold, left stick circle, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. Scope excluded pairing and Joy-Con R input
- result: conditional-pass, `1 passed in 15.62s`. Trace `joycon-left-stick-calibration.jsonl` recorded active reconnect, full handshake, `left_stick_hold_start`, `left_stick_hold_reports_sent` with `hold_report_count=120`, `left_stick_circle_complete` with `steps=32` and `step_seconds=0.15`, `left_stick_neutral_complete`, `manual_joycon_profile_cleanup connection_state=closed`, and no `error`. User observed hold, but the Switch UI rejected calibration for a horizontal Joy-Con with "横持ちだと補正できません". This is treated as a device/UI constraint, not a protocol failure
- artifact: `build\hardware\profile-regression-20260707\joycon-l-l4\joycon-left-stick-calibration.jsonl`, `build\hardware\profile-regression-20260707\joycon-l-l4\l4-joycon-left-stick-calibration-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-l-l4\joycon-left-profile-key-store.json`
- cleanup: run executed `pad.close(neutral=True)`; trace recorded neutral after the stick sequence and `transport_close_complete`. The adapter was released
- notes: L4 does not prove that Switch's stick calibration UI can complete for a horizontal single Joy-Con. It proves active reconnect, left-stick report emission, visible hold up to the UI rejection point, neutral cleanup, and close cleanup under this environment. A Joy-Con R stick scenario is expected to hit the same horizontal Joy-Con UI constraint unless a different Switch screen can reflect stick movement

### 2026-07-07: H1 open-only smoke did not start advertising

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch at commit `0aad3de`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: not started
- command / test: `uv run pytest tests\hardware\test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\h1-open-only --log-file build\hardware\profile-regression-20260707\h1-open-only\h1-open-only-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved continuing with H1 and kept the Switch on a waiting screen to visually confirm no connection starts. Scope used adapter `usb:0`, USB Bluetooth dongle open, Bumble Device initialization, SDP / HID Device initialization, close cleanup, trace save, and debug log save. Scope excluded HID advertising, discoverable / connectable wait, Switch pairing, HID channel connection, report loop, and input sending.
- result: pass, `1 passed in 0.32s`. Trace `resource-open-only.jsonl` recorded `run_metadata`, `bumble_runtime`, `transport_open_start`, `bumble_device_initialized device_name=Pro Controller class_of_device=0x002508`, `sdp_record_registered hid_descriptor_size=203`, `hid_device_initialized`, `transport_open_complete`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. The trace recorded no `advertising_start` and no `host_connection`.
- user observation: user observed no reaction on the Switch waiting screen. This matches the trace expectation that no advertising or host connection started.
- artifact: `build\hardware\profile-regression-20260707\h1-open-only\resource-open-only.jsonl`, `build\hardware\profile-regression-20260707\h1-open-only\h1-open-only-pytest-debug.log`
- cleanup: run reached `transport_close_complete`. Since no HID channels connected, disconnect request was unavailable by design. The adapter was released.
- notes: This smoke verifies resource scope only. It does not advertise, pair, open HID L2CAP channels, start the report loop, or send input reports.

### 2026-07-07: H2 advertising smoke reached advertising and closed cleanly

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch at commit `0aad3de` plus uncommitted H1 hardware log update
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: not started
- command / test: `uv run pytest tests\hardware\test_bumble_transport.py::test_bumble_hid_transport_advertising_smoke_records_diagnostics -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\h2-advertising-smoke --log-file build\hardware\profile-regression-20260707\h2-advertising-smoke\h2-advertising-smoke-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved H2 hardware verification and stated the Switch would stay on the connection screen. Scope used adapter `usb:0`, USB Bluetooth dongle open, Bumble Device initialization, SDP / HID Device initialization, HID advertising, trace save, debug log save, close cleanup, and adapter release. Scope excluded waiting for Switch pairing, HID channel connection, report loop, and input sending.
- result: pass, `1 passed in 0.52s`. Trace `bumble-hid-advertising-smoke.jsonl` recorded `run_metadata`, `bumble_runtime`, `transport_open_start`, `bumble_device_initialized device_name=Pro Controller class_of_device=0x002508`, `sdp_record_registered hid_descriptor_size=203`, `hid_device_initialized`, `transport_open_complete`, `local_bluetooth_address_configured address=001bdcf99f7d`, `classic_link_policy_configured settings=0x0005`, `advertising_start`, and `transport_close_complete`. The trace recorded no `connection_request`, `host_connection`, `classic_pairing`, or `error`.
- user observation: user observed no connection reaction on the Switch waiting screen. This matches the trace expectation that no host connection or pairing started.
- artifact: `build\hardware\profile-regression-20260707\h2-advertising-smoke\bumble-hid-advertising-smoke.jsonl`, `build\hardware\profile-regression-20260707\h2-advertising-smoke\h2-advertising-smoke-pytest-debug.log`
- cleanup: run reached `transport_close_complete`. No HID channels connected and no report loop started. The adapter was released.
- notes: This smoke verifies Bumble HID advertising setup and close cleanup only. It does not wait for pairing, does not open HID L2CAP channels, and does not send input reports.

### 2026-07-07: Pro Controller profile regression P1-P7 pass after IMU mode fix and P4 merge

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch. P1 and initial P2 runs started at `3c3aead`; P3 ran after the ProController `0x02` compatibility fix at `a4308bb`; initial LR-only P4 ran at `25824eb`; integrated P4 ran at `4db15a0` plus the working tree test change that merged LR and D-pad into one node; P5 ran at `806ec87`; P6 ran at `ec7cf6f`; P7 ran at `3388b34`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`, bus `6`, device address `14`, ports `9,1`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0. P1 and initial P2 used commit `3c3aead`; fixed P2 and P3 used the ProController `0x02` compatibility implementation committed as `a4308bb`; initial LR-only P4 used commit `25824eb`; integrated P4 used `4db15a0` plus the working tree test change; P5 used commit `806ec87`; P6 used commit `ec7cf6f`; P7 used commit `3388b34`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Pro Controller default `8000` us
- command / test: no-open adapter discovery used `uv run swbt-probe adapters --json`. P1 used `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p1-pairing-l2cap-pytest-debug.log --log-file-level=DEBUG -q -s`. P2 used `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p2-subcommand-window-pytest-debug.log --log-file-level=DEBUG -q -s`. P2 after clearing Switch-side connection information used `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro-p2-after-clear --log-file build\hardware\profile-regression-20260707\pro-p2-after-clear\p2-subcommand-window-after-clear-pytest-debug.log --log-file-level=DEBUG -q -s`. P2 after ProController `0x02` compatibility fix used `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro-p2-accept-imu-02 --log-file build\hardware\profile-regression-20260707\pro-p2-accept-imu-02\p2-subcommand-window-accept-imu-02-pytest-debug.log --log-file-level=DEBUG -q -s`. P3 used `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_semantics_pairing_writes_fresh_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p3-input-semantics-key-store-pytest-debug.log --log-file-level=DEBUG -q -s`. Initial LR-only P4 used `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_separate_l_r_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p4-button-lr-split-pytest-debug.log --log-file-level=DEBUG -q -s`. Integrated P4 used `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_lr_and_dpad_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p4-button-lr-dpad-pytest-debug.log --log-file-level=DEBUG -q -s`. P5 used `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p5-left-stick-pytest-debug.log --log-file-level=DEBUG -q -s`. P6 used `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p6-right-stick-pytest-debug.log --log-file-level=DEBUG -q -s`. P7 used `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\pro --log-file build\hardware\profile-regression-20260707\pro\p7-post-handshake-a-close-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested hardware tests and stated the Switch was waiting on controller search / change grip order for P1-P3. P1 scope included USB dongle open, Pro Controller HID advertising, Switch pairing, HID control / interrupt L2CAP, periodic neutral report, and `close(neutral=True)` cleanup. P2 added Switch-facing output report / subcommand observation and `0x21` replies for observed subcommands. P3 added fresh input semantics key store creation with full handshake and neutral close. For initial P4, user stated the Switch-side setup was complete; scope used active reconnect from the P3 key store, Button A, R-only, L-only, L+R, neutral, trace save, debug log save, and `close(neutral=True)` cleanup. For integrated P4, user requested merging P4/P5 and rerunning it as P4; scope added D-pad up/right/down/left before final neutral and close. For P5, user stated the Switch-side setup was complete; scope used active reconnect from the P3 key store, Button A, left stick hold, left stick circle, neutral, trace save, debug log save, and `close(neutral=True)` cleanup. For P6, user stated the Switch-side setup was complete; scope used active reconnect from the P3 key store, Button A, right stick hold, right stick circle, neutral, trace save, debug log save, and `close(neutral=True)` cleanup. For P7, user stated the Switch was set to controller search / change grip order; scope used USB dongle open, Pro Controller HID advertising, Switch pairing, full handshake, Button A to exit the registration screen, neutral, disconnect request, post-close UI observation window, trace save, debug log save, and `close(neutral=True)` cleanup.
- result: P1 passed, `1 passed in 2.96s`. P1 trace recorded `device_name=Pro Controller`, `class_of_device=0x002508`, `classic_pairing`, HID control / interrupt L2CAP open, `connected`, one neutral `0x30`, disconnect request, and `transport_close_complete`. First P2 failed, `1 failed in 8.17s`. P2 trace recorded `device_name=Pro Controller` and `connected`, then observed subcommands including `0x02`, `0x08`, repeated `0x10`, `0x03`, `0x04`, and repeated `0x40`. Each observed `0x40` reached `ProtocolError` with message `enable IMU subcommand argument must be 0x00 or 0x01`; this corresponds to a Joy-Con-only `0x02` IMU mode in the pre-fix implementation. After the user deleted Switch-side connection information, P2 rerun also failed, `1 failed in 7.52s`, with the same `0x40` `ProtocolError`. The rerun trace recorded `device_name=Pro Controller`, `class_of_device=0x002508`, `connected`, `report_mode=0x30`, seven `error` events, disconnect, and `transport_close_complete`. The rerun debug log recorded the first failed raw HID interrupt PDU as `a2010400014040000140404002...`; after HIDP header `a2` and report `0x01`, this is packet `0x04`, rumble payload, subcommand `0x40`, payload first byte `0x02`. After the ProController `0x02` compatibility change, P2 passed, `1 passed in 8.05s`. The pass trace recorded `device_name=Pro Controller`, `class_of_device=0x002508`, `connected`, `subcommand_session_state imu_mode=0x02 imu_enabled=true` for `0x40`, subsequent `0x48` vibration state, `0x21` reply, periodic neutral `0x30`, disconnect request, and `transport_close_complete`. The pass trace recorded no `error` or `unsupported_subcommand`.
- P3 result: passed, `1 passed in 9.76s`. Trace `input-semantics-fresh-pairing.jsonl` recorded `route=pairing`, `key_store_update status=succeeded`, `connected`, full observed handshake, `subcommand_session_state imu_mode=0x02 imu_enabled=true` for `0x40`, `manual_input_checkpoint operation=handshake_complete`, 24 `report_tx` events, and `transport_close_complete adapter=usb:0`. The trace recorded no `error` or `unsupported_subcommand`. `input-semantics-key-store.json` exists and was not opened for logging because it contains link key material.
- initial P4 result: passed, `1 passed in 10.97s`. Trace `active-reconnect-button-check-lr-split.jsonl` reused `input-semantics-key-store.json` and recorded active reconnect `status=connected`, `connection_authentication`, `connection_encryption_change encryption=1`, full handshake, Button A entry, R-only `expected_button_bytes=400000`, L-only `expected_button_bytes=000040`, L+R `expected_button_bytes=400040`, neutral complete, 178 `report_tx` events, and `transport_close_complete adapter=usb:0`. The trace recorded no `classic_pairing`, `key_store_update`, `advertising_start`, or `error`. This run was superseded by the integrated P4 because D-pad could be exercised in the same button check screen.
- integrated P4 result: passed, `1 passed in 14.09s`. Trace `active-reconnect-button-check-lr-dpad.jsonl` reused `input-semantics-key-store.json` and recorded active reconnect `status=connected`, `connection_authentication`, `connection_encryption_change encryption=1`, full handshake, Button A entry, R-only `400000`, L-only `000040`, L+R `400040`, D-pad up `000002`, right `000004`, down `000001`, left `000008`, neutral checkpoints after each hold, 330 `report_tx` events, and `transport_close_complete adapter=usb:0`. The trace recorded no `classic_pairing`, `key_store_update`, `advertising_start`, or `error`.
- P5 result: passed, `1 passed in 16.83s`. Trace `active-reconnect-left-stick.jsonl` reused `input-semantics-key-store.json` and recorded active reconnect `status=connected`, `connection_authentication`, `connection_encryption_change encryption=1`, full handshake, Button A entry, settle `1.5` seconds, left stick hold `hold_report_count=120`, left stick circle `steps=32` and `step_seconds=0.15`, neutral complete, 465 `report_tx` events, and `transport_close_complete adapter=usb:0`. The trace recorded no `classic_pairing`, `key_store_update`, `advertising_start`, or `error`.
- P6 result: passed, `1 passed in 16.87s`. Trace `active-reconnect-right-stick.jsonl` reused `input-semantics-key-store.json` and recorded active reconnect `status=connected`, `connection_authentication`, `connection_encryption_change encryption=1`, full handshake, Button A entry, settle `1.5` seconds, right stick hold `hold_report_count=120`, right stick circle `steps=32` and `step_seconds=0.15`, neutral complete, 464 `report_tx` events, and `transport_close_complete adapter=usb:0`. The trace recorded no `classic_pairing`, `key_store_update`, `advertising_start`, or `error`.
- P7 result: passed, `1 passed in 7.90s`. Trace `post-handshake-a-close.jsonl` recorded `classic_pairing`, `key_store_update status=succeeded`, `connected`, 16 observed `subcommand_rx` events and 16 matching `subcommand_reply_tx` events, `manual_close_checkpoint operation=full_handshake_complete` with `last_subcommand_id=0x30`, Button A exit checkpoint, neutral checkpoint, `close_start`, trailing neutral `0x30` input report, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete adapter=usb:0`, `close_complete`, and `post_close_ui_observation_window_complete`. The trace recorded 78 `report_tx` events and no `error`.
- user observation: first P2 showed a blue Joy-Con device toast, then the connection completed as Pro Controller. After deleting connection information, the rerun showed ProCon toast and paired as ProCon. For P4, simultaneous L+R press is not strictly observable on the Switch UI, but the user confirmed key input and accepted the scenario as pass. For integrated P4, the user reported that input confirmation was OK and input matched the expected values. For P5, the user saw the left stick hold and circle. The circle appeared counterclockwise / left-rotating; this matches the test implementation, which sends `x=cos(angle)` and `y=sin(angle)` while increasing `angle`. For P6, the user saw the right stick hold and circle. For P7, the user observed both Button A exiting the registration screen and disconnect after close. These are human-visible observations and are not automated assertions from pytest.
- artifact: `build\hardware\profile-regression-20260707\pro\pairing-l2cap.jsonl`, `build\hardware\profile-regression-20260707\pro\p1-pairing-l2cap-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\subcommand-observation-window.jsonl`, `build\hardware\profile-regression-20260707\pro\p2-subcommand-window-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\input-semantics-fresh-pairing.jsonl`, `build\hardware\profile-regression-20260707\pro\input-semantics-key-store.json`, `build\hardware\profile-regression-20260707\pro\p3-input-semantics-key-store-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\active-reconnect-button-check-lr-split.jsonl`, `build\hardware\profile-regression-20260707\pro\p4-button-lr-split-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\active-reconnect-button-check-lr-dpad.jsonl`, `build\hardware\profile-regression-20260707\pro\p4-button-lr-dpad-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\active-reconnect-left-stick.jsonl`, `build\hardware\profile-regression-20260707\pro\p5-left-stick-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\active-reconnect-right-stick.jsonl`, `build\hardware\profile-regression-20260707\pro\p6-right-stick-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro\post-handshake-a-close.jsonl`, `build\hardware\profile-regression-20260707\pro\p7-post-handshake-a-close-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro-p2-after-clear\subcommand-observation-window.jsonl`, `build\hardware\profile-regression-20260707\pro-p2-after-clear\p2-subcommand-window-after-clear-pytest-debug.log`, `build\hardware\profile-regression-20260707\pro-p2-accept-imu-02\subcommand-observation-window.jsonl`, `build\hardware\profile-regression-20260707\pro-p2-accept-imu-02\p2-subcommand-window-accept-imu-02-pytest-debug.log`
- cleanup: P1, failed P2 runs, fixed P2 rerun, P3, initial P4, integrated P4, P5, P6, and P7 all reached disconnect request and `transport_close_complete`. P2/P3/P4/P5/P6/P7 sent trailing neutral `0x30` before close. The adapter was released.
- notes: `0x40` mode `0x02` remains a hardware-observed compatibility mode for this Windows / CSR8510 A10 / Switch 2 firmware 22.1.0 condition. The implementation now accepts it for ProController and records the exact requested mode instead of collapsing it to boolean. This does not make a cross-firmware claim and does not implement IMU frame semantics.

### 2026-07-07: Joy-Con L L1 profile pairing after clearing Switch connection information

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch. Runs used commit `b325311`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con L profile default `8000` us
- command / test: initial L1 used `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l --log-file build\hardware\profile-regression-20260707\joycon-l\l1-joycon-left-profile-pairing-pytest-debug.log --log-file-level=DEBUG -q -s`. After the user deleted Switch-side connection information, L1 rerun used `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-after-clear --log-file build\hardware\profile-regression-20260707\joycon-l-after-clear\l1-joycon-left-profile-pairing-after-clear-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user stated the Switch was waiting on controller search / change grip order for L1. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con L HID advertising, Switch pairing, Device Info reply, observed order input window, SR+SL hold, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. After the first UI observation, user deleted Switch-side connection information and requested L1 rerun with the same scope.
- result: initial L1 passed, `1 passed in 24.51s`. Trace `joycon-left-profile-pairing.jsonl` recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `advertising_start`, `classic_pairing`, `key_store_update previous_saved=false status=succeeded`, `connected`, Device Info reply `device_info_data=04000102001bdcf99f7d0101` with `controller_type=0x01` and `profile_bluetooth_address_bytes=001bdcf99f7d`, order input window, SR+SL `expected_button_bytes=000030`, `input_report_delta=146`, neutral complete, UI observation hold complete, 483 `report_tx` events, `transport_close_complete`, and no `error`. Debug log confirmed `HCI_WRITE_LOCAL_NAME_COMMAND local_name=Joy-Con (L)` and EIR local name `Joy-Con (L)`, while Class of Device remained `0x002508`. After Switch-side connection information deletion, L1 rerun passed, `1 passed in 24.50s`. Trace recorded the same Joy-Con L discovery / Device Info / SR+SL / neutral / cleanup sequence with `input_report_delta=149`, 498 `report_tx` events, `transport_close_complete`, and no `error`.
- user observation: initial L1 showed an initial registration toast as Pro Controller, although registration itself completed. After deleting Switch-side connection information and rerunning L1, the user observed blue Joy-Con (L), with normal toast. This supports the inference that the initial Pro toast was caused by Switch-side stored connection information for the same Bluetooth address, not by the current Joy-Con L local name or Device Info payload.
- artifact: `build\hardware\profile-regression-20260707\joycon-l\joycon-left-profile-pairing.jsonl`, `build\hardware\profile-regression-20260707\joycon-l\l1-joycon-left-profile-pairing-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-l\joycon-left-profile-key-store.json`, `build\hardware\profile-regression-20260707\joycon-l-after-clear\joycon-left-profile-pairing.jsonl`, `build\hardware\profile-regression-20260707\joycon-l-after-clear\l1-joycon-left-profile-pairing-after-clear-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-l-after-clear\joycon-left-profile-key-store.json`
- cleanup: both L1 runs reached `transport_close_complete` and `manual_joycon_profile_cleanup connection_state=closed`. Both sent neutral after SR+SL before close. The adapter was released.
- notes: Current discovery identity evidence is mixed by design: HCI local name and EIR local name are Joy-Con (L), Device Info is Joy-Con L, and SDP policy is Joy-Con-specific, but Class of Device remains `0x002508` per existing source-audited boundary. Because the after-clear rerun produced normal Joy-Con L toast, this run does not justify changing Class of Device.

### 2026-07-07: Joy-Con L custom controller colors L2 pass

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch at commit `8c5e352`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con L profile default `8000` us
- command / test: `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_left_profile_reads_custom_controller_colors' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors --log-file build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors\l2-joycon-left-custom-colors-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the L2 custom-color run after the scope was stated. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con L HID advertising, Switch pairing, Device Info reply, SPI `0x6050` custom controller color read reply, observed order input window, SR+SL hold, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. Scope excluded reconnect, normal input reflection, Joy-Con R, and broader firmware / adapter matrix claims.
- result: pass, `1 passed in 24.58s`. Trace `joycon-left-custom-controller-colors.jsonl` recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, Device Info `device_info_data=04000102001bdcf99f7d0101` with `controller_type=0x01` and `profile_bluetooth_address_bytes=001bdcf99f7d`, SPI read `address=0x006050`, `controller_color_bytes=ff00000000ffff00ffff8000`, `matches_expected_controller_colors=true`, SR+SL `expected_button_bytes=000030`, `input_report_delta=144`, UI observation hold complete, 491 `report_tx` events, `transport_close_complete`, and no `error`.
- user observation: user observed red body and blue buttons on the Switch UI. This confirms that explicit `controller_colors` was distinguishable from the Joy-Con L default color in the live UI under this environment.
- artifact: `build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors\joycon-left-custom-controller-colors.jsonl`, `build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors\l2-joycon-left-custom-colors-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-l-l2-custom-colors\joycon-left-custom-colors-key-store.json`
- cleanup: run reached `transport_close_complete` and `manual_joycon_profile_cleanup connection_state=closed`. It sent neutral after SR+SL before close. The adapter was released.
- notes: This run is L2's pass criterion for the profile regression run. The earlier default-color run remains a diagnostic on-wire confirmation, not the main L2 result.

### 2026-07-07: Joy-Con R R1 initial registration observed but failed on unsupported 0x22

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch at commit `f2b67ea`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con R profile default `8000` us
- command / test: `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r --log-file build\hardware\profile-regression-20260707\joycon-r\r1-joycon-right-profile-pairing-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user stated the Switch was prepared for R1. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con R HID advertising, Switch pairing, Device Info reply, observed order input window, SR+SL hold, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. Scope excluded reconnect, normal input reflection, dedicated Joy-Con R color SPI test, and broader firmware / adapter matrix claims.
- result: observed-fail, `1 failed in 24.45s`. Trace `joycon-right-profile-pairing.jsonl` recorded `bumble_device_initialized device_name=Joy-Con (R) class_of_device=0x002508`, HCI local name / EIR `Joy-Con (R)`, Device Info `device_info_data=04000202001bdcf99f7d0101` with `controller_type=0x02` and `profile_bluetooth_address_bytes=001bdcf99f7d`, order input window after last subcommand `0x48`, SR+SL `expected_button_bytes=300000`, `input_report_delta=143`, neutral complete, UI observation hold complete, 495 `report_tx` events, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The same trace also recorded repeated `unsupported_subcommand` for `subcommand_id=0x22`, payload `0100000000000000000000000000000000000000000000000000000000000000000000000000`, followed by `UnsupportedSubcommandError` / `error` events. The pytest assertion failed because `error` events were present.
- user observation: user observed that the Switch registered Joy-Con (R) with red body and blue buttons. This is recorded as UI observation, but R1 remains observed-fail until the `0x22` responder change is retested.
- artifact: `build\hardware\profile-regression-20260707\joycon-r\joycon-right-profile-pairing.jsonl`, `build\hardware\profile-regression-20260707\joycon-r\r1-joycon-right-profile-pairing-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-r\joycon-right-profile-key-store.json`
- cleanup: run reached `transport_close_complete` and `manual_joycon_profile_cleanup connection_state=closed`. It sent neutral after SR+SL before close. The adapter was released.
- notes: `0x22` is NFC/IR MCU state. The follow-up code change ACKs source-audited argument bytes `0x00`, `0x01`, and `0x02` with `0x80 0x22` and no data. It does not model NFC/IR MCU state. R1 hardware rerun after that change passed under the same Windows / CSR8510 A10 / Switch 2 firmware 22.1.0 condition.

### 2026-07-07: Joy-Con R R1 rerun passed after 0x22 ACK-compatible handling

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch at commit `a8fdf5c`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con R profile default `8000` us
- command / test: `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack --log-file build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack\r1-joycon-right-profile-pairing-after-0x22-ack-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: after the `0x22` fix was committed, user stated the Switch was waiting. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con R HID advertising, Switch pairing, Device Info reply, observed order input window, SR+SL hold, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. Scope excluded reconnect, normal input reflection, dedicated Joy-Con R color SPI test, and broader firmware / adapter matrix claims.
- result: pass, `1 passed in 24.45s`. Trace `joycon-right-profile-pairing.jsonl` recorded Device Info `device_info_data=04000202001bdcf99f7d0101` with `controller_type=0x02` and `profile_bluetooth_address_bytes=001bdcf99f7d`, two `0x22` output reports, two `subcommand_reply_tx` events for `subcommand_id=0x22`, SR+SL `expected_button_bytes=300000`, `input_report_delta=138`, neutral complete, UI observation hold complete, 458 `0x30` reports by the observation checkpoint, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The trace contains no `unsupported_subcommand` or `error` events.
- user observation: user observed red body and gray buttons during pairing. Initial R1 had a separate user observation of red body and blue buttons. Both are human UI observations, not an on-wire color assertion for this R1 scenario.
- artifact: `build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack\joycon-right-profile-pairing.jsonl`, `build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack\r1-joycon-right-profile-pairing-after-0x22-ack-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-r-after-0x22-ack\joycon-right-profile-key-store.json`
- cleanup: run reached `transport_close_complete` and `manual_joycon_profile_cleanup connection_state=closed`. It sent neutral after SR+SL before close. The adapter was released.
- notes: This rerun verifies the local ACK-compatible `0x22` handling under Windows / CSR8510 A10 / Switch 2 firmware 22.1.0. It does not verify NFC/IR MCU semantics, normal Joy-Con R input reflection, reconnect, or a dedicated Joy-Con R controller-color SPI scenario.

### 2026-07-07: Joy-Con R R2 ABXY button check pass after rerun

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch with R2 hardware test implementation in working tree
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`
- driver: WinUSB expected from previous Windows inventory. This run did not re-enumerate driver state
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.2.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default periodic `0x30`
- command / test: initial R2 pairing used `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r2 --log-file build\hardware\profile-regression-20260707\joycon-r-r2\r2-joycon-right-initial-pairing-pytest-debug.log --log-file-level=DEBUG -q -s`; first ABXY run used `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_button_check_abxy_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r2 --log-file build\hardware\profile-regression-20260707\joycon-r-r2\r2-joycon-right-button-check-abxy-pytest-debug.log --log-file-level=DEBUG -q -s`; rerun used `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_button_check_abxy_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r2-rerun2 --log-file build\hardware\profile-regression-20260707\joycon-r-r2-rerun2\r2-joycon-right-button-check-abxy-rerun2-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested R2 execution, prepared controller search / change grip order for initial pairing, then prepared the button operation check selection screen for ABXY validation. Scope included Bumble adapter open, Joy-Con R pairing for fresh key store, active reconnect, Button A screen entry, Y/X/B/A, neutral after each button, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release
- result: pass after rerun. Initial pairing passed, `1 passed in 24.37s`, and created `joycon-right-profile-key-store.json`. First ABXY run passed pytest, `1 passed in 7.80s`, but the user observed that the Switch did not enter the target screen, so that run is not a UI pass. Rerun passed pytest, `1 passed in 7.29s`; trace recorded active reconnect, A entry, Y `010000`, X `020000`, B `040000`, A `080000`, neutral after each button, and cleanup. User observed that the inputs were correct
- artifact: `build\hardware\profile-regression-20260707\joycon-r-r2\joycon-right-profile-pairing.jsonl`, `build\hardware\profile-regression-20260707\joycon-r-r2\r2-joycon-right-initial-pairing-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-r-r2\joycon-right-button-check-abxy.jsonl`, `build\hardware\profile-regression-20260707\joycon-r-r2\r2-joycon-right-button-check-abxy-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-r-r2-rerun2\joycon-right-button-check-abxy.jsonl`, `build\hardware\profile-regression-20260707\joycon-r-r2-rerun2\r2-joycon-right-button-check-abxy-rerun2-pytest-debug.log`
- cleanup: pairing and both ABXY runs reached `manual_joycon_profile_cleanup connection_state=closed`; ABXY runs sent neutral after each button before close. The adapter was released
- notes: The trace proves report bytes and cleanup. UI pass is based on the rerun user observation, not the first ABXY run

### 2026-07-07: Joy-Con R R3 right stick hold conditional pass

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch with R3 hardware test implementation in working tree
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`
- driver: WinUSB expected from previous Windows inventory. This run did not re-enumerate driver state
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.2.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default periodic `0x30`
- command / test: copied the R2 key store to `build\hardware\profile-regression-20260707\joycon-r-r3\joycon-right-profile-key-store.json`; then ran `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_stick_calibration_after_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r3 --log-file build\hardware\profile-regression-20260707\joycon-r-r3\r3-joycon-right-stick-calibration-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested moving to stick input validation and then requested R3 execution. Scope included Bumble adapter open, active reconnect from the Joy-Con R key store, HID channels, periodic report loop, right stick hold, right stick circle, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. Scope excluded pairing and left stick input
- result: conditional-pass, `1 passed in 10.38s`. Trace `joycon-right-stick-calibration.jsonl` recorded active reconnect, full handshake, `right_stick_hold_start`, `right_stick_hold_reports_sent` with `hold_report_count=120`, `right_stick_circle_complete` with `steps=32` and `step_seconds=0.15`, `right_stick_neutral_complete`, `manual_joycon_profile_cleanup connection_state=closed`, and no `error`. User observed that calibration fails as expected for a horizontal Joy-Con. This is treated as a device/UI constraint, not a protocol failure
- artifact: `build\hardware\profile-regression-20260707\joycon-r-r3\joycon-right-stick-calibration.jsonl`, `build\hardware\profile-regression-20260707\joycon-r-r3\r3-joycon-right-stick-calibration-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-r-r3\joycon-right-profile-key-store.json`
- cleanup: run executed `pad.close(neutral=True)`; trace recorded neutral after the stick sequence and `transport_close_complete`. The adapter was released
- notes: R3 does not prove that Switch's stick calibration UI can complete for a horizontal single Joy-Con. It proves active reconnect, right-stick report emission, hold up to the UI rejection point, neutral cleanup, and close cleanup under this environment

### 2026-07-07: Joy-Con R R4 custom controller colors pass

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch with R4 hardware test implementation in working tree
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`
- driver: WinUSB expected from previous Windows inventory. This run did not re-enumerate driver state
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.2.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con R profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_right_profile_reads_custom_controller_colors -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors --log-file build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors\r4-joycon-right-custom-colors-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user prepared controller search / change grip order and requested the expected colors before execution. Scope included Bumble adapter open, Joy-Con R HID advertising, Switch pairing, Device Info reply, SPI `0x6050` custom controller color read reply, observed order input window, SR+SL hold, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release. Scope excluded normal input reflection and broader firmware / adapter matrix claims
- result: pass, `1 passed in 24.43s`. Trace `joycon-right-custom-controller-colors.jsonl` recorded Device Info `device_info_data=04000202001bdcf99f7d0101`, SPI read `address=0x006050`, `controller_color_bytes=00ff008000ff00ffffffff00`, `matches_expected_controller_colors=true`, SR+SL `expected_button_bytes=300000`, UI observation hold complete, cleanup, and no `error`
- user observation: user observed body green and buttons purple on the Switch UI. This confirms that explicit Joy-Con R `controller_colors` was distinguishable from the Joy-Con R default and from the earlier R1 incidental color observations in the live UI under this environment
- artifact: `build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors\joycon-right-custom-controller-colors.jsonl`, `build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors\r4-joycon-right-custom-colors-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-r-r4-custom-colors\joycon-right-custom-colors-key-store.json`
- cleanup: run reached `transport_close_complete` and `manual_joycon_profile_cleanup connection_state=closed`. It sent neutral after SR+SL before close. The adapter was released
- notes: R4 is the dedicated Joy-Con R color scenario. It supersedes treating R1's registration colors as evidence for Joy-Con R color behavior

### 2026-07-07: Joy-Con L default color L2 diagnostic superseded by custom-color scenario

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/hardware-test-scenarios` branch at commit `e908385`
- adapter: `usb:0`
- dongle: CSR8510 A10 from no-open adapter discovery, USB VID:PID `0a12:0001`, alias `usb:0A12:0001`
- driver: WinUSB expected from previous Windows runs on this machine; not re-enumerated in this run
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: 0.2.0
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con L profile default `8000` us
- command / test: `uv run pytest 'tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_reads_default_controller_colors[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\profile-regression-20260707\joycon-l-l2-colors --log-file build\hardware\profile-regression-20260707\joycon-l-l2-colors\l2-joycon-left-default-colors-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user stated the Switch was waiting on controller search / change grip order for L2. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con L HID advertising, Switch pairing, Device Info reply, SPI `0x6050` controller color read reply, observed order input window, SR+SL hold, neutral, trace save, debug log save, `close(neutral=True)` cleanup, and adapter release.
- result: superseded-pass, `1 passed in 24.43s`. Trace `joycon-left-default-controller-colors.jsonl` recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `classic_pairing`, `key_store_update previous_saved=false status=succeeded`, Device Info `device_info_data=04000102001bdcf99f7d0101`, SPI read `address=0x006050`, `controller_color_bytes=00b2ff32323200b2ff00b2ff`, `matches_expected_controller_colors=true`, SR+SL `expected_button_bytes=000030`, `input_report_delta=149`, UI observation hold complete, 496 `report_tx` events, `transport_close_complete`, and no `error`.
- user observation: user observed the same color as L1 and questioned whether this was actually testing color change. That observation is correct for the regression goal: the run proves the default SPI bytes but does not distinguish UI behavior from L1. The L2 main scenario is therefore changed to a custom `controller_colors` probe.
- artifact: `build\hardware\profile-regression-20260707\joycon-l-l2-colors\joycon-left-default-controller-colors.jsonl`, `build\hardware\profile-regression-20260707\joycon-l-l2-colors\l2-joycon-left-default-colors-pytest-debug.log`, `build\hardware\profile-regression-20260707\joycon-l-l2-colors\joycon-left-colors-key-store.json`
- cleanup: run reached `transport_close_complete` and `manual_joycon_profile_cleanup connection_state=closed`. It sent neutral after SR+SL before close. The adapter was released.
- notes: This entry is retained as a default-color diagnostic. It is not the L2 pass criterion for the current profile regression run.

### 2026-07-06: Joy-Con L default controller colors SPI reply

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` branch at `196ac6f` plus working tree hardware test addition.
- adapter: `usb:0`
- dongle: CSR8510 A10. HCI debug log read local BD_ADDR `00:1B:DC:F9:9F:7D/P`.
- driver: WinUSB. Previous runs on this machine recorded libwdi driver version `6.1.7600.16385`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: commit `196ac6f` plus uncommitted `tests/hardware/test_joycon_profile.py` probe addition.
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con L profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_reads_default_controller_colors[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-default-colors-20260706 --log-file build\hardware\joycon-left-default-colors-20260706\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-joycon-default-colors -q -s`
- approval: user approved hardware verification. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con L HID advertising, Switch pairing, HID control / interrupt L2CAP, Device Info reply, SPI `0x6050` controller color read reply, periodic `0x30`, SR+SL hold, neutral cleanup, disconnect request, transport close, and adapter release.
- result: pytest passed, `1 passed in 24.39s`. Trace recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `sdp_record_registered service_record_count=1 hid_descriptor_size=203`, `local_bluetooth_address_configured address=001bdcf99f7d`, `device_info_bluetooth_address_configured address=001bdcf99f7d`, Device Info reply `device_info_data=04000102001bdcf99f7d0101`, SPI read `address=0x006050`, `size=13`, `controller_color_bytes=00b2ff32323200b2ff00b2ff`, `matches_expected_controller_colors=true`, SR+SL `expected_button_bytes=000030`, `sr_sl_order_buttons_hold_reports_sent input_report_delta=145`, and `ui_observation_hold_complete report_0x21_count=15 report_0x30_count=481`.
- user observation: user reported that the Switch UI body looked blue / light blue and the buttons looked black. The expected buttons byte is `0x323232`, so this is recorded as a human-visible dark gray / black observation, not as proof that the byte was pure black.
- artifact: `build\hardware\joycon-left-default-colors-20260706\joycon-left-default-controller-colors.jsonl`, `build\hardware\joycon-left-default-colors-20260706\pytest-debug.log`, `build\hardware\joycon-left-default-colors-20260706\joycon-left-colors-key-store.json`
- cleanup: trace recorded `disconnect_request status=requested channels=["interrupt","control"]`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The test released the adapter.
- notes: This run verifies the on-wire Joy-Con L default ControllerColors SPI block and records one user-visible Switch UI color observation. It does not verify Joy-Con R default colors, Joy-Con reconnect, normal Joy-Con input reflection, or color UI behavior across firmware / adapter combinations.

### 2026-07-06: Joy-Con L SDP policy retest registered as Joy-Con

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` branch at `867a785`
- adapter: `usb:0`
- dongle: CSR8510 A10. HCI debug log read local BD_ADDR `00:1B:DC:F9:9F:7D/P`.
- driver: WinUSB. Previous runs on this machine recorded libwdi driver version `6.1.7600.16385`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: commit `867a785`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: Joy-Con L profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-sdp-policy-20260706 --log-file build\hardware\joycon-left-sdp-policy-20260706\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-joycon-sdp-policy -q -s`
- approval: user approved after the scope was listed. Scope used adapter `usb:0`, USB Bluetooth dongle open, Joy-Con L HID advertising, Switch pairing, HID control / interrupt L2CAP, Switch-facing output report / subcommand handling, periodic `0x30`, SR+SL hold, neutral cleanup, and adapter release.
- result: pytest passed, `1 passed in 24.40s`. Trace recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `sdp_record_registered service_record_count=1 hid_descriptor_size=203`, `local_bluetooth_address_configured address=001bdcf99f7d`, `device_info_bluetooth_address_configured address=001bdcf99f7d`, Device Info reply `device_info_data=04000102001bdcf99f7d0101`, subcommands `0x02`, `0x08`, repeated `0x10`, `0x03`, `0x04`, `0x40`, `0x30`, `0x48`, then SR+SL start `expected_button_bytes=000030`, `sr_sl_order_buttons_hold_reports_sent input_report_delta=147 input_report_delta_at_least_minimum=true report_0x30_count=150`, and `ui_observation_hold_complete report_0x21_count=15 report_0x30_count=484`.
- user observation: Joy-Con として登録された。これはユーザ目視の観測であり、pytest は Switch UI を自動判定していない。
- artifact: `build\hardware\joycon-left-sdp-policy-20260706\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-sdp-policy-20260706\pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested channels=["interrupt","control"]`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The test released the adapter.
- notes: この retest は Joy-Con profile の SDP policy を joycontrol 由来値へ変更した後に実行した。debug log は HCI local name、Class of Device、Device Info reply、HID traffic を記録するが、SDP XML attributes は出力しない。そのため、この entry は raw on-air SDP attribute dump ではなく、実装経路とユーザ目視の登録成功を根拠として扱う。Class of Device は `0x002508`、HID descriptor は 203 bytes のまま維持した。

### 2026-07-06: Joy-Con L Device Info address became nonzero but Pro toast remained

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` branch at `b81cce0` plus the hardware command below.
- adapter: `usb:0`
- dongle: CSR8510 A10. HCI debug log read local BD_ADDR `00:1B:DC:F9:9F:7D/P`.
- driver: WinUSB. Previous runs on this machine recorded libwdi driver version `6.1.7600.16385`.
- Python: 3.13.5
- Bumble: 0.0.230
- Switch model: Switch 2
- Switch firmware: 22.1.0
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-device-info-address-20260706-034000 --log-file build\hardware\joycon-left-device-info-address-20260706-034000\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-joycon-address-late -q -s`
- approval: user approved the hardware test. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection, HID control / interrupt L2CAP, Switch-facing output report / subcommand handling, periodic input report loop, SR+SL registration input after the observed Joy-Con initialization sequence, neutral cleanup, close cleanup, and adapter release.
- result: pytest failed with `TimeoutError` while waiting for the hardware test's `device_info_reply` event. Trace still recorded `local_bluetooth_address_configured address=001bdcf99f7d`, `device_info_bluetooth_address_configured address=001bdcf99f7d`, `connection_request`, `host_connection`, `classic_pairing`, `key_store_update status=succeeded`, `connected`, `subcommand_rx 0x02`, and `subcommand_reply_tx 0x02`. Debug log recorded the actual `0x02` Device Info reply payload `04 00 01 02 00 1b dc f9 9f 7d 01 01`.
- user observation: Pro Controller toast was still shown, and Joy-Con user-facing registration did not complete. This is evidence that nonzero Device Info address alone is insufficient for the current Joy-Con registration problem.
- artifact: `build\hardware\joycon-left-device-info-address-20260706-034000\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-device-info-address-20260706-034000\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The test released the adapter.
- notes: The pytest timeout was a measurement bug, not a missing Device Info reply. `SwitchGamepad` replaced `OutputReportDispatcher.subcommand_responder` when refreshing the address, which dropped the `RecordingDeviceInfoResponder` wrapper used by the hardware test. The follow-up code path updates the existing responder address in place. Remaining candidates are Joy-Con-specific SDP / descriptor-adjacent values, Switch-side stale registration keyed by the physical dongle address, or another identity source not yet audited.

### 2026-07-06: Joy-Con L Device Info address first retest still returned zero address

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` branch at `21721d5` plus working tree address guard from unit_035.
- adapter: `usb:0`
- dongle: CSR8510 A10. HCI debug log read local BD_ADDR `00:1B:DC:F9:9F:7D/P`.
- driver: WinUSB. Previous runs on this machine recorded libwdi driver version `6.1.7600.16385`.
- Python: 3.13.5
- Bumble: 0.0.230
- Switch model: Switch 2
- Switch firmware: 22.1.0
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-device-info-address-20260706-031500 --log-file build\hardware\joycon-left-device-info-address-20260706-031500\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-joycon-address -q -s`
- approval: user said to run the hardware test. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection, HID control / interrupt L2CAP, Switch-facing output report / subcommand handling, periodic input report loop, SR+SL registration input after the observed Joy-Con initialization sequence, neutral cleanup, close cleanup, and adapter release.
- result: pytest failed with `AssertionError` at the Device Info address guard. Trace recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508` without `local_bluetooth_address`, then `device_info_reply device_info_data=040001020000000000000101 profile_bluetooth_address_bytes=000000000000`. Debug log still recorded on-air local BD_ADDR `00:1B:DC:F9:9F:7D/P`, local name `Joy-Con (L)`, and class of device `[002508]`.
- user observation: the registration toast still identified the device as Pro Controller. Because Device Info address was still zero, this run is not evidence that the local-address fix failed to change toast identity.
- artifact: `build\hardware\joycon-left-device-info-address-20260706-031500\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-device-info-address-20260706-031500\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The test released the adapter.
- notes: Root cause is address injection timing. Bumble `Device.public_address` is still `ANY` before `power_on()` and becomes the real controller address during connection preparation. The follow-up fix refreshes the transport local address after Bumble power-on and reconfigures Device Info after pairing advertising or connection completion.

### 2026-07-06: Joy-Con L SR+SL after observed init completed pairing but kept Pro toast

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` branch at `f249261` plus the hardware test command below.
- adapter: `usb:0`
- dongle: CSR8510 A10. HCI debug log read local BD_ADDR `00:1B:DC:F9:9F:7D/P`.
- driver: WinUSB. Previous runs on this machine recorded libwdi driver version `6.1.7600.16385`.
- Python: 3.13.5
- Bumble: 0.0.230
- Switch model: Switch 2
- Switch firmware: 22.1.0
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-srsl-observed-window-20260706-024345 --log-file build\hardware\joycon-left-srsl-observed-window-20260706-024345\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-srsl-observed-window -q -s`
- approval: user explicitly approved the Joy-Con L hardware retest. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection, HID control / interrupt L2CAP, Switch-facing output report / subcommand handling, periodic input report loop, SR+SL registration input after the observed Joy-Con initialization sequence, neutral cleanup, close cleanup, and adapter release. Scope excluded Joy-Con R, reconnect, repeated matrix runs, and broader firmware / adapter compatibility claims.
- result: pytest failed with `TimeoutError: report 0x30 count stayed at 94, expected 123`, so the test threshold was too rigid for the observed report loop. Trace still recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `sdp_record_registered hid_descriptor_size=203`, `key_store_update status=succeeded`, `connected`, `device_info_reply device_info_data=040001020000000000000101`, `order_input_window_observed`, and SR+SL start with `expected_button_bytes=000030`. Debug log recorded local BD_ADDR `00:1B:DC:F9:9F:7D/P`, local name `Joy-Con (L)`, and class of device `[002508]`.
- user observation: pairing itself completed. The completion toast still identified the device as Pro Controller, while the controller order screen treated it as Joy-Con L. This splits the issue from SR+SL timing: Joy-Con input can be sent after the observed init sequence, but registration identity is still inconsistent.
- artifact: `build\hardware\joycon-left-srsl-observed-window-20260706-024345\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-srsl-observed-window-20260706-024345\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_joycon_profile_cleanup connection_state=closed`. The test released the adapter.
- notes: The run used local Bluetooth address `00:1B:DC:F9:9F:7D` on-air but still returned zero bytes in the `0x02` Device Info address field. Fixing production Device Info address wiring is required before the next hardware run. If the toast remains Pro Controller after the address fix, the remaining candidates are Switch-side stale registration keyed by the physical dongle address and Joy-Con-specific SDP / descriptor-adjacent values.

### 2026-07-06: Joy-Con L post-handshake SR+SL attempt timed out before SR+SL hold

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` at `8964046`
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0A12:0001`, bus 6, device address 14, port path `9,1` from previous `swbt-probe adapters --json` observation
- driver: not re-recorded in this run. Previous Windows observations for this dongle recorded WinUSB / libwdi.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`, commit `8964046`
- Switch model: not re-recorded in this run
- Switch firmware: not re-recorded in this run
- report period: profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-srsl-post-handshake-20260706-023830 --log-file build\hardware\joycon-left-srsl-post-handshake-20260706-023830\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-srsl-post-handshake -q -s`
- approval: user explicitly approved the Joy-Con L hardware test. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection attempt, HID control / interrupt channel open, Switch-facing output report / subcommand handling, neutral report loop, attempted readiness wait before SR+SL registration input, neutral cleanup, close cleanup, and adapter release. Scope excluded Joy-Con R, reconnect, repeated matrix runs, and broader firmware / adapter compatibility claims.
- result: pytest failed with `TimeoutError` while waiting for `_wait_for_full_handshake`; user reported that the visible situation was unchanged. Trace recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `sdp_record_registered hid_descriptor_size=203`, `key_store_update status=succeeded`, `connected`, `device_info_reply device_info_data=040001020000000000000101`, replies for `0x02`, `0x08`, repeated `0x10`, `0x03`, `0x04`, `0x40`, `0x30`, `0x48`, and another `0x30`, then periodic neutral `0x30` until cleanup. It did not record SR+SL hold checkpoints because the readiness wait required Pro-profile `0x21` and timed out before `_send_order_buttons`.
- artifact: `build\hardware\joycon-left-srsl-post-handshake-20260706-023830\joycon-left-profile-pairing.jsonl`
- artifact: `build\hardware\joycon-left-srsl-post-handshake-20260706-023830\pytest-debug.log`
- cleanup: final run called `close(neutral=True)`, recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and Classic scan disable in the Bumble debug log.
- notes: This run does not test SR+SL order registration. It exposed a test readiness bug: Joy-Con L did not emit `0x21` in this observed sequence, so `0x21` must not be required before SR+SL hold. The next run should wait for the Joy-Con observed initialization sequence `0x02` / `0x08` / `0x10` / `0x03` / `0x04` / `0x40` / `0x30` / `0x48` with replies, then hold SR+SL across periodic `0x30`.

### 2026-07-06: Joy-Con L immediate SR+SL still did not complete order registration

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` at `c225d68`
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0A12:0001`, bus 6, device address 14, port path `9,1` from previous `swbt-probe adapters --json` observation
- driver: not re-recorded in this run. Previous Windows observations for this dongle recorded WinUSB / libwdi.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`, commit `c225d68`
- Switch model: not re-recorded in this run
- Switch firmware: not re-recorded in this run
- report period: profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-srsl-immediate-20260706-022907 --log-file build\hardware\joycon-left-srsl-immediate-20260706-022907\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-srsl-immediate -q -s`
- approval: user explicitly approved the Joy-Con L hardware test. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection attempt, HID control / interrupt channel open, Switch-facing output report / subcommand handling, neutral report loop, immediate SR+SL registration input attempt, neutral cleanup, close cleanup, and adapter release. Scope excluded Joy-Con R, reconnect, repeated matrix runs, and broader firmware / adapter compatibility claims.
- result: pytest result was `1 passed in 19.31s`, but user reported again that pairing / controller order registration did not complete. Trace recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `sdp_record_registered hid_descriptor_size=203`, `key_store_update status=succeeded`, `connected`, `device_info_reply device_info_data=040001020000000000000101`, `subcommand_session_state imu_mode=0x02`, `sr_sl_order_buttons_start report_0x30_count_before=1`, `sr_sl_order_buttons_tap_complete input_report_delta=3 input_report_delta_at_least_2=true report_0x30_count=4`, `ui_observation_hold_complete report_0x21_count=15 report_0x30_count=319`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`; it recorded no `error` event. This proves the immediate SR+SL `0x30` reports were sent, but not that the Switch UI was ready to accept them. The SR+SL tap occurred while the initial subcommand sequence was still in progress; by the 10 second UI observation hold the device was back to neutral periodic `0x30`.
- artifact: `build\hardware\joycon-left-srsl-immediate-20260706-022907\joycon-left-profile-pairing.jsonl`
- artifact: `build\hardware\joycon-left-srsl-immediate-20260706-022907\pytest-debug.log`
- cleanup: final run called `close(neutral=True)`, recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and Classic scan disable in the Bumble debug log.
- notes: This run narrows the failure. Fact: SR+SL bytes `000030` can be sent as `0x30`; fact: sending them during early subcommand initialization did not complete the user-visible registration. Next test should wait for the full observed handshake before holding SR+SL across periodic input reports. If that still fails, the remaining likely hypothesis moves to profile identity mismatch: Pro-compatible `class_of_device=0x002508`, 203-byte Pro HID descriptor, and SDP fixed values from unit_033. Changing those values requires source-audit before implementation.

### 2026-07-06: Joy-Con L SR+SL attempt did not complete order registration

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` at `c07fc00`
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0A12:0001`, bus 6, device address 14, port path `9,1` from previous `swbt-probe adapters --json` observation
- driver: not re-recorded in this run. Previous Windows observations for this dongle recorded WinUSB / libwdi.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`, commit `c07fc00`
- Switch model: not re-recorded in this run
- Switch firmware: not re-recorded in this run
- report period: profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-srsl-20260706-022445 --log-file build\hardware\joycon-left-srsl-20260706-022445\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp-hardware-srsl -q -s`
- approval: user explicitly approved the Joy-Con L hardware test. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection attempt, HID control / interrupt channel open, Switch-facing output report / subcommand handling, neutral report loop, SR+SL registration input attempt, neutral cleanup, close cleanup, and adapter release. Scope excluded Joy-Con R, reconnect, repeated matrix runs, and broader firmware / adapter compatibility claims.
- result: pytest result was `1 passed in 19.18s`, but user reported that pairing / controller order registration did not complete. Trace recorded `bumble_device_initialized device_name=Joy-Con (L) class_of_device=0x002508`, `key_store_update status=succeeded`, `connected`, `device_info_reply device_info_data=040001020000000000000101`, `expected_button_bytes=000030`, `subcommand_session_state imu_mode=0x02`, `ui_observation_hold_complete`, `disconnect_request status=requested`, and `transport_close_complete`; it recorded no `error` event. Trace also showed `report_0x30_count=2` at `device_info_reply_observed`, `sr_sl_order_buttons_hold_complete`, and `sr_sl_order_buttons_neutral_complete`, so the SR+SL state did not produce an independent `0x30` input report during the hold. This invalidates the test as evidence for Joy-Con order registration input. It remains evidence for Bluetooth link key creation, connection, subcommand handling, and clean close under this condition.
- artifact: `build\hardware\joycon-left-srsl-20260706-022445\joycon-left-profile-pairing.jsonl`
- artifact: `build\hardware\joycon-left-srsl-20260706-022445\pytest-debug.log`
- cleanup: final run called `close(neutral=True)`, recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and Classic scan disable in the Bumble debug log.
- notes: The failed registration has two separate explanations that must not be merged. Fact: the test did not send a separate `0x30` SR+SL input report during the SR+SL hold, because periodic input was held off by subcommand replies. Inference: the remaining Pro-compatible Class of Device / SDP / HID descriptor values may still affect Switch UI identity even after immediate SR+SL `0x30` is fixed. The next run should first use immediate `tap(Button.SR, Button.SL)` so that SR+SL press/release `0x30` reports are observable before changing Bluetooth / SDP identity.

### 2026-07-06: Joy-Con L communication profile and SR+SL registration stop

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `docs/joycon-profile-specs` at `f8af996` plus uncommitted Joy-Con hardware test and IMU mode fix
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0A12:0001`, bus 6, device address 14, port path `9,1` from previous `swbt-probe adapters --json` observation
- driver: not re-recorded in this run. Previous Windows observations for this dongle recorded WinUSB / libwdi.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`, commit `f8af996` plus uncommitted Joy-Con hardware test and IMU mode fix
- Switch model: not re-recorded in this run
- Switch firmware: not re-recorded in this run
- report period: profile default `8000` us
- command / test: `uv run pytest tests\hardware\test_joycon_profile.py::test_switch_joycon_profile_pairing_records_device_info[left] -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\joycon-left-20260706-020703 --log-file build\hardware\joycon-left-20260706-020703\pytest-debug.log --log-file-level=DEBUG --basetemp build\pytest-tmp -q -s`
- approval: user explicitly approved a Joy-Con L minimal hardware run. Scope used adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, Joy-Con L HID advertising, Switch pairing / connection attempt, HID control / interrupt channel open, Switch-facing output report / subcommand handling, neutral `0x30` report loop, 10 second UI observation hold, close cleanup, and adapter release. Scope excluded non-neutral input, Joy-Con R, reconnect, repeated matrix runs, and broader firmware / adapter compatibility claims.
- result: final pytest result was `1 passed in 18.14s` after accepting Joy-Con-only `0x40` Enable IMU mode `0x02`. Trace recorded `bumble_device_initialized device_name=Joy-Con (L)`, `key_store_update status=succeeded`, `connected`, `device_info_reply device_info_data=040001020000000000000101 controller_type=0x01 tail_bytes=0101`, `subcommand_session_state imu_mode=0x02 imu_enabled=true`, `subcommand_session_state vibration_enabled=true`, `ui_observation_hold_complete`, `disconnect_request status=requested`, and `transport_close_complete`; it recorded no `error` event. The first run failed due to the test wrapper missing `session_state`; the second run exposed the `0x40` payload byte `0x02` and failed with `ProtocolError` before the fix. User-visible observation: the device was registered as Pro Controller, then the controller order screen stopped waiting for Joy-Con L SR+SL input. This is not a Joy-Con registration success.
- artifact: `build\hardware\joycon-left-20260706-020038\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-20260706-020038\pytest-debug.log`
- artifact: `build\hardware\joycon-left-20260706-020308\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-20260706-020308\pytest-debug.log`
- artifact: `build\hardware\joycon-left-20260706-020703\joycon-left-profile-pairing.jsonl`, `build\hardware\joycon-left-20260706-020703\pytest-debug.log`
- cleanup: final run called `close(neutral=True)`, recorded `disconnect_request status=requested`, `transport_close_complete`, and final Classic scan disable in the Bumble debug log.
- notes: The current Joy-Con profile still uses Pro-compatible descriptor-adjacent Bluetooth / SDP values from unit_033, including Class of Device and several HID SDP fields. That is a plausible cause of the Pro Controller registration, but it is an inference, not a controlled A/B result. Joy-Con-specific pairing button / SR+SL registration completion steps are not modeled by this run. Joy-Con R was not run, and Joy-Con non-neutral input reflection was not tested.

### 2026-07-05: unit_027 adapter discovery no-open and open-only smoke

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-027-adapter-discovery` at `54a5ccd`
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0A12:0001`, bus 6, device address 14, port path `9,1`
- driver: not re-recorded in this run. Previous Windows observations for this dongle recorded WinUSB / libwdi.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`, commit `54a5ccd`
- Switch model: not used
- Switch firmware: not used
- report period: not used
- command / test:
  - `uv run swbt-probe adapters --json`
  - `uv run pytest tests\hardware\test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_027\20260705-open-only -q -s`
- approval: user approved no-open discovery and open-only smoke for adapter `usb:0`. Scope included USB descriptor listing and Bumble adapter open / close. Scope excluded HID advertising, Switch pairing, report loop, and input sending.
- result: pass. no-open discovery returned one HCI candidate with `name="usb:0"`, `aliases=["usb:0A12:0001"]`, `manufacturer=null`, `product="CSR8510 A10"`, `serial_number=null`, and `opens_adapter=false`. open-only smoke reported `1 passed in 0.30s`; trace recorded `transport_open_start`, Bumble Device init, SDP record registration, HID Device init, `transport_open_complete`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace did not record `advertising_start` or `host_connection`.
- artifact: `.pytest_cache\hardware\unit_027\20260705-open-only\resource-open-only.jsonl`
- cleanup: `pad.close(neutral=True)` ran in `finally`; trace recorded `transport_close_complete`. No non-neutral input was sent. No advertising or host connection was started.
- notes: Initial no-open discovery before commit `54a5ccd` exposed a descriptor `None` normalization bug that emitted the string `"None"` and alias `usb:0A12:0001/None`. Commit `54a5ccd` fixed this with a regression test before the recorded pass.

### 2026-07-05: Unit 028 production default device-info tail 0302 controller color SPI reply on Windows

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree with `DEVICE_INFO_DATA=040003020000000000000302`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30`, subcommand reply `0x21`, and close-time neutral `0x30`. No non-neutral input was sent.
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-default-tail-0302 --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-default-tail-0302\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved the repeated hardware verification in the existing unit_028 scope. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback, HID advertising, Switch pairing, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, 30 second post-SPI observation hold, trace save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: hardware-pass for production default device-info tail `03 02` and tracked sentinel 12-byte controller color SPI reply. Pytest result was `1 passed in 33.45s`. Trace recorded `device_info_data=040003020000000000000302`, `address=0x006050`, `size=13`, `controller_color_bytes=ff00000000ffff00ffff8000`, `matches_expected_controller_colors=true`, `manual_controller_color_checkpoint hold_seconds=30.0 operation=ui_observation_hold_complete`, and cleanup. User reported that left grip stayed magenta and right grip stayed orange.
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-default-tail-0302/controller-colors-sentinel.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-default-tail-0302/pytest-debug.log`
- cleanup: trace recorded `transport_close_complete` and `manual_controller_color_cleanup connection_state=closed`.
- notes: This run proves the production path now uses the same `03 02` device-info tail that made Pro Controller left/right grip colors visible in the characterization runs. The UI result is a human observation for Windows / Switch 2 / firmware 22.1.0, not an automated assertion or cross-firmware guarantee.

### 2026-07-05: Unit 028 device-info tail characterization for grip colors on Windows

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree with tracked hardware characterization tests in progress
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Each run used a neutral periodic report loop and close-time neutral. No non-neutral input was sent.
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_device_info_address -m hardware --swbt-bumble-adapter usb:0 --swbt-device-info-address 00:1B:DC:F9:9F:7D --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-address --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-address\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_zero_tail_byte -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-zero-tail --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-zero-tail\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_device_info_tail_0x03_0x02 -m hardware --swbt-bumble-adapter usb:0 --swbt-device-info-address 00:1B:DC:F9:9F:7D --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302 --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile_with_device_info_tail_0x03_0x02 -m hardware --swbt-bumble-adapter usb:0 --swbt-device-info-address 00:00:00:00:00:00 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302-zero-address --log-file .pytest_cache\hardware\unit_028\tracked-sentinel-device-info-tail-0302-zero-address\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested repeated hardware experiments for grip color characterization and approved the same adapter / Switch-facing scope. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback, HID advertising, Switch pairing, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, 30 second post-SPI observation hold, trace save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: all five characterization runs passed. Old `device_info_data=040003020000000000000101` produced body/grip red and buttons blue. Old tail `01 01` with local BD_ADDR `001bdcf99f7d` still produced body/grip red and buttons blue. Old tail `01 01` with SPI `0x605C=00` still produced body/grip red and buttons blue. Tail `03 02` with local BD_ADDR `001bdcf99f7d` produced left magenta and right orange. Tail `03 02` with zero BD_ADDR `000000000000` produced the same left magenta and right orange observation.
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-device-info/controller-colors-sentinel.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-device-info-address/controller-colors-sentinel-device-info-address.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-zero-tail/controller-colors-sentinel-zero-tail.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-device-info-tail-0302/controller-colors-sentinel-device-info-tail-0302.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel-device-info-tail-0302-zero-address/controller-colors-sentinel-device-info-tail-0302.jsonl`
- cleanup: each trace recorded close cleanup and `manual_controller_color_cleanup connection_state=closed`.
- notes: These runs rule out BD_ADDR alone and the byte after the color block as the observed cause. The remaining supported change is the `0x02` device-info tail `03 02`. The meaning of these bytes is not named beyond the observed profile-byte behavior.

### 2026-07-05: Unit 028 tracked sentinel controller color SPI reply on Windows

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree with tracked hardware test changes in progress
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30`, subcommand reply `0x21`, and close-time neutral `0x30`. No non-neutral input was sent.
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_sentinel_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-sentinel --log-file .pytest_cache\hardware\unit_028\tracked-sentinel\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested continuing the hardware verification in conversation. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback, HID advertising, Switch pairing, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, 30 second post-SPI observation hold, trace save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: hardware-pass for tracked sentinel 12-byte controller color SPI reply and user-observed body/buttons UI reflection. Pytest result was `1 passed in 33.43s`. Trace recorded `reconnect_key_store_unavailable`, `active_reconnect_result status=no_bond`, `connect_pairing_fallback route=pairing`, `classic_pairing`, `key_store_update status=succeeded`, HID control / interrupt `l2cap_channel_open`, `connected`, `address=0x006050`, `size=13`, `controller_color_bytes=ff00000000ffff00ffff8000`, `matches_expected_controller_colors=true`, `manual_controller_color_checkpoint operation=controller_color_spi_reply_observed`, `manual_controller_color_checkpoint hold_seconds=30.0 operation=ui_observation_hold_complete`, and cleanup. User reported that body was red, buttons were blue, and grip also looked red.
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel/controller-colors-sentinel.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-sentinel/pytest-debug.log`
- cleanup: trace recorded `transport_close_complete` and `manual_controller_color_cleanup connection_state=closed`.
- notes: This run separates body/buttons UI reflection from the earlier green-body ambiguity. Body and buttons matched the sentinel colors. Grip did not show the independent `left_grip=0xFF00FF` / `right_grip=0xFF8000` colors and instead looked like the red body.

### 2026-07-05: Unit 028 tracked custom controller color SPI reply on Windows historical run

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree with tracked hardware test changes in progress
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30`, subcommand reply `0x21`, and close-time neutral `0x30`. No non-neutral input was sent.
- command / test: `uv run pytest tests\hardware\test_controller_colors.py::test_switch_reads_custom_controller_color_profile -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_028\tracked-custom --log-file .pytest_cache\hardware\unit_028\tracked-custom\pytest-debug.log --log-file-level=DEBUG -q -s`。この test 名は当時の履歴であり、現行 tracked test は sentinel profile の `test_switch_reads_sentinel_controller_color_profile` とする。
- approval: user requested a tracked hardware test and hardware verification in conversation. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback, HID advertising, Switch pairing, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, 30 second post-SPI observation hold, trace save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: hardware-pass for tracked custom 12-byte controller color SPI reply. Pytest result was `1 passed in 33.36s`. Trace recorded `reconnect_key_store_unavailable`, `active_reconnect_result status=no_bond`, `connect_pairing_fallback route=pairing`, `classic_pairing`, `key_store_update status=succeeded`, HID control / interrupt `l2cap_channel_open`, `connected`, `address=0x006050`, `size=13`, `controller_color_bytes=00c853ffeb3b2962ffd50000`, `matches_expected_controller_colors=true`, `manual_controller_color_checkpoint operation=controller_color_spi_reply_observed`, `manual_controller_color_checkpoint hold_seconds=30.0 operation=ui_observation_hold_complete`, and cleanup. Switch UI color reflection was not auto-detected by the test. User reported that the Switch UI still looked solid green.
- artifact: `.pytest_cache/hardware/unit_028/tracked-custom/controller-colors-custom.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/tracked-custom/pytest-debug.log`
- cleanup: trace recorded `transport_close_complete` and `manual_controller_color_cleanup connection_state=closed`.
- notes: This tracked test replaces the earlier ignored probe-script workflow for proving the on-wire SPI color bytes. It proves the Switch requested a range covering `0x6050` and swbt-python replied with the diagnostic custom body/buttons/left_grip/right_grip bytes. Human-visible UI color reflection remains a manual observation, not a pytest assertion. The observed UI result is not stable enough to treat body/buttons color display as a release guarantee.

### 2026-07-05: Unit 028 controller color SPI reply on Windows

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree, staged unit_028 diff with a git-ignored probe script under `.pytest_cache/hardware/unit_028_controller_color_probe.py`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30`, subcommand reply `0x21`, and close-time neutral `0x30`. No non-neutral input was sent.
- command / test: `uv run python .pytest_cache\hardware\unit_028_controller_color_probe.py --adapter usb:0 --artifact-dir .pytest_cache\hardware\unit_028 --body 0x00c853 --buttons 0xffeb3b --timeout 60 --spi-timeout 25 --hold-seconds 15 --switch-start-condition "Switch 2 22.1.0 controller search / change grip order screen; UI color observation by user"`
- approval: user approved via the command escalation prompt. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback, HID advertising, Switch pairing, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, trace save, key store save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: hardware-pass for body/buttons controller color SPI reply and user-observed UI reflection. Trace recorded `key_store_exists=false`, `active_reconnect_result status=no_bond`, `connect_pairing_fallback route=pairing`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, HID control / interrupt `l2cap_channel_open`, `connected`, `incoming_connection route=incoming`, and full observed subcommand sequence. The probe recorded SPI read replies including `address=0x006050`, `size=13`, `controller_color_bytes=00c853ffeb3b`, `matches_expected_controller_colors=true`, and another overlapping read from `address=0x00603d`, `size=25` with the same matching controller color bytes. `manual_controller_color_probe_checkpoint operation=controller_color_spi_reply_observed` and `ui_observation_hold_complete` were recorded. Switch UI color reflection was not auto-detected by the probe; user reported seeing a green body and yellow buttons controller in the Switch UI. This run did not verify grip color UI reflection for `0x6056`-`0x605B`.
- artifact: `.pytest_cache/hardware/unit_028/controller-colors-custom.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/controller-colors-key-store.json`
- cleanup: trace recorded interrupt/control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_controller_color_probe_cleanup connection_state=closed`.
- notes: This run proves that, under this Windows / Switch 2 / firmware 22.1.0 condition, Switch reads the body/buttons controller color SPI range and swbt-python replies with the configured body/buttons bytes. The visible UI color result is a user observation, not an automated assertion. Grip color was checked in the separate run below.

### 2026-07-05: Unit 028 controller grip color SPI reply on Windows

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree, staged unit_028 diff with a one-off probe script under `tmp/hardware/unit_028_controller_color_probe.py`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30`, subcommand reply `0x21`, and close-time neutral `0x30`. No non-neutral input was sent.
- command / test: `uv run python tmp\hardware\unit_028_controller_color_probe.py --adapter usb:0 --artifact-dir .pytest_cache\hardware\unit_028 --body 0x00c853 --buttons 0xffeb3b --left-grip 0x2962ff --right-grip 0xd50000 --timeout 60 --spi-timeout 25 --hold-seconds 15 --switch-start-condition "Switch 2 22.1.0 controller search / change grip order screen; unit_028 grip color observation by user"`
- approval: user explicitly approved this hardware experiment in conversation. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback if needed, HID advertising, Switch pairing or reconnect, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, trace save, key store save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: hardware-pass for 12-byte body/buttons/grip controller color SPI reply. Trace recorded SPI read replies including `address=0x006050`, `size=13`, `controller_color_bytes=00c853ffeb3b2962ffd50000`, `matches_expected_controller_colors=true`. The same trace recorded `manual_controller_color_probe_checkpoint operation=controller_color_spi_reply_observed`, `ui_observation_hold_complete`, and cleanup. Switch UI color reflection was not auto-detected by the probe. User reported that left/right grip did not visibly change to blue/red and still looked green.
- artifact: `.pytest_cache/hardware/unit_028/controller-colors-and-grips-custom.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/controller-colors-key-store.json`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_controller_color_probe_cleanup connection_state=closed`.
- notes: This 15 second hold run proves that, under this Windows / Switch 2 / firmware 22.1.0 condition, Switch requested the `0x6050` color block and swbt-python replied with the configured 12-byte body/buttons/grip bytes. The visible grip result is a user observation: this Switch UI did not show the configured left/right grip colors in the observed controller graphic. The 30 second hold rerun below checks the observation window separately.

### 2026-07-05: Unit 028 controller grip color SPI reply with 30 second hold on Windows

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: `work/unit-028-controller-profile-customization` worktree, staged unit_028 diff with a one-off probe script under `tmp/hardware/unit_028_controller_color_probe.py`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous Windows inventory associated `usb:0` with USB VID:PID `0a12:0001`.
- driver: not re-recorded in this run. Previous Windows inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`.
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.1`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30`, subcommand reply `0x21`, and close-time neutral `0x30`. No non-neutral input was sent.
- command / test: `uv run python tmp\hardware\unit_028_controller_color_probe.py --adapter usb:0 --artifact-dir .pytest_cache\hardware\unit_028 --trace-name controller-colors-and-grips-hold30.jsonl --body 0x00c853 --buttons 0xffeb3b --left-grip 0x2962ff --right-grip 0xd50000 --timeout 60 --spi-timeout 25 --hold-seconds 30 --switch-start-condition "Switch 2 22.1.0 controller search / change grip order screen; unit_028 grip color 30s hold observation by user"`
- approval: user requested another hardware experiment and asked to extend the post-connect hold to about 30 seconds. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect attempt, pairing fallback if needed, HID advertising, Switch pairing or reconnect, HID control / interrupt channel open, Switch output report / subcommand handling, periodic neutral report loop, trace save, key store save, close cleanup, and adapter release. Scope excluded non-neutral input, D-pad / stick / button reflection checks, extra retry loops, and persistent advertising.
- result: hardware-pass for 12-byte body/buttons/grip controller color SPI reply with a 30 second UI observation hold. Trace recorded `address=0x006050`, `size=13`, `controller_color_bytes=00c853ffeb3b2962ffd50000`, `matches_expected_controller_colors=true`, `manual_controller_color_probe_checkpoint hold_seconds=30.0 operation=ui_observation_hold_complete`, and cleanup. Switch UI color reflection was not auto-detected by the probe. User reported that the controller still showed green grips after the longer wait.
- artifact: `.pytest_cache/hardware/unit_028/controller-colors-and-grips-hold30.jsonl`
- artifact: `.pytest_cache/hardware/unit_028/controller-colors-key-store.json`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_controller_color_probe_cleanup connection_state=closed`.
- notes: This rerun reduces the likelihood that the visible grip color result was only caused by a short post-connect observation window. It is still a UI observation for this Switch 2 / firmware 22.1.0 screen, not a cross-firmware guarantee.

### 2026-07-05: macOS active reconnect button check with CSR8510 A10

- OS: macOS 15.7.7, build `24G720`, `macOS-15.7.7-x86_64-i386-64bit`
- environment: zsh, `main` at `406d2e6`, with uncommitted hardware log update from the preceding macOS pairing smoke
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`, Location ID `0x14130000`
- driver: Homebrew `libusb` 1.0.30. `DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib` was required.
- Python: 3.12.13
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, L+R hold, release to neutral, and close-time neutral were sent.
- command / test: `env DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib PATH=/usr/local/opt/pkgconf/bin:$PATH OPENSSL_DIR=/usr/local/opt/openssl@3 UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv run --python 3.12 pytest tests/hardware/test_input_operations.py::test_switch_button_check_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache/hardware/macos-20260705-button-check --log-file .pytest_cache/hardware/macos-20260705-button-check/button-check-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the active reconnect button check with `承認`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing pairing smoke key store copied to `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, L+R hold, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, D-pad, stick input, extra retry loops, and persistent advertising.
- result: hardware-pass for macOS button input. Pytest reported `1 passed in 9.77s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_enter_with_a_complete`, `hold_lr_reports_sent`, `button_check_neutral_complete`, and `transport_close_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User confirmed button reflection on the Switch UI and no stuck input after neutral.
- artifact: `.pytest_cache/hardware/macos-20260705-button-check/active-reconnect-button-check.jsonl`
- artifact: `.pytest_cache/hardware/macos-20260705-button-check/button-check-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the macOS active reconnect route, full observed subcommand handshake, and on-wire Button A / L+R / neutral checkpoints for this hardware condition. D-pad and stick input were not tested on macOS in this run.

### 2026-07-05: macOS pairing smoke with CSR8510 A10

- OS: macOS 15.7.7, build `24G720`, `macOS-15.7.7-x86_64-i386-64bit`
- environment: zsh, `main` at `406d2e6`, worktree clean before run. Python dependencies were installed with `uv run --python 3.12` after installing Homebrew `pkgconf`, `openssl@3`, and `libusb`.
- adapter: `usb:0`
- dongle: CSR8510 A10, USB VID:PID `0a12:0001`, Location ID `0x14130000`
- driver: Homebrew `libusb` 1.0.30. `DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib` was required because `libusb1` did not search Intel Homebrew's `/usr/local/opt/libusb/lib` path by default.
- Python: 3.12.13
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one neutral `0x30` close-time input report. No non-neutral input was sent.
- command / test: `env DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib PATH=/usr/local/opt/pkgconf/bin:$PATH OPENSSL_DIR=/usr/local/opt/openssl@3 UV_CACHE_DIR=.uv-cache UV_PYTHON_INSTALL_DIR=.uv-python uv run --python 3.12 swbt-probe pair --adapter usb:0 --key-store .pytest_cache/hardware/macos-20260705/pairing-key-store.json --trace .pytest_cache/hardware/macos-20260705/pairing-probe.jsonl --timeout 30`
- approval: user approved the pairing probe with `承認`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch pairing wait up to 30 seconds, trace save, key store save, close cleanup, and adapter release. Scope excluded non-neutral input, Button A, report-loop input verification, extra retry loops, and reconnect.
- result: observed-pass for macOS pairing / L2CAP smoke. Trace recorded `transport_open_complete`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, one neutral `0x30` report, L2CAP channel close, `disconnect_request status=requested`, and `transport_close_complete`.
- artifact: `.pytest_cache/hardware/macos-20260705/pairing-probe.jsonl`
- artifact: `.pytest_cache/hardware/macos-20260705/pairing-key-store.json`
- cleanup: trace recorded interrupt and control L2CAP channel close, disconnect request, disconnected events, and `transport_close_complete`. No cleanup error was recorded.
- notes: First attempts failed before adapter open because the Python environment was missing build/runtime dependencies: `cryptography==49.0.0` required Homebrew `pkgconf` and `openssl@3` for source build, and Bumble USB transport required Homebrew `libusb`. The final successful run required `DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib`. This run does not prove subcommand behavior or Switch UI input reflection.

### 2026-07-04: unit_013 fresh key store setup for active reconnect input checks

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic neutral `0x30` reports, `0x21` subcommand replies, and a close-time neutral `0x30`. No non-neutral input operation was sent.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_semantics_pairing_writes_fresh_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect -q -s`
- approval: user approved the first unit_013 hardware run with `OK。まずは1本目から行こう。`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, fresh pairing from the controller search / change grip order screen, key store write, full observed handshake wait, trace save, neutral close cleanup, and adapter release. Scope excluded Button A, L+R, stick input, active reconnect input reflection, extra retry loops, and persistent advertising.
- result: pass, `1 passed in 9.85s`. Trace recorded `key_store_exists=false`, `bonded_peers_discovered peer_count=0`, `active_reconnect_result status=no_bond`, `connect_pairing_fallback route=pairing`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `incoming_connection route=incoming`, `fresh_pairing_connect_result status=connected`, and full observed subcommand handshake through `manual_input_checkpoint operation=handshake_complete`.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\input-semantics-fresh-pairing.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\input-semantics-key-store.json` exists. The file was not opened for logging because it contains link key material.
- cleanup: trace recorded close-time neutral `0x30`, HID interrupt / control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `disconnected`, and `transport_close_complete`.
- notes: An earlier same-scope attempt created the key store but failed the pytest assertion because the test closed immediately after `key_store_update` while the first Switch subcommand reply was in flight. The test was adjusted to wait for the full observed handshake before closing, then rerun passed. This setup run is prerequisite evidence for unit_013 active reconnect input checks only; it does not exercise Button A, L+R, or stick semantic reflection.

### 2026-07-04: unit_013 active reconnect button check trace pass

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, L+R, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect -q -s`
- approval: user approved the second unit_013 hardware run with `ボタンの動作チェック選択画面で待機させている。2本目行こうか`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, L+R hold, neutral, trace save, close cleanup, and adapter release. Scope excluded stick input, new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: superseded by split diagnosis, pytest `1 passed in 9.37s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_enter_with_a_complete`, `hold_lr_reports_sent`, and `button_check_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User observed that only L looked pressed on the Switch button check screen; L+R simultaneous reflection was not confirmed in this first button run.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-button-check.jsonl`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and on-wire input checkpoints. It did not by itself prove L+R semantic reflection. The later split diagnosis captured raw outgoing HID bytes for R-only, L-only, and L+R and supersedes this run for the button result.

### 2026-07-04: unit_013 active reconnect button split diagnosis

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, R-only, L-only, L+R, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_separate_l_r_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-lr-split-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the repeat experiment with `再実験してみよう。待機済みなのでこのまま始めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, R-only hold, L-only hold, L+R hold, neutral between holds, trace save, debug log save, close cleanup, and adapter release. Scope excluded stick input, new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: hardware-pass for unit_013 button check, pytest `1 passed in 10.96s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_lr_split_enter_with_a_complete`, `hold_r_only_reports_sent expected_button_bytes=400000`, `hold_l_only_reports_sent expected_button_bytes=000040`, `hold_lr_together_reports_sent expected_button_bytes=400040`, and `button_check_lr_split_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User judged that the Switch button check UI likely does not display simultaneous button presses and shows only one side, so this is accepted as pass for the button portion.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-button-check-lr-split.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-lr-split-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: Debug log extraction of outgoing `0x30` input reports showed R-only button bytes `400000` 30 times, L-only `000040` 29 times, and L+R `400040` 30 times. This proves that the R bit was sent on-wire in this run. The remaining UI behavior is treated as a limitation of the Switch button check screen rather than a swbt-python input failure for this unit.

### 2026-07-04: unit_013 active reconnect D-pad button check

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, D-pad up, D-pad right, D-pad down, D-pad left, and neutral were sent by the test.
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_button_check_dpad_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-dpad-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the D-pad run with `待機中。実験を始めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the button check screen, D-pad up / right / down / left holds, neutral between holds, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, stick input, extra retry loops, and persistent advertising.
- result: hardware-pass. Pytest reported `1 passed in 11.71s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `button_check_dpad_enter_with_a_complete`, `hold_dpad_up_reports_sent expected_button_bytes=000002`, `hold_dpad_right_reports_sent expected_button_bytes=000004`, `hold_dpad_down_reports_sent expected_button_bytes=000001`, `hold_dpad_left_reports_sent expected_button_bytes=000008`, and `button_check_after_dpad_left_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that UI reflection was also confirmed.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-button-check-dpad.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\button-dpad-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route, D-pad direction checkpoints, and human-visible D-pad reflection on the Switch button check screen for this hardware condition.

### 2026-07-04: unit_013 active reconnect left stick trace

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, left stick hold, 16-step left stick circle, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[left]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\left-stick-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved continuing verification with `OK。switchセットアップ済み。検証を進めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the stick calibration screen, left stick hold, left stick circle, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded right stick input, new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: hardware-pass with observation caveat. Pytest reported `1 passed in 10.64s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `left_stick_calibration_enter_with_a_complete`, `left_stick_hold_reports_sent`, `left_stick_circle_complete steps=16`, and `left_stick_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that visual confirmation was possible, with the caveat that the circle may have ended quickly because the rotation was fast or screen transition timing was not fully accounted for.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-left-stick.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\left-stick-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and left stick input checkpoints. For a more inspectable operator experience, a later test could hold after entering the calibration screen for longer and slow down the circle input; this unit treats the left stick result as pass because user-visible reflection was observed.

### 2026-07-04: unit_013 active reconnect right stick trace

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, right stick hold, 16-step right stick circle, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user requested the right side run with `right側でも検証をやろう`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the stick calibration screen, right stick hold, right stick circle, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: trace-pass, visual inconclusive. Pytest reported `1 passed in 10.62s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `right_stick_calibration_enter_with_a_complete`, `right_stick_hold_reports_sent`, `right_stick_circle_complete steps=16`, and `right_stick_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that visual observation was completed, but the circle was too fast to see clearly.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-right-stick-fast.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and right stick input checkpoints. Because the human-visible right stick motion was not inspectable enough, this run is not a semantic pass. The follow-up test timing was changed to wait 1.5 seconds after A, hold for 120 reports, and send a 32-step circle at 0.15 seconds per step.

### 2026-07-04: unit_013 active reconnect right stick slow rerun

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-013-input-semantics-active-reconnect` at `5ed0e45` with uncommitted unit_013 test / spec / hardware-log updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: Switch 2
- Switch firmware: 22.1.0
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports. Button A, right stick hold, 32-step right stick circle, and neutral were sent by the test. The trace does not automatically prove Switch UI reflection.
- command / test: `uv run pytest 'tests\hardware\test_input_operations.py::test_switch_stick_calibration_after_active_reconnect_for_manual_reflection[right]' -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect --log-file .pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-slow-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the rerun with `再実験もやろう。準備済みなので片方のスティックで実施する形で確認しようか。`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, active reconnect from the existing `input-semantics-key-store.json`, HID control / interrupt channel open, full observed handshake wait, Button A to enter the stick calibration screen, right stick hold, right stick circle, neutral, trace save, debug log save, close cleanup, and adapter release. Scope excluded new pairing, key store rewrite, extra retry loops, and persistent advertising.
- result: hardware-pass. Pytest reported `1 passed in 16.77s`. Trace recorded `key_store_exists=true`, `bonded_peers_discovered peer_count=1 selection=selected`, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, `active_reconnect_result status=connected`, full observed subcommand handshake, `right_stick_calibration_enter_with_a_complete settle_seconds=1.5`, `right_stick_hold_reports_sent hold_report_count=120`, `right_stick_circle_complete steps=32 step_seconds=0.15`, and `right_stick_neutral_complete`. Trace did not record `advertising_start`, `classic_pairing`, `key_store_update`, or `error`. User reported that visual confirmation was possible.
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\active-reconnect-right-stick.jsonl`
- artifact: `.pytest_cache\hardware\unit_013\20260704-input-semantics-active-reconnect\right-stick-slow-pytest-debug.log`
- cleanup: trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No cleanup error was recorded.
- notes: This run proves the active reconnect route and slower right stick input checkpoints. The slower timing was sufficient for human-visible confirmation.

### 2026-07-03: unit_019 pairing L2CAP smoke after transport contract cleanup

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `main` at `041330b`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one neutral `0x30` input report after `connected`.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_019\20260703-pairing-l2cap-smoke -q -s`
- approval: user explicitly requested the run with `実機検証をやるか。接続画面で待機させているのでテストを始めてくれ`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch-facing pairing / HID control and interrupt connection wait, trace save, and close cleanup. Scope excluded Button A or other non-neutral input, extra retry loops, and persistent advertising.
- result: pass, `1 passed in 3.09s`. Trace recorded `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `transport_open_complete`, `classic_link_policy_configured settings="0x0005"`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `incoming_connection route=incoming`.
- artifact: `.pytest_cache\hardware\unit_019\20260703-pairing-l2cap-smoke\pairing-l2cap.jsonl`
- cleanup: trace recorded one neutral `0x30` `report_tx`, HID interrupt / control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `disconnected`, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run is a hardware smoke after the unit_019 diagnostics / transport-contract cleanup. It confirms that the current `main` can still pair and open HID control / interrupt L2CAP from the Switch connection screen. It does not exercise active reconnect or Button A input reflection.

### 2026-07-03: unit_008 swbt-probe pair passed after Switch connection wait

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-008-packaging-examples-cli` with uncommitted hardware-log update after `66fd860`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one neutral `0x30` input report after `connected`.
- command / test: `uv run swbt-probe pair --adapter usb:0 --key-store .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\keys.json --trace .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\pair-trace.jsonl --timeout 30`
- approval: user explicitly requested retry after the timeout with `接続待ちにしてないのが原因かも。もっかい頼めるか?`. Scope matched the previous approved hardware test: USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch-facing pairing / HID control and interrupt connection wait, trace save, and close cleanup. Scope excluded Button A or other non-neutral input, extra retry loops, and persistent advertising.
- result: pass, exit 0. The trace recorded `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `transport_open_complete`, `classic_link_policy_configured settings="0x0005"`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `incoming_connection route=incoming`.
- artifact: `.pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\pair-trace.jsonl`
- artifact: `.pytest_cache\hardware\unit_008\20260703-swbt-probe-pair-retry\keys.json`
- cleanup: trace recorded one neutral `0x30` `report_tx`, HID interrupt / control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`. No non-neutral input operation was sent. The key store file exists, but link key material is not logged here.
- notes: The preceding timeout is consistent with the Switch not being in connection-wait state, but this is an inference from the successful retry and the user's operator note, not a controlled A/B proof.

### 2026-07-03: unit_008 swbt-probe pair timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-008-packaging-examples-cli` at `66fd860`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device. Previous inventory associated `usb:0` with USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used. Report loop did not start because `connected` was not reached
- command / test: `uv run swbt-probe adapters --json`
- command / test: `uv run swbt-probe pair --adapter usb:0 --key-store .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair\keys.json --trace .pytest_cache\hardware\unit_008\20260703-swbt-probe-pair\pair-trace.jsonl --timeout 30`
- approval: user explicitly approved this hardware test with `実機テストやろうか。承認。`. Scope included USB Bluetooth dongle open, Classic HID Device initialization, HID advertising, Switch-facing pairing / HID control and interrupt connection wait, trace save, and close cleanup. Scope excluded Button A or other non-neutral input, extra retry loops, and persistent advertising.
- result: fail, `ConnectionTimeoutError` after 30 seconds. The no-open adapter command reported candidate `usb:0`, platform `Windows-11-10.0.26200-SP0`, Python 3.13.5, Bumble 0.0.230, and `opens_adapter=false`. The pair trace recorded `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `transport_open_complete`, `classic_link_policy_configured settings="0x0005"`, `advertising_start`, then `connection_timeout state=advertising`. The trace did not record `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`.
- artifact: `.pytest_cache\hardware\unit_008\20260703-swbt-probe-pair\pair-trace.jsonl`
- cleanup: trace recorded recoverable `error`, `disconnect_request status=unavailable` because channels were not connected, and `transport_close_complete`. No key store file was written and no non-neutral input operation was sent.
- notes: This run confirms that `swbt-probe pair --trace` leaves a diagnostic artifact and closes the transport on timeout. It does not prove Switch pairing or HID channel open for the CLI path.

### 2026-07-03: unit_007 active reconnect passed after Classic authentication and encryption

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-007-reconnect-keystore` with uncommitted active reconnect authentication/encryption change after `a4095ce`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Final active reconnect reached `connected`; trace recorded periodic `0x30`, subcommand reply `0x21`, and close-time input `0x30` reports.
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_pairing_writes_reconnect_key_store -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\pairing-pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_active_reconnect_with_existing_key_store_records_result -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-close-lock-pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_active_reconnect_with_existing_key_store_records_result -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-auth-encrypt-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved hardware work with `実機承認。一つずつやっていこう`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, initial pairing from controller search / change grip order screen, key store write, active reconnect request from HOME / normal screen, HID control L2CAP open attempt, disconnect handling, and cleanup. Incoming connection evaluation was explicitly left aside.
- 起動条件: initial pairing test recorded `expected_switch_screen=controller_search_or_change_grip_order`. Active reconnect test recorded `expected_switch_screen=home_or_normal_screen_not_change_grip_order`.
- result: pairing prerequisite passed, `1 passed in 7.92s`. Before the authentication/encryption fix, active reconnect reached ACL and sent HID control `L2CAP_CONNECTION_REQUEST` for PSM `0x0011`, then disconnected with `AUTHENTICATION_FAILURE_ERROR` reason 5; the test was still too weak and accepted `status=failed`. After changing the test to require `status=connected` and adding explicit Classic authentication/encryption before HID L2CAP, active reconnect passed, `1 passed in 8.85s`. The trace recorded `key_store_exists=true`, one bonded peer selected, `active_reconnect_attempt`, `host_connection`, `connection_authentication authenticated=true`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `active_reconnect_result status=connected`. The final active reconnect trace did not record `advertising_start`, `classic_pairing`, or `key_store_update`. Debug log order was `HCI_AUTHENTICATION_REQUESTED_COMMAND`, `HCI_AUTHENTICATION_COMPLETE_EVENT`, `HCI_SET_CONNECTION_ENCRYPTION_COMMAND`, `HCI_ENCRYPTION_CHANGE_EVENT`, then HID `L2CAP_CONNECTION_REQUEST`.
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\reconnect-initial-pair.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\pairing-pytest-debug.log`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-close-lock-pytest-debug.log`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\active-reconnect-after-auth-encrypt-pytest-debug.log`
- cleanup: final active reconnect trace recorded `disconnect_request status=requested`, `disconnect_request_terminal status=timeout`, later `disconnected reason=0`, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: The key store file exists in the artifact directory, but link key material is not logged here. The failure before the fix was not evidence of stale key material; it was reproduced as missing explicit Classic authentication/encryption before opening HID L2CAP. Incoming connection behavior is not reclassified by this entry.

### 2026-07-03: unit_007 incoming route from controller screen passed but re-paired

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-007-reconnect-keystore` at `e87ec10`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001`
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded periodic `0x30`, input `0x30`, and subcommand reply `0x21` reports after incoming connection.
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py::test_switch_incoming_connection_trace_stays_separate_from_active_reconnect -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect --log-file .pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\incoming-after-setup-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user stated that the previous incoming failure was probably Switch setup, then waited on `持ち方/順番を変える`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, incoming connection from controller search / change grip order screen, pairing/authentication as requested by Switch, HID control / interrupt channel open, Switch-facing output report / subcommand handling, periodic report loop, disconnect request, and cleanup.
- 起動条件: incoming test recorded `expected_switch_screen=controller_search_or_change_grip_order`.
- result: pass, `1 passed in 8.95s`. Trace recorded `key_store_exists=true`, `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `key_store_update status=succeeded`, `connection_encryption_change encryption=1`, HID control / interrupt `l2cap_channel_open`, `connected`, and `incoming_connection route=incoming`. It did not record `active_reconnect_attempt` or `active_reconnect_result`. Debug log recorded `HCI_CONNECTION_REQUEST_EVENT`, `HCI_LINK_KEY_NOTIFICATION_EVENT`, `HCI_ENCRYPTION_CHANGE_EVENT`, and HID L2CAP connection request/response. This proves incoming route separation under the listed operator condition, but not pairing-free incoming bond reuse.
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\incoming-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-operator-split-reconnect\incoming-after-setup-pytest-debug.log`
- cleanup: trace recorded HID interrupt/control channel close, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, later `transport_close_complete`. A queued post-close send recorded `ClosedError` diagnostics after channel close; cleanup still reached `transport_close_complete`.
- notes: The HCI debug log contains a link key notification. The raw link key value is intentionally not copied into this document. Since this run was started from the controller search / change grip order screen and emitted `classic_pairing` plus `key_store_update`, it must not be used as evidence for Switch-side-operation-free reconnect.

### 2026-07-03: unit_007 reconnect run with unrecorded Switch UI condition

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-007-reconnect-keystore` at `21013fb`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed in previous Bumble debug logs for this adapter
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Initial pairing traces recorded neutral `0x30` on close. Incoming attempt recorded periodic/input `0x30` and `0x21` subcommand replies after HID channel open.
- command / test: `uv run pytest tests\hardware\test_reconnect_keystore.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore --log-file .pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved with `承認`. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising for explicit pairing and incoming observation, initial pairing, key store write, active reconnect request, HID control / interrupt channel open wait, Switch-facing output report / subcommand handling when connected, periodic report loop, neutral, disconnect request, closed event wait, and cleanup.
- 起動条件: 未記録。この run だけでは、active reconnect 開始時の Switch が HOME / 通常アプリ画面だったのか、コントローラー探索 / 持ち方・順番を変える画面だったのかを区別できない。
- result: pass, `2 passed in 72.56s`. Initial pairing for active reconnect wrote `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\active-reconnect-key-store.json` and recorded `key_store_update status=succeeded`. The active reconnect attempt opened with `key_store_exists=true`, discovered one bonded peer, recorded `active_reconnect_attempt`, reached `host_connection` for `C8:48:05:F7:B5:21/P`, then disconnected with reason 19 before HID control / interrupt channel open. The final result was `active_reconnect_result status=timeout failure_reason=connection_timeout`; the trace did not record `advertising_start`, `classic_pairing`, or `key_store_update` during active reconnect. Incoming observation opened with `key_store_exists=true`, recorded `advertising_start`, `incoming_connection route=incoming`, HID control / interrupt `l2cap_channel_open`, `connected`, and subcommand receive/reply events. That incoming trace also recorded `classic_pairing` and `key_store_update status=succeeded`, so this run does not prove pairing-free incoming bond reuse.
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\active-reconnect-initial-pair.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\active-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\incoming-reconnect-initial-pair.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\incoming-reconnect-attempt.jsonl`
- artifact: `.pytest_cache\hardware\unit_007\20260703-013043-reconnect-keystore\pytest-debug.log`
- cleanup: all test paths closed the gamepad in `finally`. Active reconnect recorded `transport_close_complete` after timeout handling. Incoming attempt recorded `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`.
- notes: Treat this run as inconclusive for active reconnect success or failure under the intended user scenario. The next run must record the operator condition: initial pairing starts from the controller search / change grip order screen; active reconnect starts after returning to HOME or another normal screen, without controller search UI open. Some incoming close paths recorded post-close `ClosedError` diagnostics while queued report work was draining; cleanup still reached `transport_close_complete`.

### 2026-07-03: unit_015 resource open did not advertise, explicit pair and Button A path passed

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `main` at `42837e7` with uncommitted API removal and hardware-test updates
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed in previous Bumble debug logs for this adapter
- driver: not re-recorded in this run. Previous inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Pair close smoke recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)`. Button A path recorded full observed handshake, `tap(Button.A)`, neutral reports, and close cleanup.
- command / test: `uv run pytest tests/hardware/test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-resource-open-only --log-file .pytest_cache\hardware\unit_015\20260703-004306-resource-open-only\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests/hardware/test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke --log-file .pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke\pytest-debug.log --log-file-level=DEBUG -q -s`
- command / test: `uv run pytest tests/hardware/test_input_operations.py::test_switch_input_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a --log-file .pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved unit_015 hardware validation. Scope used here was adapter `usb:0`, USB Bluetooth dongle open, Classic HID Device initialization, resource-only `open()` without HID advertising, explicit `pair()` with discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop after `connected`, full observed subcommand handshake for the Button A path, one `tap(Button.A)`, neutral, trailing neutral, remote close request, closed event wait, and cleanup.
- result: pass. Resource-only smoke: `1 passed in 0.29s`; trace includes `transport_open_complete`, `disconnect_request status=unavailable`, and `transport_close_complete`; trace does not include `advertising_start` or `host_connection`. Pair close smoke: `1 passed in 4.28s`; trace includes `advertising_start`, `connection_request`, `host_connection`, `classic_pairing`, HID control / interrupt `l2cap_channel_open`, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, `transport_close_complete`, and `manual_close_checkpoint close_complete`. Button A path: `1 passed in 5.46s`; trace includes full observed handshake through `0x21`, `manual_input_checkpoint handshake_complete`, `post_handshake_tap_a_start`, `post_handshake_tap_a_complete`, `post_handshake_neutral_complete`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, and `transport_close_complete`.
- artifact: `.pytest_cache\hardware\unit_015\20260703-004306-resource-open-only\resource-open-only.jsonl`
- artifact: `.pytest_cache\hardware\unit_015\20260703-004306-pair-close-smoke\close-disconnect.jsonl`
- artifact: `.pytest_cache\hardware\unit_015\20260703-004306-post-handshake-button-a\post-handshake-input.jsonl`
- cleanup: all tests closed the gamepad in `finally`. Resource-only smoke never entered advertising. Pair close smoke and Button A path recorded `transport_close_complete` after disconnect request terminal state.
- notes: This validates the unit_015 lifecycle split, explicit `pair()` route, and Button A on-wire path for this hardware condition. It does not validate active bond reuse reconnect, key store behavior, or user-visible input reflection in this run.

### 2026-07-02: unit_014 close request reached closed event but missed final transport close

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch before commit `0979bd4`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed in adjacent Bumble debug logs for this adapter
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)` and no non-neutral input operation
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a --log-file .pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved the unit_014 hardware validation. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop, trailing neutral, remote close request, closed event wait or timeout, and cleanup. User explicitly asked not to send A twice or otherwise re-enter the device connection screen; this test sent no A input.
- result: fail. Pytest assertion failed because `transport_close_complete` was missing. Trace includes `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, public `disconnected reason=null`, Bumble `disconnected reason=0`, `disconnect_request_terminal status=closed`, and `manual_close_checkpoint close_complete`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-204228-close-disconnect-no-a\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`. Trace reached `manual_close_checkpoint close_complete`, but did not record `transport_close_complete`. The observed failure was reproduced without hardware by `test_close_request_disconnected_callback_leaves_final_close_to_user_close` and fixed in commit `0979bd4`.
- notes: This run proves only that the close request reached L2CAP close and the public closed terminal event on this hardware. It does not validate the fixed final transport close ordering.

### 2026-07-02: unit_014 post-fix close disconnect passed on Switch link

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `c08d4b1` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)` and no non-neutral input operation
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity --log-file .pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user asked to run one more connection check for the same unit_014 hardware scope. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop, trailing neutral, remote close request, closed event wait or timeout, and cleanup. No A input or other non-neutral input operation was sent.
- result: pass, `1 passed, 1 warning in 6.80s`. Trace includes `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, Bumble `disconnected reason=0`, public `disconnected reason=0`, `transport_close_complete`, and `manual_close_checkpoint close_complete`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-211502-close-disconnect-connectivity\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete` and `manual_close_checkpoint close_complete`. No non-neutral input operation was sent.
- notes: This run validates the post-fix connected close ordering for this hardware configuration. Trace still records separate public disconnection observations for L2CAP close (`reason=null`) and device disconnection (`reason=0`); `close()` remains idempotent and completed.

### 2026-07-02: subcommand observation follow-up timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `918325d` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation --log-file .pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user asked to check communication again because the Switch-side behavior did not look connected. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, subcommand observation and reply if connected, periodic neutral reports, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `l2cap_channel_open`, `connected`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation\subcommand-observation-window.jsonl`, `.pytest_cache\hardware\unit_014\20260702-211829-subcommand-observation\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run did not reach the Switch protocol layer. The observed failure point is before host connection, so it supports the user's observation that this attempt did not look like a live controller communication session.

### 2026-07-02: L2CAP-only follow-up timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `1bd4050` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check --log-file .pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved continuing the problem investigation. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open if connected, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_014\20260702-212504-pairing-l2cap-check\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This reproduces the pre-host-connection timeout with the narrower L2CAP diagnostics test. The problem is upstream of Switch output report / subcommand handling in this run.

### 2026-07-02: L2CAP-only retry timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `5e860cb` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry --log-file .pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user asked for one more retry. Scope matched the previous L2CAP-only problem investigation: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open if connected, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`. HCI debug log query found no `HCI_CONNECTION_REQUEST_EVENT`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_014\20260702-212834-pairing-l2cap-retry\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This repeat strengthens the finding that the current failure mode is pre-host-connection. It does not exercise L2CAP, output reports, subcommands, input reports, or close request ordering.

### 2026-07-02: new pairing L2CAP check timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `ceefe2a` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_pairing_l2cap_records_diagnostics -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap --log-file .pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user reported that Switch-side pairing information had been deleted and the Switch was searching from the new controller addition screen, then asked to try a fresh connection. Scope matched the L2CAP-only problem investigation: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing if the Switch initiated it, HID control / interrupt L2CAP open if connected, and cleanup. No A input or other non-neutral input operation was sent.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`. HCI debug log shows `HCI_WRITE_LOCAL_NAME_COMMAND`, `HCI_WRITE_CLASS_OF_DEVICE_COMMAND`, `HCI_WRITE_EXTENDED_INQUIRY_RESPONSE_COMMAND`, and final `HCI_WRITE_SCAN_ENABLE_COMMAND` with `scan_enable: 3` returning `SUCCESS`; the same log query found no `HCI_CONNECTION_REQUEST_EVENT` or `HCI_CONNECTION_COMPLETE_EVENT`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_014\20260702-213824-new-pairing-l2cap\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run was a new-connection attempt from the Switch side, but it did not reach pairing. The current failure point is before Switch host connection. Whether the Switch saw the inquiry response is not established by this artifact; that would need a separate discovery-side observation.

### 2026-07-02: advertising hold recorded no host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `b419cd7` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used. This diagnostic used `BumbleHidTransport` directly and did not create `ReportLoop`
- command / test: one-off `uv run python -` diagnostic script. It opened `BumbleHidTransport(adapter="usb:0")`, called `open()`, `start_advertising()`, recorded `manual_advertising_hold_start duration_seconds=90`, awaited `asyncio.sleep(90)`, recorded `manual_advertising_hold_complete`, and closed the transport in `finally`
- approval: user agreed to continue verification after the pre-host-connection timeout diagnosis. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or HID L2CAP observation only if the Switch initiated a connection, 90 second hold, and cleanup. No report loop, A input, or other non-neutral input operation was used.
- result: observed-timeout/no-host-connection. Trace includes `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `manual_advertising_hold_start`, `manual_advertising_hold_complete`, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, or `connected`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-215256-advertising-hold\advertising-hold.jsonl`
- cleanup: one-off diagnostic closed the transport in `finally`; trace recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run keeps the same failure boundary as the L2CAP-only timeout runs while removing report loop and pytest assertion behavior from the path. It does not prove whether another scanner could see the inquiry response.

### 2026-07-02: close cleanup disabled Classic scan on the dongle

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `16e6039` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used. This diagnostic used `BumbleHidTransport` directly and did not create `ReportLoop`
- command / test: one-off `uv run python -` diagnostic script. It opened `BumbleHidTransport(adapter="usb:0")`, called `open()`, `start_advertising()`, recorded `manual_close_scan_disable_probe_advertising_hold_start duration_seconds=5`, awaited `asyncio.sleep(5)`, recorded `manual_close_scan_disable_probe_close_start`, and closed the transport in `finally`
- approval: user explicitly approved running the close cleanup verification. Scope included USB Bluetooth dongle open, Classic HID Device initialization, short discoverable / connectable advertising, Switch host connection observation if the Switch initiated a connection, close path with `set_discoverable(False)` / `set_connectable(False)`, and cleanup. No report loop, A input, or other non-neutral input operation was used.
- result: observed-pass for close scan disable. Trace includes `transport_open_start`, `bumble_device_initialized` with `device_name="Pro Controller"` and `class_of_device="0x002508"`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `manual_close_scan_disable_probe_advertising_hold_start`, `host_connection`, `manual_close_scan_disable_probe_close_start`, `disconnected reason=0`, `transport_close_complete`, and `manual_close_scan_disable_probe_close_complete`. Debug log shows close path `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 2` followed by `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0`, both with `status: SUCCESS`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-220455-close-scan-disable\close-scan-disable.jsonl`, `.pytest_cache\hardware\unit_014\20260702-220455-close-scan-disable\close-scan-disable-debug.log`
- cleanup: one-off diagnostic closed the transport in `finally`; trace recorded `transport_close_complete`. Debug log recorded final `scan_enable: 0` with `SUCCESS`. No non-neutral input operation was sent.
- notes: This run confirms the software cleanup fix reaches the controller HCI boundary. It also shows that, at this moment, Switch did send a host connection request during the 5 second window. The user observed that `Pro Controller` disappeared from the iPhone Bluetooth discovery UI after this cleanup, supporting the conclusion that the earlier visible entry was caused by incomplete Classic scan cleanup rather than a still-running Python process.

### 2026-07-02: unit_014 close disconnect passed after Classic scan cleanup fix

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `82ae916` with clean worktree before the run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded one trailing neutral `0x30` input report from `pad.close(neutral=True)` and no non-neutral input operation
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup --log-file .pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved rerunning the original unit_014 close disconnect validation after confirming the close cleanup bug. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic report loop, trailing neutral, remote close request, closed event wait or timeout, Classic scan disable on close, and cleanup. No A input or other non-neutral input operation was sent.
- result: pass, `1 passed, 1 warning in 3.02s`. Trace includes `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, `manual_close_checkpoint close_start`, one neutral `report_tx`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, Bumble `disconnected reason=0`, public `disconnected reason=0`, `transport_close_complete`, and `manual_close_checkpoint close_complete`. Debug log includes `HCI_CONNECTION_REQUEST_EVENT`, `HCI_CONNECTION_COMPLETE_EVENT`, and final close path `HCI_WRITE_SCAN_ENABLE_COMMAND scan_enable: 0` with `status: SUCCESS`.
- artifact: `.pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-220940-close-disconnect-after-scan-cleanup\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete` and `manual_close_checkpoint close_complete`. Debug log recorded final `scan_enable: 0` with `SUCCESS`. No non-neutral input operation was sent.
- notes: This run validates unit_014 connected close ordering after the Classic scan cleanup fix. It closes immediately after HID control / interrupt L2CAP `connected`; it does not wait for the full observed Switch subcommand handshake or Switch UI registration completion.

### 2026-07-02: unit_014 post-handshake A exit and close passed without warning

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch with uncommitted warning fix for the first `-W error` run. The prior same-path UI observation run used commit `de8f39d`.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log in adjacent runs
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded full observed Switch handshake, Button A input reports, neutral reports, and one trailing neutral `0x30` from `pad.close(neutral=True)`
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_after_full_handshake_and_a_exit_for_manual_ui_confirmation -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-warning-fix-listener --log-file .pytest_cache\hardware\unit_014\20260702-warning-fix-listener\pytest-debug.log --log-file-level=DEBUG -q -s -W error`
- approval: user approved rerunning the same unit_014 hardware path to resolve the pytest warning. Scope included USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, full observed subcommand handshake, one explicit Button A tap to leave the registration screen, neutral, trailing neutral, remote close request, closed event wait or timeout, Classic scan disable on close, and cleanup.
- result: pass, `1 passed in 7.85s` with `-W error`. Trace includes `connection_request`, `host_connection`, `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, full observed handshake through `0x21`, `manual_close_checkpoint full_handshake_complete`, `tap_a_exit_pairing_screen_complete`, `neutral_after_a_complete`, `close_start`, trailing neutral `0x30`, interrupt and control `l2cap_channel_close`, `disconnect_request status=requested`, `disconnect_request_terminal status=closed`, public and Bumble `disconnected reason=0`, `transport_close_complete`, `close_complete`, and `post_close_ui_observation_window_complete`. User confirmed on the prior same-path run that Button A left the Switch registration screen as expected and that disconnect was visible.
- artifact: `.pytest_cache\hardware\unit_014\20260702-warning-fix-listener\post-handshake-a-close.jsonl`, `.pytest_cache\hardware\unit_014\20260702-warning-fix-listener\pytest-debug.log`; prior same-path UI observation artifact: `.pytest_cache\hardware\unit_014\20260702-221752-post-handshake-a-close\post-handshake-a-close.jsonl`, `.pytest_cache\hardware\unit_014\20260702-221752-post-handshake-a-close\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded trailing neutral, close request terminal `closed`, `transport_close_complete`, and post-close UI observation window completion. Debug log recorded final Classic scan disable without any `DeprecationWarning` or `Use utils.AsyncRunner.spawn()` entry.
- notes: The warning source was Bumble 0.0.230's host-registered incoming Classic connection handler calling deprecated `host.send_command_sync()`. swbt-python now replaces that host listener with its diagnostics bridge and runs the upstream handler while mapping `send_command_sync(command)` to `AsyncRunner.spawn(host.send_async_command(command))`.

### 2026-07-02: unit_014 post-fix close disconnect reruns timed out before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-014-close-disconnect` branch at commit `0979bd4`
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us, but report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix --log-file .pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\pytest-debug.log --log-file-level=DEBUG -q -s`; rerun: `uv run pytest tests\hardware\test_close_disconnect.py::test_switch_close_requests_disconnect_after_neutral -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry --log-file .pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: same unit_014 hardware validation approval. Scope matched the connected close test, but both post-fix reruns stopped before Switch host connection.
- result: fail for both reruns, `ConnectionTimeoutError` after 60 seconds. Both traces include `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `classic_link_policy_configured`, `advertising_start`, `connection_timeout state=advertising`, `disconnect_request status=unavailable reason=channels_not_connected`, and `transport_close_complete`. Neither trace includes `connection_request`, `host_connection`, `classic_pairing`, `l2cap_channel_open`, `connected`, trailing neutral, or close request terminal state.
- artifact: `.pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-204804-close-disconnect-no-a-fix\pytest-debug.log`, `.pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\close-disconnect.jsonl`, `.pytest_cache\hardware\unit_014\20260702-205015-close-disconnect-no-a-retry\pytest-debug.log`
- cleanup: each rerun executed `pad.close(neutral=True)` from `finally`; both traces recorded `transport_close_complete`. No non-neutral input operation was sent.
- notes: These reruns do not exercise unit_014 connected close behavior after commit `0979bd4`. The observed failure point is before Switch host connection.

### 2026-07-02: unit_006 post-handshake Button A input reflected on Switch UI

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `6b5ed73` with clean worktree before and after the hardware run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 66 `report_tx` events, 21 `output_report_rx` events, 16 `subcommand_rx` events, and 16 `subcommand_reply_tx` events. Checkpoints recorded `handshake_complete`, `post_handshake_tap_a_start`, `post_handshake_tap_a_complete`, and `post_handshake_neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_after_full_handshake_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-post-handshake-input --log-file .pytest_cache\hardware\unit_006\20260702-post-handshake-input\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved this hardware test. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, wait for full observed handshake, `Button.A` tap, neutral input, and cleanup.
- result: pass. Pytest reported `1 passed, 1 warning in 9.45s`. Trace recorded `classic_pairing`, `link_key_available`, `connection_encryption_change`, L2CAP control / interrupt open, `connected`, and the full observed M5 handshake subcommand sequence: `0x02`, `0x08`, `0x10` x8, `0x03`, `0x04`, `0x40`, `0x30` x2, `0x48`, `0x21`. `handshake_complete` was recorded at `0x30` report count 4; `post_handshake_tap_a_complete` at count 41; `post_handshake_neutral_complete` at count 49. Bumble debug log showed A button bytes `08 00 00` in `0x30` report counters 20-23 and neutral bytes `00 00 00` from counter 24 onward. The user visually confirmed that A was reflected on the Switch UI and that no residual input was visible after neutral.
- artifact: `.pytest_cache\hardware\unit_006\20260702-post-handshake-input\post-handshake-input.jsonl`, `.pytest_cache\hardware\unit_006\20260702-post-handshake-input\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final `0x30` input report, two public `disconnected reason=0` events, and `transport_close_complete`.
- notes: This run completes the M5 Button A / neutral semantic input reflection condition for this hardware configuration. It does not cover stick semantic reflection, reconnect, or multiple controller behavior.

### 2026-07-02: unit_006 shared timer rerun progressed through Switch handshake

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `4e677f2` with clean worktree before the hardware run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 54 `report_tx` events, including 16 `0x21` subcommand replies and `0x30` periodic / input reports. Checkpoints recorded `tap_a_start`, `tap_a_complete`, `hold_lr_start`, `hold_lr_reports_sent`, and `neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-shared-timer-rerun --log-file .pytest_cache\hardware\unit_006\20260702-shared-timer-rerun\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved this hardware test after shared timer / reply holdoff implementation. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, `Button.A` tap, L+R hold, neutral input, and cleanup.
- result: handshake-progressed, pairing observed-pass, input reflection pending. Pytest reported `1 passed, 1 warning in 8.44s`. Trace recorded `classic_pairing`, `link_key_available`, `connection_encryption_change` with `authenticated=false`, `encryption=1`, `secure_connections=false`, L2CAP control / interrupt open, `connected`, and `classic_mode_change`. Observed subcommands progressed from previous `0x02` / repeated `0x08` to `0x02`, `0x08`, `0x10` x8, `0x03`, `0x04`, `0x40`, `0x30` x2, `0x48`, `0x21`. Each observed subcommand had a `subcommand_reply_tx`. The user visually confirmed that pairing completed on the Switch side. The run also recorded A tap, L+R hold, neutral, clean close. `tap(Button.A)` UI reflection and neutral residual state are not auto-detected by this pytest and remain pending separate user-visible confirmation.
- artifact: `.pytest_cache\hardware\unit_006\20260702-shared-timer-rerun\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-shared-timer-rerun\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded neutral input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run supports the daemon-derived shared timer hypothesis for escaping repeated `0x08` and confirms Switch-side pairing completion under this hardware condition. It does not by itself complete M5 because `tap(Button.A)` UI reflection and neutral residual state require separate user-visible confirmation.

### 2026-07-02: unit_006 pairing diagnostics still stopped at repeated 0x08

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `228d669` with clean worktree before the diagnostic run
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded periodic/input `0x30` reports, subcommand reply attempts, `tap_a_start`, `tap_a_complete`, `hold_lr_start`, `hold_lr_reports_sent`, and `neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-pairing-diagnostics --log-file .pytest_cache\hardware\unit_006\20260702-pairing-diagnostics\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user approved this command after adapter, Switch-facing scope, and cleanup were stated. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, `Button.A` tap, L+R hold, neutral input, and cleanup.
- result: observed-fail for semantic input reflection. Pytest reported `1 passed, 1 warning in 6.51s`, but the user confirmed that the Switch device registration / authentication screen did not move. Trace recorded `classic_pairing`, `link_key_available`, `connection_encryption_change` with `authenticated=false`, `encryption=1`, `secure_connections=false`, L2CAP control / interrupt open, `connected`, `classic_mode_change`, `0x02` once, and repeated `0x08`. It did not record `pairing_complete` or `connection_authentication`, and did not progress to daemon-success subcommands `0x10`, `0x03`, `0x04`, `0x40`, `0x48`, `0x21`, `0x30`.
- artifact: `.pytest_cache\hardware\unit_006\20260702-pairing-diagnostics\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-pairing-diagnostics\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded neutral input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run confirms that link-key availability and encryption change alone are not sufficient evidence that Switch accepted the controller. Based on daemon `local_037`, swbt-python then changed software scheduling so `0x21` replies consume the shared input report timer and hold off following periodic `0x30` reports. That fix has not yet been run on hardware.

### 2026-07-02: unit_006 input operation sequence sent reports but did not move Switch UI

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-006-input-operation-api` branch at commit `79ecbd1` with clean worktree before the observable rerun
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 56 `0x30` reports and 4 `0x21` replies. Checkpoints recorded `tap_a_start`, `tap_a_complete`, `hold_lr_start`, `hold_lr_reports_sent`, and `neutral_complete`
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_input_operation_sequence_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable --log-file .pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved unit_006 hardware verification and requested commit before hardware verification. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic input report loop, `Button.A` tap, L+R hold, neutral input, and cleanup. Scope excluded reconnect and broader firmware / adapter matrix claims.
- result: observed-fail for semantic input reflection. Pytest reported `1 passed, 1 warning in 10.08s`, but that pass only proves the trace sequence and cleanup assertions. User observed that the Switch device registration screen did not move at all. Debug log confirmed outgoing HID interrupt input reports: A used button bytes `08 00 00` (`a1 30 ... 91 08 00 00 ...`), L+R used `40 00 40` (`a1 30 ... 91 40 00 40 ...`), and neutral used `00 00 00` (`a1 30 ... 91 00 00 00 ...`). Trace recorded no `error` event. The cause is not determined by this run. swbt-daemon `local_049` success observed `pairing complete, status 00`, `0x02` / `0x08` / `0x10` / `0x03` / `0x04` / `0x40` / `0x48` / `0x21` / `0x30` replies, then L+R and Button A UI reflection. swbt-daemon `local_073` pairing-free reconnect pass observed link-key DB use and no new `pairing complete`. This swbt-python run only recorded `classic_pairing`, L2CAP open, and observed `0x02` / `0x08`; it did not record authentication, encryption, link key, or full controller initialization sequence.
- artifact: `.pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\input-operation-sequence.jsonl`, `.pytest_cache\hardware\unit_006\20260702-input-operation-sequence-observable\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final neutral `0x30` input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`.
- notes: This run proves report transmission through Bumble/L2CAP under the listed conditions, but contradicts M5 completion because Switch UI input reflection was not observed. Next diagnosis should separate report acceptance / controller registration state from report byte correctness. The successful pytest assertion must not be treated as semantic input reflection. After comparison with swbt-daemon logs, the next diagnostic run should require trace evidence for `pairing_complete`, `connection_authentication`, `connection_encryption_change`, optional `link_key_available`, and whether Switch progresses beyond repeated `0x08` into the known daemon subcommand sequence. Raw link key values must not be logged.

### 2026-07-02: unit_005 observation window replied to all observed subcommands

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted observation-window hardware test, post-send `report_tx` diagnostics boundary, and Bumble ACL queue drain implementation.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Trace recorded 135 periodic neutral `0x30` reports, 9 `0x21` subcommand replies, and one neutral input report during cleanup.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_observation_window_replies_to_all_observed_commands -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain --log-file .pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved continuing unit_005 hardware verification. Scope used `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, Switch output report receive, `0x21` reply for observed subcommands, 5 second observation window after first subcommand, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: pass, `1 passed, 1 warning in 9.50s`. Trace recorded `output_report_rx` 9 件, `subcommand_rx` 9 件, `subcommand_reply_tx` 9 件, and `report_tx` reason `subcommand_reply` 9 件. Observed subcommands were `0x02` x1 and `0x08` x8, and every observed `(packet_id, subcommand_id)` had a matching reply. `unsupported_subcommand` and `error` were 0 件. Bumble debug log had 0 matches for `packets in flight`, unlike the earlier observation-window experiment without effective ACL drain where controller completed-packet backlog grew.
- artifact: `.pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\subcommand-observation-window.jsonl`, `.pytest_cache\hardware\unit_005\20260702-obs-window-host-queue-drain\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded final neutral `0x30` input, `disconnected reason=0`, the public disconnection event, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run closes the M4 residual risk that the first successful `0x02` reply did not prove later observed subcommands would receive replies. It does not cover semantic input reflection, reconnect, firmware matrix expansion, or all possible Switch subcommands.

### 2026-07-02: unit_005 link-policy-only run reached subcommand reply

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted minimized link-policy-only implementation, docs, and tests changes. The runtime implementation no longer included HID L2CAP MTU `100` re-registration or the `0x8e` / `0x80` profile prefix change.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Report loop emitted six neutral `0x30` reports before Switch output `0x01`, then sent one `0x21` reply and later neutral reports during cleanup.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-011634-link-policy-only --log-file .pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested real hardware verification. Scope used the established unit_005 M4 hardware test on `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, output report receive wait, `0x21` reply if output arrived, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: pass, `1 passed, 1 warning in 4.27s`. Trace recorded `classic_link_policy_configured` with `settings=0x0005`, `host_connection`, `classic_pairing`, control and interrupt `l2cap_channel_open`, `connected`, `output_report_rx` for report `0x01` / subcommand `0x02`, `subcommand_rx`, `subcommand_reply_tx`, and `report_tx` for `0x21`. The trace did not record `hid_l2cap_mtu`, confirming this was not the MTU-100 server re-registration variant. The debug log confirms `HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND`, `HCI_MODE_CHANGE_EVENT`, incoming HID interrupt PDU `a2 01`, and outgoing reply PDU `a1 21 00 91...`.
- artifact: `.pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-011634-link-policy-only\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded `disconnected reason=0`, the public disconnection event, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run isolates the earlier successful result to the Classic default link policy `0x0005` change. HID L2CAP MTU `100` re-registration and the `0x8e` / `0x80` profile prefix are not needed for this M4 subcommand-sequence pass under the listed adapter / driver / Bumble / Switch state. This is still a hardware observation, not a cross-platform guarantee.

### 2026-07-02: unit_005 link-policy run reached subcommand reply

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted link-policy, MTU-100, `0x8e` / `0x80` prefix, docs, and tests changes.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by prior Bumble USB debug logs. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Report loop emitted six neutral `0x30` reports before Switch output `0x01`, then sent one `0x21` reply and later neutral reports during cleanup.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-010148-link-policy --log-file .pytest_cache\hardware\unit_005\20260702-010148-link-policy\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested real hardware verification. Scope used the established unit_005 M4 hardware test on `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, output report receive wait, `0x21` reply if output arrived, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: pass, `1 passed, 1 warning in 2.92s`. Trace recorded `classic_link_policy_configured` with `settings=0x0005`, `host_connection`, `classic_pairing`, control and interrupt `l2cap_channel_open`, `connected`, `classic_mode_change` with `mode=2` and `interval=24`, `output_report_rx` for report `0x01` / subcommand `0x02`, `subcommand_rx`, `subcommand_reply_tx`, and `report_tx` for `0x21`. The debug log confirms `HCI_WRITE_DEFAULT_LINK_POLICY_SETTINGS_COMMAND`, `HCI_MODE_CHANGE_EVENT`, incoming HID interrupt PDU `a2 01`, and outgoing reply PDU `a1 21`.
- artifact: `.pytest_cache\hardware\unit_005\20260702-010148-link-policy\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-010148-link-policy\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded `disconnected reason=0`, the public disconnection event, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run moves M4 past the previous failure point. The smallest observed decisive difference from the MTU-100 failure run is Classic default link policy `0x0005`, followed by a Mode Change before the Switch output report. This run does not prove that HID L2CAP MTU `100` or the `0x8e` / `0x80` report prefix are required together with link policy `0x0005`; the minimized implementation therefore retains link policy `0x0005` and drops the MTU / prefix changes unless a later A/B hardware run proves they are needed. This is still a hardware observation under the listed adapter / driver / Bumble / Switch state, not a cross-platform guarantee.

### 2026-07-02: unit_005 MTU-100 diagnostic still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch with uncommitted MTU-100, `0x8e` / `0x80` prefix, docs, and tests changes.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: default 8000 us. Report loop started after `connected` and emitted 14 neutral `0x30` reports before Switch-side disconnect.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-004659-mtu100 --log-file .pytest_cache\hardware\unit_005\20260702-004659-mtu100\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly requested real hardware verification. Scope used the established unit_005 M4 hardware test on `usb:0`: USB Bluetooth dongle open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, periodic neutral `0x30` report loop, output report receive wait, `0x21` reply if output arrived, and cleanup. Scope excluded non-neutral input, Button A input reflection, and reconnect.
- result: fail before output report. Trace recorded `hid_device_initialized` with `hid_l2cap_mtu=100`, `host_connection`, `classic_pairing`, control and interrupt `l2cap_channel_open`, `connected`, then 14 periodic neutral `0x30` `report_tx` events. It recorded no `HID CONTROL PDU`, no `HID INTERRUPT PDU`, no `output_report_rx`, no `subcommand_rx`, and no `subcommand_reply_tx`. The debug log confirms control and interrupt channels opened as `MTU=100/672`, then `a1 30` reports with `0x8e` / `0x80` prefix were sent, and Switch-side reason 19 disconnected.
- artifact: `.pytest_cache\hardware\unit_005\20260702-004659-mtu100\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-004659-mtu100\pytest-debug.log`
- cleanup: pytest executed `pad.close(neutral=True)` from `finally`; trace recorded `disconnected reason=19`, L2CAP channel close events, and `transport_close_complete`. No non-neutral input operation was sent.
- notes: This run confirms the MTU-100 transport change reached the live L2CAP channels. It did not move the M4 failure point: output report reception is still not reached. The remaining blocker is not explained by HIDP input header absence, status prefix mismatch, or Bumble local MTU alone.

### 2026-07-02: unit_005 single 0x30 and prefix diagnostics still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch at commit `7520925`. Worktree was clean before the initial single-`0x30` runs. The `0x8e` / `0x80` prefix rerun used uncommitted profile changes after unit / integration tests passed.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: all one-off diagnostics used `50,000,000 us` to suppress periodic send. `20260702-003000` waited 300 ms after `connected` before one-shot send; the send was not reached. `20260702-002548` sent one neutral `0x30` immediately after `connected` with the then-current `0x91` / `0x00` status prefix. `20260702-003225` sent one neutral `0x30` immediately after `connected` with the daemon-aligned `0x8e` / `0x80` status prefix.
- command / test: `uv run python .pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\single_0x30_probe.py`; `uv run python .pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\single_0x30_immediate_probe.py`; `uv run python .pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\single_0x30_prefix_probe.py`
- approval: user explicitly approved the immediate single-`0x30` diagnostic and the follow-up prefix-difference diagnostic. Scope included `usb:0` adapter open, Classic HID Device initialization, discoverable / connectable / HID advertising, Switch pairing or existing connection, HID control / interrupt L2CAP open, one neutral `0x30` send, 5 s observation, and cleanup. Scope excluded periodic report loop, non-neutral input, Button A input reflection, and reconnect.
- result: fail before output report. The 300 ms delay diagnostic reached `connected` but disconnected with reason 19 before the single `0x30` send; trace recorded no `report_tx`. The `0x91` / `0x00` immediate diagnostic reached `connected`, sent one neutral `0x30` (`report_tx` reason `single_probe_immediate`), recorded no `HID CONTROL PDU`, no `HID INTERRUPT PDU`, no `output_report_rx`, no `subcommand_rx`, and no `subcommand_reply_tx`, then Switch-side reason 19 disconnected. Its debug log shows `>>> HID INTERRUPT SEND DATA, PDU: a130009100...` at line 904 and `REMOTE_USER_TERMINATED_CONNECTION_ERROR` at line 921. The `0x8e` / `0x80` prefix rerun also reached `connected`, sent one neutral `0x30` (`report_tx` reason `single_probe_prefix_8e80`), recorded no output report events, and disconnected with reason 19. Its debug log shows `>>> HID INTERRUPT SEND DATA, PDU: a130008e...80...` at line 431 and `REMOTE_USER_TERMINATED_CONNECTION_ERROR` at line 448.
- artifact: `.pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\single-0x30-delay.jsonl`, `.pytest_cache\hardware\unit_005\20260702-003000-single-0x30-delay\bumble-debug.log`, `.pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\single-0x30-immediate.jsonl`, `.pytest_cache\hardware\unit_005\20260702-002548-single-0x30-immediate\bumble-debug.log`, `.pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\single-0x30-prefix-8e80.jsonl`, `.pytest_cache\hardware\unit_005\20260702-003225-single-0x30-prefix-8e80\bumble-debug.log`
- cleanup: all one-off diagnostics called `pad.close(neutral=False)` after observation or failure. No non-neutral input operation was sent. The immediate diagnostics recorded `transport_close_complete`; final probe cleanup markers reached `probe_cleanup_done`.
- notes: These diagnostics reduce the likelihood that the failure is only caused by continuous 8 ms periodic `0x30` traffic or by the status prefix mismatch alone. They also show that a 300 ms delay is too late for this Switch-side state, because the connection closes before the first send. The remaining difference from swbt-daemon is not simply HIDP input header presence; both immediate diagnostics sent `a1 30` but still did not induce Switch output report `a2 01`. The `0x8e` / `0x80` profile change remains useful as daemon-aligned implementation policy, but this hardware run did not move the M4 failure point.

### 2026-07-02: unit_005 reset-state rerun still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch at commit `0eaaaf4`. User reported that the Switch-side connection state had been reset before this rerun.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: `20260702-001048` used default 8000 us. `20260702-001143` used 50,000,000 us as a no-report-window diagnostic and emitted no periodic input report during the observation window.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-001048 --log-file .pytest_cache\hardware\unit_005\20260702-001048\pytest-debug.log --log-file-level=DEBUG -q -s`; no-report-window diagnostic used a one-off `uv run python -` script and wrote `.pytest_cache\hardware\unit_005\20260702-001143\subcommand-sequence-no-report-window.jsonl`
- approval: user explicitly requested rerunning verification after resetting connection state. Scope followed the existing unit_005 approval: USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for the pytest run, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. The pytest run reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, `connected`, encryption change, and L2CAP open. It recorded no `HID CONTROL PDU`, `HID INTERRUPT PDU`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`, then sent 14 neutral `0x30` reports before Switch-side reason 19 disconnect. The debug log showed direct L2CAP connection requests for HID control PSM `0x0011` and interrupt PSM `0x0013`; no SDP query was observed in the extracted log lines. The no-report-window diagnostic also reached `connected`, recorded no `report_tx` and no output report, then disconnected with reason 19.
- artifact: `.pytest_cache\hardware\unit_005\20260702-001048\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-001048\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260702-001143\subcommand-sequence-no-report-window.jsonl`
- cleanup: pytest run executed `pad.close(neutral=True)` from `finally`; traces recorded `transport_close_complete`. The no-report-window diagnostic closed the pad after observing disconnect. No non-neutral input operation was sent.
- notes: Resetting the connection state did not move the failure point. The current blocker remains before M4 subcommand responder behavior is exercised. The no-report-window diagnostic again shows the disconnect is not explained solely by early neutral `0x30` reports.

### 2026-07-02: unit_005 SDP service-name run still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch at commit `e1ac888`. Runs included HID SDP service name attribute `0x0100` and corrected SDP LanguageBaseAttributeIDList values, in addition to the earlier HIDP DATA, SET_REPORT, control-channel output report, and HID SDP policy fixes.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: `20260702-000120` used default 8000 us. `20260702-000302` used 50,000,000 us as a no-report-window diagnostic and emitted no periodic input report during the observation window.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260702-000120 --log-file .pytest_cache\hardware\unit_005\20260702-000120\pytest-debug.log --log-file-level=DEBUG -q -s`; no-report-window diagnostic used a one-off `uv run python -` script and wrote `.pytest_cache\hardware\unit_005\20260702-000302\subcommand-sequence-no-report-window.jsonl`
- approval: user explicitly approved unit_005 hardware verification. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for the pytest run, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. The pytest run reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, `connected`, pairing success, encryption change, and L2CAP open. It recorded no `HID CONTROL PDU`, `HID INTERRUPT PDU`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`, then sent 14 neutral `0x30` reports before Switch-side reason 19 disconnect. The no-report-window diagnostic also reached `connected`, recorded no `report_tx` and no output report, then disconnected with reason 19.
- artifact: `.pytest_cache\hardware\unit_005\20260702-000120\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260702-000120\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260702-000302\subcommand-sequence-no-report-window.jsonl`
- cleanup: pytest run executed `pad.close(neutral=True)` from `finally`; traces recorded `transport_close_complete`. The no-report-window diagnostic closed the pad after observing disconnect. No non-neutral input operation was sent.
- notes: Adding SDP service name and correcting the SDP language base did not move the failure point. The `20260702-000120` debug log showed incoming L2CAP connection requests for HID control PSM `0x0011` and interrupt PSM `0x0013`, with no SDP PSM query observed in the captured log. This means the SDP service name / language base change may not have been re-read by the Switch in this run. Since the no-report-window diagnostic also disconnects before any output report, the current blocker is still before M4 subcommand responder behavior is exercised and is not explained solely by early neutral `0x30` reports.

### 2026-07-01: unit_005 post-transport-fix subcommand run still stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch. Runs used committed transport fixes for HIDP DATA output header stripping, SET_REPORT forwarding, control-channel output report handling, and HID SDP policy alignment with the reference implementation.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: `20260701-234045` and `20260701-234437` used default 8000 us. `20260701-234549` used 50,000,000 us as a no-report-window diagnostic and emitted no periodic input report during the observation window.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-234045 --log-file .pytest_cache\hardware\unit_005\20260701-234045\pytest-debug.log --log-file-level=DEBUG -q -s`; repeated after HID SDP policy alignment with artifact dir `.pytest_cache\hardware\unit_005\20260701-234437`. The no-report-window diagnostic used a one-off `uv run python -` script and wrote `.pytest_cache\hardware\unit_005\20260701-234549\subcommand-sequence-no-report-window.jsonl`
- approval: user explicitly approved unit_005 hardware verification. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for pytest runs, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. Runs reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, and `connected`. Debug logs confirmed `SetReport callback registered successfully`; the post-SDP run also showed pairing, link key notification, encryption change, and both L2CAP channels open. No run recorded `HID CONTROL PDU`, `HID INTERRUPT PDU`, `output_report_rx`, `subcommand_rx`, or `subcommand_reply_tx`. The pytest runs sent neutral `0x30` reports before Switch-side reason 19 disconnect. The no-report-window diagnostic sent no periodic input report before the same reason 19 disconnect.
- artifact: `.pytest_cache\hardware\unit_005\20260701-234045\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-234045\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-234437\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-234437\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-234549\subcommand-sequence-no-report-window.jsonl`
- cleanup: each pytest run executed `pad.close(neutral=True)` from `finally`; traces recorded `transport_close_complete`. The no-report-window diagnostic closed the pad after observing disconnect. No non-neutral input operation was sent.
- notes: The receive path now handles Bumble HIDP DATA headers, SET_REPORT output reports, control-channel output reports, and the reference HID SDP policy. Current failure remains before M4 subcommand responder behavior is exercised. The no-report-window diagnostic means the disconnect is not explained solely by early neutral `0x30` reports. Remaining candidates are Switch-side HID adoption state, Bumble HID Device behavior, timing, or another transport-level difference; those are not confirmed.

### 2026-07-01: unit_005 subcommand sequence attempts stopped before output report

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `feat/unit-005-subcommand-responder` branch. Attempt 1 ran from a clean worktree at commit `50d552d`. Attempts 2 and 3 used temporary uncommitted experiments that were reverted after the run: slower M4 test report period, then Bumble report-loop deferral.
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: attempt 1 used default 8000 us; attempt 2 used temporary 50000 us in the M4 hardware test; attempt 3 deferred periodic report start until host output. Attempt 3 emitted no `report_tx` before disconnect.
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py::test_switch_subcommand_sequence_gets_0x21_replies -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_005\20260701-232123 --log-file .pytest_cache\hardware\unit_005\20260701-232123\pytest-debug.log --log-file-level=DEBUG -q -s`; repeated with artifact dirs `20260701-232352` and `20260701-232634`
- approval: user explicitly approved unit_005 hardware verification. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing, output report receive wait, `0x21` reply send if output arrived, periodic report loop for attempts 1 and 2, and cleanup. Scope excluded Button A input reflection and reconnect.
- result: fail. All attempts reached `host_connection`, `classic_pairing`, HID control channel open, HID interrupt channel open, and `connected`. No attempt recorded `output_report_rx`, `subcommand_rx`, `subcommand_reply_tx`, `unsupported_subcommand`, `HID CONTROL PDU`, or `HID INTERRUPT PDU` from Switch. Attempt 1 sent periodic `0x30` reports before Switch disconnected with reason 19. Attempt 2 sent two slower `0x30` reports before the same disconnect. Attempt 3 sent no input report before Switch disconnected with reason 19. The current failure point is before M4 output report handling.
- artifact: `.pytest_cache\hardware\unit_005\20260701-232123\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-232123\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-232352\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-232352\pytest-debug.log`, `.pytest_cache\hardware\unit_005\20260701-232634\subcommand-sequence.jsonl`, `.pytest_cache\hardware\unit_005\20260701-232634\pytest-debug.log`
- cleanup: each run executed `pad.close(neutral=True)` from `finally`; trace recorded `transport_close_complete`. Attempts 1 and 2 had already received Switch-side disconnect before cleanup. Attempt 3 had no input report before disconnect.
- notes: Sending no periodic report before host output did not cause Switch to send `0x01`; therefore the earlier disconnect is not explained solely by early `0x30` reports. Existing swbt-daemon design and implementation show that output handler, report scheduler, and send-ready integration are part of the successful BTstack path; Bumble-specific L2CAP/HID readiness remains unverified for M4.

### 2026-07-01: unit_004 pairing / L2CAP pass after discovery identity alignment

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-004-pairing-l2cap` branch with uncommitted unit_004 implementation after aligning discovery identity with the reference production path
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: 8000 us default. Report loop started after `connected`; trace recorded one neutral `0x30` `report_tx`. Semantic input reflection was not tested
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-225624 --log-file .pytest_cache\hardware\unit_004\20260701-225624\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved rerunning the M3 hardware test after applying the discovery identity fix. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing attempt, HID control / interrupt channel open wait, and cleanup. Scope excluded semantic input reflection and reconnect.
- result: pass, `1 passed, 1 warning in 6.81s`. Trace includes `device_name="Pro Controller"`, `class_of_device="0x002508"`, `host_connection`, `classic_pairing`, `l2cap_channel_open` for control PSM `0x0011`, `l2cap_channel_open` for interrupt PSM `0x0013`, `connected`, one neutral `report_tx`, `disconnected reason=0`, and `transport_close_complete`. Debug log confirms `HCI_WRITE_LOCAL_NAME_COMMAND` with `Pro Controller`, `HCI_WRITE_CLASS_OF_DEVICE_COMMAND` with `[002508]`, incoming `HCI_CONNECTION_REQUEST_EVENT`, successful connection complete, successful simple pairing complete, and both L2CAP channels open. `HCI_WRITE_SECURE_CONNECTIONS_HOST_SUPPORT_COMMAND` still returned `UNKNOWN_HCI_COMMAND_ERROR`, but it did not block pairing or L2CAP in this run.
- artifact: `.pytest_cache\hardware\unit_004\20260701-225624\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_004\20260701-225624\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `disconnected reason=0` and `transport_close_complete`. No non-neutral input operation was sent.
- notes: The previous pre-connection-request timeout was no longer reproduced after changing local name from `swbt-python` to `Pro Controller` and Class of Device from `0x000508` to `0x002508`. That causal link is a strong working inference, not a controlled A/B proof, because the run also depended on manual Switch-side operation timing.

### 2026-07-01: unit_004 pairing / L2CAP timeout before connection request

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-004-pairing-l2cap` branch with uncommitted unit_004 implementation
- adapter: `usb:0`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001` observed by Bumble USB debug log. Previous unit_003 inventory associated `usb:0` with `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used; report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-224227 --log-file .pytest_cache\hardware\unit_004\20260701-224227\pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved running the M3 hardware experiment from Codex. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing attempt, HID control / interrupt channel open wait, and cleanup. Scope excluded input reflection and reconnect.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `advertising_start`, `connection_timeout state=advertising`, error event, and `transport_close_complete`. Trace does not include `connection_request`, `host_connection`, `pairing_start`, `pairing_complete`, or `l2cap_channel_open`.
- artifact: `.pytest_cache\hardware\unit_004\20260701-224227\pairing-l2cap.jsonl`, `.pytest_cache\hardware\unit_004\20260701-224227\pytest-debug.log`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. Report loop did not start and no input report was sent.
- notes: HCI debug log shows BD_ADDR `00:1B:DC:F9:9F:7D/P`, local name `swbt-python`, class of device write, `HCI_WRITE_SCAN_ENABLE_COMMAND` success, and extended inquiry response write. `HCI_WRITE_SECURE_CONNECTIONS_HOST_SUPPORT_COMMAND` returned `UNKNOWN_HCI_COMMAND_ERROR`; the run continued to scan enable afterward. This remains a pre-connection-request failure, not an L2CAP failure.

### 2026-07-01: unit_004 pairing / L2CAP timeout before host connection

- OS: Windows, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `work/unit-004-pairing-l2cap` branch with uncommitted unit_004 implementation
- adapter: `usb:0`
- dongle: not re-recorded in this run. Previous unit_003 inventory associated `usb:0` with CSR8510 A10, `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: not re-recorded in this run. Previous unit_003 inventory recorded WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not recorded
- Switch firmware: not recorded
- report period: not used; report loop did not start because `connected` was not reached
- command / test: `uv run pytest tests\hardware\test_pairing_l2cap.py -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_004\20260701-223511 -q -s`
- approval: manual user-run M3 hardware experiment. Scope included USB Bluetooth dongle open, HID advertising, Switch pairing attempt, HID control / interrupt channel open wait, and cleanup. Scope excluded input reflection and reconnect.
- result: fail, `ConnectionTimeoutError` after 60 seconds. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered`, `hid_device_initialized`, `transport_open_complete`, `advertising_start`, `connection_timeout state=advertising`, error event, and `transport_close_complete`. Trace does not include `host_connection`, `pairing_start`, `pairing_complete`, or `l2cap_channel_open`.
- artifact: `.pytest_cache\hardware\unit_004\20260701-223511\pairing-l2cap.jsonl`
- cleanup: `pad.close(neutral=True)` ran from `finally`; trace recorded `transport_close_complete`. Report loop did not start and no input report was sent.
- notes: This is not yet an L2CAP failure. The observed failure point is before Bumble reports a host connection.

### 2026-07-12: unit_047 / unit_048 Pro Controller 6-axis calibration and gyro reflection

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `fix/issue-69-gyro-calibration` branch
- adapter: `usb:0`, BD_ADDR `00:1B:DC:F9:9F:7D`
- dongle: CSR8510 A10 class device, USB VID:PID `0a12:0001`
- driver: WinUSB
- Python: 3.13.5
- Bumble: 0.0.230
- Switch model / firmware: not recorded
- report period: repository default. Each axis was held for 120 report `0x30` transmissions
- command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-with-accel-calibration-pytest-debug.log --log-file-level=DEBUG -q -s`
- approval: user explicitly approved the hardware test. Scope included `usb:0` adapter open, Pro Controller active reconnect, factory SPI replies, periodic reports, ZL control input, X/Y/Z gyro input, neutral, transport close, and adapter release
- result: pytest pass, `1 passed in 17.99s`; semantic gyro reflection observed-fail. Switch read factory 6-axis calibration as one 24-byte block. Reply contained accel zero/reference `000000000000004000400040` and gyro zero/reference `0000000000003b343b343b34`. Switch sent Enable IMU `0x40` mode `0x02`; trace recorded `imu_enabled=true`. X/Y/Z input reports contained stationary accel `(0,0,4096)` and gyro raw `(1286,0,0)`, `(0,1286,0)`, `(0,0,1286)` respectively. The user observed no Splatoon 3 camera movement. ZL had reflected in the preceding control observation, so the failure is limited to motion input semantics
- artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-with-accel-calibration-pytest-debug.log`
- cleanup: the test sent neutral after ZL and after each gyro axis, then executed `pad.close(neutral=True)`. Trace recorded `transport_close_complete`; adapter was released
- notes: The earlier all-`FF` accel calibration hypothesis is disproved as the sole cause. Calibration, IMU enable state, and outbound report bytes are confirmed. Follow-up compared 8ms/15ms periods, timer step 1/3, Pro horizontal offsets, NXIC user calibration, a published user calibration sample, and identical/varied IMU samples. None produced a repeatable low-speed improvement. NXIC uses the same Int16LE gyro placement, repeats all 3 samples, sends at 125Hz, and uses `0.070 dps/raw`; this supports the implemented packing and conversion. With 15ms reports, three Z samples at raw `+0x05FF` were not reflected, while three samples at `+0x0600` caused fast right rotation. One or two `+0x0600` samples mixed with `+0x05FF` were not reflected. Three `-0x0600` samples caused unstable motion rather than a clear left rotation. These are Switch 2 / Splatoon 3 observations, not a protocol constant or cross-game guarantee. Joy-Con SPI read regression required by Issue #70 remains not run
- additional command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-known-spi-overlay-pytest-debug.log --log-file-level=DEBUG -q -s`
- additional result: pytest pass, `1 passed in 14.43s`; semantic gyro reflection observed-pass for positive Z. A hardware-test-only SPI overlay returned the complete blocks implemented by NXIC at `0x603D`, `0x6080`, `0x6098`, `0x8010`, and `0x8028`. The Switch requested all five blocks and did not request `0x6020` in this handshake. IMU mode was `0x02`; stationary accel `(0,0,4096)` and gyro raw `(0,0,+0x0600)` were sent for 120 reports at 15ms. The user observed a moderate-speed right rotation instead of the earlier very fast rotation
- additional artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-known-spi.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-known-spi-overlay-pytest-debug.log`
- additional cleanup: neutral was sent after ZL and after the positive-Z input. Trace recorded `transport_close_complete`; the adapter was released
- additional notes: the five NXIC blocks are an implementation fact used for this diagnostic, not a factory dump or a stable Pro Controller default. Because the blocks were changed together, this run does not identify which SPI field changed the observed angular speed
- negative-Z command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-known-spi-negative-z-pytest-debug.log --log-file-level=DEBUG -q -s`
- negative-Z result: pytest pass, `1 passed in 14.42s`; semantic gyro reflection observed-fail. The Switch read the same five SPI blocks and enabled IMU mode `0x02`. Stationary accel `(0,0,4096)` and gyro raw `(0,0,-0x0600)` were sent for 120 reports at 15ms; every sample encoded Z as signed Int16LE `00 FA`. The user observed abnormal rotation rather than a stable opposite-direction rotation
- negative-Z artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-known-spi-negative-z.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-known-spi-negative-z-pytest-debug.log`
- negative-Z cleanup: calibrated input was followed by the existing neutral sequence. Trace recorded `transport_close_complete`; the adapter was released
- negative-Z notes: the known SPI set reduced the positive-Z speed but did not make negative-Z behavior symmetric. SPI completeness alone is therefore not a sufficient explanation. A diagnostic that biases gyro zero above zero can distinguish a negative wire-value problem from a signed angular-delta problem, but such a calibration is not a production default
- biased-zero command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-biased-zero-negative-z-pytest-debug.log --log-file-level=DEBUG -q -s`
- biased-zero result: pytest pass, `1 passed in 14.61s`; semantic gyro reflection observed-fail. User calibration at `0x8028` set gyro offset to `(0x4000,0x4000,0x4000)` and scale to `(0x7BE7,0x7BE7,0x7BE7)`. Reports first held calibrated rest raw `(0x4000,0x4000,0x4000)`, then sent `(0x4000,0x4000,0x3A00)` for a Z delta of `-0x0600`, using only non-negative wire values. The user observed very fast unstable camera rotation, unchanged from the signed-negative run
- biased-zero artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-biased-zero-negative-z.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-biased-zero-negative-z-pytest-debug.log`
- biased-zero cleanup: calibrated rest raw was restored for 8 reports before close. The test closed with `neutral=False` to avoid sending raw zero under the artificial offset. Trace recorded `transport_close_complete`; the adapter was released
- biased-zero notes: Linux `hid-nintendo.c` defines the IMU fields as signed 16-bit, calculates the gyro divisor as `scale - offset`, and maps gyro from `raw - offset`; the diagnostic values are internally consistent with that source model. Whether Switch accepted the unusually large user offset remains unverified. The overall run cannot separate rejection of the artificial calibration from failure of the positive-wire hypothesis without a rest-only observation
- biased-rest command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-biased-zero-rest-only-pytest-debug.log --log-file-level=DEBUG -q -s`
- biased-rest result: pytest pass, `1 passed in 14.67s`; semantic rest observed-pass. With the same user calibration offset `(0x4000,0x4000,0x4000)` and scale `(0x7BE7,0x7BE7,0x7BE7)`, every gyro sample remained `(0x4000,0x4000,0x4000)` for the control and 120-report observation windows. The user observed no camera rotation
- biased-rest artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-biased-zero-rest-only.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-biased-zero-rest-only-pytest-debug.log`
- biased-rest cleanup: calibrated rest raw remained active through the final 8-report checkpoint. Trace recorded `transport_close_complete`; the adapter was released
- biased-rest notes: the stable rest plus the preceding motion under the same calibration shows that Switch used the artificial offset sufficiently for this diagnostic. However the large offset makes the Linux-model gyro gain about `0x7BE7 / (0x7BE7 - 0x4000) = 2.07`, so the preceding positive-wire negative-delta run still included a gain confounder
- minimal-bias command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-minimal-bias-negative-z-pytest-debug.log --log-file-level=DEBUG -q -s`
- minimal-bias result: pytest pass, `1 passed in 14.78s`; semantic negative-Z reflection observed-pass. User calibration set gyro offset to `(0x0601,0x0601,0x0601)` and scale to `(0x3BE7,0x3BE7,0x3BE7)`. Reports held rest raw `(0x0601,0x0601,0x0601)`, then sent `(0x0601,0x0601,0x0001)` for a Z delta of `-0x0600`, using only non-negative wire values. After the ZL control completed, the user observed stable left rotation
- minimal-bias artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-minimal-bias-negative-z.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-minimal-bias-negative-z-pytest-debug.log`
- minimal-bias cleanup: calibrated rest raw was restored for 8 reports before close. Trace recorded `transport_close_complete`; the adapter was released
- minimal-bias notes: in this Switch 2 / Splatoon 3 setup, a negative calibrated delta was stable when every wire raw remained non-negative, while a signed-negative wire raw produced unstable motion. This is hardware observation, not a general replacement for the signed Int16LE protocol contract
- centered-symmetric command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-centered-positive-symmetric-z-pytest-debug.log --log-file-level=DEBUG -q -s`
- centered-symmetric result: pytest pass, `1 passed in 18.15s`; semantic gyro reflection observed-fail. User calibration set gyro offset to `(0x4000,0x4000,0x4000)` and scale to `(0x7FFF,0x7FFF,0x7FFF)`. Reports sent Z raw `0x4300`, restored rest `0x4000`, then sent Z raw `0x3D00`; the Linux-model calibrated deltas were approximately `+1536.047` and `-1536.047`. The user observed very fast unstable camera rotation rather than stable right and left rotation
- centered-symmetric artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-centered-positive-symmetric-z.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-centered-positive-symmetric-z-pytest-debug.log`
- centered-symmetric cleanup: calibrated rest raw was restored after each direction. Trace recorded `transport_close_complete`; the adapter was released
- centered-symmetric notes: the maximum signed scale `0x7FFF` is not a usable virtual calibration in this hardware setup. Whether Switch rejects the scale or applies a different internal calculation is unverified; do not promote this calibration to production
- minimal-bias symmetric command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-minimal-bias-symmetric-z-pytest-debug.log --log-file-level=DEBUG -q -s`
- minimal-bias symmetric result: pytest pass, `1 passed in 17.89s`; semantic direction symmetry observed-fail. User calibration set gyro offset to `(0x0601,0x0601,0x0601)` and scale to `(0x3BE7,0x3BE7,0x3BE7)`. Reports sent positive Z raw `(0x0601,0x0601,0x0C01)` for 120 reports, restored calibrated rest `(0x0601,0x0601,0x0601)` for 8 reports, then sent negative Z raw `(0x0601,0x0601,0x0001)` for 120 reports. The user observed left rotation, inertia-like rotation during the transition, then left rotation again; the two equal-magnitude calibrated deltas did not produce opposite directions
- minimal-bias symmetric artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-minimal-bias-symmetric-z.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-minimal-bias-symmetric-z-pytest-debug.log`
- minimal-bias symmetric cleanup: calibrated rest raw was restored after each direction. Trace recorded `transport_close_complete`; the adapter was released
- minimal-bias symmetric notes: the Linux-style `raw - offset` interpretation is insufficient to predict direction in this Switch 2 / Splatoon 3 setup. The transition behavior is a visual observation and does not distinguish game-side inertia from report timing or loss. Do not promote this artificial calibration to production
- quaternion-mode command / test: `uv run pytest tests\hardware\test_input_operations.py::test_switch_gyro_rate_after_active_reconnect_for_manual_reflection -m hardware --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir build\hardware\issue-69-gyro-calibration-20260712 --log-file build\hardware\issue-69-gyro-calibration-20260712\gyro-rate-quaternion-z-pytest-debug.log --log-file-level=DEBUG -q -s`
- quaternion-mode approval: user explicitly approved opening the dedicated `usb:0` CSR8510 A10 / WinUSB adapter, active reconnect with the existing bond, subcommand handling, periodic reports, ZL, symmetric Z gyro input, neutral, transport close, and adapter release. Intentional pairing and advertising were excluded
- quaternion-mode result: pytest pass, `1 passed in 17.99s`; semantic direction symmetry observed-pass. Switch 2 firmware 22.1.0 sent Enable IMU `0x40` mode `0x02`. With production factory calibration, the test sent stationary accel `(0,0,4096)`, positive Z gyro raw `(0,0,409)` for 120 reports, 8 rest reports, then negative Z gyro raw `(0,0,-409)` for 120 reports. The user observed camera left rotation, stop, right rotation, stop in Splatoon 3
- quaternion-mode artifact: `build/hardware/issue-69-gyro-calibration-20260712/active-reconnect-gyro-rate-quaternion-z.jsonl`, `build/hardware/issue-69-gyro-calibration-20260712/gyro-rate-quaternion-z-pytest-debug.log`
- quaternion-mode cleanup: the test restored stationary gyro after each direction and called `pad.close(neutral=True)`. The disconnect request reached its 0.25-second terminal timeout, after which the trace recorded `disconnected` and `transport_close_complete`; the adapter was released. The trace contains no `classic_pairing`, `key_store_update`, `advertising_start`, or `error` event
- quaternion-mode notes: opposite motion for equal-magnitude positive and negative Z, plus stopping during both neutral intervals, confirms mode `0x02` quaternion packing as the cause correction in this Switch 2 / Splatoon 3 setup. Earlier threshold-like and unstable results came from Switch interpreting the legacy 3-sample gyro layout as packing mode 2; artificial SPI calibration is not a production requirement. This observation covers Pro Controller Z rotation only and does not establish Joy-Con axis direction

### 2026-07-01: unit_003 Bumble HID advertising smoke

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/unit-003-bumble-hardware` branch
- adapter: `usb:0`
- dongle: CSR8510 A10, `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not used
- Switch firmware: not used
- report period: not used
- command / test: `uv run pytest tests\hardware\test_bumble_transport.py -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_003\20260701-022335 -q`
- approval: user approved this M2 hardware smoke. Scope included Bumble adapter open, Bumble Device initialization, Classic enable, HID Device initialization, SDP / HID descriptor registration, discoverable / connectable, and close. Scope excluded Switch pairing, L2CAP channel open, subcommand handling, periodic report loop, and input reflection.
- result: pass, `1 passed in 0.52s`. Trace includes `transport_open_start`, `bumble_device_initialized`, `sdp_record_registered` with `hid_descriptor_size=203`, `hid_device_initialized`, `transport_open_complete`, `advertising_start`, and `transport_close_complete`.
- artifact: `.pytest_cache\hardware\unit_003\20260701-022335\bumble-hid-advertising-smoke.jsonl`
- cleanup: test called `BumbleHidTransport.close()` twice in `finally`; trace recorded one `transport_close_complete`. Post-run PnP status for CSR8510 A10 was `OK`.
- notes: `usb:0` is associated with CSR8510 A10 by the pre-run Windows PnP inventory. This run did not pair with a console, open HID channels, receive subcommands, start the periodic report loop, or send input reports.

### 2026-07-01: unit_003 Bumble adapter open / close smoke

- OS: Windows 11, `Windows-11-10.0.26200-SP0`
- environment: Windows PowerShell, `test/unit-003-bumble-hardware` branch
- adapter: `usb:0`
- dongle: CSR8510 A10, `USB\VID_0A12&PID_0001\9&12127A34&0&1`, `Port_#0001.Hub_#0013`
- driver: WinUSB service, libwdi provider, driver version `6.1.7600.16385`, `oem75.inf`
- Python: 3.13.5
- Bumble: 0.0.230
- swbt-python: diagnostics package version `0.1.0`
- Switch model: not used
- Switch firmware: not used
- report period: not used
- command / test: `uv run pytest tests\hardware\test_bumble_transport.py -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_003\20260701-015427 -q`
- approval: user approved Bumble adapter open/close after read-only adapter inventory. Scope excluded Switch pairing, HID advertising, report loop, and input sending.
- result: pass, `1 passed in 0.70s`. Trace includes `transport_open_start`, `transport_open_complete`, and `transport_close_complete`.
- artifact: `.pytest_cache\hardware\unit_003\20260701-015427\bumble-adapter-open-close.jsonl`
- cleanup: test called `BumbleHidTransport.close()` in `finally`; trace recorded `transport_close_complete`.
- notes: `usb:0` is associated with CSR8510 A10 by the pre-run Windows PnP inventory. This run did not initialize Bumble HID Device, enter discoverable / connectable state, pair with a console, or open HID channels.

## Marker Result Mapping

| marker | 記録する結果 | 実行条件 |
|---|---|---|
| `@pytest.mark.bumble` | adapter open、Classic、HID advertising、cleanup | 明示承認、専用 USB Bluetooth dongle、adapter string、cleanup plan が揃った場合だけ実行する |
| `@pytest.mark.hardware` | pairing、L2CAP、subcommand sequence、input reflection、cleanup | 明示承認、対象機器、adapter string、report loop と入力操作の範囲、cleanup plan が揃った場合だけ実行する |

## Recording Rules

- `approval` には、会話上の明示承認、adapter open、HID advertising、pairing、report loop、input operation、cleanup の実行範囲を書く。
- `command / test` には、実行した command を省略せず書く。
- `result` には、成功、失敗、未実行を分けて書く。原因が未確定なら推測を書かない。
- `artifact` には、diagnostics trace、pytest log、手元記録など、後から結果を辿れる場所を書く。
- `cleanup` には、neutral、report loop stop、transport close、adapter release など実施した後始末と結果を書く。
- link key、secret、個人環境に固有の token は記録しない。
