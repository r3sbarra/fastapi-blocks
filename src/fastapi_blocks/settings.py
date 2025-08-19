from pydantic import field_serializer, field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Union
from pathlib import Path

from .utils import path_to_module

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
    """
    name : str = Field(..., min_length=3, max_length=32, description="The name of the block.")
    version : str
    block_path : Path
    requirements : List[str] = []
    dependancies : List[str] = []
    statics : Optional[str] = None
    template_router : Optional[str] = None
    templates_dir : Optional[str] = None # Shared templates
    api_router : Optional[str] = None
    extra_block_settings : Optional[str] = None
    load_order : int = 9
    schemas : Optional[List[str]] = None
    
    module : Optional[str] = None
    
    model_config = SettingsConfigDict(extra='allow')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.module = path_to_module(self.block_path)
    
    def get_dict(self) -> Dict:
        """
        Returns a dictionary representation of the block settings.

        Returns:
            Dict: A dictionary representation of the block settings.
        """
        return self.model_dump(exclude_none=True)
        
    def _setup_hooks(self) -> List: return []
    def _start_hooks(self) -> List: return []
    def _preload_hooks(self) -> List: return []
    def _postload_hooks(self) -> List: return []
    
    @field_validator('name')
    def validate_name(value: str):
        
        # verify alphanumeric, only allow underscore
        if not value.replace('_', '').isalnum():
            raise ValueError('Name must be alphanumeric and can contain underscores.')
            
        return value
    
    @field_serializer('statics', 'templates_dir')
    def serialize_to_path(self, value: str):
        if value:
            return str(self.block_path / value)
        return None
        
    @field_serializer('template_router', 'api_router', 'extra_block_settings')
    def serialize_path_to_fields(self, value: str) -> Union[str, None]:
        if not value:
            return None
        return path_to_module(self.block_path / value)
    
    @field_serializer('schemas')
    def serialize_schemas(self, value: List[str]) -> Union[List[str], None]:
        if not value:
            return None
        return [path_to_module(self.block_path / v) for v in value]
    
    @field_serializer('block_path')
    def serialize_block_path(self, value: Path) -> str:
        return str(value)
    
class BlockSettingsMixin(BaseSettings):
    """
    A mixin for block settings.
    
    This is to give other blocks some config setting that can be used. .ie for a DB block, you can
    specify a 'schemas', this will then give the other blocks the ability to specify some schema.
    
    Then you can access that data with hooks to perform some action.
    """
    block_path : Optional[Path] = None
    
    model_config = SettingsConfigDict(arbitrary_types_allowed=True)
    
    def _setup_hooks(self) -> List: return super()._start_hooks() or []
    def _start_hooks(self) -> List: return super()._start_hooks() or []
    def _postload_hooks(self) -> List: return super()._postload_hooks() or [] 
    def _preload_hooks(self) -> List: return super()._preload_hooks() or []
    