from types import ModuleType
from pydantic_settings import SettingsConfigDict, BaseSettings
from typing import Optional, List, Any, Dict
from pathlib import Path

from fastapi import FastAPI, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from jinja2 import FileSystemLoader, Environment

from .settings import BlockSettingsBase, BlockSettingsMixin

from dirhash import dirhash

import logging
import importlib
import tomllib
import tomli_w
import subprocess
import sys
import inspect
import threading
import json
import os

class SingletonMeta(type):
    _instances = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

# The BlockManager class is responsible for managing the blocks in the FastAPI application.
class BlockManager(metaclass=SingletonMeta):
    
    """
    Manages FastAPI blocks, including their discovery, dependency installation, and integration.

    Attributes:
        blocks_folder (str): The directory where blocks are located.
        db_engine (Engine): The database engine to use.
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
    
    templates : Optional[Environment] = None
    templates_globals : Dict = {}
    _db_engine : Optional[Any] = None
    _app_config : Optional[BaseSettings] = None
    
    working_dir: Path = Path.cwd()
    block_manager_folder : str = "blockmanager"
    block_manager_info: dict = {}
    
    allow_block_import_failure: bool = False
    restart_on_install: bool = True
    override_duplicate_block : bool = False
    allow_installs : bool = False
    verify_blocks: bool = False             # Set to true in production
    
    logger: logging.Logger = None
    
    # hooks
    _hooks_setup : List = []            # Runs on setup
    _hooks_start : List = []            # Runs right after loading block infos
    _hooks_block_preload : List = []    # Runs before each block info is loaded
    _hooks_block_postload : List = []   # Runs after each block info is loaded
    
    def __init__(self, 
            *args,
            late_load : bool = False, 
            **kwargs
        ):
        
        for key, value in kwargs.items():
            setattr(self, key, value)
        
        if not self.logger:
            self.logger = logging.getLogger("uvicorn") or logging.getLogger(__name__)
        
        # block manager toml
        if not late_load:
            self._load_settings_toml()
        
        self.logger.info("BlockManager initialized.")
        
    def init_app(self, app_instance: 'FastAPI'):
        """
        Initializes the BlockManager and integrates the blocks with the FastAPI application.

        Args:
            app_instance (FastAPI): The FastAPI application instance.

        Returns:
            FastAPI: The FastAPI application instance with the blocks integrated.
        """
        
        # Load Hooks
        self._hooks_start = self._resolve_hooks(self.block_manager_info.get("hooks", {}).get("_start_hooks", {}))
        self._hooks_block_preload = self._resolve_hooks(self.block_manager_info.get("hooks", {}).get("_block_preload_hooks", {}))
        self._hooks_block_postload = self._resolve_hooks(self.block_manager_info.get("hooks", {}).get("_block_postload_hooks", {}))
        
        # Run start hooks
        # .ie Schemas should be loaded in DB via this one
        self._run_hooks(self._hooks_start, blocks_infos=self.block_manager_info.get("blocks", {}))
        
        # Attach to app
        app_instance.block_manager = self
        
        # Use app logger if exists
        self.logger = app_instance.logger if hasattr(app_instance, 'logger') else self.logger
        
        # Setup Templates
        if not self.templates and "templates_dir" in self.block_manager_info.keys() and self.block_manager_info["templates_dir"] != "":
            jinja2env = Environment(loader=FileSystemLoader(self.block_manager_info["templates_dir"]))
            for key, value in self.templates_globals.items():
                jinja2env.globals[key] = value
            
            self.templates = Jinja2Templates(env=jinja2env)
            
        if not "blocks" in self.block_manager_info.keys():
            return app_instance
        
        # Get items load order
        sorted_blocks = sorted(self.block_manager_info["blocks"].items(), key=lambda x: x[1]['load_order'])
        
        # Import from toml
        for block_name, block_info in sorted_blocks:
            
            # Verify block hash
            block_path = block_info.get('block_path', None)
            
            if self.verify_blocks:
                self.logger.info("Verifying hash for %s", block_path)
                if not self._verify_block_hash(block_path):
                    message = (f"Block hash mismatch for @ '{block_path}'. " \
                                    "Block might have been tampered with or changed. " \
                                    "Please run `python -m fastapi_blocks setup --save-hashes` to update the hash.")
                    self.logger.warning(message)
                    os._exit(0)
            
            self.logger.info("Prepping: %s", block_name)
            
            try:
                # Run preload hooks
                self._run_hooks(self._hooks_block_preload, block_info=block_info)
                        
                # Mount statics
                if block_info.get('statics', None) and Path(block_info['statics']).exists():
                    app_instance.mount(
                        f"/{block_name}/static", 
                        StaticFiles(directory=block_info['statics']),
                        name=f"{block_name}-static"
                    )
                    self.logger.info("Mounted statics for %s", block_name)
                
                # Mount routers
                ## Template router
                if block_info.get('template_router', None):
                    module = importlib.import_module(block_info['template_router'])
                    if hasattr(module, 'router') and type(module.router) == APIRouter:
                        self.templates_router.include_router(module.router)
                        self.logger.info("Mounted router: %s", block_info['template_router'])
                
                ## API router
                if block_info.get('api_router', None):
                    module = importlib.import_module(block_info['api_router'])
                    if hasattr(module, 'router') and type(module.router) == APIRouter:
                        self.api_router.include_router(module.router)
                        self.logger.info("Mounted API router: %s", block_info['api_router'])
                        
                # Run postload hooks
                self._run_hooks(self._hooks_block_postload, block_info=block_info)
                
            except Exception as e:
                self.logger.exception("Failed to import block %s: %s", block_name, e)
                if not self.allow_block_import_failure:
                    raise Exception(f"Failed to import block {block_name}: {e}")         
            
        app_instance.include_router(self.templates_router)
        app_instance.include_router(self.api_router)
        
        return app_instance
    
    def _build_block_settings_class(self) -> BlockSettingsBase:
        # Build settings class
        extra_settings_classes = []
        if self.block_manager_info["extra_block_settings"]:
            for extra_settings_path in self.block_manager_info["extra_block_settings"]:
                module = importlib.import_module(extra_settings_path)
                if hasattr(module, 'Settings') and issubclass(getattr(module, 'Settings'), BlockSettingsMixin):
                    extra_settings_classes.append(getattr(module, 'Settings'))
        
        # Create a dynamic settings class
        class DynamicBlockSettings(*extra_settings_classes, BlockSettingsBase):
            model_config = SettingsConfigDict(extra='allow')
            
            def get_dict(self) -> dict:
                return super().get_dict()
            
            def get_hooks(self) -> dict:
                return super().get_hooks()
    
        return DynamicBlockSettings
    
    def _setup(self, run_hooks : bool = True, save_hashes : bool = False) -> bool:
        """
        Sets up the BlockManager.
        """
        if self.allow_installs:
            self.logger.warning(
                "\x1b[93m"
                "SECURITY WARNING: "
                "\x1b[0m" 
                "Automatic dependency installation is enabled. "
                "Only use blocks from trusted sources to prevent the execution of malicious code."
            )
            
        if not self.block_manager_info:
            if "blocks" not in self.block_manager_info.keys():
                self.block_manager_info["blocks"] = {}
            if "installs" not in self.block_manager_info.keys():
                self.block_manager_info["installs"] = []
            if "extra_block_settings" not in self.block_manager_info.keys():
                self.block_manager_info["extra_block_settings"] = []
            if "templates_dir" not in self.block_manager_info.keys():
                self.block_manager_info["templates_dir"] = []
            if "statics" not in self.block_manager_info.keys():
                self.block_manager_info["statics"] = []
                
            if "hooks" not in self.block_manager_info.keys():
                self.block_manager_info["hooks"] = {
                    "_start_hooks" : {},
                    "_block_preload_hooks" : {},
                    "_block_postload_hooks" : {}
                }
                
            if "settings" not in self.block_manager_info.keys():
                self.block_manager_info["settings"] = {}
        
        has_changes = self._setup_blocks(save_hashes=save_hashes)
        has_changes = self._setup_hooks() or has_changes
        
        self._save_settings_toml()
        
        if run_hooks:
            self._run_hooks(self._hooks_setup)
        
        return has_changes
    
    def _setup_blocks(self, save_hashes : bool = False) -> bool:
        """
        Sets up the BlockManager by discovering blocks and installing their dependencies.

        Returns:
            bool: True if new dependencies were installed, False otherwise.
        """
        HAS_INSTALLS = False
        projects_root_dir = self.working_dir / self.blocks_folder
        dynamic_block_class = self._build_block_settings_class()
    
        # Look for block_config.toml under some projects_root_dir
        if projects_root_dir.exists():
            for item in projects_root_dir.iterdir():
                try:
                    block_config_path = item / "block_config.toml"
                    
                    # Look for folders with block_config.toml
                    if item.is_dir() and block_config_path.exists():
                        
                        new_installs = self._load_block_config(item, block_config_path, settings_class=dynamic_block_class)
                        HAS_INSTALLS = HAS_INSTALLS or new_installs
                        
                        if save_hashes:
                            self._save_block_hashes(item)
                        
                except Exception as e:
                    if not self.allow_block_import_failure:
                        error_msg = f"Failed to import block config at path: {item}: {e}"
                        raise Exception(error_msg)
        else:
            raise Exception("No blocks folder found")
        
        return HAS_INSTALLS
    
    def get_block_module(self, block_name: str) -> ModuleType:
        """
        Gets the module for a given block.

        Args:
            block_name (str): The name of the block.

        Returns:
            ModuleType: The module for the given block.
        """
        if block_name in self.block_manager_info["blocks"]:
            return importlib.import_module(self.block_manager_info["blocks"][block_name]['module'])
        return None
    
        
    def _verify_block_hash(self, block_path: str) -> bool:
        """
        Verifies the hash of the block files.
        """
        
        if not self.verify_blocks:
            return True

        hashes_file = self.working_dir / Path(self.block_manager_folder) / 'block_hashes.json'
        if hashes_file.exists():
            with open(hashes_file, 'r') as f:
                hashes = json.load(f)
        else:
            hashes = {}

        block_name = Path(block_path).name
        if block_name not in hashes:
            hashes[block_name] = {}
            return True

        dir_hash = dirhash(str(block_path), 'sha256', match=["*.py", "*.toml", "*.html", "*.js"])
        
        return dir_hash == hashes[block_name]

    def _save_block_hashes(self, block_path: Path) -> None:
        """
        Saves the hash of the block files.
        """
        hashes_file = self.working_dir / Path(self.block_manager_folder) / 'block_hashes.json'
        if hashes_file.exists():
            with open(hashes_file, 'r') as f:
                hashes = json.load(f)
        else:
            hashes = {}

        block_name = block_path.name
        hashes[block_name] = dirhash(str(block_path), 'sha256', match=["*.py", "*.toml", "*.html", "*.js"])

        with open(hashes_file, 'w') as f:
            json.dump(hashes, f, indent=4)

    def _load_block_config(self, 
            block_path: Path, 
            config_path : Path,
            settings_class : BlockSettingsBase
        ) -> bool:
        
        requires_restart = False
        
        # Load Settings
        with open(config_path, 'rb') as f:
            block_config = tomllib.load(f)
            
        # Extract the 'block' section if it exists, otherwise use the whole config
        block_settings_data = block_config.get('block', block_config)
            
        block_settings = settings_class(**block_settings_data, block_path=block_path)
    
        # Block Info
        block_info_dict = block_settings.get_dict()
        
        # Dependancy check
        if block_settings.dependancies:
            for dependancy in block_settings.dependancies:
                if dependancy not in self.block_manager_info["blocks"].keys():
                    raise Exception(f"Missing dependancy: {dependancy}. Make sure that block is installed, or that load order is correct.")
        
        if block_settings.name not in self.block_manager_info["blocks"]:
            self.block_manager_info["blocks"][block_settings.name] = block_info_dict
        else:
            # If key not in block_manager_info, add it. Else, do nothing.
            for key, items in block_info_dict.items():
                if key not in self.block_manager_info["blocks"][block_settings.name].keys():
                    self.block_manager_info["blocks"][block_settings.name][key] = items
            
        # Check if extra block settings in settings, else require restart
        if 'extra_block_settings' in block_info_dict.keys() and block_info_dict['extra_block_settings'] not in self.block_manager_info['extra_block_settings']:
            self.block_manager_info["extra_block_settings"].append(block_info_dict['extra_block_settings'])
            requires_restart = True
        
        # Check if has requirements, or requirements has changed
        if block_settings.requirements or \
            self.block_manager_info["blocks"][block_settings.name]['requirements'] != block_settings.requirements:
                
            # Go through requirements and install if not installed
            for requirement in block_settings.requirements:
                if requirement not in self.block_manager_info["installs"]:
                    self.block_manager_info["installs"].append(requirement)
                    requires_restart = True
                    if self.allow_installs:
                        try:
                            subprocess.check_call([sys.executable, "-m", "pip", "install", requirement])
                        except subprocess.CalledProcessError as e:
                            self.logger.error(f"Failed to install requirement: {requirement}")
                            raise e
                    else:
                        self.logger.warning(
                            f"Block '{block_settings.name}' requires '{requirement}'. "
                            f"Automatic installation is disabled. Please install it manually."
                        )
                        
        # Templates dir
        if 'templates_dir' in block_info_dict.keys() and block_info_dict['templates_dir'] not in self.block_manager_info["templates_dir"]:
            self.block_manager_info["templates_dir"].append(block_info_dict['templates_dir'])
            requires_restart = True
                
        return requires_restart
    
    # Hooks
    def _setup_hooks(self) -> bool:
        """
        Discovers and sets up hooks for the blocks.

        Returns:
            bool: True if new hooks were discovered, False otherwise.
        """
        requires_restart = False
        
        projects_root_dir = self.working_dir / self.blocks_folder
        dynamic_block_class = self._build_block_settings_class()
        
        # Look for block_config.toml under some projects_root_dir
        if projects_root_dir.exists():
            for item in projects_root_dir.iterdir():
                try:
                    block_config_path = item / "block_config.toml"
                    
                    # Look for folders with block_config.toml
                    if item.is_dir() and block_config_path.exists():
                        # Load Settings
                        with open(block_config_path, 'rb') as f:
                            block_config = tomllib.load(f)
                            
                        # Extract the 'block' section if it exists, otherwise use the whole config
                        block_settings_data = block_config.get('block', block_config)
                            
                        block_settings = dynamic_block_class(**block_settings_data, block_path=item)
                        
                        # Hooks
                        block_hooks_setup = block_settings._setup_hooks()
                        block_hooks_start = block_settings._start_hooks()
                        block_hooks_preload = block_settings._preload_hooks()
                        block_hooks_postload = block_settings._postload_hooks()
                        
                        requires_restart = self._attach_hook("_setup_hooks", block_hooks_setup) or requires_restart
                        requires_restart = self._attach_hook("_start_hooks", block_hooks_start) or requires_restart
                        requires_restart = self._attach_hook("_block_preload_hooks", block_hooks_preload) or requires_restart
                        requires_restart = self._attach_hook("_block_postload_hooks", block_hooks_postload) or requires_restart
                        
                except Exception as e:
                    if not self.allow_block_import_failure:
                        error_msg = f"Failed to import block config at path: {item}: {e}"
                        raise Exception(error_msg)
        else:
            raise Exception("No blocks folder found")
        
        return requires_restart
    
    def _resolve_hooks(self, hooks: Dict) -> List:
        """
        Resolves the hooks for the blocks.

        Args:
            hooks (Dict): A dictionary of hooks to resolve.

        Returns:
            List: A list of resolved hooks.
        """
        resolved_hooks = []
        for module_path in hooks.keys():
            if not hooks[module_path]:
                continue
            try:
                module = importlib.import_module(module_path)
                for function_name in hooks[module_path]:
                    func = getattr(module, function_name)
                    if callable(func):
                        resolved_hooks.append(func)
                    else:
                        self.logger.warning(f"Hook '{function_name}' in module '{module_path}' is not callable.")
            except (ImportError, AttributeError) as e:
                self.logger.error(f"Error resolving hook at '{module_path}': {e}")
        return resolved_hooks
        
    def _run_hooks(self, hooks : List, **kwargs) -> None:
        """
        Runs the given hooks.

        Args:
            hooks (List): A list of hooks to run.
        """
        if hooks:
            for fn in hooks:
                if callable(fn):
                    fn(**kwargs)
        
    def _attach_hook(self, hook_group : str, block_hooks : List) -> bool:
        """
        Attaches a hook to the BlockManager.

        Args:
            hook_group (str): The group to attach the hook to.
            block_hooks (List): A list of hooks to attach.

        Returns:
            bool: True if a new hook was attached, False otherwise.
        """
        HAS_NEW = False


        for hook in block_hooks:
            if callable(hook):
                fn_name = hook.__name__
                module = inspect.getmodule(hook)
                if module:
                    if hook_group not in self.block_manager_info["hooks"].keys():
                        self.block_manager_info["hooks"][hook_group] = {}
                    
                    if module.__name__ not in self.block_manager_info["hooks"][hook_group].keys():
                        self.block_manager_info["hooks"][hook_group][module.__name__] = []
                    
                    if fn_name not in self.block_manager_info["hooks"][hook_group][module.__name__]:
                        self.block_manager_info["hooks"][hook_group][module.__name__].append(fn_name)
                        HAS_NEW = True
        return HAS_NEW

    def get_schemas(self) -> List[str]:
        """
        Gets the schemas for the blocks in str format. They will need to be imported afterwards with importlib

        Returns:
            List[str]: A list of schemas for the blocks.
        """
        schemas = [ x["schemas"] for x in self.block_manager_info["blocks"].values() if "schemas" in x.keys() and x["schemas"] ]
        schemas_flattened = [item for sublist in schemas for item in sublist]
        return schemas_flattened
    
    # DB retrieval funcs
    async def get_db_engine_async(self) -> Any:
        """
        Gets the database engine for the blocks.

        Returns:
            Any: The database engine for the blocks.
        """
        if not self._db_engine:
            raise Exception("No database engine found")
        yield self._db_engine

    def get_db_engine(self) -> Any:
        """
        Gets the database engine for the blocks.

        Returns:
            Any: The database engine for the blocks.
        """
        if not self._db_engine:
            raise Exception("No database engine found")
        return self._db_engine
        
    def set_db_engine(self, engine : Any) -> bool:
        if self._db_engine:
            self.logger.warning("Database engine already set")
            return False
        self._db_engine = engine
        return True
    
    async def get_db_session(self):
        """
        Gets the database session for the blocks.

        Returns:
            Any: The database session for the blocks.
        """
        from sqlmodel import Session
        with Session(self.get_db_engine()) as session:
            yield session
    
    # App settings
    @property
    def app_config(self):
        if self._app_config is None:
            raise Exception("No app config found")
        return self._app_config
    
    @app_config.setter
    def app_config(self, value):
        self._app_config = value
        

    # Settings 
    def _load_settings_toml(self):
        """
        Loads the settings from the block_infos.toml file.
        """
        
        toml_path = self.working_dir / Path(self.block_manager_folder) / 'block_infos.toml'
        
        if not toml_path.exists():
            self.logger.warning("No block_infos.toml found. Please run setup first")
            raise Exception("No block_infos.toml found. Please run setup first")
        else:
            with open(toml_path, 'rb') as f:
                self.block_manager_info = tomllib.load(f)
                
                self.allow_installs = self.block_manager_info["settings"].get("allow_installs", False) or self.allow_installs
                self.blocks_folder = self.block_manager_info["settings"].get("blocks_folder", self.blocks_folder)
                self.verify_blocks = self.block_manager_info["settings"].get("verify_blocks", self.verify_blocks)
                
    def _save_settings_toml(self):
        """
        Saves the settings to the block_infos.toml file.
        """
        block_manager_path = self.working_dir / Path(self.block_manager_folder)
        if not block_manager_path.exists():
            print(f"DEBUG: Creating directory: {block_manager_path}")
            block_manager_path.mkdir()
            print(f"DEBUG: Directory created: {block_manager_path.exists()}")
            
        self.block_manager_info["settings"]["allow_installs"] = self.allow_installs
        self.block_manager_info["settings"]["blocks_folder"] = self.blocks_folder
        self.block_manager_info["settings"]["verify_blocks"] = self.verify_blocks
        
        # save toml 
        toml_path = block_manager_path / 'block_infos.toml'
        with open(toml_path, 'wb') as f:
            tomli_w.dump(self.block_manager_info, f)
