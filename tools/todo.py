#!/usr/bin/env python3
"""Print the next N untranslated strings of a group (unique English texts, file order)."""
import sys
from common import en, sr

g, n = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 100
E, S = en(), sr()
seen, shown = set(), 0
left = sum(1 for k in E[g] if k not in S[g])
for k, v in E[g].items():
    if k in S[g] or v in seen:
        continue
    seen.add(v)
    if shown < n:
        print(f"{k}\t{v}")
        shown += 1
print(f"# remaining keys: {left}", file=sys.stderr)
