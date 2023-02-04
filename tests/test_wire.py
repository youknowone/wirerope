import sys

from wirerope import Wire, WireRope, RopeCore

import pytest


class hybridmethod(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        bound = obj if obj is not None else type
        return self.__func__.__get__(bound, type)


class hybridproperty(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        bound = obj if obj is not None else type
        return self.__func__.__get__(bound, type)()


class awfuldescriptor(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        return object()


def test_hybridmethod():

    class X(object):

        @hybridmethod
        def f(self):
            return self

    x = X()

    assert X.f() is X
    assert x.f() is x


def test_hybridproperty():

    class X(object):

        @hybridproperty
        def p(self):
            return self

    x = X()
    assert X.p is X
    assert x.p is x


def test_default_wire():
    class TestWire(Wire):
        pass

    rope = WireRope(TestWire, wraps=True)

    @rope
    def function(v):
        '''function'''
        return v

    class X(object):
        def baremethod(self, v):
            '''baremethod'''
            return (self, v)

        @rope
        def method(self, v):
            '''method'''
            return (self, v)

        @rope
        @classmethod
        def cmethod(cls, v):
            '''cmethod'''
            return (cls, v)

        @rope
        @staticmethod
        def smethod(v):
            '''smethod'''
            return (None, v)

        @rope
        @hybridmethod
        def hmethod(self_or_cls, v):
            '''hmethod'''
            return (self_or_cls, v)

        @rope
        @property
        def property(self):
            '''property'''
            return (self, )

        @rope
        @hybridproperty
        def hproperty(self_or_cls):
            '''hproperty'''
            return (self_or_cls,)

    assert isinstance(function, RopeCore)
    assert isinstance(X.method, Wire)  # triggered descriptor
    assert isinstance(X.cmethod, Wire)  # triggered descriptor
    assert isinstance(X.smethod, Wire)  # triggered descriptor
    assert isinstance(X.hmethod, Wire)  # triggered descriptor
    # assert isinstance(X.property, Wire)  # triggered descriptor

    x = X()

    boundmethod = rope(x.baremethod)

    assert x.method._owner == x
    assert x.cmethod._owner == X
    assert x.smethod._owner == X
    assert x.hmethod._owner == x
    assert X.cmethod._owner == X
    assert X.smethod._owner == X
    assert X.hmethod._owner == X
    assert x.method._bound_objects == (x,)
    assert x.cmethod._bound_objects == (X,)
    assert x.smethod._bound_objects == ()
    assert x.hmethod._bound_objects == (x,)
    assert X.cmethod._bound_objects == (X,)
    assert X.smethod._bound_objects == ()
    assert X.hmethod._bound_objects == (X,)

    assert not callable(function)
    assert not callable(boundmethod)
    assert not callable(x.method)
    assert not callable(x.cmethod)
    assert not callable(x.smethod)
    assert not callable(x.hmethod)
    assert not callable(x.property)
    assert not callable(x.hproperty)

    assert function.__func__(1) == 1
    assert boundmethod.__func__(1) == (x, 1)
    assert x.method.__func__(2) == (x, 2)
    assert X.method.__func__(x, 7) == (x, 7)
    assert x.cmethod.__func__(3) == (X, 3)
    assert X.cmethod.__func__(4) == (X, 4)
    assert x.smethod.__func__(5) == (None, 5)
    assert X.smethod.__func__(6) == (None, 6)
    assert x.hmethod.__func__(8) == (x, 8)
    assert X.hmethod.__func__(9) == (X, 9)
    assert x.property == (x, )
    assert x.hproperty == (x, )
    assert X.hproperty == (X, )

    assert function.__doc__ == 'function'
    assert boundmethod.__doc__ == 'baremethod'
    assert x.method.__doc__ == 'method'
    assert X.method.__doc__ == 'method'
    assert x.cmethod.__doc__ == 'cmethod'
    assert X.cmethod.__doc__ == 'cmethod'
    assert x.smethod.__doc__ == 'smethod'
    assert X.smethod.__doc__ == 'smethod'
    assert x.hmethod.__doc__ == 'hmethod'
    assert X.hmethod.__doc__ == 'hmethod'
    assert X.property.__doc__ == 'property'


def test_wire_super():
    if sys.version_info < (3, 6, 0):
        pytest.skip(
            "super() support requires __set_name__, which is not available"
            " before Python 3.6"
        )

    class CallableWire(Wire):
        def __call__(self, *args, **kwargs):
            return self.__func__(*args, **kwargs)

    rope = WireRope(CallableWire, wraps=True)

    class X(object):
        def baremethod(self, v):
            return "baremethod" + v

        @rope
        def method(self, v):
            return "method" + v

        @rope
        @classmethod
        def cmethod(cls, v):
            return "cmethod" + v

        @rope
        @staticmethod
        def smethod(v):
            return "smethod" + v

        @rope
        @hybridmethod
        def hmethod(self_or_cls, v):
            return "hmethod" + v

        @rope
        @property
        def property(self):
            return "property"

        @rope
        @hybridproperty
        def hproperty(self_or_cls):
            return "hproperty"

    class Y(X):
        def baremethod(self, v):
            return super(Y, self).baremethod(v) + "Y"

        @rope
        def method(self, v):
            return super(Y, self).method(v) + "Y"

        @rope
        @classmethod
        def cmethod(cls, v):
            return super(Y, cls).cmethod(v) + "Y"

        @rope
        @staticmethod
        def smethod(v):
            return X.smethod(v) + "Y"

        @rope
        @hybridmethod
        def hmethod(self_or_cls, v):
            # return super(Y, self_or_cls).hmethod(v) + "Y"
            return "hmethod Y"

        @rope
        @property
        def property(self):
            # return super(Y, self).property + "Y"
            return "propertyY"

        @rope
        @hybridproperty
        def hproperty(self_or_cls):
            # return super(Y, self_or_cls).hproperty + "Y"
            return "hpropertyY"

    for obj, suffix in [(X(), ""), (Y(), "Y")]:
        assert obj.baremethod(" ") == "baremethod " + suffix
        assert obj.method(" ") == "method " + suffix
        assert obj.cmethod(" ") == "cmethod " + suffix
        assert obj.smethod(" ") == "smethod " + suffix
        assert obj.hmethod(" ") == "hmethod " + suffix
        assert obj.property == "property" + suffix
        assert obj.hproperty == "hproperty" + suffix


def test_callable_wire():

    class CallableWire(Wire):

        def __call__(self, *args, **kwargs):
            return self.__func__(*args, **kwargs)

    rope = WireRope(CallableWire)

    @rope
    def f(v):
        return v

    class X(object):

        @rope
        def g(self, v):
            return v

        @rope
        @classmethod
        def h(cls, v):
            return v

        @rope
        @staticmethod
        def k(v):
            return v

        @rope
        @property
        def p(self):
            return 42

    x = X()

    assert callable(f)
    assert callable(x.g)
    assert callable(x.h)
    assert callable(x.k)
    assert not callable(x.p)

    assert f(1) == 1
    assert x.g(2) == 2
    assert X.g(x, 3) == 3
    assert x.h(4) == 4
    assert X.k(5) == 5
    assert x.p == 42


def test_wire():
    class TestWire(Wire):
        x = 7

        def y(self):
            if self._bound_objects:
                return self._bound_objects[0].v
            else:
                return None

    test_rope = WireRope(TestWire)

    @test_rope
    def f():
        return 'a'

    assert f.x == 7
    assert f.y() is None

    class A(object):

        def __init__(self, v):
            self.v = v

        @test_rope
        def f(self):
            return self.v

    a = A(10)
    b = A(20)

    assert a.f.x == 7
    assert a.f.y() == 10
    assert b.f.y() == 20
    assert not callable(a.f)


def test_unwirable():
    rope = WireRope(Wire)

    @rope
    def function(v):
        return v

    class X(object):

        @rope
        @awfuldescriptor
        def messed_up(self, v):
            return (self, v)

    with pytest.raises(TypeError):
        X.messed_up
