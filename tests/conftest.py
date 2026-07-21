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
    group.addoption(
        "--swbt-local-address",
        action="store",
        default=None,
        help=(
            "User-managed individual locally administered address for approved "
            "pairing profile hardware runs."
        ),
    )
    group.addoption(
        "--swbt-local-address-b",
        action="store",
        default=None,
        help=("Second locally administered address for the multi-address reconnect hardware run."),
    )
    group.addoption(
        "--swbt-device-info-address",
        action="store",
        default=None,
        help=(
            "Optional controller Bluetooth address bytes for hardware characterization, "
            "formatted as 00:1B:DC:F9:9F:7D."
        ),
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


@pytest.fixture
def swbt_local_address(pytestconfig: Config) -> str:
    option = pytestconfig.getoption("--swbt-local-address")
    if not isinstance(option, str) or option == "":
        pytest.skip("--swbt-local-address is required for pairing profile hardware runs")
    return option


@pytest.fixture
def swbt_secondary_local_address(pytestconfig: Config) -> str:
    option = pytestconfig.getoption("--swbt-local-address-b")
    if not isinstance(option, str) or option == "":
        pytest.skip("--swbt-local-address-b is required for multi-address reconnect runs")
    return option


@pytest.fixture
def swbt_device_info_address(pytestconfig: Config) -> bytes:
    option = pytestconfig.getoption("--swbt-device-info-address")
    if not isinstance(option, str) or option == "":
        pytest.skip("--swbt-device-info-address is required for this hardware characterization")
    return _parse_bt_address(option)


def _parse_bt_address(value: str) -> bytes:
    parts = value.split(":")
    if len(parts) != 6:
        pytest.fail("--swbt-device-info-address must contain 6 colon-separated bytes")
    try:
        address = bytes(int(part, 16) for part in parts)
    except ValueError:
        pytest.fail("--swbt-device-info-address must be hexadecimal")
    if len(address) != 6:
        pytest.fail("--swbt-device-info-address must contain byte values")
    return address
