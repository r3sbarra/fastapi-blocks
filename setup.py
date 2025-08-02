from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='fastapi-blocks',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'pydantic',
        'pydantic-settings',
        'toml'
    ],
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: FastAPI",
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'fastapi-blocks=fastapi_blocks.cli:main',
        ],
        'fastapi_blocks': [
            '__main__ = fastapi_blocks.cli:main',
        ],
    },
)
