import json
import platform
from importlib import metadata
from io import StringIO

from swbt.diagnostics import DiagnosticsRecorder


def test_diagnostics_event_is_written_as_one_json_object_per_line() -> None:
    trace = StringIO()
    recorder = DiagnosticsRecorder(trace_writer=trace)

    recorder.record_event("connected", state="connected")
    recorder.record_event("report_tx", report_id="0x30", reason="periodic")

    lines = trace.getvalue().splitlines()

    assert [json.loads(line) for line in lines] == [
        {"event": "connected", "state": "connected"},
        {"event": "report_tx", "reason": "periodic", "report_id": "0x30"},
    ]


def test_run_metadata_records_environment_and_adapter() -> None:
    trace = StringIO()
    recorder = DiagnosticsRecorder(trace_writer=trace)

    recorder.record_run_metadata(adapter="usb:0")

    payload = json.loads(trace.getvalue())

    assert payload["event"] == "run_metadata"
    assert payload["adapter"] == "usb:0"
    assert payload["os"] == platform.system()
    assert payload["python_version"] == platform.python_version()
    assert payload["package_version"] == metadata.version("swbt-python")


def test_run_metadata_records_key_store_metadata_from_caller() -> None:
    trace = StringIO()
    recorder = DiagnosticsRecorder(trace_writer=trace)

    recorder.record_run_metadata(
        adapter="usb:0",
        key_store_exists=True,
        key_store_path="missing-but-reported.json",
        key_store_previous_exists=True,
    )

    payload = json.loads(trace.getvalue())

    assert payload["key_store_exists"] is True
    assert payload["key_store_path"] == "missing-but-reported.json"
    assert payload["key_store_previous_exists"] is True


def test_run_metadata_records_profile_path_from_caller() -> None:
    trace = StringIO()
    recorder = DiagnosticsRecorder(trace_writer=trace)

    recorder.record_run_metadata(
        adapter="usb:0",
        profile_path="profiles/switch-pro.json",
    )

    payload = json.loads(trace.getvalue())

    assert payload["profile_path"] == "profiles/switch-pro.json"


def test_state_transition_records_previous_next_and_reason() -> None:
    trace = StringIO()
    recorder = DiagnosticsRecorder(trace_writer=trace)

    recorder.record_state_transition(previous="closed", next_state="opening", reason="open")

    assert json.loads(trace.getvalue()) == {
        "event": "state_transition",
        "next": "opening",
        "previous": "closed",
        "reason": "open",
    }
