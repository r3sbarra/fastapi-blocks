# FastAPI Blocks

[![PyPI version](https://badge.fury.io/py/fastapi-blocks.svg)](https://badge.fury.io/py/fastapi-blocks)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)

`fastapi-blocks` is a Python package that allows you to structure your FastAPI applications using a modular "blocks" architecture. Each block is a self-contained component with its own routes, static files, and templates. This makes it easy to develop and maintain large FastAPI applications by breaking them down into smaller, reusable pieces.

## Features

- **Modular Architecture:** Organize your code into self-contained blocks.
- **Automatic Discovery:** Blocks are automatically discovered and registered with the FastAPI application.
- **Static File Mounting:** Each block can have its own static files, which are automatically mounted.
- **Router Management:** Each block can have its own template and API routers, which are automatically included in the main application.
- **Dependency Management:** Blocks can specify their own Python dependencies, which are automatically installed.
- **Command-Line Interface:** A CLI for managing blocks.

## Installation

```bash
pip install fastapi-blocks
```

## Usage

### Creating a Block

A block is a directory that contains a `block_config.toml` file. The directory can also contain routers, static files, and templates.

Here is an example of a `block_config.toml` file:

```toml
name = "my_block"
version = 0.1
requirements = []
statics = "static"
template_router = "router.py"
api_router = "api_router.py"
load_order = 1
```

- `name`: The name of the block.
- `version`: The version of the block.
- `requirements`: A list of Python packages that the block depends on.
- `statics`: The path to the block's static files directory.
- `template_router`: The path to the block's template router file.
- `api_router`: The path to the block's API router file.
- `load_order`: The order in which the block should be loaded.

### Initializing the Block Manager

To use `fastapi-blocks`, you need to initialize the `BlockManager` and then call the `init_app` method, passing your FastAPI application instance.

```python
from fastapi import FastAPI
from fastapi_blocks import BlockManager

app = FastAPI()

# Initialize the BlockManager
block_manager = BlockManager(blocks_folder="blocks")
block_manager.init_app(app)

@app.get("/")
def read_root():
    return {"Hello": "World"}
```

The `BlockManager` will automatically discover and load all the blocks in the `blocks` folder.

## Command-Line Interface

`fastapi-blocks` comes with a command-line interface for managing blocks.

```bash
fastapi-blocks --help
```

## Example

See the `examples/block_example` directory for a working example of a block.

## Contributing

Contributions are welcome! Please see the [contributing guide](CONTRIBUTING.md) for more information.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.