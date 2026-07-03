"""Bumble JSON key store metadata helpers."""

import json
from dataclasses import dataclass
from pathlib import Path

PREVIOUS_NAMESPACE_PREFIX = "swbt.previous::"


@dataclass(frozen=True)
class KeyStoreMetadata:
    """Observed metadata for a Bumble JSON key store file."""

    exists: bool
    previous_exists: bool


def read_key_store_metadata(key_store_path: str | Path) -> KeyStoreMetadata:
    """Read non-sensitive metadata from a Bumble JSON key store file."""
    path = Path(key_store_path)
    if not path.exists():
        return KeyStoreMetadata(exists=False, previous_exists=False)
    return KeyStoreMetadata(
        exists=True,
        previous_exists=_previous_generation_exists(path),
    )


def _previous_generation_exists(key_store_path: Path) -> bool:
    try:
        key_store_data = json.loads(key_store_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(key_store_data, dict):
        return False
    return any(str(namespace).startswith(PREVIOUS_NAMESPACE_PREFIX) for namespace in key_store_data)
