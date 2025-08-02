from pydantic import BaseModel
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    
    name : str
    template_folder : Optional[str] = None
    static_folder : Optional[str] = None
    
    def __init__(self, env_file: str = ".env", *args, **kwargs):
        self.model_config = SettingsConfigDict(env_file=env_file, env_file_encoding="utf-8")
        super().__init__(args, kwargs)
        
    
class Block:
    
    def __init__(self, folder: str = None):
        
        settings_file = os.path.join(folder, ".env")
        
        if os.path.exists(settings_file):
            self.settings = Settings(settings_file)
        else:
            self.settings = Settings()
       