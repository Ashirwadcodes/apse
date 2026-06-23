"""
Post-processing fix: derive proper titles from URL slugs in csir_india.json.
Run from apctt-gateway directory:
    python scripts/fix_csir_titles.py
"""

import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "backend" / "sources" / "data" / "csir_india.json"

with open(DATA_PATH, encoding="utf-8") as f:
    records = json.load(f)

fixed = 0
for rec in records:
    slug = rec["url"].split("/")[-1]
    slug = re.sub(r"-T-\d+-tech\.htm$", "", slug)
    title = slug.replace("-", " ").title()
    rec["title"] = title
    fixed += 1

with open(DATA_PATH, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"Fixed {fixed} titles. Sample:")
for rec in records[:5]:
    print(f"  {rec['id']}: {rec['title']}")
