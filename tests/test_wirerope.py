import wirerope


def test_package():
    assert wirerope.__version__
    assert wirerope.__version__.startswith('1.')
