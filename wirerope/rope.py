""":mod:`ring.wire` --- Universal method/function wrapper.
==========================================================
"""
import six
from .callable import Callable
from .wire import descriptor_bind
from ._compat import functools


class RopeCore(object):

    def __init__(self, callable, rope):
        super(RopeCore, self).__init__()
        self.callable = callable
        self.rope = rope
        self.wire_class = rope.wire_class


class MethodRopeMixin(object):

    def __init__(self, *args, **kwargs):
        super(MethodRopeMixin, self).__init__(*args, **kwargs)
        assert not self.callable.is_barefunction

    def __get__(self, obj, type=None):
        cw = self.callable
        co = cw.wrapped_object
        owner = descriptor_bind(co, obj, type)
        if owner is None:  # invalid binding but still wire it
            owner = obj if obj is not None else type
        wrapper_name_parts = ['__wire_', cw.wrapped_callable.__name__]
        if owner is type:
            wrapper_name_parts.extend(('_', type.__name__))
        wrapper_name = ''.join(wrapper_name_parts)
        wrapper = getattr(owner, wrapper_name, None)
        if wrapper is None:
            boundmethod = co.__get__(obj, type)
            wire = self.wire_class(self, (obj, type))
            wrapper = functools.wraps(boundmethod)(wire)
            setattr(owner, wrapper_name, wrapper)
        return wrapper


class FunctionRopeMixin(object):

    def __init__(self, *args, **kwargs):
        super(FunctionRopeMixin, self).__init__(*args, **kwargs)
        assert self.callable.is_barefunction
        boundmethod = self.callable.wrapped_object
        wire = self.wire_class(self, None)
        self._wire = functools.wraps(boundmethod)(wire)

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass
        return getattr(self._wire, name)


class CallableRopeMixin(object):

    def __init__(self, *args, **kwargs):
        super(CallableRopeMixin, self).__init__(*args, **kwargs)
        self.__call__ = functools.wraps(self.callable.wrapped_object)(self)

    def __call__(self, *args, **kwargs):
        return self._wire(*args, **kwargs)


class WireRope(object):

    def __init__(self, wire_class, core_class=RopeCore):
        self.wire_class = wire_class
        self.method_rope = type(
            '_MethodRope', (MethodRopeMixin, core_class), {})
        self.function_rope = type(
            '_FunctionRope', (FunctionRopeMixin, core_class), {})
        self.callable_function_rope = type(
            '_CallableFunctionRope',
            (CallableRopeMixin, FunctionRopeMixin, core_class), {})

    def __call__(self, function):
        """Wrap a function/method definition.

        :return: Wrapper object. The return type is up to given callable is
                 function or method.
        """
        wrapper = Callable(function)
        if wrapper.is_barefunction:
            rope_class = self.callable_function_rope
            wire_class_call = self.wire_class.__call__
            if six.PY3:
                if wire_class_call.__qualname__ == 'type.__call__':
                    rope_class = self.function_rope
            else:
                # method-wrapper test for CPython2.7
                # im_class == type test for PyPy2.7
                if type(wire_class_call).__name__ == 'method-wrapper' or \
                        wire_class_call.im_class == type:
                    rope_class = self.function_rope
        else:
            rope_class = self.method_rope
        rope = rope_class(wrapper, rope=self)
        return rope
