#!/usr/bin/env python3
"""Serbian versions of the images with Polish text baked in (img/loc-pl/*.png).

The game shows these instead of the English images when the Polish slot is active
(main menu buttons, LOADING, pause banners, NO FUEL, MISS/RESIST, ...).

Every image is re-rendered from the game's own (Serbian-patched) bitmap fonts:
  * the text core (letter fill, dark strokes/borders) is drawn with the colours found
    in the original Polish image;
  * the glow/shadow around it is copied from the original as a function of the
    distance to the text core (mean colour per distance), so the look is preserved.
MISS/RESIST use a tiny hand-drawn font that is not in any .font file; its letters are
cut out of the images of all the game's languages.

Usage: images.py [--preview out.png]     (build.py calls render_all())
"""
import argparse
import io
import os
from collections import Counter

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

import pkg
from common import ROOT, PATCHED_FONTS
from font import Font
from serbian_glyphs import patch

ORIG_IMG = os.path.join(ROOT, "src", "orig", "img")
LANGS = ["de", "es", "fr", "it", "ja", "pl", "pt", "ru", "zh-Hans"]

# --- texts (keep in sync with src/sr/misc.tsv) ---------------------------------
MENU = {"continue": "NASTAVI", "start": "NOVA IGRA", "stats": "STATISTIKA", "tutorial": "OBUKA",
        "credits": "AUTORI", "options": "OPCIJE", "quit": "IZLAZ"}
PAUSE = {  # file: (title, subtitle)
    "autopause": ("AUTOPAUZA", "Igra će se nastaviti kad se radnja završi"),
    "pause_crewselection": ("IZBOR POSADE", "Prevuci da izabereš više članova posade"),
    "pause_doors": ("KONTROLA VRATA", "Dodirni ili prevuci da otvoriš ili zatvoriš vrata"),
    "pause_hacking": ("HAKOVANJE", "Dodirni prostoriju da pošalješ dron za hakovanje"),
    "pause_mind": ("KONTROLA UMA", "Dodirni neprijatelja da ga nakratko kontrolišeš"),
    "pause_roomselection": ("IZBOR PROSTORIJE", "Dodirni prostoriju da izabereš odredište"),
    "pause_target": ("NIŠANJENJE", "Dodirni prostoriju da izabereš metu"),
    "pause_target_beam": ("NIŠANJENJE", "Dodirni i prevuci da izabereš ciljanu oblast"),
    "pause_teleport_arrive": ("TELEPORTACIJA", "Dodirni neprijateljsku prostoriju da pošalješ abordažni tim"),
    "pause_teleport_leave": ("TELEPORTACIJA", "Dodirni neprijateljsku prostoriju da vratiš svoju posadu"),
}
LOADING = "UČITAVANJE"
NOFUEL = "NEMA GORIVA"
WAITING = "Čekanje..."
AE_WARNING = ["ZA PRISTUP UKLJUČI", "SADRŽAJ ADVANCED EDITION"]
MISS = "PROMAŠAJ"
RESIST = "OTPOR"
# Text_pause1/2.png and ipad/pause.png already say "PAUZA" (identical in Serbian) -> kept.


# --- originals -------------------------------------------------------------------
def ensure_orig():
    if os.path.isdir(os.path.join(ORIG_IMG, "loc-pl")):
        return
    with open(pkg.DEFAULT_DAT, "rb") as f:
        idx = pkg.read_index(f)
        loc = {n for n, *_ in idx if n.startswith("img/loc-")}
        want = loc | {"img/" + n.split("/", 2)[2] for n in loc}
        for name, off, size, usize, fl in idx:
            if name in want:
                f.seek(off)
                dst = os.path.join(ROOT, "src", "orig", name)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                open(dst, "wb").write(f.read(size))


def orig(path):
    return np.array(Image.open(os.path.join(ORIG_IMG, path)).convert("RGBA"))


_fonts = {}


def font(name):
    if name not in _fonts:
        f = Font(os.path.join(ROOT, "src", "orig", "fonts", f"{name}.font"))
        if name in PATCHED_FONTS:
            patch(f)
        _fonts[name] = f
    return _fonts[name]


# --- text rendering ----------------------------------------------------------------
class Text:
    """Rendered line: boolean masks `light` (glyph pixels) and `inner` (enclosed holes of
    outlined fonts like HL2), plus `cap` = row of the capital-letter top."""

    def __init__(self, fname, text, scale=1, gap=0, outlined=False):
        F = font(fname)
        gl = [F.glyphs[ord(c)] for c in text]
        cap_by = F.glyphs[ord("H")].by
        asc = max([g.by for g in gl if g.h] + [cap_by])
        desc = max(g.h - g.by for g in gl if g.h)
        s = scale
        W = sum((g.left + g.w + g.right) * s + gap for g in gl) + 8 * s
        H = (asc + desc) * s
        light = np.zeros((H, W), bool)
        inner = np.zeros((H, W), bool)
        x = 0
        for c, g in zip(text, gl):
            if g.w * g.h > 1:
                b = np.array(F.bitmap(ord(c))) > 128
                hole = np.zeros_like(b)
                if outlined:
                    lab, n = ndi.label(~b)
                    border = set(lab[0]) | set(lab[-1]) | set(lab[:, 0]) | set(lab[:, -1])
                    hole = (lab > 0) & ~np.isin(lab, list(border))
                k = np.ones((s, s), bool)
                y0, x0 = (asc - g.by) * s, x + g.left * s
                light[y0:y0 + g.h * s, x0:x0 + g.w * s] |= np.kron(b, k)
                inner[y0:y0 + g.h * s, x0:x0 + g.w * s] |= np.kron(hole, k)
            x += (g.left + g.w + g.right) * s + gap
        xs = np.where((light | inner).any(0))[0]
        self.light, self.inner = light[:, xs[0]:xs[-1] + 1], inner[:, xs[0]:xs[-1] + 1]
        self.cap = (asc - cap_by) * s
        self.h, self.w = self.light.shape


def ring(m, r=1, square=True):
    st = np.ones((2 * r + 1, 2 * r + 1), bool) if square else ndi.generate_binary_structure(2, 1)
    return ndi.binary_dilation(m, st, iterations=1 if square else r) & ~m


# --- style learning ------------------------------------------------------------------
def bbox(m):
    ys, xs = np.where(m)
    return ys.min(), ys.max(), xs.min(), xs.max()


def mode_color(px):
    return np.array(Counter(map(tuple, px)).most_common(1)[0][0], np.float64)


def halo_table(o, core, dmax=48):
    """Mean premultiplied RGBA of the original per (rounded) distance to its text core."""
    d = np.rint(ndi.distance_transform_edt(~core)).astype(int)
    a = o[..., 3:4].astype(np.float64) / 255
    pm = np.concatenate([o[..., :3] * a, a], -1)
    tab = np.zeros((dmax + 1, 4))
    for k in range(1, dmax + 1):
        sel = d == k
        if sel.any():
            tab[k] = pm[sel].mean(0)
    return tab


def apply_halo(core_rgba, core, tab):
    d = np.rint(ndi.distance_transform_edt(~core)).astype(int)
    d = np.clip(d, 0, len(tab) - 1)
    pm = tab[d]
    pm[core] = 0
    a = pm[..., 3:4]
    rgb = np.divide(pm[..., :3], a, out=np.zeros_like(pm[..., :3]), where=a > 0)
    halo = np.concatenate([rgb, a * 255], -1)
    # core over halo
    ca = core_rgba[..., 3:4] / 255
    out_a = ca + a * (1 - ca)
    out_rgb = np.divide(core_rgba[..., :3] * ca + rgb * a * (1 - ca), out_a, out=np.zeros_like(rgb),
                        where=out_a > 0)
    out = np.concatenate([out_rgb, out_a * 255], -1)
    return Image.fromarray(np.clip(np.rint(out), 0, 255).astype(np.uint8), "RGBA")


class Canvas:
    def __init__(self, h, w):
        self.rgba = np.zeros((h, w, 4))
        self.core = np.zeros((h, w), bool)

    def put(self, mask, color, y, x):
        h, w = mask.shape
        reg = (slice(y, y + h), slice(x, x + w))
        self.rgba[reg][mask] = color
        self.core[reg] |= mask


def lum(c):
    return c[..., 0] * 0.3 + c[..., 1] * 0.59 + c[..., 2] * 0.11


# --- image kinds ----------------------------------------------------------------------
def make_menu(src, text):
    """Main menu button: solid HL2 x4 letters + soft glow."""
    o = orig(src)
    core = o[..., 3] >= 250
    y0, y1, x0, x1 = bbox(core)
    t = Text("HL2", text, 4, 2)
    top = max(0, t.cap - y0)  # extra rows needed above (accents)
    H, W = o.shape[0] + top, x0 + t.w + (o.shape[1] - 1 - x1)
    c = Canvas(H, W)
    c.put(t.light, mode_color(o[core]), y0 + top - t.cap, x0)
    return apply_halo(c.rgba, c.core, halo_table(o, core))


def make_pause(src, title, sub):
    """Pause banner: HL2 x4 outlined title + c&cnew subtitle on a dark band."""
    o = orig(src)
    core = o[..., 3] >= 200
    bright = core & (lum(o[..., :3].astype(float)) > 128)
    rows = np.where(bright.any(1))[0]
    split = rows[np.argmax(np.diff(rows))] + 1  # gap between title and subtitle rows
    ty0 = rows[0]
    sy0 = rows[rows >= split][0]
    tl = mode_color(o[bright & (np.arange(o.shape[0])[:, None] < split)])
    sl = mode_color(o[bright & (np.arange(o.shape[0])[:, None] >= split)])
    dk = mode_color(o[core & ~bright])
    T = Text("HL2", title, 4, 2, outlined=True)
    S = Text("c&cnew", sub)
    _, _, cx0, cx1 = bbox(core)
    margin = min(cx0, o.shape[1] - 1 - cx1)
    top = max(0, T.cap + 1 - ty0)
    H = o.shape[0] + top
    W = max(T.w + 2, S.w + 4) + 2 * margin
    c = Canvas(H, W)
    ty, tx = ty0 + top - T.cap, (W - T.w) // 2
    tm = T.light | T.inner
    full = np.zeros((H, W), bool)
    full[ty:ty + T.h, tx:tx + T.w] = tm
    c.put(ring(full) | full, dk, 0, 0)
    c.put(T.light, tl, ty, tx)
    sy, sx = sy0 + top - S.cap, (W - S.w) // 2
    band = np.zeros((H, W), bool)
    band[sy - 3:sy + S.h + 1, sx - 2:sx + S.w + 2] = True
    c.put(band, dk, 0, 0)
    c.put(S.light, sl, sy, sx)
    return apply_halo(c.rgba, c.core, halo_table(o, core))


def make_lines(src, lines, fname, scale, gap, thr=200, pitch=None):
    """Centered single-colour text line(s) with glow (NO FUEL, Waiting..., AE warning)."""
    o = orig(src)
    core = o[..., 3] >= thr
    y0, y1, x0, x1 = bbox(core)
    ts = [Text(fname, l, scale, gap) for l in lines]
    margin = min(x0, o.shape[1] - 1 - x1)
    top = max(0, ts[0].cap - y0)
    W = max(o.shape[1], max(t.w for t in ts) + 2 * margin)
    c = Canvas(o.shape[0] + top, W)
    col = mode_color(o[o[..., 3] >= 250]) if (o[..., 3] >= 250).any() else mode_color(o[core])
    for i, t in enumerate(ts):
        c.put(t.light, col, y0 + top - t.cap + i * (pitch or 0), (W - t.w) // 2)
    return apply_halo(c.rgba, c.core, halo_table(o, core))


def make_loading(src):
    """LOADING: outlined HL2 x4 text (translucent teal holes) above a bar of the same width."""
    o = orig(src)
    a = o[..., 3]
    solid = a >= 250
    def longest(row):
        best = run = 0
        for v in row:
            run = run + 1 if v else 0
            best = max(best, run)
        return best
    wide = np.array([longest(r) > o.shape[1] // 2 for r in solid])  # bar top/bottom border rows
    bar_rows = np.where(wide)[0]
    by0, by1 = bar_rows[0], bar_rows[-1]
    _, _, bx0, bx1 = bbox(solid[by0:by0 + 1])
    border = int(np.argmax(~solid[by0:, bx0 + 8])) # thickness of the bar's top border
    text_core = solid.copy()
    text_core[by0:] = False
    y0, _, x0, x1 = bbox(text_core)
    light = mode_color(o[solid])
    fill = mode_color(o[(a >= 150) & (a < 250)])
    T = Text("HL2", LOADING, 4, 2, outlined=True)
    top = max(0, T.cap - y0)
    W = x0 + T.w + (o.shape[1] - 1 - x1)
    H = o.shape[0] + top
    c = Canvas(H, W)
    ty = y0 + top - T.cap
    c.put(T.inner, fill, ty, x0)
    c.put(T.light, light, ty, x0)
    bar = np.ones((by1 - by0 + 1, T.w), bool)
    inner = np.zeros_like(bar)
    inner[border:-border, border:-border] = True
    c.put(bar & ~inner, light, by0 + top, x0)
    c.put(inner, fill, by0 + top, x0)
    core = (a >= 150)
    return apply_halo(c.rgba, c.core, halo_table(o, core))


# --- MISS / RESIST mini font -------------------------------------------------------
MINI_WORDS = {  # loc: (miss, resist)
    "": ("MISS", "RESIST"), "loc-de/": ("VERFEHLT", "WIDERSTANDEN"), "loc-es/": ("FALLO", "RESISTE"),
    "loc-fr/": ("RATÉ", "RÉSISTÉ"), "loc-it/": ("MANCATO", "RESISTITO"), "loc-pt/": ("ERROU", "RESISTIU"),
    "loc-pl/": ("PUDŁO", "NIESKUTECZNE")}
MINI_FILL = (234, 246, 229, 255)
MINI_DARK = (9, 5, 10, 255)


def mini_letters():
    """Fill masks of the MISS/RESIST letters, keyed by character (bottom-aligned)."""
    lib = {}
    for loc, words in MINI_WORDS.items():
        for name, word in zip(("text_miss", "text_resist"), words):
            o = orig(f"{loc}numbers/{name}.png")
            fill = (o[..., 3] > 200) & (lum(o[..., :3].astype(float)) > 128)
            cols = fill.any(0)
            runs, x = [], 0
            while x < len(cols):
                if cols[x]:
                    s = x
                    while x < len(cols) and cols[x]:
                        x += 1
                    runs.append((s, x))
                x += 1
            if len(runs) != len(word):
                continue
            for ch, (s, e) in zip(word, runs):
                m = fill[:, s:e]
                lib.setdefault(ch, m[-20:])  # body = bottom 20 rows (accent rows dropped)
    # Serbian additions
    lib["J"] = mini_j(lib["U"])
    lib["Š"] = mini_caron(lib["S"])
    return lib


def mini_j(u):
    j = u.copy()
    h = j.shape[0]
    j[: h * 2 // 3, :3] = False  # left stem only in the lower third
    return j


def mini_caron(s):
    """Caron in the font's 3-px grid: two outer blocks, then the centre block, 2 px above S."""
    w = s.shape[1]
    c = w // 2
    acc = np.zeros((6, w), bool)
    acc[0:2, c - 4:c - 1] = True
    acc[0:2, c + 2:c + 5] = True
    acc[2:4, c - 1:c + 2] = True
    return np.vstack([acc, s])


def make_mini_img(word):
    lib = mini_letters()
    ms = [lib[ch] for ch in word]
    h = max(m.shape[0] for m in ms)
    gap = 6
    W = sum(m.shape[1] for m in ms) + gap * (len(ms) - 1) + 4
    H = h + 4
    fill = np.zeros((H, W), bool)
    x = 2
    for m in ms:
        fill[H - 2 - m.shape[0]:H - 2, x:x + m.shape[1]] = m
        x += m.shape[1] + gap
    dark = ndi.binary_dilation(fill, np.ones((5, 5), bool))
    out = np.zeros((H, W, 4), np.uint8)
    out[dark] = MINI_DARK
    out[fill] = MINI_FILL
    return Image.fromarray(out, "RGBA")


# --- all ------------------------------------------------------------------------------
def render_all():
    """Returns {archive path: PIL image} for every Serbian image."""
    ensure_orig()
    out = {}
    for key, text in MENU.items():
        for st in ("on", "off", "select2"):
            p = f"img/loc-pl/main_menus/{key}_{st}.png"
            out[p] = make_menu(p[4:], text)
    out["img/loc-pl/main_menus/Loading_main.png"] = make_loading("loc-pl/main_menus/Loading_main.png")
    for key, (title, sub) in PAUSE.items():
        out[f"img/loc-pl/{key}.png"] = make_pause(f"loc-pl/{key}.png", title, sub)
    out["img/loc-pl/map/map_fuel_text_nofuel.png"] = make_lines("loc-pl/map/map_fuel_text_nofuel.png", [NOFUEL],
                                                                "c&c", 4, 3)
    out["img/loc-pl/map/map_fuel_text_waiting.png"] = make_lines("loc-pl/map/map_fuel_text_waiting.png", [WAITING],
                                                                 "c&cnew", 3, 0)
    out["img/loc-pl/customizeUI/advanced_warning.png"] = make_lines(
        "loc-pl/customizeUI/advanced_warning.png", AE_WARNING, "JustinFont11Bold", 2, 0, pitch=37)
    out["img/loc-pl/numbers/text_miss.png"] = make_mini_img(MISS)
    out["img/loc-pl/numbers/text_resist.png"] = make_mini_img(RESIST)
    return out


def png_bytes(im):
    b = io.BytesIO()
    im.save(b, "PNG", optimize=True)
    return b.getvalue()


def preview(imgs, path):
    """Polish original (left) vs Serbian (right) on a dark background."""
    pairs = []
    for p, im in imgs.items():
        pl = Image.open(os.path.join(ROOT, "src", "orig", p)).convert("RGBA")
        pairs.append((pl, im))
    W = max(a.width + b.width for a, b in pairs) + 30
    H = sum(max(a.height, b.height) + 6 for a, b in pairs)
    sheet = Image.new("RGBA", (W, H), (32, 48, 72, 255))
    y = 0
    for a, b in pairs:
        sheet.alpha_composite(a, (0, y))
        sheet.alpha_composite(b, (a.width + 30, y))
        y += max(a.height, b.height) + 6
    sheet.save(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview")
    a = ap.parse_args()
    imgs = render_all()
    for p, im in imgs.items():
        print(f"{im.width:4}x{im.height:<4} {p}")
    if a.preview:
        preview(imgs, a.preview)
