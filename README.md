# Your Health Timeline

**🔗 Live site: <https://buildthisnextonline.github.io/your-health-timeline/>**
Pick your name and unlock with the passphrase you were given — you'll only ever
see your own data.

A private, longitudinal view of lab reports — organised around **each person and
their biomarkers**, not around individual PDFs. Every blood test becomes a new
chapter in one continuous history, so you can see how a marker (LDL, Vitamin D,
HbA1c, TSH…) has moved over years and across different labs.

Inspired by the *Build This Next* essays on turning scattered medical reports into
a usable health history (see `input/BTN_substack/`).

## What it does

- Reads existing lab-report PDFs (**read-only** — the source folder is never touched)
  and extracts each measurement with its **date, value, unit, reference range, lab,
  and a link back to the exact source file and page**.
- Organises everything per biomarker over time, flags values outside their range,
  and surfaces **focus areas, improvements, and things worth discussing with a doctor**.
- Produces two outputs from one dataset:
  1. an **interactive dashboard** (`site/`) with per-marker timelines, and
  2. a **written summary per person** (`reports/*.md`).

## Privacy model (important)

This is designed to be hostable on a **public URL (GitHub Pages)** without exposing
anyone's health data:

- Each person's data is **encrypted with their own passphrase** (PBKDF2-SHA256 →
  AES-GCM-256) *before* it ever reaches the repo.
- The public site contains **only ciphertext** (`site/data/*.enc`) plus a
  names-only `manifest.json`. There is no server — decryption happens entirely in
  the visitor's browser after they type the passphrase.
- Without a person's passphrase, their reports **cannot be read**, even by someone
  who downloads the whole repository. Different people listed on the login screen
  cannot see each other's data.
- The published site and scripts use **first names only** — surnames never leave
  your machine (the full name lives inside the encrypted payload, seen only after
  unlock).
- The **plaintext** data, the written summaries, the **passphrases**, and the
  **pipeline config** (`scripts/reports_manifest.py` and `scripts/manual_extracts.py`,
  which hold full names, source-file paths, and any hand-transcribed values) stay on
  your machine only and are git-ignored (see `.gitignore`). Only the committed
  `*.example.py` templates are public. Share each person's passphrase with them
  privately (not in the repo).

> This is **not** a medical device or medical advice. It reorganises your own past
> reports. Results from different labs/methods/units are not always directly
> comparable. Always discuss results and decisions with a qualified clinician.

## Project layout

```
YourHealthTimeline/
├─ input/BTN_substack/     the essays that inspired the concept
├─ scripts/                the pipeline (read reports → encrypt)
│   ├─ reports_manifest.py  which reports to read, per person   ← edit to add data
│   ├─ biomarkers.py        canonical biomarker catalog + name matching
│   ├─ units.py             unit canonicalisation + plausibility bounds
│   ├─ parse.py / geom.py   geometry-aware PDF table extraction
│   ├─ extract_all.py       → data/structured/*.json
│   ├─ build_payload.py     analytics + narrative → data/payload/*.json
│   ├─ encrypt.mjs          → site/data/*.enc + manifest.json  (+ passphrases)
│   ├─ make_reports.py      → reports/*.md
│   └─ build.py             runs the whole pipeline
├─ site/                   the public app (HTML/CSS/JS, no dependencies)
│   └─ data/               *.enc (encrypted) + manifest.json (names only)
├─ data/                   PLAINTEXT + secrets — git-ignored
└─ reports/                written summaries — git-ignored
```

## Running it

Requirements: Python 3 (with `pymupdf`), Node 18+.

First-time setup — create your local (git-ignored) pipeline config from the
committed examples, then edit them for your own people and report paths:

```bash
cp scripts/reports_manifest.example.py scripts/reports_manifest.py
cp scripts/manual_extracts.example.py scripts/manual_extracts.py
```

Then run the whole pipeline:

```bash
python scripts/build.py
```

Then serve `site/` over http (ES modules need http, not file://):

```bash
python -m http.server 8777 --directory site
```

Open <http://127.0.0.1:8777>, pick a profile, and enter the passphrase from
`data/passphrases.json`.

## Adding a new report (when the next test comes in)

1. Add the PDF to the person's folder in your health-records location.
2. Add one line to `scripts/reports_manifest.py` (person, date, lab, path).
3. Run `python scripts/build.py`. The new values join the existing timelines.

## Adding a new person

1. Create their folder with reports in your records location.
2. Add their reports to `reports_manifest.py` and a name/sex entry in
   `extract_all.py` (`PEOPLE`) and `build_payload.py`.
3. Run the pipeline — a new encrypted profile and passphrase are generated.

## Known limitations

- Extraction is tuned to the lab formats in this dataset (Orange Health, Thyrocare,
  Healthians, Tata 1mg, Sakra, Narayana, Sehgal, Suburban, Ferra). A new lab layout
  may need a tweak; check `data/provenance/review.csv` (what was read) and
  `dropped.csv` (what was skipped and why) after each build.
- Where a report doesn't state a reference range, a general adult range is used as a
  **hint only** (marked as such in the UI and tables).
- A few markers are reported in different units by different labs (e.g. T3). These
  are shown together but flagged as not directly comparable.
- See `DEPLOY.md` for publishing to GitHub Pages.
