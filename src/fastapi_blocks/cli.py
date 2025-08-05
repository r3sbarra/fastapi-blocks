import argparse
import shutil
import os
from pathlib import Path


def setup(folder : str = "blocks"):
    """
    Run setup
    """
    from fastapi import FastAPI
    from fastapi_blocks import BlockManager
    
    cwd = os.getcwd()
    
    if not os.path.exists(os.path.join(cwd, folder)):
        os.mkdir(os.path.join(cwd, folder))
    
    app = FastAPI()    
    manager = BlockManager(blocks_folder=folder)
    if manager._setup(save_mako=True):
        print(f"Setup complete. Folder: {folder}")
    else:
        print(f"Setup failed. Folder: {folder}")


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
    parser_setup.add_argument("folder_path", type=str, default="blocks", help="The folder path where the blocks are stored")

    # Example command
    parser_hello = subparsers.add_parser("hello", help="Prints a hello message.")
    parser_hello.add_argument("name", type=str, help="The name to say hello to.")

    args = parser.parse_args()

    if args.command == "init":
        init_project()
    elif args.command == "hello":
        print(f"Hello, {args.name}!")
    elif args.command == "setup":
        setup(args.folder_path)
    else:
        parser.print_help()