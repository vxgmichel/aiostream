
from setuptools import setup, find_packages

setup(name='aiostream',
      packages=find_packages(),
      setup_requires=['pytest_runner'],
      tests_require=['pytest', 'pytest-asyncio', 'pytest-cov'],
      )
