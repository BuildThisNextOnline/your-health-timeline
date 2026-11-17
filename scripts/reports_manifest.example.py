"""
EXAMPLE pipeline config. Copy this to `reports_manifest.py` (which is git-ignored)
and fill in your own people and report paths. The real `reports_manifest.py` is
never published, because it contains full names and source-file paths.

    cp scripts/reports_manifest.example.py scripts/reports_manifest.py

READ-ONLY source root. We never write back there.
Non-medical PII (IDs, bills), imaging (CT/PET/DICOM), and similar are excluded —
only lab/biomarker-bearing reports are listed.
"""
import glob, os

HEALTH_ROOT = r"C:\path\to\your\health-records"

# Full names + sex live here (local only). The published site shows FIRST names
# only; the full name stays inside the encrypted payload, visible after unlock.
PEOPLE = {
    "alex": dict(name="Alex Example", sex="M"),
}

# Each entry: dict(person, date(YYYY-MM-DD), lab, path(relative to HEALTH_ROOT), kind)
# kind: "blood" (lab panel), "body" (body composition / weight)
REPORTS = []

def add(person, date, lab, relpath, kind="blood"):
    REPORTS.append(dict(person=person, date=date, lab=lab, path=relpath, kind=kind))

# One line per report PDF you want extracted:
add("alex", "2024-01-15", "Example Lab", r"Alex\2024-01-15_bloodwork.pdf")

# You can also glob a folder of single-analyte PDFs, e.g.:
# for p in sorted(glob.glob(os.path.join(HEALTH_ROOT, r"Alex\2024-07-01", "*.pdf"))):
#     add("alex", "2024-07-01", "Some Hospital", os.path.relpath(p, HEALTH_ROOT))


def existing_reports():
    out = []
    for r in REPORTS:
        full = os.path.join(HEALTH_ROOT, r["path"])
        r2 = dict(r); r2["full"] = full; r2["exists"] = os.path.isfile(full)
        out.append(r2)
    return out

if __name__ == "__main__":
    for r in existing_reports():
        print(("OK " if r["exists"] else "MISSING "), r["person"], r["date"], "|", os.path.basename(r["path"]))
