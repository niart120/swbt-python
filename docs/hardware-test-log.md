# Hardware Test Log

この文書は、Bumble adapter と対象機器に依存する観測を記録する正本である。

実機観測は、OS、driver、dongle、adapter string、Bumble version、Python version、Switch model / firmware に依存する。ここに記録した結果は、その条件での観測であり、別構成での保証には使わない。

## Current Status

- Hardware run: 未記録
- Bumble adapter run: 未記録
- Pairing run: 未記録
- Input reflection run: 未記録

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

| OS | Bluetooth dongle | Driver | Adapter | Switch model | Firmware | Pairing | L2CAP | Subcommands | Input reflected | Result source | Last updated | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Windows | 未検証 | WinUSB 想定 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期想定構成。実行結果は未記録 |
| Linux | 未検証 | libusb 想定 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期保証対象に含めるか未決 |
| macOS | 未検証 | 未検証 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期検証対象外 |

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
