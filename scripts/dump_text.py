"""Dump raw text of every curated report into data/raw_text/ for format inspection.
Read-only on the source. Uses PyMuPDF (fitz)."""
import os, re, sys
import fitz
from reports_manifest import existing_reports

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "raw_text")
os.makedirs(OUT, exist_ok=True)

def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")

index = []
for r in existing_reports():
    if not r["exists"]:
        continue
    try:
        doc = fitz.open(r["full"])
        parts = []
        for i, pg in enumerate(doc):
            parts.append(f"\n----- PAGE {i+1} -----\n" + pg.get_text())
        text = "".join(parts)
        doc.close()
    except Exception as e:
        text = f"EXTRACT_ERROR: {e}"
    name = f"{r['person']}__{r['date']}__{slug(os.path.basename(r['path']))[:60]}.txt"
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        f.write(f"# person={r['person']} date={r['date']} lab={r['lab']}\n# path={r['path']}\n")
        f.write(text)
    index.append((r["person"], r["date"], len(text), name))

index.sort()
for person, date, n, name in index:
    print(f"{person:7} {date}  {n:7d} chars  {name}")
print(f"\nTotal reports dumped: {len(index)}")
