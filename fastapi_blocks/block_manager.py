from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import TYPE_CHECKING, Optional
import logging
import os
import importlib
import toml
from fastapi import FastAPI, APIRouter

class BlockManager(BaseModel):
    
    blocks_folder : str = "blocks"
    templates_router : APIRouter = APIRouter()
    api_router : APIRouter = APIRouter(prefix='/api')
    allow_block_import_failure : bool = False
    working_dir : str = os.getcwd()
    block_infos : dict = {}
    logger : logging.Logger = logging.getLogger(__name__)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
        
    def init_app(self, app_instance: 'FastAPI'):
        
        # block manager toml
        self._load_settings_toml()
        
        # Attach to app
        app_instance.block_manager = self
        
        self.logger = app_instance.logger or self.logger
        
        projects_root_dir = os.path.join(self.working_dir, self.blocks_folder)
        
        # Check to see if new requirements were installed
        HAS_INSTALLS = False
        
        # Look for block_config.toml under some projects_root_dir
        if os.path.exists(projects_root_dir):
            for item in os.scandir(projects_root_dir):
                try:
                    block_config_path = os.path.join(item.path, "block_config.toml")
                    
                    # Look for folders with block_config.toml
                    if item.is_dir() and os.path.exists(block_config_path):
                        
                        new_installs = self._load_block_config(item.path, block_config_path)
                        HAS_INSTALLS = HAS_INSTALLS or new_installs
                        
                        self._save_settings_toml()
                            
                except Exception as e:
                    if not self.allow_block_import_failure:
                        error_msg = f"Failed to import block config at path: {item.path}: {e}"
                        raise Exception(error_msg)
        else:
            raise Exception("No blocks folder found.")

        if HAS_INSTALLS:
            self.logger.warning("New items installed, please restart the server.")
            os._exit(0)
            
        # Get items load order
        sorted_blocks = sorted(self.block_infos["blocks"].items(), key=lambda x: x[1]['load_order'])
        
        for block_name, block_info in sorted_blocks:
            
            self.logger.info("Prepping: %s", block_name)
            
            try:
                # Mount statics
                
                # Mount schemas
                
                # Mount routers
                
                ## Template router
                if block_info['template_router']:
                    module = importlib.import_module(block_info['template_router'])
                    if hasattr(module, 'router'):
                        self.templates_router.include_router(module.router)
                        self.logger.info("Mounted router: %s", block_info['template_router'])
                
                ## API router
                if block_info['api_router']:
                    module = importlib.import_module(block_info['api_router'])
                    if hasattr(module, 'router'):
                        self.api_router.include_router(module.router)
                        self.logger.info("Mounted API router: %s", block_info['api_router'])
                
            except Exception as e:
                self.logger.exception("Failed to import block %s: %s", block_name, e)
                if not self.allow_block_import_failure:
                    raise Exception(f"Failed to import block {block_name}: {e}")
                
                
        app_instance.include_router(self.templates_router)
        app_instance.include_router(self.api_router)
        
        return app_instance
    
    def _load_block_config(self, block_path: str, config_path : str) -> bool:
        
        requires_install = False
        
        # Load Settings
        with open(config_path, 'r') as f:
            block_config = toml.load(f)
            
        # Why'd I do this? No clue. /shrug
        class BlockSettings(BaseSettings):
            
            name : str
            version : float
            requirements : list[str] = []
            statics : Optional[str] = None
            schemas : Optional[str] = None
            template_router : Optional[str] = None
            api_router : Optional[str] = None
            load_order : int = 9
            
            model_config = SettingsConfigDict(extra='allow')
            
        block_settings = BlockSettings(**block_config)
        
        # if block version doesn't match in block_infos, then install requirements
        if block_settings.name not in self.block_infos["blocks"].keys() or \
            block_settings.version > self.block_infos["blocks"][block_settings.name]['version']:
                
            self.block_infos["blocks"][block_settings.name] = { 
                "version": block_settings.version,
                "requirements": block_settings.requirements,
                "statics": os.path.join(block_path,block_settings.statics) if block_settings.statics else None,
                "schemas": self._path_to_module(os.path.join(block_path, block_settings.schemas)) if block_settings.schemas else None,
                "template_router": self._path_to_module(os.path.join(block_path, block_settings.template_router)) if block_settings.template_router else None,
                "api_router": self._path_to_module(os.path.join(block_path, block_settings.api_router)) if block_settings.api_router else None,
                "load_order": block_settings.load_order
            }
            
            # Check if has requirements, or requirements has changed
            if block_settings.requirements or \
                self.block_infos["blocks"][block_settings.name]['requirements'] != block_settings.requirements:
                    
                # Go through requirements and install if not installed
                for requirement in block_settings.requirements:
                    if requirement not in self.block_infos["installs"]:
                        self.block_infos["installs"].append(requirement)
                        requires_install = True
                        exit_code = os.system(f"pip install {requirement}")
                
        return requires_install
    
    def _path_to_module(self, path : str, working_path : str = None) -> str:
        sep = os.path.sep
        working_path = working_path or self.working_dir
        new_path = path.replace(working_path, '').replace(sep, '.')
        if new_path.startswith('.'):    
            new_path = new_path[1:]
        
        return new_path
    
    def _load_settings_toml(self):
        
        toml_path = os.path.join(self.working_dir, 'block_infos.toml')
        
        if not os.path.exists(toml_path):
            self.block_infos = {"blocks": {}, "installs": []}
            self._save_settings_toml()
        else:
            with open(toml_path, 'r') as f:
                self.block_infos = toml.load(f)
        
    def _save_settings_toml(self):
        toml_path = os.path.join(self.working_dir, 'block_infos.toml')
        with open(toml_path, 'w') as f:
            toml.dump(self.block_infos, f)