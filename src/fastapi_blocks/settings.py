from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict
import os

class BlockSettingsBase(BaseSettings):
    """
    Base settings for a block, used to configure its properties.

    Attributes:
        name (str): The name of the block.
        version (float): The version of the block.
        requirements (List[str]): A list of requirements for the block.
        dependancies (List[str]): A list of dependancies for the block.
        statics (Optional[str]): The path to the static files for the block.
        template_router (Optional[str]): The path to the template router for the block.
        templates_dir (Optional[str]): The path to the public templates directory for the block.
        api_router (Optional[str]): The path to the API router for the block.
        extra_block_settings (Optional[str]): The path to extra block settings for the block.
        load_order (int): The load order of the block.
        block_path (str): The path to the block.
        project_path (str): The path to the project.
    """
    name : str
    version : float
    block_path : str
    requirements : List[str] = []
    dependancies : List[str] = []
    statics : Optional[str] = None
    template_router : Optional[str] = None
    templates_dir : Optional[str] = None # Shared templates
    api_router : Optional[str] = None
    extra_block_settings : Optional[str] = None
    load_order : int = 9
    project_path : str = os.getcwd()
    
    model_config = SettingsConfigDict(extra='allow')
    
    def get_dict(self) -> Dict:
        """
        Returns a dictionary representation of the block settings.

        Returns:
            Dict: A dictionary representation of the block settings.
        """
        return { 
            "name": self.name,
            "version": self.version,
            "requirements": self.requirements,
            "dependancies": self.dependancies,
            "module": self._path_to_module(self.block_path),
            "statics": os.path.join(self.block_path, self.statics) if self.statics else None,
            "templates_dir": os.path.join(self.block_path, self.templates_dir) if self.templates_dir else None,
            "template_router": self._path_to_module(os.path.join(self.block_path, self.template_router)) if self.template_router else None,
            "api_router": self._path_to_module(os.path.join(self.block_path, self.api_router)) if self.api_router else None,
            "extra_block_settings": self._path_to_module(os.path.join(self.block_path, self.extra_block_settings)) if self.extra_block_settings else None,
            "load_order": self.load_order
        }
        
    def _path_to_module(self, path : str, working_path : str = None) -> Optional[str]:
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
        working_path = working_path or self.project_path
        
        # Ensure the path is absolute before making it relative
        if not os.path.isabs(path):
            path = os.path.join(working_path, path)

        rel_path = os.path.relpath(path, working_path)

        if rel_path.endswith('.py'):
            rel_path = rel_path[:-3]
        
        module_path = rel_path.replace(os.path.sep, '.')
        return module_path
    
class BlockSettingsMixin(BaseSettings):
    """
    A mixin for block settings.
    """
    block_path : Optional[str] = None
    
    def get_dict(self) -> Dict:
        """
        Returns a dictionary representation of the block settings.

        Returns:
            Dict: A dictionary representation of the block settings.
        """
        return super().get_dict() | {}