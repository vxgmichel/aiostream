
import sys
from setuptools import setup

TESTING = any(x in sys.argv for x in ['test', 'pytest'])
UPLOAD = 'upload_sphinx' in sys.argv

if not UPLOAD and sys.version_info < (3, 6):
    raise RuntimeError("aiostream requires Python 3.6")

with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name='aiostream',
    version='0.3.3.dev0',

    packages=['aiostream', 'aiostream.stream'],
    setup_requires=['pytest-runner' if TESTING else ''],
    install_requires=['async_exit_stack;python_version<"3.7"'],
    tests_require=['pytest', 'pytest-asyncio', 'pytest-cov'],

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
