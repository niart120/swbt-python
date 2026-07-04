"""Public Markdown documentation checks."""

from pathlib import Path

import swbt

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
DOC_INDEX = DOCS / "index.md"
API_DOC = DOCS / "api.md"
USAGE_DOC = DOCS / "usage.md"
HARDWARE_DOC = DOCS / "hardware.md"
HARDWARE_LOG = DOCS / "hardware-test-log.md"
AGENT_BRIEF = DOCS / "agent-brief.md"
PUBLIC_DOCS = (DOC_INDEX, API_DOC, USAGE_DOC, HARDWARE_DOC, HARDWARE_LOG, AGENT_BRIEF)


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
        "`HidDeviceTransport`",
    ):
        assert token in text

    assert "set_input" not in text
    assert "Bumble 型を public API に露出" in text


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
        "Windows Driver Setup",
        "Zadig",
        "https://zadig.akeo.ie/",
        "Zadig 2.x User Guide",
        "swbt-probe adapters --json",
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
        "Linux / macOS の手順",
        "動作検証されていないことに留意してください",
        "未確認",
        "Bumble USB transport で必要なこと",
        "libusb_package",
        "apt install libusb-1.0-0",
        "hciconfig hciX down",
        "brew install libusb",
        'bluetoothHostControllerSwitchBehavior="never"',
        "USB デバイスへのアクセス権",
        "CSR8510 A10 以外",
        "PC の通常 Bluetooth 機能",
        "key_store_path",
        "no bond",
        "multiple current peers",
        "Input Is Not Reflected In The UI",
    ):
        assert token in text

    assert "| Linux | experimental |" in text
    assert "| macOS | experimental |" in text
    assert "| Linux | supported |" not in text
    assert "| macOS | supported |" not in text
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
        "from swbt import Button, InputState, Stick, SwitchGamepad",
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
        "Do not pass tuples",
        "Do not invent `pad.gyro()`",
        "`pad.accel()`",
        "Do not invent `hold()`",
        "`sequence()`",
        "`send_current_input()`",
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
    ):
        assert stale_token not in text
