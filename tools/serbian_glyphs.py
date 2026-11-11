#!/usr/bin/env python3
"""Add Serbian Latin glyphs (č ć š ž đ + capitals) to FTL .font files.

Glyphs are composed from pixels already in the same font, so they match its style:
  * an accent (caron/acute) is copied from an accented reference glyph (š, ć, é…),
    keeping that font's gap and placement conventions for lower/upper case;
  * if the font has no caron at all, one is built from its acute accent plus a mirrored copy;
  * đ/Đ get a horizontal bar across the stem, as thick as the stem.

usage: serbian_glyphs.py IN.font OUT.font [--show] [--preview out.png]
"""
import argparse
import os
import sys

from PIL import Image, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from font import Font  # noqa: E402

TARGETS = {
    # cp: (base, mark)
    "č": ("c", "caron"), "ć": ("c", "acute"), "š": ("s", "caron"), "ž": ("z", "caron"),
    "Č": ("C", "caron"), "Ć": ("C", "acute"), "Š": ("S", "caron"), "Ž": ("Z", "caron"),
    "đ": ("d", "bar"), "Đ": ("D", "bar"),
}
REFS = {
    "caron": "čšžřěňťďČŠŽŘĚŇŤĎ",
    "acute": "ćśźńóéáíúýĆŚŹŃÓÉÁÍÚÝ",
}
ON = 255


def ink_bbox(img):
    """(x0, y0, x1, y1) inclusive of non-zero pixels, or None."""
    b = img.getbbox()
    return None if b is None else (b[0], b[1], b[2] - 1, b[3] - 1)


class Accent:
    """An accent mark: its ink bitmap, gap rows under it and centre offset (in half pixels)."""

    def __init__(self, ink, gap, delta2):
        self.ink, self.gap, self.delta2 = ink, gap, delta2


def base_of(ch):
    """'š' -> 's' via Unicode decomposition."""
    import unicodedata
    d = unicodedata.decomposition(ch).split()
    return chr(int(d[0], 16)) if d and not d[0].startswith("<") else None


def extract_accent(f, ref_ch):
    """Pull the accent block out of ref glyph by comparing with its base glyph."""
    rc, bc = ord(ref_ch), ord(base_of(ref_ch))
    if rc not in f.glyphs or bc not in f.glyphs:
        return None
    R, B = f.glyphs[rc], f.glyphs[bc]
    k = R.h - B.h
    if k <= 0 or R.by - B.by != k:
        return None
    rimg = f.bitmap(rc)
    top = rimg.crop((0, 0, R.w, k))
    bottom = rimg.crop((0, k, R.w, R.h))
    ib = ink_bbox(top)
    bb = ink_bbox(bottom)
    if ib is None or bb is None:
        return None
    if not same_body(bottom, f.bitmap(bc)):
        return None  # accented glyph was redrawn (e.g. HL1 Š), its accent can't be lifted
    ink = top.crop((ib[0], ib[1], ib[2] + 1, ib[3] + 1))
    gap = k - (ib[3] + 1)
    # centre (×2) of accent ink minus centre (×2) of base ink, both in R's coordinates
    delta2 = (ib[0] + ib[2]) - (bb[0] + bb[2]) - 2 * (R.left - R.left)
    return Accent(ink, gap, delta2)


def same_body(a, b, min_ratio=0.85):
    """Do two bitmaps show the same letter (ink-cropped, >= min_ratio matching pixels)?"""
    ba, bb = a.getbbox(), b.getbbox()
    if not ba or not bb:
        return False
    a, b = a.crop(ba), b.crop(bb)
    if a.size != b.size:
        return False
    pa, pb = a.load(), b.load()
    n = a.size[0] * a.size[1]
    same = sum((pa[x, y] > 127) == (pb[x, y] > 127) for x in range(a.size[0]) for y in range(a.size[1]))
    return same / n >= min_ratio


def pixels(rows):
    """Bitmap from strings: '#' = on, anything else = off."""
    img = Image.new("L", (max(len(r) for r in rows), len(rows)), 0)
    px = img.load()
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == "#":
                px[x, y] = ON
    return img


# Hand-drawn accents for fonts where references can't be extracted.
# mark -> (ink rows, gap rows under the accent)
ACCENT_OVERRIDES = {
    "HL1": {"caron": (["# #", " # "], 0)},
    # HL2 is an outlined font: '#' is the outline, the hollow V inside is the stroke
    "HL2": {"caron": (["#####", "# # #", " # # "], 0)},
}
# Whole hand-drawn glyphs: char -> (rows, bearing_y, left, right)
GLYPH_OVERRIDES = {
    "HL2": {
        "đ": (["  #####",
               "  #   #",
               " ### ##",
               "##   # ",
               "# ## # ",
               "# ## # ",
               "# ## # ",
               "##   # ",
               " ##### "], 8, 0, 0),
    },
}


# fonts whose Icelandic Ð is well drawn and can serve as Serbian Đ
ETH_AS_DJ = {"HL1", "HL2"}


def find_accent(f, mark, upper):
    ov = ACCENT_OVERRIDES.get(getattr(f, "name", ""), {}).get(mark)
    if ov:
        return Accent(pixels(ov[0]), ov[1], 0)
    """Best accent for (mark, case); falls back to other case / synthesised caron."""
    refs = REFS[mark]
    same = [c for c in refs if c.isupper() == upper]
    other = [c for c in refs if c.isupper() != upper]
    for c in same:
        a = extract_accent(f, c)
        if a:
            return a
    gap = case_gap(f, upper)
    for c in other:
        a = extract_accent(f, c)
        if a:
            return Accent(a.ink, gap, a.delta2)
    if mark == "caron":
        ac = find_accent(f, "acute", upper)
        if ac:
            return Accent(make_caron(ac.ink), ac.gap, 0)
    raise SystemExit(f"no reference for {mark} upper={upper}")


def case_gap(f, upper):
    for mark in REFS:
        for c in REFS[mark]:
            if c.isupper() == upper:
                a = extract_accent(f, c)
                if a:
                    return a.gap
    return 1


def make_caron(acute, overlap=None):
    """Build a caron 'V' from an acute ('/'): mirrored copy on the left, original on the right.
    Returns the odd-width variant; an even variant is chosen at placement time."""
    return acute


def caron_for_width(acute, base_w):
    """Two caron candidates (overlap w-1 and w); pick the one whose width parity matches base."""
    w, h = acute.size
    mir = ImageOps.mirror(acute)
    out = []
    for o in (w - 1, w):
        img = Image.new("L", (o + w, h), 0)
        img.paste(mir, (0, 0))
        px = img.load()
        ap = acute.load()
        for y in range(h):
            for x in range(w):
                if ap[x, y]:
                    px[o + x, y] = max(px[o + x, y], ap[x, y])
        out.append(img)
    return next((c for c in out if c.size[0] % 2 == base_w % 2), out[0])


def compose(f, base_ch, acc, synth_caron):
    g = f.glyphs[ord(base_ch)]
    bimg = f.bitmap(ord(base_ch))
    bb = ink_bbox(bimg)
    ink = acc.ink
    if synth_caron:
        ink = caron_for_width(acc.ink, bb[2] - bb[0] + 1)
    k = ink.size[1] + acc.gap
    # accent x so that its centre = base centre + delta (half-pixel units, round right)
    c2 = bb[0] + bb[2] + acc.delta2
    ax = (c2 - (ink.size[0] - 1) + 1) // 2
    x0 = min(0, ax)
    x1 = max(g.w, ax + ink.size[0])
    W = x1 - x0
    img = Image.new("L", (W, g.h + k), 0)
    img.paste(bimg, (-x0, k))
    img.paste(ink, (ax - x0, 0))
    left = g.left + x0
    right = g.right - (x1 - g.w)
    return img, g.by + k, left, right, g.extra


def stem_width(img, x_from_right, row):
    px = img.load()
    w = img.size[0]
    n = 0
    cols = range(w - 1, -1, -1) if x_from_right else range(w)
    started = False
    for x in cols:
        if px[x, row]:
            started = True
            n += 1
        elif started:
            break
    return max(n, 1)


def bar_lower(f):
    """đ: bar across the ascender of d, one stroke below its top.
    If the ascender is too short to fit a bar clear of the bowl, the stem is extended upwards."""
    d, c = f.glyphs[ord("d")], f.glyphs[ord("c")]
    img = f.bitmap(ord("d"))
    s = stem_width(img, True, 0)
    asc = d.h - c.h  # rows above x-height
    grow = s if asc < 3 * s else 0
    px = img.load()
    stem = [x for x in range(d.w) if px[x, 0]]
    sx0, sx1 = min(stem), max(stem)
    x_from, x_to = sx0 - 2 * s, sx1 + s
    extra = max(0, x_to - (d.w - 1))
    out = Image.new("L", (d.w + extra, d.h + grow), 0)
    out.paste(img, (0, grow))
    op = out.load()
    for y in range(grow):  # extend stem
        for x in range(sx0, sx1 + 1):
            op[x, y] = ON
    for y in range(s, 2 * s):
        for x in range(max(0, x_from), x_to + 1):
            op[x, y] = ON
    return out, d.by + grow, d.left, d.right, d.extra


def bar_upper(f):
    """Đ: bar through the left stem of D at mid height, sticking out one stroke to the left."""
    D = f.glyphs[ord("D")]
    img = f.bitmap(ord("D"))
    s = stem_width(img, False, D.h // 2)
    out = Image.new("L", (D.w + s, D.h), 0)
    out.paste(img, (s, 0))
    op = out.load()
    row = (D.h - s) // 2
    for y in range(row, row + s):
        for x in range(0, 4 * s):
            op[x, y] = ON
    return out, D.by, D.left - s, D.right, D.extra


def patch(f):
    added = []
    for ch, (base, mark) in TARGETS.items():
        cp = ord(ch)
        if (cp in f.glyphs and not f.is_placeholder(cp)) or ord(base) not in f.glyphs:
            continue
        gov = GLYPH_OVERRIDES.get(getattr(f, "name", ""), {}).get(ch)
        if gov:
            rows, by, l, r = gov
            img, ex = pixels(rows), f.glyphs[ord(base)].extra
        elif ch == "Đ" and f.name in ETH_AS_DJ and ord("Ð") in f.glyphs:
            # Icelandic Eth has the same shape as Serbian Đ: reuse the designer's glyph
            e = f.glyphs[ord("Ð")]
            img, by, l, r, ex = f.bitmap(ord("Ð")).copy(), e.by, e.left, e.right, e.extra
        elif mark == "bar":
            img, by, l, r, ex = bar_lower(f) if ch == "đ" else bar_upper(f)
        else:
            has_ref = (any(extract_accent(f, c) for c in REFS[mark])
                       or mark in ACCENT_OVERRIDES.get(getattr(f, "name", ""), {}))
            acc = find_accent(f, mark, ch.isupper())
            synth = mark == "caron" and not has_ref
            img, by, l, r, ex = compose(f, base, acc, synth)
        f.add(cp, img, by, l, r, ex)
        added.append(ch)
    return added


def show(f, chars):
    for ch in chars:
        g = f.glyphs.get(ord(ch))
        if not g:
            continue
        b = f.bitmap(ord(ch)).load()
        print(f"{ch} w{g.w} h{g.h} by{g.by} l{g.left} r{g.right}")
        for y in range(g.h):
            print("  |" + "".join("#" if b[x, y] > 127 else ("+" if b[x, y] else " ") for x in range(g.w)) + "|")


def render(f, text, scale=3):
    """Render text with the font's metrics (for visual QA)."""
    line_h, base = f.head[1], f.head[2]
    lines = text.split("\n")
    width = max(sum(f.glyphs[ord(c)].left + f.glyphs[ord(c)].w + f.glyphs[ord(c)].right
                    for c in ln if ord(c) in f.glyphs) for ln in lines) + 8
    img = Image.new("L", (width, line_h * len(lines) + 8), 0)
    for i, ln in enumerate(lines):
        x, y0 = 4, 4 + i * line_h + base
        for c in ln:
            g = f.glyphs.get(ord(c)) or f.glyphs.get(ord("?"))
            img.paste(f.bitmap(g.cp), (x + g.left, y0 - g.by), f.bitmap(g.cp))
            x += g.left + g.w + g.right
    return img.resize((img.size[0] * scale, img.size[1] * scale), Image.NEAREST)


SAMPLE = ("PODEŠAVANJA IZAĐI SAČUVAJ KRENI ČUVAR ĐAK\nČačak, Ćuprija, Šabac, Žabalj, Đurđevdan\n"
          "čćšžđ ČĆŠŽĐ — Brod je oštećen! Đavolski štit\n"
          "ŠTIT ŽIVOTNA PODRŠKA ĆELIJA ČUVAR ĐAK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--preview")
    a = ap.parse_args()
    f = Font(a.src)
    added = patch(f)
    print(f"{os.path.basename(a.src)}: added {''.join(added) or 'nothing'}")
    if a.show:
        show(f, "".join(added))
    f.save(a.dst)
    if a.preview:
        render(Font(a.dst), SAMPLE).save(a.preview)


if __name__ == "__main__":
    main()
