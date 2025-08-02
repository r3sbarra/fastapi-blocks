from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict
import os

class BlockSettingsBase(BaseSettings):
    name : str
    version : float
    requirements : List[str] = []
    dependancies : List[str] = []
    statics : Optional[str] = None
    template_router : Optional[str] = None
    api_router : Optional[str] = None
    extra_block_settings : Optional[str] = None
    load_order : int = 9
    block_path : str
    project_path : str = os.getcwd()
    
    model_config = SettingsConfigDict(extra='allow')
    
    def get_dict(self) -> Dict:
        return { 
            "name": self.name,
            "version": self.version,
            "requirements": self.requirements,
            "dependancies": self.dependancies,
            "module": self._path_to_module(self.block_path),
            "statics": os.path.join(self.block_path, self.statics) if self.statics else None,
            "template_router": self._path_to_module(os.path.join(self.block_path, self.template_router)) if self.template_router else None,
            "api_router": self._path_to_module(os.path.join(self.block_path, self.api_router)) if self.api_router else None,
            "extra_block_settings": self._path_to_module(os.path.join(self.block_path, self.extra_block_settings)) if self.extra_block_settings else None,
            "load_order": self.load_order
        }
        
    def _path_to_module(self, path : str, working_path : str = None) -> Optional[str]:
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
    block_path : Optional[str] = None
    
    def get_dict(self) -> Dict:
        return super().get_dict() | {}