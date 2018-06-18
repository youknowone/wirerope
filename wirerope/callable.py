from __future__ import absolute_import

import types
import six
from ._util import cached_property
from ._compat import inspect

__all__ = ('Callable', )


_inspect_iscoroutinefunction = getattr(
    inspect, 'iscoroutinefunction', lambda f: False)


class Callable(object):
    """A wrapper object including more information of callables."""

    def __init__(self, f):
        self.wrapped_object = f
        if not callable(f):
            f = f.__func__
        self.wrapped_callable = f
        self.is_wrapped_coroutine = getattr(f, '_is_coroutine', None)
        self.is_coroutine = self.is_wrapped_coroutine or \
            _inspect_iscoroutinefunction(f)

    @cached_property
    def signature(self):
        return inspect.signature(self.wrapped_callable)

    @cached_property
    def parameters(self):
        return list(self.signature.parameters.values())

    @property
    def first_parameter(self):
        return self.parameters[0] if self.parameters else None

    @cached_property
    def is_descriptor(self):
        return type(self.wrapped_object).__get__ is not types.FunctionType.__get__  # noqa

    @cached_property
    def is_barefunction(self):
        cc = self.wrapped_callable
        if six.PY34:
            method_name = cc.__qualname__.split('<locals>.')[-1]
            if method_name == cc.__name__:
                return True
            return False
        else:
            if self.is_descriptor:
                return False
            # im_class does not exist at this point
            return not (self.is_membermethod or self.is_classmethod)

    @cached_property
    def is_membermethod(self):
        """Test given argument is a method or not.

        :rtype: bool

        :note: The test is partially based on the first parameter name.
            The test result might be wrong.
        """
        if six.PY34:
            if self.is_barefunction:
                return False
            if not self.is_descriptor:
                return True

        return self.first_parameter is not None \
            and self.first_parameter.name == 'self'

    @cached_property
    def is_classmethod(self):
        """Test given argument is a classmethod or not.

        :rtype: bool

        :note: The test is partially based on the first parameter name.
            The test result might be wrong.
        """
        if isinstance(self.wrapped_object, classmethod):
            return True
        if six.PY34:
            if self.is_barefunction:
                return False
            if not self.is_descriptor:
                return False

        return self.first_parameter is not None \
            and self.first_parameter.name == 'cls'
