# Adapter Discovery API 仕様書

## 1. 概要

### 1.1 目的

Python 利用者が `SwitchGamepad(adapter=...)` に渡せる USB Bluetooth adapter 候補を、adapter open なしで確認できる公開 API を追加する。

API 名は `list_adapters()`、戻り値の要素は `AdapterInfo` とする。この API が列挙するのは PC 側の専用 USB Bluetooth dongle 候補であり、Nintendo Switch 本体や周辺の Bluetooth host を探索する API ではない。

### 1.2 起点 / source

| source | 内容 | path |
|---|---|---|
| user request | 接続可能なデバイスを列挙する API を検討する | conversation |
| user scope | `list_adapters()` / `AdapterInfo` を仮名とし、Switch 本体ではなく `SwitchGamepad(adapter=...)` に渡す USB Bluetooth adapter 候補の列挙とする | conversation |
| public API design | 公開 API は `swbt` module root から import でき、Bumble の詳細を public API に露出しない | `spec/initial/api.md` |
| public error policy | no-open discovery の列挙不能は adapter open 失敗ではないため、public 例外 `AdapterDiscoveryError` として分ける | conversation |
| Bumble transport design | `adapter` は Bumble transport に渡す adapter moniker。既存例は `usb:0` | `spec/initial/api.md`, `spec/initial/transport-bumble.md` |
| no-open CLI | `swbt-probe adapters --json` は `opens_adapter=false` を返し、adapter を開かない診断境界として存在する | `src/swbt/probe.py`, `tests/unit/test_probe_cli.py` |
| hardware guide | adapter 名確認は `swbt-probe adapters --json`。この command は pairing、HID advertising、report loop を開始しない | `docs/hardware.md` |
| local Bumble implementation | `usb_probe.py` は libusb の device iterator から候補名、VID/PID、serial、manufacturer、product を表示する | `.venv/Lib/site-packages/bumble/apps/usb_probe.py` |
| local Bumble implementation | `open_usb_transport()` は endpoint 探索後に `found.open()` へ進むため、adapter open 境界である | `.venv/Lib/site-packages/bumble/transport/usb.py` |
| previous work unit | Linux/macOS experimental 対応では `swbt-probe adapters --json` の no-open 境界を診断入口として扱った | `spec/complete/unit_026/LINUX_MACOS_ADAPTER_EXPERIMENTAL.md` |

### 1.3 use case

| actor / boundary | 入力または状態 | 期待する観測結果 | 制約 |
|---|---|---|---|
| Python user | `from swbt import list_adapters` して呼び出す | `SwitchGamepad(adapter=info.name)` に渡せる候補を取得できる | Switch 本体は列挙しない |
| Python user | adapter が 0 件 | 空 tuple を受け取る | 「adapter なし」と「列挙不能」は区別する |
| Python user | 同じ VID/PID の dongle が複数ある | `usb:N` と VID/PID alias、可能なら serial alias で候補を区別できる | `usb:N` の順序は USB 接続状態で変わり得る |
| CLI user | `swbt-probe adapters --json` | API と同じ候補情報を機械処理できる JSON で確認できる | adapter open、power on、advertising、pairing、report loop は行わない |
| maintainer | unit test | 実 USB device なしで no-open 契約と JSON 形状を固定できる | 実USB列挙は必須 gate にしない |
| hardware tester | 承認済みの手動確認 | 実 USB device の列挙結果を characterization として確認できる | adapter open や Switch-facing 動作へ進まない |

## 2. 対象範囲

- `swbt` module root から import する公開 API として、`list_adapters()` と `AdapterInfo` を追加する仕様。
- `AdapterInfo.name` を `SwitchGamepad(adapter=...)` に渡せる adapter moniker として扱う仕様。
- Bumble / libusb の object 型や callback 型を公開 API に出さない境界。
- 実 USB device を開かずに、USB descriptor と Bumble transport name 候補を取得する no-open 契約。
- 既存 `swbt-probe adapters --json` を `list_adapters()` の CLI 表面として再利用する方向性。
- 単体テストと CLI regression を中心にした TDD Test List。
- 実 USB device を使う列挙確認を、承認が必要な `bumble` / `hardware` 境界として分ける方針。

## 3. 対象外

- Nintendo Switch 本体、pairing 待ちの host、周辺 Bluetooth 機器の探索。
- USB Bluetooth dongle を Bumble transport として開くこと。
- `open_transport()`、`open_usb_transport()`、`BumbleHidTransport.open()`、`SwitchGamepad.open()`、`connect()`、`pair()`、`reconnect()` の呼び出し。
- Bluetooth controller の `power_on`。
- HID Device advertising、pairing、HID control / interrupt channel open。
- periodic input report loop。
- Switch-facing output report / subcommand handling。
- `@pytest.mark.bumble` / `@pytest.mark.hardware` を標準 gate に入れること。
- OS 別の driver 修復、udev rule 作成、Zadig 操作、macOS NVRAM 設定。
- 接続成功や Switch 互換性を `list_adapters()` の戻り値だけで保証すること。

## 4. 関連 docs

- `spec/initial/README.md`
- `spec/initial/api.md`
- `spec/initial/transport-bumble.md`
- `spec/initial/testing.md`
- `spec/initial/risks.md`
- `spec/complete/unit_008/M7_PACKAGING_EXAMPLES_CLI.md`
- `spec/complete/unit_026/LINUX_MACOS_ADAPTER_EXPERIMENTAL.md`
- `docs/hardware.md`
- `src/swbt/probe.py`
- `tests/unit/test_probe_cli.py`
- `.venv/Lib/site-packages/bumble/apps/usb_probe.py`
- `.venv/Lib/site-packages/bumble/transport/usb.py`

## 5. 根拠監査

| 項目 | 要否 | 状態 | 根拠 / 理由 |
|---|---|---|---|
| Switch HID / report bytes | not applicable | not applicable | この unit は Switch HID report、subcommand、SPI、rumble、report period を変更しない |
| Bumble / transport | required | reviewed-for-spec | adapter moniker と USB 列挙、transport open の境界をローカル Bumble 実装で確認した |
| OS / driver / adapter | required | reviewed-for-spec | public docs と既存 hardware observation を確認した。ただしこの turn では実 USB device を列挙していない |

### 5.1 監査結果

| 項目 | 値 / 判断 | 根拠分類 | source | status |
|---|---|---|---|---|
| 公開 API 境界 | `swbt` module root から import でき、Bumble object 型を public API に出さない | source fact | `spec/initial/api.md` | done |
| adapter 引数 | `SwitchGamepad(adapter="usb:0")` は Bumble transport に渡す adapter moniker | source fact | `spec/initial/api.md`, `spec/initial/transport-bumble.md` | done |
| CLI no-open | `_run_adapters()` は `list_adapters()` 由来の `adapters` 配列と `opens_adapter=false` を返し、`SwitchGamepad` を作らない | implementation fact | `src/swbt/probe.py` | done |
| CLI regression | `test_swbt_probe_adapters_json_reports_no_open_environment` は `adapters` 配列、VID/PID の int / hex 併記、`opens_adapter=false` を確認する | implementation fact | `tests/unit/test_probe_cli.py` | done |
| Hardware Guide の no-open 説明 | `swbt-probe adapters --json` は pairing、HID advertising、report loop を開始しない | source fact | `docs/hardware.md` | done |
| Bumble USB 列挙 | `usb_probe.py` は `load_libusb()`、`usb1.USBContext()`、`getDeviceIterator(skip_on_error=True)`、descriptor getter で候補情報を作る | source fact | `.venv/Lib/site-packages/bumble/apps/usb_probe.py` | done |
| Bumble transport name | HCI device には `usb:N`、全 USB device には `usb:VID:PID`、重複時は `#index`、serial があれば `/serial` の alias を作る | source fact | `.venv/Lib/site-packages/bumble/apps/usb_probe.py` | done |
| Bumble HCI 判定 | device class または interface class が Wireless Controller / RF Controller / Bluetooth primary controller の tuple に一致するかを見る | source fact | `.venv/Lib/site-packages/bumble/apps/usb_probe.py` | done |
| Bumble open 境界 | `open_usb_transport()` は `context.open()`、endpoint 探索、`found.open()`、kernel driver auto-detach、configuration 設定へ進む | source fact | `.venv/Lib/site-packages/bumble/transport/usb.py` | done |
| Windows 確認済み構成 | Windows 11 / CSR8510 A10 / WinUSB / Switch 2 firmware 22.1.0 で pairing、reconnect、入力反映が確認済み | hardware observation | `docs/hardware.md` | done |
| macOS 確認済み構成 | macOS 15.7.7 / CSR8510 A10 / Homebrew libusb / Bumble 0.0.230 / Python 3.12.13 / `usb:0` で pairing、active reconnect、入力反映が確認済み | hardware observation | `docs/hardware.md` | done |
| Linux 状態 | Linux の adapter listing、adapter open、HID advertising、pairing、reconnect、input reflection は未確認 | hardware observation | `docs/hardware.md` | done |
| no-open API の意味 | libusb による USB device enumeration は行うが、Bumble transport open、controller power on、HID advertising へ進まない | inference | Bumble `usb_probe.py` と `open_usb_transport()` の差分 | spec decision |
| `AdapterInfo` の候補性 | HCI class の USB device でも driver、権限、OS stack 競合、Switch 互換性は別問題 | inference | `docs/hardware.md`, `spec/initial/transport-bumble.md` | spec decision |
| 列挙結果が接続成功を保証する | adapter 候補が返れば Switch と接続できる | unverified hypothesis | none | not a contract |
| descriptor getter の OS 差 | manufacturer、product、serial の取得可否は OS、driver、permission、device に依存する | unverified hypothesis | local source inspection only | keep-optional |

### 5.2 未解決事項

- `usb1.USBContext()` と descriptor getter が各 OS でどの程度の権限を要求するかは、Windows / CSR8510 A10 / WinUSB / `usb:0` では no-open discovery として確認した。macOS / Linux はこの unit では実機確認しない。
- `usb_probe.py` と同じ HCI 判定で、swbt-python が実際に扱える adapter 候補を過不足なく列挙できるかは未検証である。
- serial number を読めない device では、VID/PID duplicate の識別が `#index` に寄る。この順序は接続状態で変わり得る。
- macOS / Linux の実USB列挙結果は、この unit の必須検証には含めない。

## 6. 振る舞い仕様

| 振る舞い | 入力・状態 | 期待結果 | 備考 |
|---|---|---|---|
| API import | `from swbt import list_adapters, AdapterInfo` | import できる | `swbt` module root の公開 API とする |
| public error import | `from swbt import AdapterDiscoveryError` | import できる | no-open discovery 専用の public 例外とする |
| API result shape | `list_adapters()` | `tuple[AdapterInfo, ...]` を返す | 呼び出し側が immutable snapshot として扱える |
| adapter target | 返却された `AdapterInfo.name` | `SwitchGamepad(adapter=info.name)` に渡せる文字列 | Switch 本体の列挙ではない |
| no-open contract | `list_adapters()` | adapter open、power on、advertising、pairing、report loop を行わない | libusb enumeration は行う |
| no devices | HCI 候補が 0 件 | 空 tuple を返す | 例外にしない |
| discovery failure | libusb load または USBContext 作成、iteration が開始できない | `AdapterDiscoveryError` を投げる | adapter 0 件と区別する |
| descriptor failure | serial、manufacturer、product の取得だけ失敗 | 該当 field を `None` にして候補全体は残す | Bumble `usb_probe.py` と同じく descriptor USBError を候補落ちにしない |
| HCI filter | default call | Bluetooth HCI class と判定できる device だけを返す | unknown class の forced mode は初期対象外 |
| aliases | HCI device | `usb:N`、VID/PID、重複 index、serial alias を表現する | alias は `AdapterInfo.aliases` に保持する |
| unstable index | USB 接続状態が変わる | `usb:N` の安定性を保証しない | docs と docstring に書く |
| CLI JSON | `swbt-probe adapters --json` | `opens_adapter=false` と adapters 配列を出す | `candidate_adapters` は維持しない。`AdapterInfo` 相当の構造化 JSON を正本にする |
| CLI text | `swbt-probe adapters` | no-open 境界、候補名、主要 metadata を表示する | 実 USB 列挙が失敗した場合は setup 問題として表示する |

## 7. API 案

```python
@dataclass(frozen=True, slots=True)
class AdapterInfo:
    name: str
    aliases: tuple[str, ...]
    vendor_id: int | None
    product_id: int | None
    manufacturer: str | None
    product: str | None
    serial_number: str | None
    bus_number: int | None
    device_address: int | None
    port_numbers: tuple[int, ...]
    is_bluetooth_hci: bool


class AdapterDiscoveryError(SwbtError):
    ...


def list_adapters() -> tuple[AdapterInfo, ...]: ...
```

`name` は最初に利用者へ提示する adapter moniker である。HCI class device では `usb:0` のような index moniker を優先する。`aliases` には `usb:VID:PID`、`usb:VID:PID#index`、`usb:VID:PID/serial` のような別指定を入れる。`aliases` に `name` を重複して入れない。

`vendor_id` と `product_id` は Python API では `int` とする。CLI JSON でも同じ `int` field を正とし、人間が USB ID と照合しやすいように `vendor_id_hex` / `product_id_hex` を 4 桁大文字 hex 文字列で併記する。

`AdapterDiscoveryError` は public 例外として `swbt` module root から公開する。候補 0 件ではなく、libusb load、USB context 作成、device iteration などの列挙処理自体が成立しない場合に使う。`TransportOpenError` は adapter open の失敗用なので、no-open API の列挙失敗には流用しない。

`AdapterDiscoveryError` は `raise ... from exc` で元例外を保持する。追加 field は `platform`、`backend="bumble-usb"`、`libusb_available: bool | None`、`bumble_version: str | None` に限定し、libusb や Bumble の生 object は public API に出さない。

## 8. TDD Test List

| status | item | type | layer | hardware | notes |
|---|---|---|---|---|---|
| green | `list_adapters()` と `AdapterInfo` を `swbt` module root から import できる | new | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。Bumble object 型を公開しない |
| green | `AdapterDiscoveryError` を `swbt` module root から import でき、`SwbtError` の派生として扱える | new | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。no-open discovery の public 例外として固定する |
| green | fake USB enumerator が 1 件の Bluetooth HCI device を返すと、`list_adapters()` が `AdapterInfo(name="usb:0")` を返す | new | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。実USB列挙を使わない |
| green | fake USB enumerator の HCI device から VID/PID、manufacturer、product、serial、bus/device 情報を `AdapterInfo` へ写す | new | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。descriptor getter は fake で観測する |
| green | 同じ VID/PID の HCI device が複数ある場合、`aliases` に duplicate index または serial alias が入る | edge | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。`usb_probe.py` の重複 moniker 生成を仕様化する |
| green | serial、manufacturer、product の取得だけが失敗しても、該当 field を `None` にして候補を返す | edge | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。descriptor access 失敗を列挙失敗にしない |
| green | HCI class ではない USB device は default の `list_adapters()` に含めない | new | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。forced mode や unknown USB device は初期対象外 |
| green | HCI 候補が 0 件の場合、`list_adapters()` は空 tuple を返す | edge | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。no devices と discovery failure を分ける |
| green | libusb load または USBContext 初期化が失敗した場合、`AdapterDiscoveryError` を投げる | edge | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で確認。元例外と public metadata を保持し、`TransportOpenError` にしない |
| green | `list_adapters()` は `open_transport()`、`open_usb_transport()`、`device.open()`、`SwitchGamepad` を呼ばない | regression | unit | no | `uv run pytest tests/unit/test_adapter_discovery.py -q` で spy 確認。monkeypatch / spy で no-open 契約を固定する |
| green | `swbt-probe adapters --json` は `list_adapters()` の結果を `adapters` 配列に出し、`opens_adapter=false` を維持する | regression | unit | no | `uv run pytest tests/unit/test_probe_cli.py -q` で確認。`candidate_adapters` は出さない。VID/PID は int と 4 桁大文字 hex を併記する |
| green | `swbt-probe adapters --json` は discovery failure を adapter open 失敗として報告しない | edge | unit | no | `uv run pytest tests/unit/test_probe_cli.py -q` で確認。exit code `1`、`status="discovery_error"`、`error.type="AdapterDiscoveryError"` を返す |
| green | `swbt-probe adapters` の human output が no-open 境界と候補 adapter name を表示する | regression | unit | no | `uv run pytest tests/unit/test_probe_cli.py -q` で確認。help text の no-open 文言も維持する |
| green | public API docs と docstring が `AdapterDiscoveryError` を候補 0 件ではなく列挙不能の例外として説明する | new | unit | no | `uv run pytest tests/unit/test_public_api_docstrings.py tests/unit/test_public_docs.py::test_api_doc_covers_top_level_public_exports_and_methods tests/unit/test_package_import.py -q` で確認 |
| green | Windows で `uv run swbt-probe adapters --json` を実 USB dongle ありで実行する | characterization | bumble | yes | 2026-07-05 に承認済み範囲で実行。CSR8510 A10 / `usb:0` を検出し、`opens_adapter=false`、`manufacturer=null`、`serial_number=null` を確認。adapter open はしていない |
| deferred | macOS で `uv run swbt-probe adapters --json` を実 USB dongle ありで実行する | characterization | bumble | yes | 実行する場合は libusb path と OS Bluetooth stack 状態を記録する |
| deferred | Linux で `uv run swbt-probe adapters --json` を実 USB dongle ありで実行する | characterization | bumble | yes | Linux は adapter listing も未確認。udev / BlueZ 状態を記録する |
| green | `list_adapters()` で返った adapter を `SwitchGamepad(adapter=...)` で open できるか確認する | characterization | bumble | yes | 2026-07-05 に承認済みの open-only smoke で `usb:0` を確認。`transport_open_complete` と `transport_close_complete` を記録し、`advertising_start` と `host_connection` は記録しなかった。HID advertising、pairing、report loop、入力送信はしていない |

## 9. 設計メモ

- API 名に `device` を入れない。`device` は Switch 本体、仮想 controller、USB dongle のどれにも読めるため、公開名は `adapter` を使う。
- `list_adapters()` は「接続可能な Switch」を探す関数ではない。`SwitchGamepad(adapter=...)` の入力候補を返す関数である。
- `list_adapters()` の no-open 契約は「USB に一切触れない」ではない。libusb の列挙と descriptor 読み取りは行うが、Bumble transport として device handle を開かない。
- `swbt-probe adapters --json` は `list_adapters()` 由来の `adapters` 配列と環境情報を返す。unit 着手前の固定候補 `candidate_adapters=["usb:0"]` は維持しない。`opens_adapter=false` は no-open 契約として維持する。
- `usb:N` は短く便利だが、接続順や他の dongle に影響される。利用者向け docs では、`serial_number` が取れる場合に serial alias を永続的な指定として推奨する。serial を取れない同一 VID/PID 複数台では、`usb:N` と duplicate index は接続状態で変わる診断用識別子として扱う。
- `AdapterInfo` は Bumble の device object を保持しない。戻り値は文字列、数値、文字列 tuple だけにする。
- `AdapterDiscoveryError` は public API とする。docstring、root export、CLI のエラー表示を同じ unit で固定する。
- 実 USB 列挙は adapter open ではないが、OS driver と libusb permission に依存する。標準 gate では fake enumerator の unit test を先に固定し、実 USB は characterization に分ける。
- `usb_probe.py` は HCI class ではない USB device にも transport name を出すが、swbt-python の初期 API は HCI class と判定できる adapter だけを返す。unknown class の forced mode は、必要性が出た時点で別 unit に分ける。
- `docs/hardware.md` の troubleshooting では、`adapters=[]`、`AdapterDiscoveryError`、候補は出るが `SwitchGamepad(adapter=...)` で open できない状態を別症状として説明する。

## 10. 対象ファイル

### 10.1 この unit で編集したファイル

| path | change | 内容 |
|---|---|---|
| `src/swbt/__init__.py` | modify | `list_adapters`、`AdapterInfo`、`AdapterDiscoveryError` を公開する |
| `src/swbt/adapter_discovery.py` | new | no-open adapter 列挙 API の実装 |
| `src/swbt/transport/_bumble_usb_devices.py` | new | Bumble / usb1 による no-open USB device enumeration 境界 |
| `src/swbt/errors.py` | modify | `AdapterDiscoveryError` を public 例外として追加する |
| `src/swbt/probe.py` | modify | `swbt-probe adapters` を `list_adapters()` ベースへ寄せる |
| `tests/unit/test_adapter_discovery.py` | new | fake USB enumerator による API unit tests |
| `tests/unit/test_probe_cli.py` | modify | `swbt-probe adapters --json` の no-open regression を更新する |
| `tests/unit/test_package_import.py` | modify | `swbt.__all__` の public export を更新する |
| `tests/unit/test_public_api_docstrings.py` | modify | `AdapterInfo` / `AdapterDiscoveryError` / `list_adapters()` の docstring contract を固定する |
| `tests/unit/test_public_docs.py` | modify | hardware docs の adapter discovery 境界を固定する |
| `spec/initial/api.md` | modify | adapter discovery API を正本へ反映する |
| `spec/initial/transport-bumble.md` | modify | adapter discovery と adapter open 境界を追記する |
| `docs/api.md` | modify | public API docs へ adapter discovery を追加する |
| `docs/hardware.md` | modify | `list_adapters()` と `swbt-probe adapters` の使い分けを追記する |
| `spec/complete/unit_027/ADAPTER_DISCOVERY_API.md` | moved | TDD 結果、検証、完了境界を更新して complete へ移動する |

## 11. 検証

| command | result | notes |
|---|---|---|
| `uv run pytest tests/unit/test_adapter_discovery.py -q` | pass | public import、fake USB enumerator、metadata、alias、descriptor fallback、HCI filter、0 件時の空 tuple、discovery failure、no-open spy を確認。10 passed |
| `uv run pytest tests/unit/test_probe_cli.py -q` | pass | `swbt-probe adapters` の JSON success / discovery error、human output、既存 help / pair 境界を確認。7 passed |
| `uv run pytest tests/unit/test_public_api_docstrings.py tests/unit/test_public_docs.py::test_api_doc_covers_top_level_public_exports_and_methods tests/unit/test_package_import.py -q` | pass | adapter discovery の public export、API docs、docstring を確認。4 passed |
| `uv run ruff format --check .` | pass | 76 files already formatted |
| `uv run ruff check .` | pass | All checks passed |
| `uv run ty check --no-progress` | pass | All checks passed |
| `uv run pytest tests/unit -q` | pass | 243 passed |
| `uv run pytest tests/integration -q` | pass | 69 passed |
| `uv build` | pass | `dist\swbt_python-0.1.1.tar.gz` と `dist\swbt_python-0.1.1-py3-none-any.whl` を生成。`dist/` は gitignore 対象 |
| `uv run swbt-probe adapters --json` | pass | 2026-07-05 に Windows / CSR8510 A10 / `usb:0` で実行。`opens_adapter=false`、`aliases=["usb:0A12:0001"]`、`manufacturer=null`、`product="CSR8510 A10"`、`serial_number=null` を確認 |
| `uv run pytest tests\hardware\test_context_manager_resource_scope.py::test_switch_gamepad_open_only_does_not_start_advertising_on_bumble -m bumble --swbt-bumble-adapter usb:0 --swbt-hardware-artifact-dir .pytest_cache\hardware\unit_027\20260705-open-only -q -s` | pass | 2026-07-05 に承認済み範囲で実行。`1 passed in 0.30s`。trace は `transport_open_complete` と `transport_close_complete` を記録し、`advertising_start` と `host_connection` は記録しなかった |
| `uv run pytest -m bumble` | not run | 承認範囲を no-open discovery と open-only smoke に限定したため、bumble marker 全体は実行しない |
| `uv run pytest -m hardware` | not run | Switch-facing 動作をこの unit の必須条件にしない。HID advertising、pairing、report loop、入力送信は未実行 |

## 12. 実機実行条件

| 項目 | 内容 |
|---|---|
| 実機要否 | Python 実装の単体テストでは不要。実 USB 列挙と open-only smoke の characterization では必要 |
| 承認範囲 | 2026-07-05 にユーザが `usb:0`、no-open discovery、open-only smoke を承認した。範囲は USB descriptor listing と Bumble adapter open / close まで。HID advertising、Switch pairing、report loop、入力送信は対象外 |
| adapter | 2026-07-05 の実行では `usb:0`。文書例としての `usb:0` は固定値扱いしない |
| 実行遮断 | 環境変数による遮断は採用しない。明示承認、対象 adapter、command、cleanup plan で管理する |
| log / artifact | `spec/hardware-test-log.md` に記録済み。open-only smoke artifact は `.pytest_cache\hardware\unit_027\20260705-open-only\resource-open-only.jsonl` |
| cleanup | open-only smoke は `pad.close(neutral=True)` を `finally` で実行し、trace に `transport_close_complete` を記録した。no-open discovery は adapter open、advertising、pairing、report loop を発生させていない |

## 13. 先送り事項

- 実 USB dongle ありの macOS / Linux 列挙結果。
- Windows 以外で `list_adapters()` の結果を `SwitchGamepad(adapter=...)` で open できるかの characterization。
- Unit 027 の範囲を超える HID advertising、pairing、report loop、入力送信の実機確認。

## 14. チェックリスト

- [x] 対象範囲と対象外を確認した
- [x] `Switch` 本体の列挙ではなく USB Bluetooth adapter 候補の列挙であることを明記した
- [x] no-open 契約を adapter open、power on、HID advertising、pairing、report loop と分けて記録した
- [x] Bumble / libusb / OS driver の根拠を分類して記録した
- [x] TDD Test List を観測可能な振る舞いで作成した
- [x] `list_adapters()`、`AdapterInfo`、`AdapterDiscoveryError` を public API として実装した
- [x] `swbt-probe adapters` を `list_adapters()` ベースへ更新した
- [x] public docs と initial docs へ adapter discovery 境界を反映した
- [x] unit / integration / static gate を実行した
- [x] 実 USB 列挙を `bumble` / `hardware` 承認境界として分けた
- [x] Windows / CSR8510 A10 / `usb:0` で承認済み no-open discovery と open-only smoke を記録した
- [x] 検証結果または未実行理由を記録した
