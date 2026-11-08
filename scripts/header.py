"""Builds header-dark.webp and header-light.webp: the info lines and the name in Google Sans
Flex (rounded), next to the spinning snow leopard cube from cube.webp.

Edit ROWS below, then run from the repo root:

    nix-shell -p 'python3.withPackages (p: [p.pillow p.fonttools p.uharfbuzz])' resvg \
      --run 'python3 scripts/header.py'

Text is shaped with HarfBuzz (kerning) and drawn from the font's outlines at exact
positions, then rasterised by resvg; Pillow's own text drawing skips kerning and snaps each
letter to a whole pixel, which made the spacing uneven.
"""

import io
import subprocess

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageSequence

ROWS = [
    ("stack", "rust · nix · qml"),
    (None, "python · typescript"),
    ("building", "wave-launcher · aial"),
    (None, "vapor · palettegen"),
    (None, "t3code-dithered"),
]
NAME = "Kalkaro"
# Text colour per GitHub theme. The header is transparent, so white would vanish on light.
THEMES = {"dark": "ffffff", "light": "1f2328"}

W, H = 760, 290
CUBE_AT = (480, 0)  # where cube.webp's 280x270 frames go
SIZE, NAME_SIZE = 22, 76
PITCH, TOP = 32, 30  # row spacing; first row's middle
GROUP_GAP, NAME_GAP = 10, 34  # before the second group; from the last row to the name's capitals
VALUES_X = 124
CAP = 0.716  # Google Sans Flex cap height, in ems


class Face:
    def __init__(self, path):
        self.ft = TTFont(path)
        self.glyphs = self.ft.getGlyphSet()
        self.order = self.ft.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(path)))
        self.upem = self.ft["head"].unitsPerEm

    def path(self, text, x, baseline, size):
        """SVG path data for `text` with its baseline at (x, baseline)."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {})
        scale, pen_x, d = size / self.upem, 0, []
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            pen = SVGPathPen(self.glyphs)
            gx = x + (pen_x + pos.x_offset) * scale
            gy = baseline - pos.y_offset * scale
            self.glyphs[self.order[info.codepoint]].draw(TransformPen(pen, (scale, 0, 0, -scale, gx, gy)))
            d.append(pen.getCommands())
            pen_x += pos.x_advance
        return " ".join(d)


def text_layer(colour):
    body = Face("fonts/GoogleSansFlex-Regular.ttf")
    label = Face("fonts/GoogleSansFlex-SemiBold.ttf")
    paths, baseline = [], 0.0
    for i, (key, value) in enumerate(ROWS):
        # Capitals centred on the row; the second group starts a little lower.
        baseline = TOP + PITCH * i + (GROUP_GAP if i >= 2 else 0) + CAP * SIZE / 2
        if key:
            paths.append(label.path(key, 5, baseline, SIZE))
        paths.append(body.path(value, VALUES_X, baseline, SIZE))
    paths.append(label.path(NAME, 1, baseline + NAME_GAP + CAP * NAME_SIZE, NAME_SIZE))
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"><path fill="#{colour}" d="{" ".join(paths)}"/></svg>'
    png = subprocess.run(["resvg", "-", "-c"], input=svg.encode(), capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGBA")


def main():
    cube = [(f.convert("RGBA"), f.info.get("duration") or 62) for f in ImageSequence.Iterator(Image.open("cube.webp"))]
    for theme, colour in THEMES.items():
        text = text_layer(colour)
        frames = []
        for frame, _ in cube:
            f = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            f.paste(frame, CUBE_AT)
            f.alpha_composite(text)
            frames.append(f)
        out = f"header-{theme}.webp"
        frames[0].save(out, save_all=True, append_images=frames[1:], duration=[d for _, d in cube], loop=0,
                       quality=85, method=6)
        print(f"wrote {out}: {len(frames)} frames")


main()
