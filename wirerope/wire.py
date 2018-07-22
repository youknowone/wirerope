""":mod:`wirerope.wire` --- Universal method/function wrapper.
==========================================================
"""
import types
from .callable import Descriptor
from ._compat import functools


@functools.singledispatch
def descriptor_bind(descriptor, obj, type_):
    binder = Descriptor(descriptor).detect_binder(obj, type_)
    return binder(descriptor, obj, type_)


@descriptor_bind.register(types.FunctionType)
def descriptor_bind_function(descriptor, obj, type):
    return obj


class Wire(object):
    """The core data object for each function for bound method.

    Inherit this class to implement your own Wire classes.

    - For normal functions, each function is directly wrapped by **Wire**.
    - For any methods or descriptors (including classmethod, staticmethod),
      each one is wrapped by :class:`wirerope.wire.MethodRopeMixin`
      and it creates **Wire** object for each bound object.
    """

    __slots__ = (
        '_rope', '_callable', '_binding', '__func__', '_bound_objects')

    def __init__(self, rope, binding):
        self._rope = rope
        self._callable = rope.callable
        self._binding = binding
        if binding:
            if self._callable.is_property:
                self.__func__ = functools.partial(
                    self._callable.wrapped_object.__get__, *binding)
            else:
                self.__func__ = self._callable.wrapped_object.__get__(*binding)
        else:
            self.__func__ = self._callable.wrapped_object
        if self._binding is None:
            self._bound_objects = ()
        else:
            self._bound_objects = (descriptor_bind(
                self._callable.wrapped_object, *self._binding),)

    def _on_property(self):
        return self.__func__()
