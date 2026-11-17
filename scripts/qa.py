"""QA scan: per person+biomarker, print the time series and flag anomalies
(unit drift across dates, values far outside plausible physiological bounds)."""
import os, sys, json, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from biomarkers import BY_ID

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "structured")

# very loose physiological sanity bounds per biomarker (not clinical ranges)
PLAUSIBLE = {
    "hba1c":(3,20),"glucose_fasting":(30,500),"glucose_pp":(30,600),"glucose_random":(30,600),
    "total_cholesterol":(50,500),"ldl":(20,400),"hdl":(10,150),"triglycerides":(20,2000),
    "vldl":(2,120),"non_hdl":(20,450),"vitamin_d":(2,150),"vitamin_b12":(50,2000),
    "tsh":(0.01,100),"creatinine":(0.1,15),"urea":(5,300),"bun":(2,150),"uric_acid":(1,20),
    "alt":(2,2000),"ast":(2,2000),"alp":(10,1500),"ggt":(2,2000),"hemoglobin":(3,22),
    "platelets":(10,900),"wbc":(500,80000),"calcium":(4,16),"vitamin_b12_":(0,0),
    "bilirubin_total":(0.1,30),"folate":(0.5,40),
}

anom = 0
for pid in ("kamal","seema","mugdha"):
    p = json.load(open(os.path.join(OUT, f"{pid}.json"), encoding="utf-8"))
    print(f"\n================= {p['name']} ({p['n_observations']} obs, {p['n_biomarkers']} biomarkers) =================")
    series = {}
    for o in p["observations"]:
        series.setdefault(o["biomarker"], []).append(o)
    for bid in sorted(series, key=lambda b:(BY_ID[b]['panel'], b)):
        pts = sorted(series[bid], key=lambda o:o["date"])
        units = set((o["unit"] or "").lower() for o in pts)
        flags = []
        if len(units) > 1:
            flags.append(f"UNIT-DRIFT {units}")
        lo, hi = PLAUSIBLE.get(bid, (None,None))
        for o in pts:
            if lo is not None and o["value"] is not None and not (lo <= o["value"] <= hi):
                flags.append(f"IMPLAUSIBLE {o['value']} on {o['date']}")
        vals = " ".join(f"{o['date'][2:].replace('-','')}:{o['value']}{('['+o['unit']+']') if False else ''}" for o in pts)
        mark = "  <<< "+" | ".join(flags) if flags else ""
        if flags: anom += 1
        print(f"  {BY_ID[bid]['panel'][:4]:4} {bid:18} [{list(units)[0] if len(units)==1 else '??'}] {vals}{mark}")
print(f"\nAnomalies flagged: {anom}")
