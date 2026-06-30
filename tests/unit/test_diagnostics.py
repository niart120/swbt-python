import json
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
