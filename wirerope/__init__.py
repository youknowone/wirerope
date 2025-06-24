""":mod:`wirerope` --- Universal method/function wrapper.
=========================================================
"""

# this line must be placed first for setup.cfg
from ._version import __version__

# Try to import Rust implementation first
_RUST_AVAILABLE = False
try:
    # Import Rust implementation directly (no wrapper needed)
    from ._wirerope_rust import Wire, WireRope, RopeCore

    _RUST_AVAILABLE = True
except ImportError:
    # Fall back to Python implementation
    from .wire import Wire
    from .rope import WireRope, RopeCore

__all__ = ("__version__", "Wire", "RopeCore", "WireRope", "_RUST_AVAILABLE")
