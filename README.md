# FastAPI Blocks

[![PyPI version](https://badge.fury.io/py/fastapi-blocks.svg)](https://badge.fury.io/py/fastapi-blocks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/release/python-311/)
![Tests](https://github.com/r3sbarra/fastapi-blocks/actions/workflows/python-tests.yml/badge.svg)


`fastapi-blocks` is a Python package that allows you to structure your FastAPI applications using a modular "blocks" architecture. Each block is a self-contained component with its own routes, static files, and templates. This makes it easy to develop and maintain large FastAPI applications by breaking them down into smaller, reusable pieces.

## Installation

```bash
pip install fastapi-blocks
```

Then run
```bash
python -m fastapi_blocks setup BLOCKS_FOLDER
```
*Replace `BLOCKS_FOLDER` with path to blocks folder from root

## Examples

# Example Block
- [Example Block](https://github.com/r3sbarra/fablocks-example-block) - An example block

# Example Project
- [Example Project](https://github.com/r3sbarra/fablocks-example-project) - An example project

## Reserved Words

# Variable names
- `router` - In router files, the variable router is used to searche for router to include into app.

# Template names
- 

## Todo:

- [ ] Put more meaningful tests
- [ ] Add command to setup templates/default
- [ ] Add todos