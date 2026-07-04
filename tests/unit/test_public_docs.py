"""Public Markdown documentation checks."""

from pathlib import Path

import swbt

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
API_DOC = DOCS / "api.md"
USAGE_DOC = DOCS / "usage.md"
HARDWARE_DOC = DOCS / "hardware.md"
AGENT_BRIEF = DOCS / "agent-brief.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_docs_files_exist() -> None:
    for path in (API_DOC, USAGE_DOC, HARDWARE_DOC, AGENT_BRIEF):
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
        "`snapshot()`",
        "`status()`",
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
        "await pad.sticks(left=Stick.normalized(",
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


def test_hardware_doc_separates_confirmed_unconfirmed_and_troubleshooting() -> None:
    text = _read(HARDWARE_DOC)

    for token in (
        "Python 3.12",
        "Bumble 0.0.230",
        "専用 USB Bluetooth dongle",
        "Windows 11",
        "CSR8510 A10",
        "WinUSB / libwdi",
        "`usb:0`",
        "Python 3.13.5",
        "Switch 2",
        "22.1.0",
        "Button A",
        "neutral",
        "D-pad",
        "left / right stick",
        "active bond reuse reconnect",
        "Linux",
        "macOS",
        "CSR8510 A10 以外",
        "pairing-free incoming bond reuse",
        "OS 標準 Bluetooth stack",
        "key_store_path",
        "no bond",
        "multiple current peers",
        "Input Is Not Reflected In The UI",
        "未確認",
    ):
        assert token in text

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
        "`InputState` + `apply()`",
        "Do not invent `hold()`",
        "`sequence()`",
        "`send_current_input()`",
        "Do not import internal modules",
    ):
        assert token in text

    assert "set_input" not in text


def test_public_docs_do_not_carry_stale_or_placeholder_wording() -> None:
    text = "\n".join(_read(path) for path in (API_DOC, USAGE_DOC, HARDWARE_DOC, AGENT_BRIEF))

    for stale_token in (
        "set_input",
        "Poetry",
        "TODO",
        "TBD",
        "xxx",
        "設計上できるはず",
    ):
        assert stale_token not in text
