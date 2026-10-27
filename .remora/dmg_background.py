#!/usr/bin/env python3
"""Build the Ray DMG background from the same icon used by the app bundle."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFont


if len(sys.argv) != 4:
    raise SystemExit("usage: dmg_background.py OldTitle NewTitle /path/to/checkout")

old_title, new_title, root_arg = sys.argv[1:]
root = Path(root_arg)
icon_path = root / ".remora" / f"{old_title}.png"
output = root / "packaging" / "macos" / "dmg" / "background.tiff"
if not icon_path.is_file() or not output.parent.is_dir():
    raise SystemExit("Ray icon or DMG directory is missing")

ACCENTS = {
    "DesignRay": (249, 78, 145),
    "EffectRay": (190, 97, 246),
    "FigRay": (227, 91, 211),
    "FilmRay": (155, 104, 246),
    "LightRay": (112, 199, 236),
    "PdfRay": (230, 96, 102),
    "PhotoRay": (61, 157, 239),
    "SoundRay": (55, 200, 220),
    "VectorRay": (245, 167, 41),
}


def font(size: int, bold: bool = False):
    candidates = (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default(size=size)


with Image.open(icon_path) as source:
    icon = source.convert("RGBA")


def render(scale: int) -> Image.Image:
    width, height = 660 * scale, 400 * scale
    canvas = Image.new("RGB", (width, height), (246, 247, 251))
    draw = ImageDraw.Draw(canvas)

    def box(coords, fill, radius=0, outline=None, line_width=1):
        coords = tuple(round(n * scale) for n in coords)
        draw.rounded_rectangle(
            coords,
            radius=round(radius * scale),
            fill=fill,
            outline=outline,
            width=round(line_width * scale),
        )

    def text(x, y, value, size, color, bold=False):
        draw.text((round(x * scale), round(y * scale)), value,
                  font=font(size * scale, bold), fill=color)

    accent = ACCENTS.get(new_title, (82, 142, 238))
    box((0, 0, 232, 400), (19, 27, 46))
    box((26, 25, 205, 30), accent, radius=2)
    text(27, 41, "RAY / DESKTOP", 12, (190, 202, 224), True)

    # Display exactly the personalized icon supplied for the app. It is also
    # used for the .icns/.ico, so this panel cannot drift from the installer.
    icon_size = 184 * scale
    visible_icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    canvas.paste(visible_icon, (24 * scale, 111 * scale), visible_icon)
    text(27, 334, new_title, 20, (255, 255, 255), True)
    text(27, 365, "Made for your Mac", 11, (170, 184, 210))

    text(270, 42, new_title, 30, (28, 37, 58), True)
    text(271, 83, "INSTALLATION", 11, (104, 116, 140), True)
    box((270, 111, 625, 113), accent, radius=1)

    # Finder draws the real app and Applications icons at (326,205) and
    # (574,205); leave these areas clear rather than baking icon art in twice.
    box((418, 204, 476, 206), accent, radius=1)
    draw.polygon(
        [(round(475 * scale), round(198 * scale)),
         (round(485 * scale), round(205 * scale)),
         (round(475 * scale), round(212 * scale))],
        fill=accent,
    )
    box((270, 327, 625, 328), (211, 218, 230))
    text(270, 344, "DRAG TO APPLICATIONS TO INSTALL", 11, (92, 105, 129), True)
    return canvas


one = render(1)
two = render(2)
one.save(output, format="TIFF", save_all=True, append_images=[two],
         compression="tiff_adobe_deflate", dpi=(72, 72))
with Image.open(output) as check:
    if check.n_frames != 2 or check.size != (660, 400):
        raise SystemExit("Ray DMG background failed validation")
    check.seek(1)
    if check.size != (1320, 800):
        raise SystemExit("Ray DMG HiDPI background failed validation")
print(f"{new_title}: Ray DMG background generated from {icon_path.name}")
