""":mod:`ring.wire` --- Universal method/function wrapper.
==========================================================
"""
from ._compat import functools
from ._util import cached_property


@functools.singledispatch
def descriptor_bind(descriptor, obj, type):
    return obj


@descriptor_bind.register(staticmethod)
@descriptor_bind.register(classmethod)
def descriptor_bind_(descriptor, obj, type):
    return type


class Wire(object):
    """The core data object for each function for bound method.

    Inherit this class to implement your own Wire classes.

    - For normal functions, each function is directly wrapped by **Wire**.
    - For any methods or descriptors (including classmethod, staticmethod),
      each one is wrapped by :class:`ring.wire.MethodRopeMixin`
      and it creates **Wire** object for each bound object.
    """

    def __init__(self, rope, binding):
        self._rope = rope
        self._callable = rope.callable
        self._binding = binding
        if binding:
            self.__func__ = self._callable.wrapped_object.__get__(*binding)
        else:
            self.__func__ = self._callable.wrapped_object

    @cached_property
    def _bound_objects(self):
        if self._binding is None:
            return ()
        else:
            return (descriptor_bind(
                self._callable.wrapped_object, *self._binding),)
