from setuptools import setup, find_packages

setup(
    setup_requires=['pbr>=3.1.1'],
    pbr=True,
    packages=find_packages('.')
)
