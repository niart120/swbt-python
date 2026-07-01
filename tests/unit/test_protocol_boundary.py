import subprocess
import sys


def test_protocol_package_does_not_import_bumble() -> None:
    code = """
import importlib
import pkgutil
import sys

import swbt.protocol

for module in pkgutil.walk_packages(swbt.protocol.__path__, f"{swbt.protocol.__name__}."):
    importlib.import_module(module.name)

imported_bumble_modules = [
    module_name
    for module_name in sys.modules
    if module_name == "bumble" or module_name.startswith("bumble.")
]
if imported_bumble_modules:
    raise AssertionError(imported_bumble_modules)
"""

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", code],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
