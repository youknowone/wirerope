import pytest
from wirerope import Wire, WireRope


class SimpleWire(Wire):
    """A simple Wire implementation for benchmarking."""

    def __call__(self, *args, **kwargs):
        return self.__func__(*args, **kwargs)


class TestBenchmark:
    """Benchmark tests for WireRope performance."""

    def setup_method(self):
        """Setup test classes for benchmarking."""

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

        class Wrapped:
            @WireRope(SimpleWire)
            def method(self):
                return 42

            @WireRope(SimpleWire)
            @classmethod
            def classmethod(cls):
                return cls

            @WireRope(SimpleWire)
            @staticmethod
            def staticmethod():
                return "static"

            @WireRope(SimpleWire)
            @property
            def prop(self):
                return "property"

        self.regular = Regular()
        self.wrapped = Wrapped()
        self.Regular = Regular
        self.Wrapped = Wrapped

    def test_benchmark_method_regular(self, benchmark):
        """Benchmark regular method calls."""
        result = benchmark(self.regular.method)
        assert result == 42

    def test_benchmark_method_wrapped(self, benchmark):
        """Benchmark WireRope-wrapped method calls."""
        result = benchmark(self.wrapped.method)
        assert result == 42

    def test_benchmark_classmethod_regular(self, benchmark):
        """Benchmark regular classmethod calls."""
        result = benchmark(self.Regular.classmethod)
        assert result == self.Regular

    def test_benchmark_classmethod_wrapped(self, benchmark):
        """Benchmark WireRope-wrapped classmethod calls."""
        result = benchmark(self.Wrapped.classmethod)
        assert result == self.Wrapped

    def test_benchmark_staticmethod_regular(self, benchmark):
        """Benchmark regular staticmethod calls."""
        result = benchmark(self.Regular.staticmethod)
        assert result == "static"

    def test_benchmark_staticmethod_wrapped(self, benchmark):
        """Benchmark WireRope-wrapped staticmethod calls."""
        result = benchmark(self.Wrapped.staticmethod)
        assert result == "static"

    def test_benchmark_property_regular(self, benchmark):
        """Benchmark regular property access."""
        result = benchmark(lambda: self.regular.prop)
        assert result == "property"

    def test_benchmark_property_wrapped(self, benchmark):
        """Benchmark WireRope-wrapped property access."""
        result = benchmark(lambda: self.wrapped.prop)
        assert result == "property"

    def test_benchmark_first_call_vs_cached(self, benchmark):
        """Benchmark first call (Wire creation) vs subsequent calls."""

        class FreshWrapped:
            @WireRope(SimpleWire)
            def method(self):
                return "fresh"

        @benchmark
        def first_call():
            obj = FreshWrapped()
            # First call creates Wire instance
            return obj.method()

        assert first_call == "fresh"
