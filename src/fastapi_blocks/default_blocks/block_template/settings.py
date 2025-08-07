from typing import Optional, List
from fastapi_blocks import BlockSettingsMixin
    
class Settings(BlockSettingsMixin):
    is_main : Optional[bool] = None

    def _start_hooks(self) -> List:
        return super()._start_hooks() + []