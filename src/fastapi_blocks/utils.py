import string
import random
import os
from typing import Optional

def generate_random_name(length=8, prefix : str = '', exclude : list = []):
    letters = string.ascii_lowercase
    name = prefix+''.join(random.choice(letters) for i in range(length))
    if name in exclude:
        return generate_random_name(length, exclude)
    return name

def path_to_module(path : str, working_path : str = None) -> Optional[str]:
    """
    Converts a path to a module.

    Args:
        path (str): The path to convert.
        working_path (str, optional): The working path. Defaults to None.

    Returns:
        Optional[str]: The module path.
    """
    if not path:
        return None
    working_path = working_path or os.getcwd()
    
    # Ensure the path is absolute before making it relative
    if not os.path.isabs(path):
        path = os.path.join(working_path, path)

    rel_path = os.path.relpath(path, working_path)

    if rel_path.endswith('.py'):
        rel_path = rel_path[:-3]
    
    module_path = rel_path.replace(os.path.sep, '.')
    return module_path