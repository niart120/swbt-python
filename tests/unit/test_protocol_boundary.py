import importlib
import pkgutil
import sys

import swbt.protocol


def test_protocol_package_does_not_import_bumble() -> None:
    for module in pkgutil.walk_packages(swbt.protocol.__path__, f"{swbt.protocol.__name__}."):
        importlib.import_module(module.name)

    imported_bumble_modules = [
        module_name
        for module_name in sys.modules
        if module_name == "bumble" or module_name.startswith("bumble.")
    ]
    assert imported_bumble_modules == []
