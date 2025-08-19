import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from fastapi_blocks import cli

class TestCLI(unittest.TestCase):

    @patch('fastapi_blocks.cli.init_project')
    def test_init_command(self, mock_init_project):
        """Test the 'init' command."""
        sys.argv = ['fastapi-blocks', 'init']
        cli.main()
        mock_init_project.assert_called_once()

    @patch('fastapi_blocks.cli.setup')
    def test_setup_command(self, mock_setup):
        """Test the 'setup' command with arguments."""
        sys.argv = ['fastapi-blocks', 'setup', '--folder', 'my_blocks', '-A', '-S', '-V']
        cli.main()
        mock_setup.assert_called_once_with('my_blocks', True, True, False)

    @patch('fastapi_blocks.cli.make_block')
    def test_create_command(self, mock_make_block):
        """Test the 'create' command."""
        sys.argv = ['fastapi-blocks', 'create', 'my_new_block']
        cli.main()
        mock_make_block.assert_called_once_with('my_new_block', False)

    def test_main_no_command(self):
        """Test running the CLI with no command."""
        sys.argv = ['fastapi-blocks']
        with patch('argparse.ArgumentParser.print_help') as mock_print_help:
            cli.main()
            mock_print_help.assert_called_once()

if __name__ == '__main__':
    unittest.main()
