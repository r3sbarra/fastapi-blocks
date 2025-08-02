from fastapi_blocks import BlockSettingsMixin
import os
from typing import Optional

class Settings(BlockSettingsMixin):
    schemas : Optional[str] = None
    
    def get_dict(self) -> dict:
        super_dict = super().get_dict()
        super_dict['schemas'] = self._path_to_module(os.path.join(self.block_path, self.schemas)) if self.schemas else None
        return super_dict