import json, os, re, sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
GROUPS = ["misc", "blueprints", "achievements", "tooltips", "sectorname", "tutorial", "events"]
PATCHED_FONTS = ["JustinFont10", "JustinFont12Bold", "c&c", "num_font"]
# fonts used for translated text (HL1/HL2 are ASCII-only title fonts, not used by translations)
TEXT_FONTS = ["JustinFont8", "JustinFont10", "JustinFont11Bold", "JustinFont12Bold", "c&c", "c&cnew", "num_font"]
PLACEHOLDER = re.compile(r"\\\d|\[\[[^\]]*\]\]")


def en():
    return {g: json.load(open(os.path.join(ROOT, "src", "en", f"{g}.json"), encoding="utf-8")) for g in GROUPS}


def sr():
    out = {}
    for g in GROUPS:
        p = os.path.join(ROOT, "src", "sr", f"{g}.json")
        out[g] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    return out


def pl_order():
    root = ET.parse(os.path.join(ROOT, "src", "orig", "data", "text-pl.xml")).getroot()
    return [t.get("name") for t in root.iter("text")]
