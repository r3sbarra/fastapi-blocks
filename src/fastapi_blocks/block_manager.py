from types import ModuleType
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Any, Dict

from fastapi import FastAPI, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from jinja2 import FileSystemLoader, Environment
from mako.template import Template

from .utils import generate_random_name, path_to_module

from .settings import BlockSettingsBase, BlockSettingsMixin

import logging
import os
import importlib
import toml
import subprocess
import sys
import inspect

class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
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
    _db_engine : Optional[Any] = None
    
    working_dir: str = os.getcwd()
    block_manager_folder : str = "blockmanager"
    block_manager_info: dict = {}
    block_manager_module : Any = None
    
    allow_block_import_failure: bool = False
    restart_on_install: bool = True
    override_duplicate_block : bool = False
    allow_installs : bool = False
    late_setup : bool = False
    
    logger: logging.Logger = logging.getLogger(__name__)
    
    # hooks
    _start_hooks : List = []            # Runs right after loading block infos
    _block_preload_hooks : List = []    # Runs before each block info is loaded
    _block_postload_hooks : List = []   # Runs after each block info is loaded
    
    def __init__(self, *args, **kwargs):
        
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        # block manager toml
        if not self.late_setup:
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
        
        if os.path.exists(os.path.join(self.working_dir, self.block_manager_folder, "__init__.py")):
            try:
                self.block_manager_module = importlib.import_module(path_to_module(self.block_manager_folder))
            except ImportError as e:
                self.logger.error(f"Failed to import block manager module: {e}")
                
        # Load Hooks
        self._start_hooks = self._resolve_hooks(self.block_manager_info.get("hooks", {}).get("_start_hooks", {}))
        self._block_preload_hooks = self._resolve_hooks(self.block_manager_info.get("hooks", {}).get("_block_preload_hooks", {}))
        self._block_postload_hooks = self._resolve_hooks(self.block_manager_info.get("hooks", {}).get("_block_postload_hooks", {}))
        
        # Run start hooks
        # .ie Schemas should be loaded in DB via this one
        self._run_hooks(self._start_hooks, blocks_infos=self.block_manager_info.get("blocks", {}))
        
        # Attach to app
        app_instance.block_manager = self
        
        # Use app logger if exists
        self.logger = app_instance.logger if hasattr(app_instance, 'logger') else self.logger
        
        # Setup Templates
        if not self.templates:
            jinja2env = Environment(loader=FileSystemLoader(self.block_manager_info["templates_dir"]))
            self.templates = Jinja2Templates(env=jinja2env)
            
        # Get items load order
        sorted_blocks = sorted(self.block_manager_info["blocks"].items(), key=lambda x: x[1]['load_order'])
        
        # Import from toml
        for block_name, block_info in sorted_blocks:
            
            self.logger.info("Prepping: %s", block_name)
            
            try:
                # Run preload hooks
                self._run_hooks(self._block_preload_hooks, block_info=block_info)
                        
                # Mount statics
                if block_info.get('statics', None) and os.path.exists(block_info['statics']):
                    app_instance.mount(
                        f"/{block_name}/static", 
                        StaticFiles(directory=block_info['statics']), 
                        name=f"{block_name}-static"
                    )
                    self.logger.info("Mounted statics for %s", block_name)
                
                # Mount routers
                ## Template router
                if block_info.get('template_router', None) and not hasattr(self.block_manager_module, 'template_router'):
                    module = importlib.import_module(block_info['template_router'])
                    if hasattr(module, 'router') and type(module.router) == APIRouter:
                        self.templates_router.include_router(module.router)
                        self.logger.info("Mounted router: %s", block_info['template_router'])
                
                ## API router
                if block_info.get('api_router', None) and not hasattr(self.block_manager_module, 'api_router'):
                    module = importlib.import_module(block_info['api_router'])
                    if hasattr(module, 'router') and type(module.router) == APIRouter:
                        self.api_router.include_router(module.router)
                        self.logger.info("Mounted API router: %s", block_info['api_router'])
                        
                # Run postload hooks
                self._run_hooks(self._block_postload_hooks, block_info=block_info)
                
            except Exception as e:
                self.logger.exception("Failed to import block %s: %s", block_name, e)
                if not self.allow_block_import_failure:
                    raise Exception(f"Failed to import block {block_name}: {e}")

        # Import from Mako
        if self.block_manager_module:
            if hasattr(self.block_manager_module, 'template_router') and type(self.block_manager_module.template_router) == APIRouter:
                self.templates_router.include_router(self.block_manager_module.template_router)
                self.logger.info("Mounted template router from mako file")
                
            if hasattr(self.block_manager_module, 'api_router') and type(self.block_manager_module.api_router) == APIRouter:
                self.api_router.include_router(self.block_manager_module.api_router)
                self.logger.info("Mounted api router from mako file")                
            
        app_instance.include_router(self.templates_router)
        app_instance.include_router(self.api_router)
        
        return app_instance
    
    def _build_block_settings_class(self,) -> BlockSettingsBase:
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
    
    def _setup(self, save_mako : bool = False) -> bool:
        """
        Sets up the BlockManager.
        """
        if self.allow_installs:
            self.logger.warning(
                "SECURITY WARNING: Automatic dependency installation is enabled. "
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
        
        has_changes = self._setup_blocks()
        has_changes = self._setup_hooks() or has_changes
        
        self._save_settings_toml()
        
        if save_mako:
            self._save_mako()
        
        return has_changes
    
    def _setup_blocks(self) -> bool:
        """
        Sets up the BlockManager by discovering blocks and installing their dependencies.

        Returns:
            bool: True if new dependencies were installed, False otherwise.
        """
        HAS_INSTALLS = False
        projects_root_dir = os.path.join(self.working_dir, self.blocks_folder)
        dynamic_block_class = self._build_block_settings_class()
    
        # Look for block_config.toml under some projects_root_dir
        if os.path.exists(projects_root_dir):
            for item in os.scandir(projects_root_dir):
                try:
                    block_config_path = os.path.join(item.path, "block_config.toml")
                    
                    # Look for folders with block_config.toml
                    if item.is_dir() and os.path.exists(block_config_path):
                        
                        new_installs = self._load_block_config(item.path, block_config_path, settings_class=dynamic_block_class)
                        HAS_INSTALLS = HAS_INSTALLS or new_installs
                        
                except Exception as e:
                    if not self.allow_block_import_failure:
                        error_msg = f"Failed to import block config at path: {item.path}: {e}"
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
        if block_info_dict['extra_block_settings'] and block_info_dict['extra_block_settings'] not in self.block_manager_info['extra_block_settings']:
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
        if block_info_dict['templates_dir'] and block_info_dict['templates_dir'] not in self.block_manager_info["templates_dir"]:
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
        
        projects_root_dir = os.path.join(self.working_dir, self.blocks_folder)
        dynamic_block_class = self._build_block_settings_class()
        
        # Look for block_config.toml under some projects_root_dir
        if os.path.exists(projects_root_dir):
            for item in os.scandir(projects_root_dir):
                try:
                    block_config_path = os.path.join(item.path, "block_config.toml")
                    
                    # Look for folders with block_config.toml
                    if item.is_dir() and os.path.exists(block_config_path):
                        # Load Settings
                        with open(block_config_path, 'r') as f:
                            block_config = toml.load(f)
                            
                        block_settings = dynamic_block_class(**block_config, block_path=item.path)
                        
                        # Hooks
                        block_hooks_start = block_settings._start_hooks()
                        block_hooks_preload = block_settings._preload_hooks()
                        block_hooks_postload = block_settings._postload_hooks()
                        
                        requires_restart = self._attach_hook("_start_hooks", block_hooks_start) or requires_restart
                        requires_restart = self._attach_hook("_block_preload_hooks", block_hooks_preload) or requires_restart
                        requires_restart = self._attach_hook("_block_postload_hooks", block_hooks_postload) or requires_restart
                        
                except Exception as e:
                    if not self.allow_block_import_failure:
                        error_msg = f"Failed to import block config at path: {item.path}: {e}"
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
    
    # Settings 
    def _load_settings_toml(self):
        """
        Loads the settings from the block_infos.toml file.
        """
        
        toml_path = os.path.join(self.working_dir, self.block_manager_folder, 'block_infos.toml')
        
        if not os.path.exists(toml_path):
            self.logger.warning("No block_infos.toml found. Please run setup first")
            raise Exception("No block_infos.toml found. Please run setup first")
        else:
            with open(toml_path, 'r') as f:
                self.block_manager_info = toml.load(f)
                
                self.allow_installs = self.block_manager_info["settings"].get("allow_installs", False) or self.allow_installs
                
        
    def _save_settings_toml(self):
        """
        Saves the settings to the block_infos.toml file.
        """
        if not os.path.exists(os.path.join(self.working_dir, self.block_manager_folder)):
            os.mkdir(os.path.join(self.working_dir, self.block_manager_folder))
        toml_path = os.path.join(self.working_dir, self.block_manager_folder, 'block_infos.toml')
        with open(toml_path, 'w') as f:
            toml.dump(self.block_manager_info, f)

    def _save_mako(self):
        if not os.path.exists(os.path.join(self.working_dir, self.block_manager_folder)):
            os.mkdir(os.path.join(self.working_dir, self.block_manager_folder))
            
        init_file_path = os.path.join(self.working_dir, self.block_manager_folder, "__init__.py")
        
        used_names = []
        
        template_routers_dict = {}
        template_routers = [v["template_router"] for x, v in self.block_manager_info["blocks"].items() if "template_router" in v.keys() and v["template_router"]]
        for x in template_routers:
            random_name = generate_random_name(exclude=used_names)
            used_names.append(random_name)
            template_routers_dict[random_name] = x
            
        api_routers_dict = {}
        api_routers = [v["api_router"] for x, v in self.block_manager_info["blocks"].items() if "api_router" in v.keys() and v["api_router"]]
        for x in api_routers:
            random_name = generate_random_name(exclude=used_names)
            used_names.append(random_name)
            api_routers_dict[random_name] = x
            
        data = {
            "template_routers" : template_routers_dict,
            "api_routers" : api_routers_dict
        }
            
        current_folder = os.path.dirname(os.path.abspath(__file__))
        mako_path = os.path.join(current_folder, "__init__.py.mako")
            
        with open(mako_path) as f:
            template = Template(f.read())

        rendered = template.render(**data)
        
        with open(init_file_path, 'w') as f:
            f.write(rendered)

    def get_schemas(self) -> List[str]:
        """
        Gets the schemas for the blocks in str format. They will need to be imported afterwards with importlib

        Returns:
            List[str]: A list of schemas for the blocks.
        """
        schemas = [ x["schemas"] for x in self.block_manager_info["blocks"].values() if "schemas" in x.keys() and x["schemas"] ]
        schemas_flattened = [item for sublist in schemas for item in sublist]
        return schemas_flattened
    
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
