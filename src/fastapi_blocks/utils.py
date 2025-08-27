import string
import random
from pathlib import Path
from typing import Optional, Union

def generate_random_name(length=8, prefix : str = '', exclude : list = []):
    letters = string.ascii_lowercase
    name = prefix+''.join(random.choice(letters) for i in range(length))
    if name in exclude:
        return generate_random_name(length, exclude)
    return name

def path_to_module(path: Union[str, Path], working_path: Union[str, Path] = None) -> Optional[str]:
    """
    Converts a path to a module.

    Args:
        path (Union[str, Path]): The path to convert.
        working_path (Union[str, Path], optional): The working path. Defaults to None.

    Returns:
        Optional[str]: The module path.
    """
    if not path:
        return None
    
    working_path = Path(working_path or Path.cwd())
    path = Path(path)

    if not path.is_absolute():
        path = working_path / path

    try:
        rel_path = path.relative_to(working_path)
    except ValueError:
        return str(path)


    if rel_path.suffix == '.py':
        rel_path = rel_path.with_suffix('')

    return '.'.join(rel_path.parts)