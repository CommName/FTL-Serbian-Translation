#!/usr/bin/env python3
"""Build dist/FTL-Srpski.ftl (Slipstream mod). Untranslated strings fall back to English."""
import os, zipfile
from xml.sax.saxutils import escape
from common import ROOT, GROUPS, PATCHED_FONTS, en, sr, pl_order
from font import Font
from serbian_glyphs import patch
from images import render_all, png_bytes

VERSION = "1.1"
METADATA = f"""<?xml version="1.0" encoding="UTF-8"?>
<metadata>
	<title><![CDATA[Srpski prevod (Serbian translation)]]></title>
	<threadUrl><![CDATA[]]></threadUrl>
	<author><![CDATA[Milan Janković]]></author>
	<version><![CDATA[{VERSION}]]></version>
	<description><![CDATA[Serbian (Latin script) translation for FTL 1.6.
Replaces the Polish language slot: choose "Srpski" in Options > Language.
Adds č ć š ž đ glyphs to the game fonts and Serbian versions of the
images with text (main menu, loading, pause banners, map, MISS/RESIST).]]></description>
</metadata>
"""


def main():
    E, S = en(), sr()
    merged = {}
    for g in GROUPS:
        for k, v in E[g].items():
            merged[k] = S[g].get(k, v)
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<FTL>"]
    for k in pl_order():
        lines.append(f'<text name="{escape(k)}" language="pl">{escape(merged[k])}</text>')
    lines.append("</FTL>\n")
    xml = "\n".join(lines).encode("utf-8")
    os.makedirs(os.path.join(ROOT, "dist"), exist_ok=True)
    out = os.path.join(ROOT, "dist", "FTL-Srpski.ftl")
    tmp = os.path.join(ROOT, "dist", "fonts.tmp")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mod-appendix/metadata.xml", METADATA)
        z.writestr("data/text-pl.xml", xml)
        for name in PATCHED_FONTS:
            f = Font(os.path.join(ROOT, "src", "orig", "fonts", f"{name}.font"))
            patch(f)
            f.save(tmp)
            z.write(tmp, f"fonts/{name}.font")
        for path, im in render_all().items():
            z.writestr(path, png_bytes(im))
    os.remove(tmp)
    n = sum(len(S[g]) for g in GROUPS)
    print(f"wrote {out} ({n}/{len(merged)} strings translated)")


if __name__ == "__main__":
    main()
