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
python -m fastapi_blocks setup -f BLOCKS_FOLDER
```
*Replace `BLOCKS_FOLDER` with path to blocks folder from root

### Updating blocks

```bash
python -m fastapi_blocks update
```

Additional flags:
- -A - Auto-install pip packages from blocks
- -S - Save block hashes
- -V - Do not verify block hashes (Default is to verify)

## Examples

### Example Block
- [Example Block](https://github.com/r3sbarra/fablocks-example-block) - An example block

### Example Project
- [Example Project](https://github.com/r3sbarra/fablocks-example-project) - An example project

## Reserved Words

### Variable names
- `router` - In router files, the variable router is used to searche for router to include into app.

### Template names
- 

## How to

### Register Jinja funcs for shared templates
In order to allow other blocks to access functions via jinja, you would need to add the functions via hook into `BlockManager().templates_globals`, the key being the name of the function to call from jinja, and the value being the function itself.

eg.
```python
def register_jinja_funcs(**kwargs):
    from fastapi_blocks import BlockManager
    BlockManager().templates_globals['has_role'] = has_role

class Settings(BlockSettingsMixin):
    
    additional_user_roles : Optional[List[str]] = Field(description="Additional user roles to add", default=None)

    def _start_hooks(self) -> List:
        return super()._start_hooks() + [register_jinja_funcs]
```

Then, make sure that the block_config.toml has an entry for `extra_block_settings` with the name of the python file as value. .ie for 'settings.py', it would be settings.

Once that is done, you will need to run setup so that the blockmanager toml is updated.

In some other block, you would then be able to call the function from jinja as long as it is using `templates` from BlockManager.

If you want to use jinja within a blocks jinja2env, you'd have to get the template_globals from blockmanager then add them to the jinja2env's globals.

## Todo:

- [ ] Put more meaningful tests
- [ ] Add command to setup templates/default
- [ ] Add todos
- [ ] Add some sort of security check   