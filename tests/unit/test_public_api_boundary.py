import builtins
import importlib
import inspect
import pkgutil
import sys

import pytest

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


def test_public_api_import_does_not_resolve_bumble(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        global_vars: dict[str, object] | None = None,
        local_vars: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "bumble" or name.startswith("bumble."):
            msg = f"public API import resolved Bumble unexpectedly: {name}"
            raise AssertionError(msg)
        return original_import(name, global_vars, local_vars, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    __import__("swbt")


def test_only_bumble_transport_module_may_resolve_bumble(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def guarded_import(
        name: str,
        global_vars: dict[str, object] | None = None,
        local_vars: dict[str, object] | None = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ) -> object:
        if name == "bumble" or name.startswith("bumble."):
            msg = f"unexpected Bumble import outside swbt.transport.bumble: {name}"
            raise AssertionError(msg)
        return original_import(name, global_vars, local_vars, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    for module in pkgutil.walk_packages(swbt.__path__, f"{swbt.__name__}."):
        if module.name == "swbt.transport.bumble":
            continue
        importlib.import_module(module.name)


def test_switch_gamepad_signature_does_not_expose_bumble_types() -> None:
    signature = inspect.signature(SwitchGamepad)
    annotation_text = " ".join(
        repr(parameter.annotation) for parameter in signature.parameters.values()
    )

    assert "bumble" not in annotation_text.lower()
