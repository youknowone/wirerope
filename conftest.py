"""Pytest configuration for testing both Rust and Python implementations."""

import pytest
import sys
import importlib


def pytest_addoption(parser):
    parser.addoption(
        "--implementation",
        action="store",
        default="both",
        choices=["rust", "python", "both"],
        help="Run tests with specific implementation: rust, python, or both (default: both)",
    )


def pytest_generate_tests(metafunc):
    """Generate tests for both implementations if requested."""
    if "implementation" in metafunc.fixturenames:
        option_value = metafunc.config.option.implementation
        if option_value == "both":
            metafunc.parametrize("implementation", ["rust", "python"])
        else:
            metafunc.parametrize("implementation", [option_value])


def reload_wirerope_with_implementation(use_rust):
    """Reload wirerope module with specified implementation."""
    # Remove all wirerope modules from sys.modules
    modules_to_remove = [
        key for key in sys.modules.keys() if key.startswith("wirerope")
    ]
    for module in modules_to_remove:
        del sys.modules[module]

    if use_rust:
        # Try to import Rust version directly
        try:
            import wirerope

            if not wirerope._RUST_AVAILABLE:
                pytest.fail("Rust implementation not available")
            return wirerope
        except ImportError:
            pytest.fail("Rust implementation not available")
    else:
        # Force Python implementation by blocking Rust import
        import unittest.mock

        with unittest.mock.patch.dict(sys.modules, {"wirerope._wirerope_rust": None}):
            import wirerope

            return wirerope


@pytest.fixture
def implementation(request):
    """Fixture that provides the implementation name."""
    return request.param if hasattr(request, "param") else "rust"


@pytest.fixture
def wirerope_impl(implementation):
    """Fixture that provides both Rust and Python implementations."""
    use_rust = implementation == "rust"
    return reload_wirerope_with_implementation(use_rust)


@pytest.fixture
def Wire(wirerope_impl):
    """Wire class from the selected implementation."""
    return wirerope_impl.Wire


@pytest.fixture
def WireRope(wirerope_impl):
    """WireRope class from the selected implementation."""
    return wirerope_impl.WireRope


@pytest.fixture
def RopeCore(wirerope_impl):
    """RopeCore class from the selected implementation."""
    return wirerope_impl.RopeCore
