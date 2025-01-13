# nb: these type hint are not correct, but enough for my purpose

import io

ERROR_CORRECT_L: int
ERROR_CORRECT_M: int
ERROR_CORRECT_Q: int
ERROR_CORRECT_H: int

class BaseImage:
    def save(self, path: str | io.BufferedIOBase) -> None: ...

class QRCode:
    def __init__(self, error_correction: int, border: int) -> None: ...
    def add_data(self, data: str) -> None: ...
    def make_image(self) -> BaseImage: ...
