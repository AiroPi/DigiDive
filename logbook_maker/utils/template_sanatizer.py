# Edit exported SVG from figma to simplify the image implementation.

import re
import sys

with open(sys.argv[1]) as f:
    template = f.read()

    result = re.finditer(r"<image id=\"image.+/>\n", template)
    for i, match in enumerate(result):
        template = template.replace(match.group(), "")

    result = re.finditer(r"<rect (.+)fill=\"url\(#pattern[^)]+\)\"/>", template)
    for i, match in enumerate(result):
        if i == 0:
            template = template.replace(
                match.group(),
                f'<image {match.group(1)}href="data:{{BG_MIMETYPE}};base64,{{BG_BASE64}}" preserveAspectRatio="xMidYMid slice"/>',
            )
        template = template.replace(
            match.group(), f'<image {match.group(1)}href="data:image/png;base64,{{QR{i}_BASE64}}"/>'
        )

    result = re.finditer(r"<pattern (?:.|\n)+?</pattern>\n", template)
    for i, match in enumerate(result):
        template = template.replace(match.group(), "")

    template = re.sub(
        r"<image id=\"([^\"]+)\" width=\"[^\"]+\" height=\"[^\"]+\" xlink:href=\"[^\"]+\"/>",
        r'<image id="\1" width="{BG_WIDTH}" height="{BG_HEIGHT}" xlink:href="data:{BG_MIMETYPE};base64,{BG_BASE64}"/>',
        template,
    )

    with open("template.svg", "w") as f:
        f.write(template)
