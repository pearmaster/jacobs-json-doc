from setuptools import setup, find_packages
import jacobsjsondoc._version as _version

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="jacobs-json-doc",
    version=_version.__version__,
    description='A JSON/YAML loader',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author="Jacob Brunson",
    author_email="pypi@jacobbrunson.com",
    url="https://github.com/pearmaster/jacobs-json-doc",
    license='GPLv2',
    packages=find_packages(),
    install_requires=[
        "ruamel.yaml",
    ],
    keywords='conversion',
    classifiers= [
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.7',
)