import gc
import json
import platform
import weakref
from importlib import metadata
from io import StringIO

from swbt.diagnostics import DiagnosticsRecorder


def test_report_events_are_not_retained_without_a_trace_writer() -> None:
    recorder = DiagnosticsRecorder()

    first_event = recorder.record_report_tx(report_id=0x30, reason="periodic")
    first_event_ref = weakref.ref(first_event)
    del first_event

    recorder.record_report_tx(report_id=0x30, reason="periodic")
    gc.collect()

    assert first_event_ref() is None
    assert recorder.report_counters == {0x30: 2}


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


def test_run_metadata_records_profile_path_from_caller() -> None:
    trace = StringIO()
    recorder = DiagnosticsRecorder(trace_writer=trace)

    recorder.record_run_metadata(
        adapter="usb:0",
        profile_path="profiles/switch-pro.json",
    )

    payload = json.loads(trace.getvalue())

    assert payload["profile_path"] == "profiles/switch-pro.json"


def test_diagnostics_keeps_only_status_aggregates() -> None:
    recorder = DiagnosticsRecorder()
    error = RuntimeError("callback failed")

    recorder.record_subcommand_rx(packet_id=0x2A, subcommand_id=0x40)
    recorder.record_raw_rumble(bytes.fromhex("00 01 02 03 04 05 06 07"))
    recorded_error = recorder.record_error(error, recoverable=False)

    assert recorder.last_subcommand_id == 0x40
    assert recorder.raw_rumble == bytes.fromhex("00 01 02 03 04 05 06 07")
    assert recorder.last_error == recorded_error
