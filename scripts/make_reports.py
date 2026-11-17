"""
Generate a plain-English written summary per person (Markdown) from the payload.
These are PLAINTEXT and stay local (git-ignored) — they contain health data.
Factual and cautious: describes what the numbers show, frames everything as
something to discuss with a clinician, never diagnoses or prescribes.
"""
import os, sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "data", "payload")
OUT = os.path.join(ROOT, "reports")
os.makedirs(OUT, exist_ok=True)

def fmt(v): return "?" if v is None else (f"{v:g}")

def refstr(x):
    lo, hi = x.get("ref_low"), x.get("ref_high")
    if lo is not None and hi is not None: return f"{fmt(lo)}–{fmt(hi)}"
    if hi is not None: return f"< {fmt(hi)}"
    if lo is not None: return f"> {fmt(lo)}"
    return "—"

def status_word(s):
    return {"normal":"in range","high":"high","low":"low","nolimit":"—","unknown":"—"}.get(s, s)

def report(pid):
    p = json.load(open(os.path.join(SRC, f"{pid}.json"), encoding="utf-8"))
    N = p["narrative"]
    L = []
    L.append(f"# Your Health Timeline — {p['name']}")
    L.append("")
    L.append(f"*Generated {p['generated']} · {p['n_biomarkers']} biomarkers across "
             f"{p['n_reports']} report dates ({p['date_range'][0]} → {p['date_range'][1]}) "
             f"from {len(p['labs'])} laboratories.*")
    L.append("")
    L.append("> **This is not medical advice.** " + p["disclaimer"])
    L.append("")
    if p.get("headline"):
        L.append("## In a nutshell")
        L.append("")
        L.append(p["headline"])
        L.append("")
    def bullets(title, items, empty):
        L.append(f"## {title}")
        if not items:
            L.append(f"_{empty}_")
        else:
            for it in items:
                L.append(f"- {it['text']}")
        L.append("")
    bullets("Focus areas", N["focus_areas"],
            "Nothing is currently outside its reference range or trending the wrong way.")
    bullets("Improvements over time", N["improvements"],
            "No clear improvements identified yet (needs more than one test for most markers).")
    bullets("Current findings (latest test outside the usual range)", N["findings"],
            "No markers are outside their reference range on the latest test.")
    bullets("Worth raising with a doctor", N["discuss"],
            "Nothing flagged for discussion from these numbers alone.")

    # action-driven "what can help": common actions -> the flagged markers each helps
    acts = p.get("actions") or []
    ctx = p.get("action_context") or []
    L.append("## General things that can help")
    if not acts and not ctx:
        L.append("_No general lifestyle notes apply to the currently flagged markers._")
    else:
        L.append("_General, educational information — not medical advice. Grouped by common "
                 "action; what is right for you is a conversation for your doctor._")
        L.append("")
        for a in acts:
            det = f" ({a['detail']})" if a["detail"] else ""
            helps = ", ".join(m["display"] for m in a["markers"])
            L.append(f"- **{a['label']}**{det} — may help: {helps}.")
        for c in ctx:
            if c["text"]:
                L.append(f"- **{c['display']}** — {c['text']}.")
    L.append("")

    # per-panel detail
    L.append("## All markers by panel")
    L.append("")
    for panel in p["panels"]:
        items = [b for b in p["biomarkers"] if b["panel"] == panel["id"]]
        if not items: continue
        L.append(f"### {panel['label']}")
        L.append("")
        L.append("| Marker | Latest | Status | Reference | Trend | Tests |")
        L.append("|---|---|---|---|---|---|")
        for b in items:
            lt = b["latest"]
            trend = {"improved":"improved","improving":"improving","worsened":"worsened",
                     "worsening":"worsening"}.get(b["moved"], "")
            L.append(f"| {b['display']} | {fmt(lt['value'])} {b['unit']} | "
                     f"{status_word(lt['status'])} | {refstr(lt)} {b['unit'] if refstr(lt)!='—' else ''} | "
                     f"{trend} | {b['n']} |")
        L.append("")
    L.append("---")
    L.append("*Each value is traceable to its original report (file name and page) in the "
             "interactive dashboard. Reference ranges come from each report where available; "
             "where a report gave none, a general adult range is used as a hint only.*")
    text = "\n".join(L)
    path = os.path.join(OUT, f"{p['name'].replace(' ','_')}_health_summary.md")
    open(path, "w", encoding="utf-8").write(text)
    print(f"{pid:7} -> {os.path.relpath(path, ROOT)}  ({len(text)} chars)")

if __name__ == "__main__":
    for pid in ("kamal", "seema", "mugdha"):
        report(pid)
