#!/usr/bin/env python3
"""FTL 1.6 bitmap .font reader/writer.

Layout (big endian), reverse-engineered:
  0  "FONT"
  4  u8 version(1), u8 line_height, u8 baseline, u8 pad
  8  u32 glyph_table_offset (0x18)
  12 u16 glyph_count, u16 record_size (16)
  16 u32 tex_offset, u32 tex_size
  24 glyph records, sorted by codepoint:
       u32 codepoint, u16 x, u16 y, u8 w, u8 h,
       i8 bearing_y (top above baseline), u8 pad, i8 left, u8 pad, i8 right, u8 pad
     advance = left + w + right
  tex_offset: "TEX\\n", u8 fmt(2), u8 0x40, u16 0, u16 width, u16 height,
     u16 mips(1), u16 0, u32 data_rel_offset(0x20), u32 data_size, 8 pad,
     then width*height 8-bit alpha.
"""
import struct
from dataclasses import dataclass

from PIL import Image


@dataclass
class Glyph:
    cp: int
    x: int
    y: int
    w: int
    h: int
    by: int
    left: int
    right: int
    extra: bytes  # bytes 11,13,15 preserved verbatim

    def pack(self):
        e = self.extra
        return struct.pack(">IHHBBbBbBbB", self.cp, self.x, self.y, self.w, self.h,
                           self.by, e[0], self.left, e[1], self.right, e[2])


class Font:
    def __init__(self, path):
        d = open(path, "rb").read()
        assert d[:4] == b"FONT"
        self.head = bytearray(d[4:8])
        tbl, = struct.unpack(">I", d[8:12])
        n, rs = struct.unpack(">HH", d[12:14 + 2])
        assert tbl == 24 and rs == 16
        self.tex_off, self.tex_size = struct.unpack(">II", d[16:24])
        self.order = []  # original record order (HL1 contains a duplicate codepoint)
        self.glyphs = {}
        for i in range(n):
            r = d[tbl + i * 16: tbl + i * 16 + 16]
            cp, x, y, w, h, by, e0, l, e1, rt, e2 = struct.unpack(">IHHBBbBbBbB", r)
            g = Glyph(cp, x, y, w, h, by, l, rt, bytes([e0, e1, e2]))
            self.order.append(g)
            self.glyphs.setdefault(cp, g)
        t = d[self.tex_off:]
        assert t[:4] == b"TEX\n"
        self.tex_head = bytearray(t[4:8])
        self.tw, self.th = struct.unpack(">HH", t[8:12])
        mips, _z, rel, size = struct.unpack(">HHII", t[12:24])
        assert mips == 1 and rel == 0x20 and size == self.tw * self.th
        self.img = Image.frombytes("L", (self.tw, self.th), t[rel:rel + size])

    # --- bitmap helpers -------------------------------------------------
    def bitmap(self, cp):
        g = self.glyphs[cp]
        return self.img.crop((g.x, g.y, g.x + g.w, g.y + g.h))

    def free_spot(self, w, h, pad=1):
        """Find a free rectangle in the atlas (all-zero and not used by any glyph)."""
        used = [(g.x - pad, g.y - pad, g.x + g.w + pad, g.y + g.h + pad)
                for g in self.order if g.w and g.h]
        px = self.img.load()
        for y in range(pad, self.th - h - pad):
            for x in range(pad, self.tw - w - pad):
                if any(x < x2 and x + w > x1 and y < y2 and y + h > y1 for x1, y1, x2, y2 in used):
                    continue
                if all(px[i, j] == 0 for j in range(y - pad, y + h + pad) for i in range(x - pad, x + w + pad)):
                    return x, y
        return None

    def grow(self):
        """Double atlas height (keeps existing coordinates valid)."""
        new = Image.new("L", (self.tw, self.th * 2), 0)
        new.paste(self.img, (0, 0))
        self.img, self.th = new, self.th * 2

    def add(self, cp, bmp, by, left, right, template_extra=b"\0\0\0"):
        w, h = bmp.size
        spot = self.free_spot(w, h)
        while spot is None:
            self.grow()
            spot = self.free_spot(w, h)
        x, y = spot
        self.img.paste(bmp, (x, y))
        if cp in self.glyphs:
            raise ValueError(f"U+{cp:04X} already present")
        g = Glyph(cp, x, y, w, h, by, left, right, template_extra)
        self.glyphs[cp] = g
        self.order.append(g)

    # --- output ---------------------------------------------------------
    def save(self, path):
        gl = self.order  # original order; new glyphs appended (game does not need sorting)
        table = b"".join(g.pack() for g in gl)
        tex_off = (24 + len(table) + 0x3F) & ~0x3F  # original files align to 64
        data = self.img.tobytes()
        tex = (b"TEX\n" + bytes(self.tex_head) + struct.pack(">HHHHII", self.tw, self.th, 1, 0, 0x20, len(data))
               + b"\0" * 8 + data)
        out = (b"FONT" + bytes(self.head) + struct.pack(">IHHII", 24, len(gl), 16, tex_off, len(tex))
               + table)
        out += b"\0" * (tex_off - len(out)) + tex
        open(path, "wb").write(out)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("font")
    ap.add_argument("--png")
    ap.add_argument("--roundtrip")
    a = ap.parse_args()
    f = Font(a.font)
    print(f"{len(f.glyphs)} glyphs, atlas {f.tw}x{f.th}, head {f.head.hex()}")
    if a.png:
        f.img.save(a.png)
    if a.roundtrip:
        f.save(a.roundtrip)
        print("identical" if open(a.roundtrip, "rb").read() == open(a.font, "rb").read() else "DIFFERENT")
