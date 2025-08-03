from fastapi_blocks import BlockSettingsMixin
import os
from typing import Optional

class Settings(BlockSettingsMixin):
    schemas : Optional[str] = None
    
    def get_dict(self) -> dict:
        super_dict = super().get_dict()
        if self.schemas:
            super_dict['schemas'] = self._path_to_module(os.path.join(self.block_path, self.schemas))
        return super_dict