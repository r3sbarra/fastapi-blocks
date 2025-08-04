from typing import Optional, List
from fastapi_blocks import BlockSettingsMixin

def _say_hi(*args, **kwargs):
    if 'logger' in kwargs.keys():
        logger = kwargs['logger']
        logger.info("Hi")
    else:
        print("Hi")
    
class Settings(BlockSettingsMixin):
    is_main : Optional[bool] = None
    start_hooks : List = [_say_hi]