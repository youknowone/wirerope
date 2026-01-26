""":mod:`wirerope.wire` --- end-point instant for each bound method
===================================================================
"""

import six
import types
from .callable import Descriptor
from ._compat import functools

__all__ = ("Wire",)


def descriptor_bind(descriptor, obj, type_):
    """Bind a descriptor to an object and type.

    This function determines how to bind a descriptor based on its type.
    It replaces the previous singledispatch implementation for better performance.
    """
    # Direct type check for FunctionType - most common case
    if isinstance(descriptor, types.FunctionType):
        return obj, obj

    # Fall back to the generic descriptor handling for all other types
    binder = Descriptor(descriptor).detect_binder(obj, type_)
    return binder(descriptor, obj, type_)


class Wire(object):
    """The core data object for each function for bound method.

    Inherit this class to implement your own Wire classes.

    - For normal functions, each function is directly wrapped by **Wire**.
    - For any methods or descriptors (including classmethod, staticmethod),
      each one is wrapped by :class:`wirerope.rope.MethodRopeMixin`
      and it creates **Wire** object for each bound object.
    """

    __slots__ = (
        "_rope",
        "_callable",
        "_binding",
        "__func__",
        "_owner",
        "_bound_objects",
    )

    def __init__(self, rope, owner, binding):
        self._rope = rope
        self._callable = rope.callable
        self._owner = owner
        self._binding = binding
        if binding:
            func = self._callable.wrapped_object.__get__
            if self._callable.is_property:
                wrapped_obj = self._callable.wrapped_object
                # Optimization: try to cache property getter for direct calls
                if hasattr(wrapped_obj, "fget") and wrapped_obj.fget:
                    # Store the property getter and bound instance for fast access
                    self._property_fget = wrapped_obj.fget
                    self._property_instance = binding[0]
                    # Still create partial for compatibility
                    wrapped = functools.partial(func, *binding)
                else:
                    # Fallback for non-standard properties
                    wrapped = functools.partial(func, *binding)
                    self._property_fget = None

                if six.PY2:
                    # functools.wraps requires those attributes but
                    # py2 functools.partial doesn't have them
                    wrapped.__module__ = owner.__module__
                    wrapped.__name__ = func.__name__
                self.__func__ = wrapped
            else:
                self.__func__ = func(*binding)
        else:
            self.__func__ = self._callable.wrapped_object
        if self._binding is None:
            self._bound_objects = ()
        else:
            _, binder = descriptor_bind(self._callable.wrapped_object, *self._binding)
            if binder is not None:
                self._bound_objects = (binder,)
            else:
                self._bound_objects = ()
        assert callable(self.__func__), self.__func__
        if rope._wrapped:
            functools.wraps(self.__func__)(self)

    def _on_property(self):
        # Optimized property access: use cached getter when available
        if hasattr(self, "_property_fget") and self._property_fget is not None:
            return self._property_fget(self._property_instance)
        # Fallback to original approach
        return self.__func__()
