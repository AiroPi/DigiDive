import io
from typing import Any

def svg2pdf(
    bytestring: bytes | str | None = None,
    *,
    file_obj: io.FileIO | None = None,
    url: str | None = None,
    dpi: int = 96,
    parent_width: int | None = None,
    parent_height: int | None = None,
    scale: float = 1,
    unsafe: bool = False,
    background_color: Any = None,
    negate_colors: bool = False,
    invert_images: bool = False,
    write_to: Any = None,
    output_width: int | None = None,
    output_height: int | None = None,
) -> bytes: ...
