"""
One-command pipeline. Run after adding new reports to scripts/reports_manifest.py:

    python scripts/build.py

Steps:
  1. extract_all.py   read reports (READ-ONLY) -> data/structured/*.json
  2. build_payload.py analytics + narrative    -> data/payload/*.json
  3. encrypt.mjs      encrypt per person        -> site/data/*.enc + manifest
  4. make_reports.py  written summaries         -> reports/*.md

Nothing here ever writes to the source health-records folder.
"""
import os, sys, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

def run(cmd, label):
    print(f"\n=== {label} ===")
    r = subprocess.run(cmd, cwd=HERE)
    if r.returncode != 0:
        print(f"!! {label} failed (exit {r.returncode})"); sys.exit(r.returncode)

run([sys.executable, "extract_all.py"], "1/4 extract")
run([sys.executable, "build_payload.py"], "2/4 analytics + narrative")
run(["node", "encrypt.mjs"], "3/4 encrypt")
run([sys.executable, "make_reports.py"], "4/4 written summaries")
print("\nAll done. Open site/index.html (served over http) and unlock with the "
      "passphrase from data/passphrases.json.")
