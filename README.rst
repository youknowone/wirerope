wirerope
========

.. image:: https://github.com/youknowone/wirerope/actions/workflows/python-package.yml/badge.svg
.. image:: https://codecov.io/gh/youknowone/wirerope/graph/badge.svg
    :target: https://codecov.io/gh/youknowone/wirerope


The concepts:

- `wirerope.rope.WireRope` is a wrapper interface for python callable.
- Custom `wirerope.wire.Wire` class provides user-defined behavior.
  A subclass of this class is working similar to a *decorator function* body.
- A wire object is associated with a bound method.
- Rope is dispatching types.

`wirerope.rope.WireRope` is the wrapper for callables. By wrapping a
function with `WireRope` with a custom subclass of the `wirerope.wire.Wire`
class, the wire object will be created by each function or bound method.

`Wire` is the most important part. The given class will be instantiated and
bound to each function or bound method - which fits the concept of *instance
cmethod* of human.
For example, when `f` is a free function or staticmethod, the wire also will
be a single object. When `f` is a method or property, wires will be created for
each method owner object `self`. When `f` is a classmethod, wires will be
created for each method owner class `cls`. Yes, it will detect the owner
and bound to it regardless of the calling type.

`Rope` is internal dispatcher. It will be helpful when creating a complex
object for decorated callable instead of simple callable feature.


See also
--------

- See [documentation](https://wirerope.readthedocs.io/en/latest/) - though it
  is not yet written very well.
- See `tests/test_wire.py` for simple example.
- See [methodtools](https://github.com/youknowone/methodtools) for practical
  example.
