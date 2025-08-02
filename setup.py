from setuptools import setup, find_packages

setup(
    name='fastapi-blocks',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'fastapi',
        'pydantic',
        'pydantic-settings'
    ],
    entry_points={
        'console_scripts': [
            # If you have any command-line scripts, define them here
        ],
    },
)
