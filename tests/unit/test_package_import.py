"""Package import smoke tests."""

import swbt


def test_package_imports() -> None:
    assert swbt.__all__ == ()
