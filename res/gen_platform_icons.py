#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate BlinkDesk platform icons from the master icon (res/icon.png).

The master is a full-bleed, rounded-corner, dark tile with a colored glyph in
the centre (keep its rounded corners where transparency is wanted, and fill the
transparent corners with the tile frame colour where a platform forbids alpha,
e.g. iOS, Android legacy launcher icons).

Usage:
    python gen_platform_icons.py [--corner-radius 0.08]   # regenerate
    python gen_platform_icons.py --dry-run                # print what would happen

Steps:
  0. res/icon.png is first rewritten with its 4 corners cut transparent
     (rounded). Radius = --corner-radius fraction of the icon size.
  1. All platform icons below are generated from that new rounded master.

Outputs (paths relative to repo root):
  Windows
    res/icon.ico                                   multi-size 16..256
    res/tray-icon.ico                              multi-size 16..48
    flutter/windows/runner/resources/app_icon.ico  multi-size 16..256
    flutter/assets/icon.ico                        multi-size 16..256  (runtime window icon)
    flutter/assets/icon.png                        256x256 RGBA tile   (tray/UI fallback)
  macOS
    res/mac-icon.png                             master copy (launcher source used by pubspec)
    flutter/macos/Runner/AppIcon.icns              full .icns (16..1024)
    res/mac-tray-dark-x2.png                       64x64 white glyph template
  Linux
    res/32x32.png res/64x64.png res/128x128.png res/128x128@2x.png
    res/scalable.svg                               raster-backed scalable icon
  iOS
    flutter/ios/Runner/Assets.xcassets/AppIcon.appiconset/*.png  (opaque, sizes from Contents.json)
  Android
    flutter/android/app/src/main/res/mipmap-*/ic_launcher.png / ic_launcher_round.png (opaque tile)
    flutter/android/app/src/main/res/mipmap-*/ic_launcher_foreground.png (adaptive, tile at 90%)
    flutter/android/app/src/main/res/mipmap-*/ic_stat_logo.png (white glyph)
    flutter/android/app/src/main/res/values/ic_launcher_background.xml (frame colour)
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import struct
import sys

from PIL import Image, ImageChops, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))     # .../res
ROOT = os.path.dirname(HERE)                           # repo root
FLUTTER = os.path.join(ROOT, "flutter")

MASTER_PATH = os.path.join(HERE, "icon.png")
DRY = "--dry-run" in sys.argv

# Fraction of the icon size that is cut from each corner to make it rounded.
# res/icon.png is first regenerated with 4 transparent (rounded) corners and
# every derived icon is then generated from that rounded master.
# Override on the command line, e.g.  python gen_platform_icons.py --corner-radius 0.10
CORNER_RADIUS_FRAC = 0.2
if "--corner-radius" in sys.argv:
    CORNER_RADIUS_FRAC = float(sys.argv[sys.argv.index("--corner-radius") + 1])

_MASTER: Image.Image | None = None


def round_corners(im: Image.Image, frac: float | None = None) -> Image.Image:
    """Cut the four corners off `im`, making them transparent (rounded).

    Idempotent: already-transparent corners stay transparent.
    """
    im = im.convert("RGBA")
    w, h = im.size
    frac = CORNER_RADIUS_FRAC if frac is None else frac
    radius = max(1, int(min(w, h) * frac))
    alpha = im.getchannel("A")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, w - 1, h - 1], radius=radius, fill=255)
    im.putalpha(ImageChops.multiply(alpha, mask))
    return im


def master() -> Image.Image:
    global _MASTER
    if _MASTER is None:
        # First round the master's corners, then derive everything from it.
        _MASTER = round_corners(Image.open(MASTER_PATH).convert("RGBA"))
    return _MASTER


def frame_colour() -> tuple[int, int, int]:
    """Sample the tile frame (just inside the top/left/right/bottom edges)."""
    im = master()
    w, h = im.size
    pts = [(0.5, 0.02), (0.5, 0.98), (0.02, 0.5), (0.98, 0.5), (0.25, 0.02),
           (0.75, 0.98)]
    rs = gs = bs = n = 0
    for fx, fy in pts:
        p = im.getpixel((int(w * fx), int(h * fy)))
        if p[3] > 200:
            rs += p[0]; gs += p[1]; bs += p[2]; n += 1
    if n == 0:
        return (33, 33, 32)
    return (rs // n, gs // n, bs // n)


BG = frame_colour()


def _out(path: str, rel_to_root: bool = True) -> str:
    return os.path.join(ROOT, path) if rel_to_root else path


def tile(px: int) -> Image.Image:
    """Master scaled to px, keeping rounded-corner transparency."""
    return master().resize((px, px), Image.Resampling.LANCZOS)


def tile_opaque(px: int) -> Image.Image:
    """Master scaled to px with transparent corners filled by the frame colour."""
    im = tile(px)
    bg = Image.new("RGBA", im.size, BG + (255,))
    bg.alpha_composite(im)
    return bg.convert("RGB")


def glyph_mask(px: int) -> Image.Image:
    """Monochrome alpha mask of the glyph (colourless) at px size.

    A coloured glyph on any neutral background (dark or white) is isolated by
    chroma alone, so this works regardless of the master's background colour.
    """
    im = master()
    w, h = im.size
    m = Image.new("L", (w, h), 0)
    mp = m.load()
    sp = im.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = sp[x, y]
            if a <= 30:
                continue
            chroma = max(r, g, b) - min(r, g, b)
            val = int(min(255, chroma * 2.2))
            if val:
                mp[x, y] = val
    return m.resize((px, px), Image.Resampling.LANCZOS)


def glyph_white(px: int) -> Image.Image:
    """White glyph on transparent canvas."""
    mask = glyph_mask(px)
    out = Image.new("RGBA", (px, px), (255, 255, 255, 0))
    out.putalpha(mask)
    return out


def glyph_coloured(px: int, colour: tuple[int, int, int]) -> Image.Image:
    mask = glyph_mask(px)
    out = Image.new("RGBA", (px, px), colour + (0,))
    out.putalpha(mask)
    return out


def save_png(im: Image.Image, path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    if DRY:
        print("  [dry-run] would write", os.path.relpath(path, ROOT))
        return
    im.save(path, "PNG")
    print("  wrote", os.path.relpath(path, ROOT))


# ---------------------------------------------------------------- Windows
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
TRAY_ICO_SIZES = (16, 20, 24, 32, 48)


def save_ico(path: str, sizes: tuple[int, ...]) -> None:
    sizes = sorted(set(sizes))
    frames = [tile(s) for s in sizes]          # ascending; largest is the base
    if DRY:
        print("  [dry-run] would write", os.path.relpath(path, ROOT))
        return
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    # Base image must be the biggest: smaller append_images are kept as-is,
    # and Pillow falls back to resizing the base for any listed size.
    frames[-1].save(path, format="ICO",
                    sizes=[(s, s) for s in sizes],
                    append_images=frames[:-1])
    print("  wrote", os.path.relpath(path, ROOT))


def gen_windows() -> None:
    print("[Windows]")
    save_ico(_out("res/icon.ico"), ICO_SIZES)
    save_ico(_out("res/tray-icon.ico"), TRAY_ICO_SIZES)
    save_ico(_out("flutter/windows/runner/resources/app_icon.ico"), ICO_SIZES)
    save_ico(_out("flutter/assets/icon.ico"), ICO_SIZES)      # runtime window icon
    save_png(tile(256), _out("flutter/assets/icon.png"))      # tray/UI fallback


# ----------------------------------------------------------------- macOS
ICNS_TYPES = [  # (OSType, pixel size) -- modern icns stores these as PNG
    (b"icp4", 16), (b"icp5", 32), (b"ic07", 128), (b"ic08", 256),
    (b"ic09", 512), (b"ic10", 1024),
    (b"ic11", 32), (b"ic12", 64), (b"ic13", 256), (b"ic14", 512),
]


def save_icns(path: str) -> None:
    streams = {}
    for _t, px in ICNS_TYPES:
        if px not in streams:
            buf = io.BytesIO()
            tile(px).save(buf, "PNG")
            streams[px] = buf.getvalue()
    payload = bytearray()
    for typ, px in ICNS_TYPES:
        png = streams[px]
        payload += typ + struct.pack(">I", 8 + len(png)) + png
    header = b"icns" + struct.pack(">I", 8 + len(payload))
    if DRY:
        print("  [dry-run] would write", os.path.relpath(path, ROOT))
        return
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + payload)
    print("  wrote", os.path.relpath(path, ROOT))


def gen_macos() -> None:
    print("[macOS]")
    # Launcher source used by pubspec (flutter_launcher_icons macos image_path):
    # keep it an exact copy of the rounded master so it never goes stale.
    save_png(master(), _out("res/mac-icon.png"))
    save_icns(_out("flutter/macos/Runner/AppIcon.icns"))
    # Tray template (name says "dark x2"); colour is not important, it is tinted.
    save_png(glyph_white(64), _out("res/mac-tray-dark-x2.png"))


# ------------------------------------------------------------------ Linux
def gen_linux() -> None:
    print("[Linux]")
    save_png(tile(32), _out("res/32x32.png"))
    save_png(tile(64), _out("res/64x64.png"))
    save_png(tile(128), _out("res/128x128.png"))
    save_png(tile(256), _out("res/128x128@2x.png"))

    # Raster-backed "scalable" icon so .desktop/AppImage/deb show BlinkDesk too.
    buf = io.BytesIO()
    tile(512).save(buf, "PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'width="512" height="512" viewBox="0 0 512 512">'
        f'<image width="512" height="512" '
        f'xlink:href="data:image/png;base64,{b64}"/></svg>\n'
    )
    if DRY:
        print("  [dry-run] would write", os.path.relpath(_out("res/scalable.svg"), ROOT))
        return
    with open(_out("res/scalable.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    print("  wrote", os.path.relpath(_out("res/scalable.svg"), ROOT))


# -------------------------------------------------------------------- iOS
def _ios_size_from_name(name: str) -> int:
    m = re.match(r"Icon-App-([\d.]+)x[\d.]+@(\d)x", name)
    if not m:
        raise ValueError(f"unexpected iOS icon name: {name}")
    return int(round(float(m.group(1)) * int(m.group(2))))


def gen_ios() -> None:
    print("[iOS]")
    appiconset = _out(
        "flutter/ios/Runner/Assets.xcassets/AppIcon.appiconset")
    json_path = os.path.join(appiconset, "Contents.json")
    with open(json_path, encoding="utf-8") as f:
        spec = json.load(f)
    done = set()
    for entry in spec.get("images", []):
        fn = entry.get("filename")
        if not fn or fn in done:
            continue
        done.add(fn)
        save_png(tile_opaque(_ios_size_from_name(fn)),
                 os.path.join(appiconset, fn))


# ---------------------------------------------------------------- Android
ANDROID_MIPMAP = {
    "mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0,
}


def gen_android() -> None:
    print("[Android]")
    base = _out("flutter/android/app/src/main/res")
    for dpi, scale in ANDROID_MIPMAP.items():
        d = os.path.join(base, f"mipmap-{dpi}")
        # legacy launcher icons (square, opaque)
        save_png(tile_opaque(int(48 * scale)), os.path.join(d, "ic_launcher.png"))
        save_png(tile_opaque(int(48 * scale)),
                 os.path.join(d, "ic_launcher_round.png"))
        # adaptive foreground: 108dp canvas, tile at 90% keeps glyph in safe zone
        canvas = int(108 * scale)
        fg = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
        inner = int(canvas * 0.9)
        t = tile(inner)
        fg.alpha_composite(t, ((canvas - inner) // 2, (canvas - inner) // 2))
        save_png(fg, os.path.join(d, "ic_launcher_foreground.png"))
        # status-bar small icon: white glyph
        save_png(glyph_white(int(24 * scale)), os.path.join(d, "ic_stat_logo.png"))

    # adaptive background colour -> match the dark frame
    hexc = "#%02x%02x%02x" % BG
    xml_path = os.path.join(base, "values", "ic_launcher_background.xml")
    with open(xml_path, encoding="utf-8") as f:
        xml = f.read()
    new_xml = re.sub(r"(<color name=\"ic_launcher_background\">)#[0-9a-fA-F]{6}",
                     lambda m: m.group(1) + hexc, xml)
    if new_xml == xml:
        print("  ! ic_launcher_background.xml: pattern not found, leaving as-is")
    elif DRY:
        print("  [dry-run] would update colour in", os.path.relpath(xml_path, ROOT))
    else:
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(new_xml)
        print("  updated", os.path.relpath(xml_path, ROOT), "->", hexc)


def main() -> None:
    print(f"master: {MASTER_PATH}  frame colour: #{BG[0]:02x}{BG[1]:02x}{BG[2]:02x}"
          f"  corner radius: {CORNER_RADIUS_FRAC:.0%} of size")
    # Step 0: make res/icon.png itself rounded (4 transparent corners), so the
    # regenerated file is the master all other icons are derived from.
    rounded = master()
    if DRY:
        print("  [dry-run] would rewrite", os.path.relpath(MASTER_PATH, ROOT),
              "with 4 transparent rounded corners")
    else:
        rounded.save(MASTER_PATH, "PNG")
        print("  updated", os.path.relpath(MASTER_PATH, ROOT),
              "(4 corners now transparent, radius ~"
              f"{int(min(rounded.size) * CORNER_RADIUS_FRAC)}px)")
    gen_windows()
    gen_macos()
    gen_linux()
    gen_ios()
    gen_android()
    print("done.")


if __name__ == "__main__":
    main()
