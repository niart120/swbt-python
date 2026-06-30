# Hardware Test Log

この文書は、Bumble adapter と対象機器に依存する観測を記録する正本である。

実機観測は、OS、driver、dongle、adapter string、Bumble version、Python version、Switch model / firmware に依存する。ここに記録した結果は、その条件での観測であり、別構成での保証には使わない。

## Current Status

- Hardware run: 2026-07-01 に CSR8510 A10 / WinUSB / `usb:0` で M2 advertising smoke pass
- Bumble adapter run: adapter open、Bumble Device 初期化、Classic HID 初期化、SDP / HID descriptor 登録、discoverable / connectable、close を記録済み
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
| Windows | CSR8510 A10 | WinUSB / libwdi 6.1.7600.16385 | `usb:0` | 未使用 | 未使用 | 未実行 | 未実行 | 未実行 | 未実行 | 2026-07-01 M2 advertising smoke | 2026-07-01 | Bumble Device 生成、Classic HID 初期化、SDP / HID descriptor 登録、discoverable / connectable、close に成功。Switch pairing 以降は未実行 |
| Linux | 未検証 | libusb 想定 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期保証対象に含めるか未決 |
| macOS | 未検証 | 未検証 | 未記録 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | 未検証 | template only | 2026-06-30 | 初期検証対象外 |

## Run Entries

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
