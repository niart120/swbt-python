"""Public Markdown documentation checks."""

from pathlib import Path

import swbt

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DOC_INDEX = DOCS / "index.md"
API_DOC = DOCS / "api.md"
USAGE_DOC = DOCS / "usage.md"
HARDWARE_DOC = DOCS / "hardware.md"
AGENT_BRIEF = DOCS / "agent-brief.md"
REARCHITECTURE_OVERVIEW = ROOT / "spec" / "rearchitecture" / "01-design-change-overview.md"
REARCHITECTURE_POLICY = ROOT / "spec" / "rearchitecture" / "03-public-api-config-profile.md"
UNIT_038_SPEC = (
    ROOT / "spec" / "complete" / "unit_038" / "REARCHITECTURE_DECISION_BOUNDARY_TESTS.md"
)
PUBLIC_DOCS = (DOC_INDEX, API_DOC, USAGE_DOC, HARDWARE_DOC, AGENT_BRIEF)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_docs_files_exist() -> None:
    for path in PUBLIC_DOCS:
        assert path.is_file(), f"missing public docs file: {path}"


def test_api_doc_covers_top_level_public_exports_and_methods() -> None:
    text = _read(API_DOC)

    for exported_name in swbt.__all__:
        assert f"`{exported_name}`" in text

    for token in (
        "`open()`",
        "`close(neutral=True)`",
        "`pair(timeout=None)`",
        "`reconnect(timeout=None)`",
        "`try_reconnect(timeout=None)`",
        "`connect(timeout=None, allow_pairing=False)`",
        "`try_connect(timeout=None, allow_pairing=False)`",
        "`press(*buttons)`",
        "`release(*buttons)`",
        "`tap(*buttons, duration=0.08)`",
        "`neutral()`",
        "`apply(state)`",
        "`sticks(left=None, right=None)`",
        "`lstick(stick)`",
        "`rstick(stick)`",
        "`imu(*frames)`",
        "`snapshot()`",
        "`status()`",
        "`Stick.tilt(x, y)`",
        "`Stick.up(amount=1.0)`",
        "`Stick.down(amount=1.0)`",
        "`Stick.left(amount=1.0)`",
        "`Stick.right(amount=1.0)`",
        "`IMUFrame.raw(accel=None, gyro=None)`",
        "`IMUFrame.gyro(x=0, y=0, z=0)`",
        "`IMUFrame.accel(x=0, y=0, z=0)`",
        "`IMUFrame.with_gyro(x=0, y=0, z=0)`",
        "`IMUFrame.with_accel(x=0, y=0, z=0)`",
        "`InputState.with_imu(...)`",
        "`InputState.with_gyro(...)`",
        "`InputState.with_accel(...)`",
        "state update API",
        "action API",
        "complete state",
        "即時送信を保証しない",
        "接続済みを要求",
        "`ProController`、`JoyConL`、`JoyConR` が生成用の concrete controller",
        "`JoyConL` と `JoyConR` は単体 Joy-Con L/R 相当の concrete controller",
        "left = JoyConL(",
        "right = JoyConR(",
        "await left.tap(Button.SR, Button.SL)",
        "片側 profile が持たない入力は `UnsupportedInputError`",
        "await left.tap(Button.SR, Button.SL)",
        "`JoyConPair` は public API にありません",
        "Switch UI で Joy-Con として登録",
        "Joy-Con R、reconnect",
        "`None` は controller profile の既定周期",
        "表示名は concrete controller class が内部 profile から選びます",
    ):
        assert token in text

    assert "set_input" not in text
    assert "Bumble 型や transport protocol を public API に露出" in text
    for stale_token in (
        "`HidDeviceTransport` | custom transport",
        "`BondedPeer` | transport",
        "`DisconnectRequestResult` | remote disconnect request",
        "## Transport Extension Point",
        "custom transport は",
        "concrete controller の `transport=...`",
        "custom transport を注入",
    ):
        assert stale_token not in text


def test_usage_doc_covers_connection_input_neutral_and_diagnostics_examples() -> None:
    text = _read(USAGE_DOC)

    for token in (
        "allow_pairing=True",
        "await pad.pair(timeout=30.0)",
        "await pad.reconnect(timeout=10.0)",
        "await pad.try_connect(",
        "await pad.try_reconnect(",
        'key_store_path="switch-bond.json"',
        'key_store_path="switch-2-fw-22-1-0.json"',
        "await pad.tap(Button.A)",
        "await pad.press(Button.ZL)",
        "await pad.press(Button.L, Button.R)",
        "await pad.release(Button.L, Button.R)",
        "await pad.lstick(Stick.up())",
        "await pad.lstick(Stick.up(0.5))",
        "await pad.rstick(Stick.right())",
        "await pad.sticks(left=Stick.tilt(",
        "await pad.imu(IMUFrame.gyro(100, 0, 0))",
        "IMUFrame.accel(0, 0, 4096).with_gyro(100, 0, 0)",
        ".with_accel((0, 0, 4096))",
        ".with_gyro((100, 0, 0))",
        "InputState.neutral().with_buttons",
        "await pad.apply(state)",
        "await pad.neutral()",
        "close(neutral=True)",
        "## Single Joy-Con L/R",
        "JoyConL(...)",
        "JoyConR(...)",
        'key_store_path="switch-left-joycon-bond.json"',
        'key_store_path="switch-right-joycon-bond.json"',
        "await left.tap(Button.SR, Button.SL)",
        "`UnsupportedInputError`",
        "await left.tap(Button.SR, Button.SL)",
        "`JoyConPair` は未実装",
        "Switch UI で Joy-Con として登録",
        "Joy-Con R、reconnect",
        "DiagnosticsConfig(trace_writer=trace)",
        "pad.status()",
        "即時送信を保証しません",
        "同一 HID report に入る保証はありません",
    ):
        assert token in text

    assert "set_input" not in text
    assert "hold(" not in text
    assert "sequence(" not in text
    assert "send_current_input" not in text
    assert "await pad.gyro(" not in text
    assert "await pad.accel(" not in text


def test_hardware_doc_separates_confirmed_unconfirmed_and_troubleshooting() -> None:
    text = _read(HARDWARE_DOC)

    for token in (
        "Python 3.12",
        "専用 USB Bluetooth dongle",
        "Windows USB & Driver Setup",
        "Zadig",
        "https://zadig.akeo.ie/",
        "Zadig 2.x User Guide",
        "swbt-probe adapters --json",
        "list_adapters()",
        "AdapterDiscoveryError",
        "adapters=[]",
        "Switch に向けた pairing",
        "USB HCI transport",
        "libusb",
        "OS 側設定",
        "管理者権限",
        "対象の dongle",
        "VID / PID",
        "Install Driver",
        "Windows 11",
        "CSR8510 A10",
        "WinUSB / libwdi",
        "`usb:0`",
        "Switch 2",
        "22.1.0",
        "初回 pairing",
        "保存済み pairing 情報",
        "Button A",
        "neutral",
        "D-pad",
        "left / right stick",
        "Linux",
        "macOS",
        "experimental",
        "Linux USB & Driver Setup",
        "macOS USB & Driver Setup",
        "動作検証されていないことに留意してください",
        "Linux / macOS Verification Scope",
        "確認していません",
        "Bumble USB Transport Requirements",
        "libusb_package",
        "apt install libusb-1.0-0",
        "hciconfig hciX down",
        "brew install libusb",
        "brew install pkgconf openssl@3",
        "DYLD_LIBRARY_PATH=/usr/local/opt/libusb/lib",
        'bluetoothHostControllerSwitchBehavior="never"',
        "USB デバイスへのアクセス権",
        "PC の通常 Bluetooth 機能",
        "key_store_path",
        "Profile-specific Key Stores",
        "controller profile ごと",
        "Joy-Con L 相当",
        "Joy-Con R 相当",
        "1 つの対象機器",
        "1 つの controller profile",
        "Joy-Con profile の実機互換は限定的な観測",
        "Switch UI で Joy-Con として登録",
        "Joy-Con 固有の reconnect",
        "`Button.SR` + `Button.SL`",
        "SDP の細部一致",
        "OS / dongle / firmware をまたぐ互換性",
        "対象 adapter、実行 command、Switch-facing 動作範囲、cleanup plan",
        "人間の承認",
        "no bond",
        "multiple current peers",
        "Input Is Not Reflected In The UI",
    ):
        assert token in text

    assert "| Linux | experimental |" in text
    assert "| macOS | experimental |" in text
    assert "| Linux | supported |" not in text
    assert "| macOS | supported |" not in text
    assert "macOS 15.7.7" in text
    assert "Button 入力の反映" in text
    assert "unsupported / untrusted" not in text
    assert "experimental" + " target" not in text
    assert "準備" + "候補" not in text
    assert "source" + " fact" not in text
    assert "dependency" + " sync" not in text
    assert "supported としては" + "扱いません" not in text
    assert "試す前に" + "確認すること" not in text
    assert "設計上できるはず" not in text
    assert "保証" in text


def test_agent_brief_keeps_generation_on_implemented_public_api() -> None:
    text = _read(AGENT_BRIEF)

    for token in (
        "from swbt import Button, InputState, JoyConL, JoyConR, "
        "ProController, Stick, SwitchGamepad",
        "allow_pairing=True",
        "await pad.tap(Button.A)",
        "await pad.neutral()",
        "`pair()`",
        "`reconnect()`",
        "`tap()`",
        "`press()`",
        "`release()`",
        "`sticks()`",
        "`lstick()`",
        "`rstick()`",
        "`imu()`",
        "`Stick.tilt()`",
        "`Stick.up()`",
        "`IMUFrame.gyro()`",
        "`IMUFrame.accel()`",
        "`IMUFrame.raw()`",
        "`IMUFrame.with_gyro()`",
        "`IMUFrame.with_accel()`",
        "`InputState` + `apply()`",
        'async with ProController(adapter="usb:0"',
        'JoyConL(adapter="usb:0"',
        "Use a separate `key_store_path` for Pro Controller, Joy-Con L, and Joy-Con R profiles",
        "Use `SwitchGamepad` as a shared type annotation only",
        "Treat unsupported one-sided Joy-Con inputs as `UnsupportedInputError`",
        "Do not pass tuples",
        "Do not invent `pad.gyro()`",
        "`pad.accel()`",
        "Do not invent `hold()`",
        "`sequence()`",
        "`send_current_input()`",
        "Do not invent `JoyConPair`",
        "Do not show low-level Joy-Con profile classes",
        "Do not present Joy-Con real-device compatibility",
        "Do not import internal modules",
    ):
        assert token in text

    assert "set_input" not in text


def test_public_docs_do_not_carry_stale_or_placeholder_wording() -> None:
    text = "\n".join(_read(path) for path in PUBLIC_DOCS)

    for stale_token in (
        "set_input",
        "Poetry",
        "TODO",
        "TBD",
        "xxx",
        'JoyCon("',
        "SwitchGamepad(",
        "設計上できるはず",
        "準備" + "候補",
        "source" + " fact",
        "dependency" + " sync",
        "supported としては" + "扱いません",
        "試す前に" + "確認すること",
        "この文書は",
        "このサイトでは",
        "このページでは",
        "まとめています",
        "参照してください",
        "JoyConLeftProfile",
        "JoyConRightProfile",
        'device_name="Pro Controller"',
    ):
        assert stale_token not in text


def test_rearchitecture_records_transport_removal_as_breaking_change() -> None:
    api_text = _read(API_DOC)
    overview_text = _read(REARCHITECTURE_OVERVIEW)
    policy_text = _read(REARCHITECTURE_POLICY)
    unit_text = _read(UNIT_038_SPEC)

    assert "`HidDeviceTransport` は custom transport 用の public extension point" not in api_text
    assert "## Transport Extension Point" not in api_text
    assert "この変更は breaking change とする" in overview_text
    assert "test / power user 用に `transport=` を残す" in overview_text
    assert "Public constructor からは消す" in overview_text
    assert "custom transport が削除対象の breaking API" in unit_text
    assert "transport=FakeHidTransport()    internal tests only" in policy_text
