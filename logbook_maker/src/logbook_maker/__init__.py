import base64
import io
import os
import pathlib
from importlib.resources import files
from typing import cast

from cairosvg import svg2pdf
from PIL import Image, ImageFile

from logbook_maker.qr_code_maker import generate_code, make_qr_code

_template_path = str(files("logbook_maker").joinpath("templates"))
if not os.path.exists(_template_path):
    _template_path = "./templates"

TEMPLATE_PATH = pathlib.Path(_template_path) / "logbook.svg"


def base64_encode(fp: io.BufferedIOBase) -> str:
    fp.seek(0)
    return base64.b64encode(fp.read()).decode("utf-8")


def generate(bg_path: str | pathlib.Path, output_path: str | io.BufferedIOBase) -> None:
    with open(TEMPLATE_PATH) as f:
        template = f.read()
    with Image.open(fp=bg_path) as bg:
        bg = cast(ImageFile.ImageFile, bg)
        mimetype = cast(str, bg.get_format_mimetype())  # type: ignore
        base64_bg = base64_encode(bg.fp)

    format_values = {"BG_WIDTH": bg.width, "BG_HEIGHT": bg.height, "BG_MIMETYPE": mimetype, "BG_BASE64": base64_bg}

    for i in range(11):
        code = generate_code(i)
        qr = make_qr_code(code)
        buffer = io.BytesIO()
        qr.save(buffer)
        base64_qr = base64_encode(buffer)

        format_values[f"QR{i + 1}_BASE64"] = base64_qr

    template = template.format(**format_values)

    svg2pdf(bytestring=template, write_to=output_path)
