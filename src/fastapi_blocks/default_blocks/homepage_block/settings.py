from typing import Optional, List
from fastapi_blocks import BlockSettingsMixin

def _say_hi(*args, **kwargs):
    if 'logger' in kwargs.keys():
        logger = kwargs['logger']
        logger.info("Hi")
    else:
        print("Hi")
    
class Settings(BlockSettingsMixin):

    def _start_hooks(self) -> List:
        return super()._start_hooks() + [_say_hi]