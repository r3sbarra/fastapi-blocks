from pydantic import field_serializer
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Union
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
    
    module : Optional[str] = None
    
    project_path : str = os.getcwd()
    
    start_hooks : List = []
    preload_hooks : List = []
    postload_hooks : List = []
    
    model_config = SettingsConfigDict(extra='allow')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.module = self._path_to_module(self.block_path)
    
    def get_dict(self) -> Dict:
        """
        Returns a dictionary representation of the block settings.

        Returns:
            Dict: A dictionary representation of the block settings.
        """
        return self.model_dump(exclude={'start_hooks', 'preload_hooks', 'postload_hooks', 'project_path'})
        
    def _get_hooks(self) -> Dict:
        return {}
    
    @field_serializer('statics', 'templates_dir')
    def serialize_to_path(self, value: str):
        if value:
            return os.path.join(self.block_path, value)
        return None
        
    @field_serializer('template_router', 'api_router', 'extra_block_settings')
    def serialize_path_to_fields(self, value: str) -> Union[str, None]:
        if not value:
            return None
        return self._path_to_module(os.path.join(self.block_path, value))
    
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
    
    start_hooks : List = []
    preload_hooks : List = []
    postload_hooks : List = []
    
    model_config = SettingsConfigDict(arbitrary_types_allowed=True)
    
    def _get_hooks(self) -> Dict:
        super_dict = super()._get_hooks() | {}
        
        if self.start_hooks:
            if not super_dict.get('_start_hooks'):
                super_dict['_start_hooks'] = []
            super_dict['_start_hooks'] = super_dict['_start_hooks'] + self.start_hooks
        if self.preload_hooks:
            if not super_dict.get('_block_preload_hooks'):
                super_dict['_block_preload_hooks'] = []
            super_dict['_block_preload_hooks'] = super_dict['_block_preload_hooks'] + self.preload_hooks
        if self.postload_hooks:
            if not super_dict.get('_block_postload_hooks'):
                super_dict['_block_postload_hooks'] = []
            super_dict['_block_postload_hooks'] = super_dict['_block_postload_hooks'] + self.postload_hooks
        
        return super_dict