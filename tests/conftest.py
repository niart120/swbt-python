from pathlib import Path

import pytest
from _pytest.config import Config, Parser


def pytest_addoption(parser: Parser) -> None:
    group = parser.getgroup("swbt hardware")
    group.addoption(
        "--swbt-bumble-adapter",
        action="store",
        default=None,
        help="Bumble USB HCI adapter string for approved hardware runs, such as usb:0.",
    )
    group.addoption(
        "--swbt-hardware-artifact-dir",
        action="store",
        default=None,
        help="Directory where hardware diagnostics artifacts should be written.",
    )


@pytest.fixture
def swbt_bumble_adapter(pytestconfig: Config) -> str:
    adapter = pytestconfig.getoption("--swbt-bumble-adapter")
    if not isinstance(adapter, str) or adapter == "":
        pytest.skip("--swbt-bumble-adapter is required for approved Bumble runs")
    return adapter


@pytest.fixture
def swbt_hardware_artifact_dir(pytestconfig: Config, tmp_path: Path) -> Path:
    option = pytestconfig.getoption("--swbt-hardware-artifact-dir")
    if not isinstance(option, str) or option == "":
        return tmp_path

    artifact_dir = Path(option)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    return artifact_dir
