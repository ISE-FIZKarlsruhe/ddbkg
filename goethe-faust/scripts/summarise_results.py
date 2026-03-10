#!/usr/bin/env python3
"""
summarise_results.py
====================
Print a summary of the objecttype-to-ontology matching results from
ddb-type2fabio.json: counts and percentages per matching method, and
one representative example per method.

Usage
-----
    python summarise_results.py
"""

import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
IN_PATH = PROJECT / "output" / "ddb-type2fabio.json"

with open(IN_PATH) as f:
    data = json.load(f)

s = data["summary"]
total = s["unique_objecttypes"]
bm = s["by_method"]

print(f"Total unique objecttypes: {total}\n")
print(f"{'Method':<22} {'n':>5}  {'%':>6}")
print("-" * 38)
for method in ["strict", "strict_translated", "levenshtein", "embeddings", "unmatched"]:
    n = bm[method]
    print(f"{method:<22} {n:>5}  {100 * n / total:>5.1f}%")

# One example per method
print("\nExamples:")
seen = set()
for otype, v in data["type_to_fabio"].items():
    m = v["match_method"]
    if m in seen:
        continue
    seen.add(m)
    trans = v.get("translated_term") or ""
    trans_str = f" → '{trans}'" if trans and trans != otype else ""
    conf = v["confidence"]
    onto = v["ontology"] or "-"
    cls = v["ontology_class"] or "-"
    print(f"  [{m}] '{otype}'{trans_str} → {onto}:{cls}  (conf={conf})")
