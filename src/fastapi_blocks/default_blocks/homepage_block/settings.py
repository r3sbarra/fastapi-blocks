from typing import Optional
from fastapi_blocks import BlockSettingsMixin

class Settings(BlockSettingsMixin):
    is_main : Optional[bool] = None
    
    def get_dict(self) -> dict:
        super_dict = super().get_dict()
        if self.is_main != None:
            super_dict['is_main'] = self.is_main
        return super_dict