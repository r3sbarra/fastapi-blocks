import os
import json
from fastapi_blocks import BlockManager
import pytest
from dirhash import dirhash
from fastapi import FastAPI, APIRouter
import importlib.util
import sys

@pytest.fixture
def tmp_block_dir(tmp_path):
    block_dir = tmp_path / "test_block"
    block_dir.mkdir()
    (block_dir / "file1.py").write_text("print('hello')")
    (block_dir / "file2.toml").write_text("[block]\nname = 'test'")
    return block_dir

@pytest.fixture
def block_manager_instance(tmp_path):
    # Ensure the blockmanager directory exists within the temporary working directory
    block_manager_path = tmp_path / "blockmanager"
    block_manager_path.mkdir(exist_ok=True)
    return BlockManager(working_dir=tmp_path, late_load=True)

def test_save_block_hashes(tmp_block_dir, block_manager_instance):
    block_manager_instance._save_block_hashes(tmp_block_dir)
    
    hashes_file = tmp_block_dir.parent / "blockmanager" / "block_hashes.json"
    assert hashes_file.exists()
    
    with open(hashes_file, 'r') as f:
        hashes = json.load(f)
    
    block_name = tmp_block_dir.name
    assert block_name in hashes
    expected_hash = dirhash(tmp_block_dir, 'sha256', match=["*.py", "*.toml"])
    assert hashes[block_name] == expected_hash

def test_verify_block_hash_verify_blocks_false(block_manager_instance):
    block_manager_instance.verify_blocks = False
    assert block_manager_instance._verify_block_hash("dummy_path") == True

def test_verify_block_hash_no_hashes_file(tmp_block_dir, block_manager_instance):
    block_manager_instance.verify_blocks = True
    # Ensure no block_hashes.json exists initially
    hashes_file = tmp_block_dir.parent / "blockmanager" / "block_hashes.json"
    if hashes_file.exists():
        os.remove(hashes_file)
    
    assert block_manager_instance._verify_block_hash(tmp_block_dir) == True

def test_verify_block_hash_match(tmp_block_dir, block_manager_instance):
    block_manager_instance.verify_blocks = True
    block_manager_instance._save_block_hashes(tmp_block_dir)
    
    assert block_manager_instance._verify_block_hash(tmp_block_dir) == True

def test_verify_block_hash_no_match(tmp_block_dir, block_manager_instance):
    block_manager_instance.verify_blocks = True
    block_manager_instance._save_block_hashes(tmp_block_dir)
    
    # Modify a file to change the hash
    (tmp_block_dir / "file1.py").write_text("print('hello world')")
    
    assert block_manager_instance._verify_block_hash(tmp_block_dir) == False

def test_block_manager_init_no_block_infos_toml(tmp_path):
    # This test expects an exception because block_infos.toml does not exist
    # Ensure the blockmanager directory does NOT exist for this test
    block_manager_path = tmp_path / "blockmanager"
    if block_manager_path.exists():
        import shutil
        shutil.rmtree(block_manager_path)

    # Ensure the BlockManager singleton is reset for this test
    if BlockManager in BlockManager._instances:
        del BlockManager._instances[BlockManager]

    with pytest.raises(Exception, match="No block_infos.toml found. Please run setup first"):
        BlockManager(working_dir=tmp_path, late_load=False)

def test_basic(test_app, block_manager_instance):
    block_manager_instance.init_app(test_app.app)
    assert test_app.app.block_manager == block_manager_instance