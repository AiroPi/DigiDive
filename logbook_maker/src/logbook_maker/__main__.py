import io
import pathlib

import pypdf
import typer

import logbook_maker

app = typer.Typer()


@app.command()
def single(background_image_path: str, output_path: str):
    """
    Generate a single logbook page as a PDF.
    """

    logbook_maker.generate(background_image_path, output_path)


@app.command()
def batch(background_images_directory: str, output_path: str):
    """
    Generate a PDF with multiple pages, using different images for background.
    """
    with pypdf.PdfWriter() as merger:
        for img_path in pathlib.Path(background_images_directory).iterdir():
            buffer = io.BytesIO()
            logbook_maker.generate(img_path, buffer)

            merger.append(buffer)

        merger.write(output_path)


@app.command()
def qr_sticker_page():
    """
    Generate a PDF with multiple QR code in one sigle page.
    The goal is to print them on a sticker paper.
    """


@app.command()
def qr_single():
    """
    Generate one single QR code as a PNG.
    """


if __name__ == "__main__":
    app()
