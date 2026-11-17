"""
Column-aware lab report extractor.

Strategy: reconstruct visual rows by geometry (geom.rows_for_pdf), locate the
table header row to learn the x-position of Result / Unit / Reference / Method
columns, then assign each data row's words to columns by x-centre. The name
column (left of Result) identifies the biomarker; the Result column gives the
value; Unit and Reference are read from their columns.

Every observation keeps provenance (source file, page, raw row text) and a
confidence flag. Values are never invented: if no numeric value sits in the
Result column, the row is skipped.
"""
import sys, os, re, io
sys.path.insert(0, os.path.dirname(__file__))
import fitz
from geom import rows_for_pdf
from biomarkers import match_biomarker, BY_ID, RATIO_IDS
from units import normalize

NUM = re.compile(r"^[<>]?=?\s*\d{1,3}(?:,\d{2,3})*(?:\.\d+)?$|^\d+(?:\.\d+)?$")
PURE_NUM = re.compile(r"^\d+(?:\.\d+)?$")

def to_float(tok):
    t = tok.replace(",", "").replace("<","").replace(">","").replace("=","").strip()
    try:
        return float(t)
    except Exception:
        return None

def parse_ref(text):
    """Return (low, high, text). Handles 'a - b', '< b', '> a', 'a-b', 'upto b'."""
    if not text:
        return (None, None, "")
    t = text.strip()
    # range a - b
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)", t)
    if m:
        return (float(m.group(1)), float(m.group(2)), t)
    m = re.search(r"[<≤]\s*=?\s*(\d+(?:\.\d+)?)", t)
    if m:
        return (None, float(m.group(1)), t)
    m = re.search(r"[>≥]\s*=?\s*(\d+(?:\.\d+)?)", t)
    if m:
        return (float(m.group(1)), None, t)
    m = re.search(r"up\s*to\s*(\d+(?:\.\d+)?)", t, re.I)
    if m:
        return (None, float(m.group(1)), t)
    return (None, None, t)

CATEGORY_RE = re.compile(r"optimal|normal\s*:|borderline|hypoglyc|pre[- ]?diabet|"
                         r"\bdiabet|deficien|insufficien|sufficien|desirable|therapeut|"
                         r"\brisk\b|high\s*:|low\s*:|\bnear\b", re.I)
HEADER_HINTS = ("result", "value", "observed")
HEADER_SECOND = ("unit", "units", "reference", "ref", "range", "bio.", "result")

SKIP_ROW = re.compile(r"(uhid|name\s*:|age\s*/|gender|ref doctor|ref\.|client code|barcode|"
                      r"collected|received|reported|page \d|authorized|consultant|"
                      r"end of report|specimen|accession|order no|date of birth|"
                      r"passport|nationality|sample collection|verification|department of|"
                      r"interpretation|note:|disclaimer|method\b.*method|www\.|email|"
                      r"\bmbbs\b|\bmd\b,|signature)", re.I)

def collapse_dupes(xs):
    """Collapse runs of identical consecutive words (some PDFs overprint each
    word 2-4x). Keeps the first (x, word) of each run."""
    out = []
    prev = None
    for x, w in xs:
        if w == prev:
            continue
        out.append((x, w)); prev = w
    return out

def find_header(rows):
    """Return (index, columns) where columns = {result_x, unit_x, ref_x, method_x}."""
    for i, (pno, y, text, xs) in enumerate(rows):
        xs = collapse_dupes(xs)
        text = " ".join(w for _, w in xs)
        low = text.lower()
        if ("result" in low or "value" in low or "observ" in low) and \
           ("unit" in low or "ref" in low or "range" in low):
            # x positions of labels
            cols = {}
            for x, w in xs:
                wl = w.lower().strip(".")
                if wl in ("result","results","value","observed") and "result" not in cols:
                    cols["result"] = x
                elif wl in ("unit","units") and "unit" not in cols:
                    cols["unit"] = x
                elif wl in ("reference","range","bio","bio.","ref","ref.") and "ref" not in cols:
                    cols.setdefault("ref", x)
                elif wl in ("method","methodology","instrument") and "method" not in cols:
                    cols["method"] = x
            if "result" in cols:
                return i, cols
    return None, None

def assign_columns(xs, cols):
    """Split row words into name/result/unit/ref/method buckets by x."""
    result_x = cols.get("result")
    unit_x = cols.get("unit", result_x + 60 if result_x else None)
    ref_x = cols.get("ref", (unit_x + 60) if unit_x else None)
    method_x = cols.get("method")
    buckets = {"name": [], "result": [], "unit": [], "ref": [], "method": []}
    for x, w in xs:
        if result_x is not None and x < result_x - 20:
            buckets["name"].append(w)
        elif unit_x is not None and x < unit_x - 15:
            buckets["result"].append(w)
        elif ref_x is not None and x < ref_x - 15:
            buckets["unit"].append(w)
        elif method_x is not None and x < method_x - 15:
            buckets["ref"].append(w)
        else:
            if method_x is not None:
                buckets["method"].append(w)
            else:
                buckets["ref"].append(w)
    return {k: " ".join(v).strip() for k, v in buckets.items()}

def extract(path):
    rows = rows_for_pdf(path)
    obs = []
    # process page by page; re-find header on each page
    # group rows by page
    pages = {}
    for r in rows:
        pages.setdefault(r[0], []).append(r)
    for pno, prows in pages.items():
        hi, cols = find_header(prows)
        if cols is None:
            continue
        pending_name = ""
        for (p, y, text, xs) in prows[hi+1:]:
            if SKIP_ROW.search(text):
                pending_name = ""
                continue
            xs = collapse_dupes(xs)
            b = assign_columns(xs, cols)
            res = b["result"].strip()
            # value = first numeric token in result column
            val_tok = None
            for tok in res.split():
                if NUM.match(tok):
                    val_tok = tok; break
            name = (pending_name + " " + b["name"]).strip()
            if not val_tok:
                # row with only name text -> accumulate as (continuation) name
                if b["name"] and not b["unit"] and not res:
                    pending_name = name
                else:
                    pending_name = ""
                continue
            pending_name = ""
            if not name or len(re.sub(r"[^A-Za-z]","",name)) < 2:
                continue
            bid = match_biomarker(name)
            if not bid:
                continue
            value = to_float(val_tok)
            if value is None:
                continue
            # Unit is a single token; anything after it in the unit column is
            # actually reference text that bled left, so fold it into the ref.
            utoks = b["unit"].split()
            unit = utoks[0] if utoks else ""
            ref_src = (" ".join(utoks[1:]) + " " + b["ref"]).strip()
            low, high, reftext = parse_ref(ref_src)
            # Categorical interpretation bands (Optimal / Normal: / Borderline /
            # Hypoglycemia / Pre-diabetes / Deficient ...) are not a single
            # reference interval and the one-line value we grab is unreliable, so
            # blank it and let the standard adult target apply downstream.
            if CATEGORY_RE.search(ref_src):
                low, high = None, None
            # Prose/interpretation guard: a real result row has a unit OR a
            # numeric reference range. Rows without either are almost always
            # sentences from interpretation notes that happen to contain a digit.
            has_unit = bool(re.search(r"[A-Za-z%/]", unit)) and len(unit) <= 18
            has_ref = (low is not None) or (high is not None)
            is_ratio = bid in RATIO_IDS
            if is_ratio and not unit:
                unit = "ratio"                 # ratios are legitimately unitless
            if not (has_unit or has_ref or is_ratio):
                continue
            value_n, unit_n, converted, conv_note = normalize(bid, value, unit)
            obs.append(dict(
                biomarker=bid, display=BY_ID[bid]["display"], panel=BY_ID[bid]["panel"],
                raw_name=name, value=value_n, raw_value=value, unit=unit_n or unit,
                raw_unit=unit, ref_low=low, ref_high=high, ref_text=reftext,
                converted=converted, conv_note=conv_note,
                page=pno, row_text=text,
            ))
    return _dedup(obs)

def _dedup(obs):
    """Keep one observation per biomarker per report. Prefer the row whose unit
    matches the canonical unit; tie-break on having a reference range."""
    best = {}
    def score(o):
        canon = BY_ID[o["biomarker"]]["unit"].lower().replace(" ", "")
        u = (o["raw_unit"] or "").lower().replace(" ", "")
        s = 0
        if canon and canon in u:
            s += 2
        if o["ref_low"] is not None or o["ref_high"] is not None:
            s += 1
        return s
    for o in obs:
        k = o["biomarker"]
        if k not in best or score(o) > score(best[k]):
            best[k] = o
    # preserve catalog/panel ordering
    from biomarkers import PANEL_ORDER
    return sorted(best.values(),
                  key=lambda o: (PANEL_ORDER.index(o["panel"]), o["display"]))

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    path = sys.argv[1]
    for o in extract(path):
        print(f"{o['biomarker']:18} {str(o['value']):>9} {o['unit']:10} "
              f"ref[{o['ref_low']},{o['ref_high']}] <- {o['raw_name'][:40]!r}")
