import json, os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
GROUPS = ["misc", "blueprints", "achievements", "tooltips", "sectorname", "tutorial", "events"]
PATCHED_FONTS = ["JustinFont10", "JustinFont12Bold", "c&c", "num_font", "HL1", "HL2"]
# fonts used for translated text (HL1/HL2 = main menu and titles)
TEXT_FONTS = ["JustinFont8", "JustinFont10", "JustinFont11Bold", "JustinFont12Bold", "c&c", "c&cnew", "num_font",
              "HL1", "HL2"]
PLACEHOLDER = re.compile(r"\\\d|\[\[[^\]]*\]\]")


def en():
    return {g: json.load(open(os.path.join(ROOT, "src", "en", f"{g}.json"), encoding="utf-8")) for g in GROUPS}


def read_tsv(path):
    """key<TAB>text per line; text uses the game's literal escapes (\\n, \\1). '#' lines = comments."""
    out = {}
    if not os.path.exists(path):
        return out
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        line = line.rstrip("\n")
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            raise SystemExit(f"{path}:{n}: missing TAB")
        k, v = line.split("\t", 1)
        if k in out:
            raise SystemExit(f"{path}:{n}: duplicate key {k}")
        out[k] = v
    return out


def sr(propagate=True):
    """Translations per group. With propagate, a key whose English text is identical to an
    already translated key (anywhere) reuses that translation."""
    out = {g: read_tsv(os.path.join(ROOT, "src", "sr", f"{g}.tsv")) for g in GROUPS}
    if propagate:
        E = en()
        by_text = {}
        for g in GROUPS:
            for k, v in out[g].items():
                if k in E[g]:
                    by_text.setdefault(E[g][k], v)
        for g in GROUPS:
            for k, src in E[g].items():
                if k not in out[g] and src in by_text:
                    out[g][k] = by_text[src]
    return out


def pl_order():
    root = ET.parse(os.path.join(ROOT, "src", "orig", "data", "text-pl.xml")).getroot()
    return [t.get("name") for t in root.iter("text")]
