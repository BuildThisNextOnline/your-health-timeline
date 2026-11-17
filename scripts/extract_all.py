"""
Run extraction across every curated report, aggregate per person, and write
data/structured/<person>.json plus a provenance review CSV.

Each observation is traceable to its source file, page and the exact reconstructed
row of text it came from. Range flags use the report's own reference interval when
present; otherwise a general adult hint from the catalog (flagged ref_source).
"""
import os, sys, json, csv, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from reports_manifest import existing_reports, HEALTH_ROOT, PEOPLE
from parse import extract
try:
    from manual_extracts import MANUAL, manual_extract   # local, git-ignored (private data)
except ModuleNotFoundError:                               # fresh clone: no private data present
    MANUAL, manual_extract = {}, (lambda rp: [])
from biomarkers import BY_ID, PANELS, PANEL_ORDER
from units import canonicalize, is_unit_like, PLAUSIBLE

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = os.path.join(ROOT, "data", "structured")
PROV = os.path.join(ROOT, "data", "provenance")
os.makedirs(OUT, exist_ok=True); os.makedirs(PROV, exist_ok=True)

# PEOPLE (full names + sex) is defined in reports_manifest.py, which is git-ignored.

def status(value, low, high):
    if value is None:
        return "unknown"
    if high is not None and value > high:
        return "high"
    if low is not None and value < low:
        return "low"
    if low is not None or high is not None:
        return "normal"
    return "nolimit"

DROPPED = []

def dedup_by_date(obs):
    """One observation per (biomarker, date). Prefer the report's own reference
    range, then a value whose unit matches the canonical unit."""
    best = {}
    for o in obs:
        k = (o["biomarker"], o["date"])
        if k not in best:
            best[k] = o; continue
        cur = best[k]
        def score(x):
            s = 0
            if x["ref_source"] == "report": s += 2
            if BY_ID[x["biomarker"]]["unit"].lower() in (x["unit"] or "").lower(): s += 1
            return s
        if score(o) > score(cur):
            best[k] = o
    return list(best.values())

def main():
    people = {k: dict(id=k, observations=[], **v) for k, v in PEOPLE.items()}
    review_rows = []
    for r in existing_reports():
        if not r["exists"] or r["person"] not in people:
            continue
        try:
            if r["path"] in MANUAL:
                obs = manual_extract(r["path"])   # scanned PDF, hand-transcribed
            else:
                obs = extract(r["full"])
        except Exception as e:
            print("ERROR", r["path"], e); continue
        for o in obs:
            bid = o["biomarker"]
            value = o["value"]
            # reject prose-leak units (e.g. 'consumption', 'mild') for non-ratio markers
            if not is_unit_like(o["unit"]):
                if bid in ("egfr",) or BY_ID[bid]["unit"] == "ratio":
                    o["unit"] = BY_ID[bid]["unit"]       # infer canonical unit
                else:
                    DROPPED.append((r["person"], r["date"], bid, value, o["unit"],
                                    "non-unit", os.path.basename(r["path"])))
                    continue
            if o["unit"].strip().lower() == "x":          # 'X 10^3/µL' split artifact
                if bid in ("platelets", "wbc", "rbc"):
                    o["unit"] = ""                         # let count-scaler set the unit
                else:                                       # differential absolute, not %
                    DROPPED.append((r["person"], r["date"], bid, value, o["unit"],
                                    "x-unit-artifact", os.path.basename(r["path"])))
                    continue
            value, unit, cnote = canonicalize(bid, value, o["unit"])
            # plausibility drop
            lo, hi = PLAUSIBLE.get(bid, (None, None))
            if lo is not None and value is not None and not (lo <= value <= hi):
                DROPPED.append((r["person"], r["date"], bid, value, unit,
                                "implausible", os.path.basename(r["path"])))
                continue
            # reference: prefer report's own; else catalog hint
            low, high, ref_source = o["ref_low"], o["ref_high"], "report"
            # scale count references the same way the value was scaled
            if bid in ("platelets", "wbc"):
                if low is not None and low > 1500: low = round(low/1000.0, 2)
                if high is not None and high > 1500: high = round(high/1000.0, 2)
            # a "higher is better" marker given only an upper bound is a misparse
            # (these have a lower target) -> use the standard target instead
            if BY_ID[bid]["higher_is"] == "good" and low is None and high is not None:
                low, high = None, None
            if low is None and high is None:
                hint = BY_ID[bid]["ref_adult"]
                if hint:
                    low, high, ref_source = hint[0], hint[1], "general-hint"
            st = status(value, low, high)
            rec = dict(
                biomarker=bid, display=o["display"], panel=o["panel"],
                date=r["date"], lab=r["lab"], value=value, unit=unit,
                ref_low=low, ref_high=high, ref_text=o["ref_text"], ref_source=ref_source,
                status=st, direction=BY_ID[bid]["higher_is"],
                converted=o["converted"] or bool(cnote), conv_note=(o["conv_note"] or cnote),
                source_file=r["path"], source_page=o["page"],
            )
            people[r["person"]]["observations"].append(rec)
            review_rows.append([r["person"], r["date"], bid, value,
                                unit, low, high, st, ref_source,
                                os.path.basename(r["path"]), o["row_text"][:80]])

    for pid, p in people.items():
        p["observations"] = dedup_by_date(p["observations"])
        p["observations"].sort(key=lambda o: (o["biomarker"], o["date"]))
        p["n_observations"] = len(p["observations"])
        p["n_biomarkers"] = len(set(o["biomarker"] for o in p["observations"]))
        dates = sorted(set(o["date"] for o in p["observations"]))
        p["date_range"] = [dates[0], dates[-1]] if dates else []
        with open(os.path.join(OUT, f"{pid}.json"), "w", encoding="utf-8") as f:
            json.dump(p, f, indent=1, ensure_ascii=False)
        print(f"{pid:7} {p['n_observations']:4} obs  {p['n_biomarkers']:3} biomarkers  "
              f"dates={len(dates)} {p['date_range']}")

    with open(os.path.join(PROV, "review.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["person","date","biomarker","value","unit","ref_low","ref_high",
                    "status","ref_source","source","row_text"])
        w.writerows(review_rows)
    print(f"\nReview CSV: data/provenance/review.csv ({len(review_rows)} rows)")
    with open(os.path.join(PROV, "dropped.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["person","date","biomarker","value","unit","reason","source"])
        w.writerows(DROPPED)
    print(f"Dropped (logged): data/provenance/dropped.csv ({len(DROPPED)} rows)")

if __name__ == "__main__":
    main()
