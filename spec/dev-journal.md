# Dev Journal

swbt-python の設計観測、未解決事項、先送り判断の記録。

## 2026-07-26: VID:PID 33FA:0010 の HCI extended-features 応答

### 現状

Windows 11 / WinUSB / libwdi / Bumble 0.0.233 で検出した `33FA:0010` は、Bumble の `Read Local Extended Features` (`0x1004`) に対する応答を event length `0x01` として返し、通常の `power_on()` を停止させた。

### 観察

実験用に `0x1004` の対応判定を抑止すると、Bumble は既存の `0x1003` 代替経路を使い、HID advertising、fresh pairing、protocol ready、Button A の Switch UI 反映、neutral close まで成功した。active reconnect は同条件で2回、`host_connection` 後かつ L2CAP 前に Switch reason `19` で切断された。実験用コードは main に取り込まない。

### 方針

この adapter を正式対応にしない。再検討する場合は、Bumble の upstream driver / quirk として扱える根拠、または複数個体・別 OS/driver での再現を先に集める。観測 artifact と実行条件は `spec/hardware-test-log.md` を正本とする。
