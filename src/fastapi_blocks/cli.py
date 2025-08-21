import argparse
import shutil
from typing import Union
from pathlib import Path
import importlib

def setup(folder : Union[str, None] = None,
          auto_install : bool = False,
          save_hashes_flag: bool = False,
          verify_blocks_flag: bool = False
    ):
    """
    Run setup
    """
    from fastapi_blocks import BlockManager
    
    cwd = Path.cwd()
    
    if folder:
        folder_path = cwd / folder
        if not folder_path.exists():
            folder_path.mkdir()
    
        manager = BlockManager(
            blocks_folder=folder, 
            late_load=True, 
            allow_installs=auto_install, 
            verify_blocks=verify_blocks_flag
        )
    else:
        manager = BlockManager(
            allow_installs=auto_install, 
            verify_blocks=verify_blocks_flag
        )
    
    if not manager._setup(run_hooks=True, save_hashes=save_hashes_flag):
        # If hasn't been setup before, add to gitignore.
        gitignore_path = cwd / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, "r") as f:
                lines = f.read()
            if "blockmanager/" not in lines:
                with open(gitignore_path, "a") as f:
                    f.write("\nblockmanager/\n")
        else:
            with open(gitignore_path, "w") as f:
                f.write("blockmanager/\n")

    print(f"Setup complete. Folder: {manager.blocks_folder}\n")


def make_block(block_name : str, run_setup : bool):
    """
    Creates a new block.
    """
    from fastapi_blocks import BlockManager
    cwd = Path.cwd()
    
    try:
        block_manager = BlockManager()
    except Exception as e:
        print(f"Error: {e}")
        return
    
    if not block_manager.block_manager_info:
        print(f"Error: 'block_manager_info' is empty. Please run setup first")
        return
    
    # Get extra settings from blockmanager
    extra_settings_class = block_manager._build_block_settings_class()
    
    temp_class = extra_settings_class(
        name=block_name, 
        version="0.1"
    )
    extra_settings_dict = temp_class.get_dict()
    extra_settings_dict["template_router"] = "router"
    extra_settings_dict["api_router"] = "api_router"
    extra_settings_dict["extra_block_settings"] = "settings"
    
    # copy placeholder
    source = Path(__file__).parent / "default_blocks" / "block_template"
    dest = Path.cwd() / block_manager.blocks_folder / block_name
    
    if dest.exists():
        print(f"Error: '{block_name}' already exists.")
        return
    
    print(f"Copying 'block_template' to '{dest}'...")
    shutil.copytree(source, dest)
    print("Initialization complete.")
    
    # Make toml
    toml_path = dest / "block_config.toml"
    import tomli_w
    
    with open(toml_path, "wb") as f:
        tomli_w.dump(extra_settings_dict, f)
        
    # gitignore
    
    gitignore_path = cwd / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            lines = f.read()
        if "block_infos.toml" not in lines:
            with open(gitignore_path, "a") as f:
                f.write("\nblock_infos.toml\n")
    else:
        with open(gitignore_path, "w") as f:
            f.write("block_infos.toml\n")
            
    # Run setup
    if run_setup:
        print("Running setup...")
        block_manager._setup(run_hooks=True)
            
    print("Block creation complete")


def init_project():
    """
    Initializes a new project by copying the default homepage_block.
    """
    source_dir = Path(__file__).parent / "default_blocks" / "homepage_block"
    dest_dir = Path.cwd() / "blocks" / "homepage_block"

    if dest_dir.exists():
        print("Error: 'blocks/homepage_block' already exists.")
        return

    print(f"Copying 'homepage_block' to '{dest_dir}'...")
    shutil.copytree(source_dir, dest_dir)
    print("Initialization complete.")


def main():
    """
    The main entry point for the command-line interface.
    """
    parser = argparse.ArgumentParser(description="A CLI for managing FastAPI Blocks.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands.")

    # Init command
    parser_init = subparsers.add_parser("init", help="Initializes a new project.")
    
    # Setup command
    parser_setup = subparsers.add_parser("setup", help="Runs setup")
    parser_setup.add_argument("--folder", "-f", type=str, default=None, help="The folder path where the blocks are stored")
    parser_setup.add_argument("--auto-install", "-A", action="store_true", help="Automatically install missing dependencies", default=False)
    parser_setup.add_argument("--save-hashes", "-S", action="store_true", help="Save current block hashes after setup.", default=False)
    parser_setup.add_argument("--verify-blocks", "-V", action="store_false", help="Enable hash-based block verification.", default=True)

    # Create command
    parser_create = subparsers.add_parser("create", help="Creates a new block.")
    parser_create.add_argument("block_name", type=str, help="The name of the block to create.")
    parser_create.add_argument("--setup", "-S", action="store_true", help="Run setup", default=False)

    args = parser.parse_args()

    if args.command == "init":
        init_project()
    elif args.command == "setup":
        setup(args.folder, args.auto_install, args.save_hashes, args.verify_blocks)
    elif args.command == "create":
        make_block(args.block_name, args.setup)
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main()
