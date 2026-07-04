"""MkDocs site configuration checks."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
MKDOCS_CONFIG = ROOT / "mkdocs.yml"
DOCS_INDEX = ROOT / "docs" / "index.md"


def _load_mkdocs_config() -> dict[str, Any]:
    return yaml.safe_load(MKDOCS_CONFIG.read_text(encoding="utf-8"))


def test_mkdocs_navigation_lists_public_docs() -> None:
    config = _load_mkdocs_config()

    assert config["site_name"] == "swbt-python"
    assert config["theme"]["name"] == "mkdocs"
    assert config["site_url"] == "https://niart120.github.io/swbt-python/"

    nav = config["nav"]
    assert nav == [
        {"Home": "index.md"},
        {"API Reference": "api.md"},
        {"Usage Guide": "usage.md"},
        {"Hardware Guide": "hardware.md"},
        {"Agent Brief": "agent-brief.md"},
    ]


def test_docs_index_explains_site_scope_and_links_docs() -> None:
    text = DOCS_INDEX.read_text(encoding="utf-8")

    assert "swbt-python" in text
    assert "README" in text
    assert "docs/api.md" in text
    assert "docs/usage.md" in text
    assert "docs/hardware.md" in text
    assert "docs/agent-brief.md" in text
    assert "Bluetooth" in text
    assert "実機" in text
