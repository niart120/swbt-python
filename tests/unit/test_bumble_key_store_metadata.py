import json
from pathlib import Path

from swbt.transport._bumble_key_store import (
    _CurrentPreviousJsonKeyStore,
    _DiagnosticKeyStore,
    read_key_store_metadata,
)


def test_bumble_key_store_classes_live_in_key_store_module() -> None:
    assert _CurrentPreviousJsonKeyStore.__module__ == "swbt.transport._bumble_key_store"
    assert _DiagnosticKeyStore.__module__ == "swbt.transport._bumble_key_store"


def test_bumble_key_store_metadata_reports_missing_file(tmp_path: Path) -> None:
    metadata = read_key_store_metadata(tmp_path / "missing.json")

    assert metadata.exists is False
    assert metadata.previous_exists is False


def test_bumble_key_store_metadata_reports_current_only_file(tmp_path: Path) -> None:
    key_store_path = tmp_path / "keys.json"
    key_store_path.write_text(
        json.dumps({"AA:BB:CC:DD:EE:FF": {"01:02:03:04:05:06": {"link_key_type": 4}}}),
        encoding="utf-8",
    )

    metadata = read_key_store_metadata(key_store_path)

    assert metadata.exists is True
    assert metadata.previous_exists is False


def test_bumble_key_store_metadata_reports_previous_generation(tmp_path: Path) -> None:
    key_store_path = tmp_path / "keys.json"
    key_store_path.write_text(
        json.dumps(
            {
                "AA:BB:CC:DD:EE:FF": {},
                "swbt.previous::AA:BB:CC:DD:EE:FF": {},
            }
        ),
        encoding="utf-8",
    )

    metadata = read_key_store_metadata(key_store_path)

    assert metadata.exists is True
    assert metadata.previous_exists is True
