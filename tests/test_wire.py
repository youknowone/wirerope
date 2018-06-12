
from wirerope import Wire, WireRope, RopeCore


def test_default_wire():
    rope = WireRope(Wire)

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

    assert isinstance(f, RopeCore)
    assert isinstance(X.g, Wire)  # triggered descriptor
    assert isinstance(X.h, Wire)  # triggered descriptor

    x = X()

    assert not callable(f)
    assert not callable(x.g)
    assert not callable(x.h)
    assert not callable(x.k)

    assert f.__func__(1) == 1
    assert x.g.__func__(2) == 2
    assert X.g.__func__(x, 7) == 7
    assert x.h.__func__(3) == 3
    assert X.h.__func__(4) == 4
    assert x.k.__func__(5) == 5
    assert X.k.__func__(6) == 6


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

    x = X()

    assert callable(f)
    assert callable(x.g)
    assert callable(x.h)
    assert callable(x.k)

    assert f(1) == 1
    assert x.g(2) == 2
    assert X.g(x, 3) == 3
    assert x.h(4) == 4
    assert X.k(5) == 5


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
