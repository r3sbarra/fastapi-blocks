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


def make_block(block_name):
    """
    Creates a new block.
    """
    from fastapi_blocks import BlockManager
    cwd = Path.cwd()
    block_manager = BlockManager()
    block_manager._load_settings_toml()
    
    if not block_manager.block_manager_info:
        print(f"Error: 'block_manager_info' is empty. Start the app at least once")
        return
    
    # copy placeholder
    source = Path(__file__).parent / "default_blocks" / "block_template"
    dest = Path.cwd() / "blocks" / block_name
    
    if dest.exists():
        print(f"Error: '{block_name}' already exists.")
        return
    
    print(f"Copying 'block_template' to '{dest}'...")
    shutil.copytree(source, dest)
    print("Initialization complete.")
    gitignore_path = cwd / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, "r") as f:
            lines = f.readlines()
        if "block_infos.toml\n" not in lines:
            with open(gitignore_path, "a") as f:
                f.write("block_infos.toml\n")
    else:
        with open(gitignore_path, "w") as f:
            f.write("block_infos.toml\n")
            
    print("setup complete")


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

    # Verify command
    parser_verify = subparsers.add_parser("verify", help="Enables or disables block verification.")
    parser_verify.add_argument("status", type=str, choices=['on', 'off'], help="The status of block verification.")

    args = parser.parse_args()

    if args.command == "init":
        init_project()
    elif args.command == "setup":
        setup(args.folder, args.auto_install, args.save_hashes, args.verify_blocks)
    elif args.command == "create":
        make_block(args.block_name)
    elif args.command == "verify":
        if args.status == 'on':
            print("Block verification enabled.")
        elif args.status == 'off':
            print("Block verification disabled.")
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main()
