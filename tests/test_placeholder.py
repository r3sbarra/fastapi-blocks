from fastapi_blocks import BlockManager
import os

def test_nothing(test_app):
    assert test_app != None
    
def test_tmp_file(tmp_path):
    assert tmp_path.is_dir()
    assert tmp_path.exists()
    
def test_block_manager_init(tmp_path, test_app, tmpdir):
    tmpdir.mkdir("blocks")
    block_manager = BlockManager(blocks_folder="blocks", working_dir=str(tmp_path), skip_installs=True)
    app = block_manager.init_app(test_app.app)
    assert app != None
    assert app.block_manager != None
    
    # Verify that block_infos was created
    assert os.path.exists(os.path.join(tmp_path, 'block_infos.toml'))