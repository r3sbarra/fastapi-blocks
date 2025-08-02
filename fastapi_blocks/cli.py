import argparse
import shutil
from pathlib import Path


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

    # Example command
    parser_hello = subparsers.add_parser("hello", help="Prints a hello message.")
    parser_hello.add_argument("name", type=str, help="The name to say hello to.")

    args = parser.parse_args()

    if args.command == "init":
        init_project()
    elif args.command == "hello":
        print(f"Hello, {args.name}!")
    else:
        parser.print_help()