
import sys
from setuptools import setup

TESTING = any(x in sys.argv for x in ['test', 'pytest'])

if sys.version_info < (3, 6):
    raise RuntimeError("aiostream requires Python 3.6")

with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='aiostream',
    version='1.0.0.dev0',

    packages=['aiostream', 'aiostream.stream'],
    setup_requires=['pytest-runner' if TESTING else ''],
    install_requires=[
        'anyio>=1.2.3,<2',
        'outcome>=1.0.1,<2',
        'sniffio>=1.1.0,<2',
        'async_generator>=1.10,<2',
    ],
    tests_require=[
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'trio>=0.12,<1',
        'curio>=0.9,<1'],
    extras_require={
        "asyncio": [],
        "curio": ["curio>=0.9,<1"],
        "trio": ["trio>=0.12,<1"],
    },
    description="Generator-based operators for asynchronous iteration",
    long_description=long_description,
    url="https://github.com/vxgmichel/aiostream",

    license="GPLv3",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],

    author="Vincent Michel",
    author_email="vxgmichel@gmail.com",
)
