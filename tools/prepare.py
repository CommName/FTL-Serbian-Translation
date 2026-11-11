#!/usr/bin/env python3
"""Extract originals from ftl.dat and write English reference JSON per group to src/en/."""
import json, os, subprocess, sys, xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUPS = ["misc", "blueprints", "achievements", "tooltips", "sectorname", "tutorial", "events"]
FONTS = ["JustinFont8", "JustinFont10", "JustinFont11Bold", "JustinFont12Bold", "c&c", "c&cnew",
         "num_font", "HL1", "HL2"]


def load(path):
    raw = open(path, encoding="utf-8-sig").read()
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:  # some vanilla files lack the <FTL> wrapper
        root = ET.fromstring("<FTL>" + raw.split("?>", 1)[-1] + "</FTL>")
    return {t.get("name"): t.text or "" for t in root.iter("text")}


def main():
    orig = os.path.join(ROOT, "src", "orig")
    files = ["data/text-pl.xml"] + [f"data/text_{g}.xml" for g in GROUPS] + [f"fonts/{f}.font" for f in FONTS]
    subprocess.check_call([sys.executable, "-I", os.path.join(ROOT, "tools", "pkg.py"), "extract", orig] + files)
    os.makedirs(os.path.join(ROOT, "src", "en"), exist_ok=True)
    for g in GROUPS:
        d = load(os.path.join(orig, "data", f"text_{g}.xml"))
        with open(os.path.join(ROOT, "src", "en", f"{g}.json"), "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        with open(os.path.join(ROOT, "src", "en", f"{g}.tsv"), "w", encoding="utf-8") as f:
            f.writelines(f"{k}\t{v}\n" for k, v in d.items())
        print(f"{g}: {len(d)} strings")


if __name__ == "__main__":
    main()
