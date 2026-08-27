from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="helix-education",
    version="2.0.0",
    author="HatemShelby",
    description="Event-sourced learning state engine with zero AI dependencies",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "pydantic>=2.0",
        "grpcio>=1.50.0",
        "scipy>=1.10.0",
        "numpy>=1.24.0",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
