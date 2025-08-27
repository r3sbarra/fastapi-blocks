from typing import Optional, List
from fastapi_blocks import BlockSettingsMixin
    
class Settings(BlockSettingsMixin):
    # Add settings that you'd other 'blocks' to use/share
    
    # is_main : Optional[bool] = None

    def _start_hooks(self) -> List:
        return super()._start_hooks() + []