# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

wirerope is a Python library that provides a wrapper interface for Python callables, implementing advanced decorator functionality through the Wire and Rope system.

## Development Commands

### Testing
- Run tests: `pytest`
- Run tests with coverage: `pytest --verbose --cov-config .coveragerc --cov wirerope`
- Run a single test file: `pytest tests/test_wire.py`
- Run a specific test: `pytest tests/test_wire.py::test_specific_test_name`

### Benchmarking
- Run only benchmarks: `pytest tests/test_benchmark.py --benchmark-only`
- Run benchmarks with comparison: `pytest tests/test_benchmark.py --benchmark-compare`
- Skip benchmarks in normal test run: `pytest --benchmark-skip`
- Save benchmark results: `pytest tests/test_benchmark.py --benchmark-save=NAME`
- Compare with saved results: `pytest tests/test_benchmark.py --benchmark-compare=NAME`

### Linting
- Run flake8: `flake8 . --statistics`
- Configuration: See `[flake8]` section in setup.cfg (ignores E701)

### Building

#### Python-only build
- Install development dependencies: `pip install -e '.[test]'`
- Build package: `python -m build` (requires build package)
- Create wheel: `python setup.py bdist_wheel`

#### Rust extension build
- Install Rust: https://rustup.rs/
- Install maturin: `pip install maturin`
- Development build: `maturin develop`
- Release build: `maturin develop --release`
- Build wheels: `maturin build --release`

## Architecture

The wirerope library implements a sophisticated decorator system with three main components:

### Core Classes

1. **Wire** (`wirerope/wire.py`): The core data object for each function or bound method. It wraps callables and maintains binding information.

2. **WireRope** (`wirerope/rope.py`): The main wrapper interface for callables. It dispatches to different rope mixins based on the callable type:
   - `FunctionRopeMixin`: For regular functions and static methods
   - `MethodRopeMixin`: For instance and class methods
   - `PropertyRopeMixin`: For properties

3. **Callable** (`wirerope/callable.py`): Analyzes and wraps Python callables, detecting their type (function, method, property, etc.)

### Key Concepts

- **Wire objects** are created per binding context:
  - For functions/staticmethods: single Wire instance
  - For methods: Wire instance per object instance
  - For classmethods: Wire instance per class
  - For properties: Wire instance per object with special handling

- **Rope** acts as a dispatcher that creates appropriate Wire instances based on the callable type and binding context.

- The library uses `functools.singledispatch` for type-based dispatching and maintains compatibility across Python versions through `_compat.py`.

### Usage Pattern

Users typically:
1. Create a custom Wire subclass with desired behavior
2. Wrap callables with WireRope, passing the Wire class
3. The system automatically creates Wire instances for each binding context

### Rust Implementation

The library includes an optional high-performance Rust implementation:
- Automatically used when available (falls back to Python if not)
- Provides ~30-46% performance improvement  
- 100% API compatible with Python implementation
- Check availability: `wirerope._RUST_AVAILABLE`

The Rust implementation uses a thin Python wrapper (`_rust_wrapper.py`) to ensure
full compatibility with functools.wraps and other Python features. This wrapper
maintains complete API compatibility while leveraging Rust's performance benefits.

See RUST_IMPLEMENTATION.md for details.