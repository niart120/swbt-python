import inspect
import sys

import swbt
from swbt import SwitchGamepad


def test_public_api_import_does_not_import_bumble() -> None:
    imported_bumble_modules = [
        module_name
        for module_name in sys.modules
        if module_name == "bumble" or module_name.startswith("bumble.")
    ]

    assert swbt.SwitchGamepad is SwitchGamepad
    assert imported_bumble_modules == []


def test_switch_gamepad_signature_does_not_expose_bumble_types() -> None:
    signature = inspect.signature(SwitchGamepad)
    annotation_text = " ".join(
        repr(parameter.annotation) for parameter in signature.parameters.values()
    )

    assert "bumble" not in annotation_text.lower()
