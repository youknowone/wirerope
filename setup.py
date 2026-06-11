import setuptools
from importlib.metadata import version

try:
    assert tuple(int(x) for x in version("setuptools").split(".")[:2]) >= (39, 2)
except Exception as e:
    raise AssertionError(
        "Please upgrade setuptools by `pip install -U setuptools`: {}".format(
            e
        )
    )

setuptools.setup()
