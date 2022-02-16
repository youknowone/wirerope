import setuptools
from pkg_resources import get_distribution

try:
    get_distribution("setuptools>=39.2.0")
except Exception as e:
    raise AssertionError(
        "Please upgrade setuptools by `pip install -U setuptools`: {}".format(
            e
        )
    )

setuptools.setup()
