"""
EXAMPLE scaffold for reports that have NO extractable text layer (scanned image
PDFs). Copy this to `manual_extracts.py` (which is git-ignored) and add your
hand-read rows there. The real file is never published, because transcribed rows
are plaintext health values.

    cp scripts/manual_extracts.example.py scripts/manual_extracts.py

Hand-read rows run through the SAME matching / reference-parsing / unit-normalisation
functions the automatic parser uses, so a hand-read report is treated identically
to a parsed one, and is flagged source_method="manual-ocr" in the review CSV.

Keyed by path RELATIVE TO HEALTH_ROOT (same key as reports_manifest paths).
Each row: (raw_name, value, unit, ref_text, page)
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from biomarkers import match_biomarker, BY_ID, RATIO_IDS
from parse import parse_ref
from units import normalize

# Example (commented): one scanned report, a couple of hand-read rows.
# _EXAMPLE_2022 = [
#     ("Haemoglobin", 13.5, "g/dl", "13 - 17",   1),
#     ("HBA1C",       5.4,  "%",    "4.0 - 5.6", 2),
# ]

MANUAL = {
    # r"Alex\2022-09-26_scanned.pdf": _EXAMPLE_2022,
}


def manual_extract(relpath):
    """Return observations for a manually transcribed report, in the exact shape
    parse.extract() produces, so extract_all.py can consume it unchanged."""
    rows = MANUAL.get(relpath)
    if not rows:
        return []
    out = {}
    for name, value, unit, ref_text, page in rows:
        bid = match_biomarker(name)
        if not bid:
            print(f"  [manual] no biomarker match for {name!r} — skipped")
            continue
        low, high, reftext = parse_ref(ref_text)
        is_ratio = bid in RATIO_IDS
        if is_ratio and not unit:
            unit = "ratio"
        value_n, unit_n, converted, conv_note = normalize(bid, float(value), unit)
        rec = dict(
            biomarker=bid, display=BY_ID[bid]["display"], panel=BY_ID[bid]["panel"],
            raw_name=name, value=value_n, raw_value=float(value),
            unit=unit_n or unit, raw_unit=unit,
            ref_low=low, ref_high=high, ref_text=reftext,
            converted=converted, conv_note=conv_note,
            page=page, row_text=f"[manual-ocr] {name}  {value} {unit}  ({ref_text})",
        )
        out[bid] = rec
    return list(out.values())


if __name__ == "__main__":
    for rp in MANUAL:
        obs = manual_extract(rp)
        print(f"{rp}: {len(obs)} observations")
