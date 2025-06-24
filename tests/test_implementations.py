"""Test both Rust and Python implementations."""

import pytest
import sys
import unittest.mock


def get_rust_implementation():
    """Get Rust implementation if available."""
    # Clear modules
    for key in list(sys.modules.keys()):
        if key.startswith("wirerope"):
            del sys.modules[key]

    try:
        import wirerope

        if wirerope._RUST_AVAILABLE:
            return wirerope
    except ImportError:
        pass
    return None


def get_python_implementation():
    """Get Python implementation."""
    # Clear modules
    for key in list(sys.modules.keys()):
        if key.startswith("wirerope"):
            del sys.modules[key]

    # Force Python implementation
    with unittest.mock.patch.dict(sys.modules, {"wirerope._wirerope_rust": None}):
        import wirerope

        return wirerope


# Get implementations
rust_impl = get_rust_implementation()
python_impl = get_python_implementation()

# Create test parameters
implementations = []
if rust_impl:
    implementations.append(("rust", rust_impl))
implementations.append(("python", python_impl))


@pytest.mark.parametrize("impl_name,wirerope", implementations)
def test_basic_wire(impl_name, wirerope):
    """Test basic Wire functionality with both implementations."""
    Wire = wirerope.Wire
    WireRope = wirerope.WireRope

    class TestWire(Wire):
        def __call__(self, *args, **kwargs):
            return self.__func__(*args, **kwargs)

    rope = WireRope(TestWire)

    @rope
    def add(a, b):
        """Add two numbers."""
        return a + b

    # Test function works
    result = add(2, 3)
    assert result == 5

    # Test docstring is preserved
    assert add.__doc__ == "Add two numbers."

    print(f"✓ Basic wire test passed with {impl_name} implementation")


@pytest.mark.parametrize("impl_name,wirerope", implementations)
def test_wraps_functionality(impl_name, wirerope):
    """Test functools.wraps functionality with both implementations."""
    Wire = wirerope.Wire
    WireRope = wirerope.WireRope

    class TestWire(Wire):
        pass

    rope = WireRope(TestWire, wraps=True)

    @rope
    def multiply(x, y):
        """Multiply two numbers."""
        return x * y

    # Check that attributes are copied
    assert multiply.__doc__ == "Multiply two numbers."
    assert multiply.__name__ == "multiply"

    print(f"✓ Wraps functionality test passed with {impl_name} implementation")


@pytest.mark.parametrize("impl_name,wirerope", implementations)
def test_method_wrapping(impl_name, wirerope):
    """Test method wrapping with both implementations."""
    Wire = wirerope.Wire
    WireRope = wirerope.WireRope

    class TestWire(Wire):
        pass

    rope = WireRope(TestWire, wraps=True)

    class Calculator:
        @rope
        def add(self, a, b):
            """Add method."""
            return a + b

        @rope
        @classmethod
        def multiply(cls, a, b):
            """Multiply classmethod."""
            return a * b

        @rope
        @staticmethod
        def divide(a, b):
            """Divide staticmethod."""
            return a / b

    calc = Calculator()

    # Test instance method
    assert calc.add.__doc__ == "Add method."
    assert Calculator.add.__doc__ == "Add method."

    # Test classmethod
    assert calc.multiply.__doc__ == "Multiply classmethod."
    assert Calculator.multiply.__doc__ == "Multiply classmethod."

    # Test staticmethod
    assert calc.divide.__doc__ == "Divide staticmethod."
    assert Calculator.divide.__doc__ == "Divide staticmethod."

    print(f"✓ Method wrapping test passed with {impl_name} implementation")


@pytest.mark.parametrize("impl_name,wirerope", implementations)
def test_property_wrapping(impl_name, wirerope):
    """Test property wrapping with both implementations."""
    Wire = wirerope.Wire
    WireRope = wirerope.WireRope

    class TestWire(Wire):
        def _on_property(self):
            return self.__func__()

    rope = WireRope(TestWire, wraps=True)

    class Thing:
        def __init__(self, value):
            self._value = value

        @rope
        @property
        def value(self):
            """Value property."""
            return self._value

    thing = Thing(42)

    # Test property access
    assert thing.value == 42

    # Test docstring
    assert Thing.value.__doc__ == "Value property."

    print(f"✓ Property wrapping test passed with {impl_name} implementation")


if __name__ == "__main__":
    # Run tests manually
    for impl_name, impl in implementations:
        print(f"\nTesting {impl_name} implementation:")
        test_basic_wire(impl_name, impl)
        test_wraps_functionality(impl_name, impl)
        test_method_wrapping(impl_name, impl)
        test_property_wrapping(impl_name, impl)
