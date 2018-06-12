from __future__ import with_statement

from setuptools import setup
import sys


def get_version():
    with open('wirerope/__version__.py') as f:
        empty, version = f.read().split('__version__ = ')
    assert empty == ''
    version = version.strip().strip("'")
    assert version.startswith('0.')
    return version


install_requires = [
    'six>=1.11.0',
]
tests_require = [
    'pytest>=3.0.2', 'pytest-cov',
]
docs_require = [
    'sphinx',
]

dev_require = tests_require + docs_require

# backports - py2
if sys.version_info[0] == 2:
    install_requires.extend([
        'inspect2>=0.1.0',
    ])

# backports - py34
if sys.version_info[:2] < (3, 4):
    install_requires.extend([
        'singledispatch>=3.4.0.3',
    ])


def get_readme():
    try:
        with open('README.rst') as f:
            return f.read().strip()
    except IOError:
        return ''


setup(
    name='wirerope',
    version=get_version(),
    description='Turn functions and methods into fully controllable objects',
    long_description=get_readme(),
    author='Jeong YunWon',
    author_email='wirerope@youknowone.org',
    url='https://github.com/youknowone/wirerope',
    packages=(
        'wirerope',
    ),
    package_data={},
    install_requires=install_requires,
    tests_require=tests_require + ['tox', 'tox-pyenv'],
    extras_require={
        'tests': tests_require,
        'docs': docs_require,
        'dev': dev_require,
    },
    classifiers=[
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)  # noqa
