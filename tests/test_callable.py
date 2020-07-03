from wirerope.callable import Callable


def test_callable_attributes():

    def f():
        pass
    w = Callable(f)
    assert w.is_barefunction is True
    assert w.is_boundmethod is False
    assert w.is_descriptor is False
    assert w.is_membermethod is False
    assert w.is_boundmethod is False
    assert w.is_classmethod is False
    assert w.is_property is False

    class A():

        def m(self):
            pass
        w = Callable(m)
        assert w.is_barefunction is False
        assert w.is_boundmethod is False
        assert w.is_descriptor is False
        assert w.is_membermethod is True
        assert w.is_boundmethod is False
        assert w.is_classmethod is False
        assert w.is_property is False

        @classmethod
        def c(cls):
            pass
        w = Callable(c)
        assert w.is_barefunction is False
        assert w.is_boundmethod is False
        assert w.is_descriptor is True
        assert w.is_membermethod is False
        assert w.is_boundmethod is False
        assert w.is_classmethod is True
        assert w.is_property is False

        @staticmethod
        def s():
            pass
        w = Callable(s)
        assert w.is_barefunction is False
        assert w.is_boundmethod is False
        assert w.is_descriptor is True
        assert w.is_membermethod is False
        assert w.is_boundmethod is False
        assert w.is_classmethod is False
        assert w.is_property is False

        @property
        def p(self):
            pass
        w = Callable(p)
        assert w.is_barefunction is False
        assert w.is_boundmethod is False
        assert w.is_descriptor is True
        assert w.is_membermethod is False
        assert w.is_boundmethod is False
        assert w.is_classmethod is False
        assert w.is_property is True

    w = Callable(A.m)
    assert w.is_barefunction is False
    assert w.is_boundmethod is False
    assert w.is_descriptor is False
    assert w.is_membermethod is True
    assert w.is_boundmethod is False
    assert w.is_classmethod is False
    assert w.is_property is False

    a = A()

    w = Callable(a.m)
    assert w.is_barefunction is False
    assert w.is_boundmethod is True
    assert w.is_descriptor is False
    assert w.is_membermethod is False
    assert w.is_boundmethod is True
    assert w.is_classmethod is False
    assert w.is_property is False

    w = Callable(a.c)
    assert w.is_barefunction is False
    assert w.is_boundmethod is True
    assert w.is_descriptor is False
    assert w.is_membermethod is False
    assert w.is_boundmethod is True
    assert w.is_classmethod is False
    assert w.is_property is False

    w = Callable(a.s)
    # assert w.is_barefunction is False
    assert w.is_descriptor is False
    assert w.is_property is False
    assert w.is_boundmethod is False
    assert w.is_classmethod is False
    # assert w.is_membermethod is False
