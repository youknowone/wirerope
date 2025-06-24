"""Unified benchmark tests for wirerope implementations."""

import pytest
import sys
import importlib


class TestUnifiedBenchmark:
    """Unified benchmark tests comparing all implementations."""

    def setup_method(self):
        """Setup all test implementations."""
        # Force reload to test both Python and Rust implementations
        modules_to_remove = [
            "wirerope",
            "wirerope._wirerope_rust",
            "wirerope.wire",
            "wirerope.rope",
            "wirerope.callable",
        ]
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

        # Import Python version by blocking Rust import
        import unittest.mock

        with unittest.mock.patch.dict(sys.modules, {"wirerope._wirerope_rust": None}):
            wirerope_py = importlib.import_module("wirerope")
            self.WireRope_py = wirerope_py.WireRope
            self.Wire_py = wirerope_py.Wire

        # Clean up for Rust import
        for module in modules_to_remove:
            if module in sys.modules:
                del sys.modules[module]

        # Import Rust version (current default)
        wirerope = importlib.import_module("wirerope")
        self.WireRope = wirerope.WireRope
        self.Wire = wirerope.Wire
        self.rust_available = wirerope._RUST_AVAILABLE

        if self.rust_available:
            self.WireRope_rust = wirerope.WireRope
            self.Wire_rust = wirerope.Wire
        else:
            self.WireRope_rust = self.WireRope_py
            self.Wire_rust = self.Wire_py

        # Define Wire implementations
        class SimpleWire(self.Wire):
            """Simple callable wire for current implementation."""

            def __call__(self, *args, **kwargs):
                return self.__func__(*args, **kwargs)

        class CallableWirePy(self.Wire_py):
            """Callable wire for Python implementation."""

            def __call__(self, *args, **kwargs):
                return self.__func__(*args, **kwargs)

        class CallableWireRust(self.Wire_rust):
            """Callable wire for Rust implementation."""

            def __call__(self, *args, **kwargs):
                return self.__func__(*args, **kwargs)

        # Store Wire classes
        self.SimpleWire = SimpleWire
        self.CallableWirePy = CallableWirePy
        self.CallableWireRust = CallableWireRust

        # Define test classes
        self._setup_test_classes()

    def _setup_test_classes(self):
        """Setup all test class variations."""

        # Regular (unwrapped) class
        class Regular:
            def method(self):
                return 42

            @classmethod
            def classmethod(cls):
                return cls

            @staticmethod
            def staticmethod():
                return "static"

            @property
            def prop(self):
                return "property"


        # Python with default Wire
        class PythonDefault:
            @self.WireRope_py(self.Wire_py)
            def method(self):
                return 42

            @self.WireRope_py(self.Wire_py)
            @classmethod
            def classmethod(cls):
                return cls

            @self.WireRope_py(self.Wire_py)
            @staticmethod
            def staticmethod():
                return "static"

            @self.WireRope_py(self.Wire_py)
            @property
            def prop(self):
                return "property"

        # Rust with default Wire
        class RustDefault:
            @self.WireRope_rust(self.Wire_rust)
            def method(self):
                return 42

            @self.WireRope_rust(self.Wire_rust)
            @classmethod
            def classmethod(cls):
                return cls

            @self.WireRope_rust(self.Wire_rust)
            @staticmethod
            def staticmethod():
                return "static"

            @self.WireRope_rust(self.Wire_rust)
            @property
            def prop(self):
                return "property"

        # Python with callable Wire
        class PythonCallable:
            @self.WireRope_py(self.CallableWirePy)
            def method(self):
                return 42

            @self.WireRope_py(self.CallableWirePy)
            @classmethod
            def classmethod(cls):
                return cls

            @self.WireRope_py(self.CallableWirePy)
            @staticmethod
            def staticmethod():
                return "static"

            @self.WireRope_py(self.CallableWirePy)
            @property
            def prop(self):
                return "property"

        # Rust with callable Wire
        class RustCallable:
            @self.WireRope_rust(self.CallableWireRust)
            def method(self):
                return 42

            @self.WireRope_rust(self.CallableWireRust)
            @classmethod
            def classmethod(cls):
                return cls

            @self.WireRope_rust(self.CallableWireRust)
            @staticmethod
            def staticmethod():
                return "static"

            @self.WireRope_rust(self.CallableWireRust)
            @property
            def prop(self):
                return "property"

        # Store classes and instances
        self.Regular = Regular
        self.PythonDefault = PythonDefault
        self.RustDefault = RustDefault
        self.PythonCallable = PythonCallable
        self.RustCallable = RustCallable

        self.regular = Regular()
        self.python_default = PythonDefault()
        self.rust_default = RustDefault()
        self.python_callable = PythonCallable()
        self.rust_callable = RustCallable()


    # Group 2: Three-way comparison with callable Wire
    @pytest.mark.benchmark(group="three-way-callable")
    @pytest.mark.parametrize(
        "impl,method_type",
        [
            ("regular", "method"),
            ("python", "method"),
            ("rust", "method"),
            ("regular", "classmethod"),
            ("python", "classmethod"),
            ("rust", "classmethod"),
            ("regular", "staticmethod"),
            ("python", "staticmethod"),
            ("rust", "staticmethod"),
            ("regular", "property"),
            ("python", "property"),
            ("rust", "property"),
        ],
    )
    def test_three_way_callable(self, benchmark, impl, method_type):
        """Compare regular vs Python vs Rust with callable Wire."""
        if not self.rust_available and impl == "rust":
            pytest.skip("Rust implementation not available")

        # Select implementation
        if impl == "regular":
            obj = self.regular
            cls = self.Regular
        elif impl == "python":
            obj = self.python_callable
            cls = self.PythonCallable
        else:  # rust
            obj = self.rust_callable
            cls = self.RustCallable

        # Select method type
        if method_type == "method":
            func = obj.method
        elif method_type == "classmethod":
            func = cls.classmethod
        elif method_type == "staticmethod":
            func = cls.staticmethod
        else:  # property
            def func():
                return obj.prop

        # Run benchmark
        benchmark.group = f"{method_type}-three-way"
        benchmark.name = f"{method_type}_{impl}"
        result = benchmark(func)

        # Verify result
        if method_type == "classmethod":
            assert result == cls
        elif method_type == "property":
            assert result == "property"
        elif method_type == "staticmethod":
            assert result == "static"
        else:
            assert result == 42


    # Group 4: First call vs cached call
    @pytest.mark.benchmark(group="first-vs-cached")
    def test_first_call_vs_cached(self, benchmark):
        """Benchmark first call (wire creation) vs cached calls."""

        class TestClass:
            @self.WireRope(self.SimpleWire)
            def method(self):
                return 42

        def first_and_cached_calls():
            instance = TestClass()
            # First call - creates wire
            result1 = instance.method()
            # Cached calls
            for _ in range(9):
                instance.method()
            return result1

        result = benchmark(first_and_cached_calls)
        assert result == 42
