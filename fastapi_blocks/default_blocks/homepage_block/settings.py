from fastapi_blocks import BlockSettingsMixin

class Settings(BlockSettingsMixin):
    is_main : bool = False
    
    def get_dict(self) -> dict:
        super_dict = super().get_dict()
        super_dict['is_main'] = self.is_main
        return super_dict