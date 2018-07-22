from wirerope import Wire, WireRope, RopeCore


class hybridmethod(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        bound = obj if obj is not None else type
        return self.__func__.__get__(bound, type)


def test_hybridmethod():

    class X(object):

        @hybridmethod
        def f(self):
            return self

    x = X()

    assert X.f() is X
    assert x.f() is x


def test_default_wire():
    rope = WireRope(Wire)

    @rope
    def function(v):
        return v

    class X(object):

        @rope
        def method(self, v):
            return (self, v)

        @rope
        @classmethod
        def cmethod(cls, v):
            return (cls, v)

        @rope
        @staticmethod
        def smethod(v):
            return (None, v)

        @rope
        @hybridmethod
        def hmethod(self_or_cls, v):
            return (self_or_cls, v)

        @rope
        @property
        def property(self):
            return (self, )

    assert isinstance(function, RopeCore)
    assert isinstance(X.method, Wire)  # triggered descriptor
    assert isinstance(X.cmethod, Wire)  # triggered descriptor
    assert isinstance(X.smethod, Wire)  # triggered descriptor
    assert isinstance(X.hmethod, Wire)  # triggered descriptor
    # assert isinstance(X.property, Wire)  # triggered descriptor

    x = X()

    assert not callable(function)
    assert not callable(x.method)
    assert not callable(x.cmethod)
    assert not callable(x.smethod)
    assert not callable(x.hmethod)
    assert not callable(x.property)

    assert function.__func__(1) == 1
    assert x.method.__func__(2) == (x, 2)
    assert X.method.__func__(x, 7) == (x, 7)
    assert x.cmethod.__func__(3) == (X, 3)
    assert X.cmethod.__func__(4) == (X, 4)
    assert x.smethod.__func__(5) == (None, 5)
    assert X.smethod.__func__(6) == (None, 6)
    assert x.hmethod.__func__(8) == (x, 8)
    assert X.hmethod.__func__(9) == (X, 9)
    assert x.property == (x, )


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
