#!/usr/bin/env python3
"""Validate the Serbian translation against English source and patched fonts."""
import argparse, os, sys
from common import ROOT, GROUPS, TEXT_FONTS, PATCHED_FONTS, PLACEHOLDER, en, sr
from font import Font
from serbian_glyphs import patch


BR = "\\n"
ALLOWED = set("čćšžđČĆŠŽĐ„”")


def font_charsets():
    sets = {}
    for name in TEXT_FONTS:
        f = Font(os.path.join(ROOT, "src", "orig", "fonts", f"{name}.font"))
        if name in PATCHED_FONTS:
            patch(f)
        # empty stand-in glyphs (e.g. HL1 Ž before patching) don't count as covered
        sets[name] = {c for c in f.glyphs if not (chr(c).isalpha() and f.is_placeholder(c))}
    return sets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--long", type=float, default=1.6, help="warn if sr is this much longer than en")
    ap.add_argument("-v", action="store_true")
    a = ap.parse_args()
    E, S = en(), sr()
    fonts = font_charsets()
    common_chars = set.intersection(*fonts.values())
    errors = warnings = 0
    total = done = 0
    for g in GROUPS:
        e, s = E[g], S[g]
        total += len(e)
        for k in s:
            if k not in e:
                print(f"ERROR {g}:{k}: unknown key"); errors += 1
        for k, src in e.items():
            if k not in s:
                continue
            done += 1
            t = s[k]
            if sorted(PLACEHOLDER.findall(src)) != sorted(PLACEHOLDER.findall(t)):
                print(f"ERROR {g}:{k}: placeholders {PLACEHOLDER.findall(src)} -> {PLACEHOLDER.findall(t)}"); errors += 1
            if src.strip() and not t.strip():
                print(f"ERROR {g}:{k}: empty translation"); errors += 1
            foreign = {c for c in t if not (32 <= ord(c) < 127 or c in ALLOWED)}
            if foreign:
                print(f"ERROR {g}:{k}: disallowed chars {''.join(sorted(foreign))!r}"); errors += 1
            bad = {c for c in t if ord(c) not in common_chars and c not in "\n\t"}
            if bad:
                missing_in = [n for n, cs in fonts.items() if any(ord(c) not in cs for c in bad)]
                print(f"ERROR {g}:{k}: chars {''.join(sorted(bad))!r} missing in {missing_in}"); errors += 1
            if src.count("\\n") != t.count("\\n"):
                print(f"WARN  {g}:{k}: line breaks {src.count(BR)} -> {t.count(BR)}"); warnings += 1
            if len(src) >= 8 and len(t) > a.long * len(src) + 4:
                if a.v:
                    print(f"WARN  {g}:{k}: long ({len(src)} -> {len(t)})")
                warnings += 1
    print(f"\ntranslated {done}/{total} ({100*done/total:.1f}%), {errors} errors, {warnings} warnings")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
