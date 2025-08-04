from types import ModuleType
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Any

from fastapi import FastAPI, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from jinja2 import FileSystemLoader, Environment

from .settings import BlockSettingsBase, BlockSettingsMixin

import logging
import os
import importlib
import toml
import subprocess
import sys
    
class BlockManager(BaseModel):
    """
    Manages FastAPI blocks, including their discovery, dependency installation, and integration.

    Attributes:
        blocks_folder (str): The directory where blocks are located.
        templates_router (APIRouter): The router for block templates.
        api_router (APIRouter): The router for block APIs.
        allow_block_import_failure (bool): Whether to allow the application to continue running if a block fails to import.
        restart_on_install (bool): Whether to restart the application after new block requirements are installed.
        working_dir (str): The current working directory.
        block_infos (dict): A dictionary containing information about the blocks.
        logger (logging.Logger): The logger for the BlockManager.
    """
    
    blocks_folder: str = "blocks"
    
    templates_router: APIRouter = APIRouter()
    api_router: APIRouter = APIRouter(prefix='/api')
    
    allow_block_import_failure: bool = False
    restart_on_install: bool = True
    working_dir: str = os.getcwd()
    block_infos: dict = {}
    logger: logging.Logger = logging.getLogger(__name__)
    override_duplicate_block : bool = False
    
    templates : Optional[Jinja2Templates] = None
    
    # hooks
    _start_hooks : List = []            # Runs right after loading block infos
    _block_preload_hooks : List = []    # Runs before each block info is loaded
    _block_postload_hooks : List = []   # Runs after each block info is loaded
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
        
    def init_app(self, app_instance: 'FastAPI'):
        """
        Initializes the BlockManager and integrates the blocks with the FastAPI application.

        Args:
            app_instance (FastAPI): The FastAPI application instance.

        Returns:
            FastAPI: The FastAPI application instance with the blocks integrated.
        """
        
        # block manager toml
        self._load_settings_toml()
        
        # Load Hooks
        self._start_hooks = self.block_infos["hooks"]["_start_hooks"] or []
        self._block_preload_hooks = self.block_infos["hooks"]["_block_preload_hooks"] or []
        self._block_postload_hooks = self.block_infos["hooks"]["_block_postload_hooks"] or []
        
        # Run start hooks
        # .ie Schemas should be loaded in DB via this one
        self._run_hooks(self._start_hooks, blocks_infos=self.block_infos)
        
        # Attach to app
        app_instance.block_manager = self
        
        # Use app logger if exists
        self.logger = app_instance.logger or self.logger
        
        # Basic setup
        HAS_INSTALLS = self._setup()
        
        # Setup Templates
        if not self.templates:
            jinja_env = Environment(loader=FileSystemLoader(self.block_infos["templates_dir"]))
            self.templates = Jinja2Templates(env=jinja_env)

        if HAS_INSTALLS and self.restart_on_install:
            self.logger.warning("New items installed, please restart the server.")
            os._exit(0)
            
        # Get items load order
        sorted_blocks = sorted(self.block_infos["blocks"].items(), key=lambda x: x[1]['load_order'])
        
        for block_name, block_info in sorted_blocks:
            
            self.logger.info("Prepping: %s", block_name)
            
            try:
                # Run preload hooks
                self._run_hooks(self._block_preload_hooks, block_info=block_info)
                        
                # Mount statics
                if block_info['statics'] and os.path.exists(block_info['statics']):
                    app_instance.mount(
                        f"/{block_name}/static", 
                        StaticFiles(directory=block_info['statics']), 
                        name=f"{block_name}-static"
                    )
                    self.logger.info("Mounted statics for %s", block_name)
                
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
                        
                # Run postload hooks
                self._run_hooks(self._block_postload_hooks, block_info=block_info)
                
            except Exception as e:
                self.logger.exception("Failed to import block %s: %s", block_name, e)
                if not self.allow_block_import_failure:
                    raise Exception(f"Failed to import block {block_name}: {e}")
                
                
        app_instance.include_router(self.templates_router)
        app_instance.include_router(self.api_router)
        
        return app_instance
    
    
    def _setup(self) -> bool:
        HAS_INSTALLS = False
        projects_root_dir = os.path.join(self.working_dir, self.blocks_folder)
        # Build settings class
        extra_settings_classes = []
        if self.block_infos["extra_block_settings"]:
            for extra_settings_path in self.block_infos["extra_block_settings"]:
                module = importlib.import_module(extra_settings_path)
                if hasattr(module, 'Settings') and issubclass(getattr(module, 'Settings'), BlockSettingsMixin):
                    extra_settings_classes.append(getattr(module, 'Settings'))
        
        # Create a dynamic settings class
        class DynamicBlockSettings(*extra_settings_classes, BlockSettingsBase):
            model_config = SettingsConfigDict(extra='allow')
            
            def get_dict(self) -> dict:
                return super().get_dict()
    
        # Look for block_config.toml under some projects_root_dir
        if os.path.exists(projects_root_dir):
            for item in os.scandir(projects_root_dir):
                try:
                    block_config_path = os.path.join(item.path, "block_config.toml")
                    
                    # Look for folders with block_config.toml
                    if item.is_dir() and os.path.exists(block_config_path):
                        
                        new_installs = self._load_block_config(item.path, block_config_path, settings_class=DynamicBlockSettings)
                        HAS_INSTALLS = HAS_INSTALLS or new_installs
                        
                        self._save_settings_toml()
                            
                except Exception as e:
                    if not self.allow_block_import_failure:
                        error_msg = f"Failed to import block config at path: {item.path}: {e}"
                        raise Exception(error_msg)
        else:
            raise Exception("No blocks folder found")
        return HAS_INSTALLS
    
    def get_block_module(self, block_name: str) -> ModuleType:
        if block_name in self.block_infos["blocks"]:
            return importlib.import_module(self.block_infos["blocks"][block_name]['module'])
        return None
        
    def _run_hooks(self, hooks : List, **kwargs) -> None:
        if hooks:
            for fn in hooks:
                if callable(fn):
                    fn(**kwargs)
        
    def _load_block_config(self, 
            block_path: str, 
            config_path : str,
            settings_class : BlockSettingsBase
        ) -> bool:
        
        requires_restart = False
        
        # Load Settings
        with open(config_path, 'r') as f:
            block_config = toml.load(f)
            
        block_settings = settings_class(**block_config, block_path=block_path)
    
        block_info_dict = block_settings.get_dict()
        
        if block_settings.name not in self.block_infos["blocks"]:
            self.block_infos["blocks"][block_settings.name] = block_info_dict
        else:
            for key, items in block_info_dict.items():
                if key not in self.block_infos["blocks"][block_settings.name].keys():
                    self.block_infos["blocks"][block_settings.name][key] = items
            
        # Check if extra block settings in settings, else require restart
        if block_info_dict['extra_block_settings'] and block_info_dict['extra_block_settings'] not in self.block_infos['extra_block_settings']:
            self.block_infos["extra_block_settings"].append(block_info_dict['extra_block_settings'])
            requires_restart = True
        
        # Check if has requirements, or requirements has changed
        if block_settings.requirements or \
            self.block_infos["blocks"][block_settings.name]['requirements'] != block_settings.requirements:
                
            # Go through requirements and install if not installed
            for requirement in block_settings.requirements:
                if requirement not in self.block_infos["installs"]:
                    self.block_infos["installs"].append(requirement)
                    requires_restart = True
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", requirement])
                    except subprocess.CalledProcessError as e:
                        self.logger.error(f"Failed to install requirement: {requirement}")
                        raise e
                
        return requires_restart

    def _load_settings_toml(self):
        
        toml_path = os.path.join(self.working_dir, 'block_infos.toml')
        
        if not os.path.exists(toml_path):
            self.block_infos = {"blocks": {}, "installs": [], "templates_dir": [], "extra_block_settings": [], "hooks" : {}}
            self._save_settings_toml()
        else:
            with open(toml_path, 'r') as f:
                self.block_infos = toml.load(f)
                
                if "blocks" not in self.block_infos.keys():
                    self.block_infos["blocks"] = {}
                if "installs" not in self.block_infos.keys():
                    self.block_infos["installs"] = []
                if "extra_block_settings" not in self.block_infos.keys():
                    self.block_infos["extra_block_settings"] = []
                if "templates_dir" not in self.block_infos.keys():
                    self.block_infos["templates_dir"] = []
                    
                if "hooks" not in self.block_infos.keys():
                    self.block_infos["hooks"] = {
                        "start_hooks" : [],
                        "block_preload_hooks" : [],
                        "block_postload_hooks" : []
                    }
        
    def _save_settings_toml(self):
        toml_path = os.path.join(self.working_dir, 'block_infos.toml')
        with open(toml_path, 'w') as f:
            toml.dump(self.block_infos, f)
