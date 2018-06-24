""":mod:`wirerope.wire` --- Universal method/function wrapper.
==========================================================
"""
import types
from ._compat import functools


def _f(owner):
    return owner


def _type_binder(descriptor, obj, type):
    return type


def _obj_binder(descriptor, obj, type):
    return obj


_descriptor_binders = {}


@functools.singledispatch
def descriptor_bind(descriptor, obj, type_):
    descriptor_class = type(descriptor)
    key = (descriptor_class, obj is not None)
    if key not in _descriptor_binders:
        d = descriptor_class(_f)
        method = d.__get__(obj, type_)
        if isinstance(method, types.FunctionType):
            register = descriptor_bind.register(type(descriptor))
            binder = _type_binder
            register(binder)
        else:
            owner = method()
            if owner is type_:
                binder = _type_binder
            elif owner is obj:
                binder = _obj_binder
            else:
                raise TypeError(
                    "'descriptor_bind' fails to auto-detect binding rule of "
                    "the given descriptor. Specify the rule by "
                    "'wirerope.wire.descriptor_bind.register'.")
        _descriptor_binders[key] = binder
    else:
        binder = _descriptor_binders[key]
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
            self.__func__ = self._callable.wrapped_object.__get__(*binding)
        else:
            self.__func__ = self._callable.wrapped_object
        if self._binding is None:
            self._bound_objects = ()
        else:
            self._bound_objects = (descriptor_bind(
                self._callable.wrapped_object, *self._binding),)
