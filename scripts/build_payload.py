"""
Build the per-person payload that the dashboard renders and that the written
summary is generated from. Derives longitudinal views and a cautious, factual
narrative (findings / improvements / focus areas / discuss-with-clinician).

IMPORTANT (per the Build This Next essays): this describes what the numbers show,
never diagnoses or prescribes. Every statement is framed as an observation to
discuss with a clinician. A change in a value is not assumed to have a cause.
"""
import os, sys, json, io, datetime
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(__file__))
from biomarkers import BY_ID, PANELS, PANEL_ORDER
from levers import lever_for, actions_for, LEVERS

ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(ROOT, "data", "structured")
OUT = os.path.join(ROOT, "data", "payload")
os.makedirs(OUT, exist_ok=True)

DISCLAIMER = ("This is a personal view of your own past lab reports, organised over time. "
              "It is not medical advice, a diagnosis, or a treatment recommendation. "
              "Lab values depend on the laboratory, method, units and testing conditions, "
              "so results from different labs are not always directly comparable. "
              "Always discuss your results and any decisions with a qualified clinician.")

def concern(direction, status):
    if status in ("unknown", "nolimit", "normal"):
        return False
    if direction == "bad":
        return status == "high"
    if direction == "good":
        return status == "low"
    return status in ("high", "low")

def pct_change(a, b):
    if a in (None, 0) or b is None:
        return None
    return (b - a) / abs(a) * 100.0

def summarize_biomarker(bid, pts):
    pts = sorted(pts, key=lambda o: o["date"])
    latest, earliest = pts[-1], pts[0]
    meta = BY_ID[bid]
    direction = meta["higher_is"]
    units = sorted(set(o["unit"] for o in pts if o["unit"]))
    comparable = len(units) <= 1
    trend = None
    if len(pts) >= 2 and comparable:
        ch = pct_change(earliest["value"], latest["value"])
        trend = dict(
            from_date=earliest["date"], from_value=earliest["value"],
            to_date=latest["date"], to_value=latest["value"], pct=ch,
        )
    # improved / worsened: judged on how the VALUE moved in the good direction,
    # plus whether it crossed the reference boundary. Using the value (not the
    # distance to a range that can differ between labs) avoids false trends.
    moved = None
    if len(pts) >= 2 and comparable and earliest["value"] and latest["value"] is not None:
        c0, c1 = concern(direction, earliest["status"]), concern(direction, latest["status"])
        delta = latest["value"] - earliest["value"]
        if direction == "good":
            good_change = delta
        elif direction == "bad":
            good_change = -delta
        else:  # neutral: "good" = moving toward the middle of the range
            good_change = 0
        pct = abs(delta) / abs(earliest["value"]) * 100.0
        if c0 and not c1:
            moved = "improved"            # crossed from flagged into range
        elif (not c0) and c1:
            moved = "worsened"            # crossed from in-range to flagged
        elif c1 and good_change > 0 and pct >= 5:
            moved = "improving"           # still flagged but moving the right way
        elif c1 and good_change < 0 and pct >= 5:
            moved = "worsening"           # flagged and moving the wrong way
    return dict(
        biomarker=bid, display=meta["display"], panel=meta["panel"], direction=direction,
        unit=latest["unit"], comparable=comparable, units=units,
        latest=dict(value=latest["value"], date=latest["date"], status=latest["status"],
                    lab=latest["lab"], ref_low=latest["ref_low"], ref_high=latest["ref_high"],
                    ref_text=latest["ref_text"], ref_source=latest["ref_source"]),
        n=len(pts), trend=trend, moved=moved, concern=concern(direction, latest["status"]),
        points=[dict(date=o["date"], value=o["value"], unit=o["unit"], status=o["status"],
                     lab=o["lab"], ref_low=o["ref_low"], ref_high=o["ref_high"],
                     ref_source=o["ref_source"], source_file=o["source_file"],
                     source_page=o["source_page"]) for o in pts],
    )

def fmt(v):
    if v is None: return "?"
    return f"{v:g}"

def severity(s):
    """How far the latest value sits OUTSIDE its reference range, normalised by the
    range width (fallback: the violated bound). 0 for in-range / non-concern.
    Used only for the optional 'sort by severity' view — not a clinical score."""
    if not s["concern"]:
        return 0.0
    L = s["latest"]; v = L["value"]; lo = L["ref_low"]; hi = L["ref_high"]
    if v is None:
        return 0.0
    if L["status"] == "high" and hi is not None:
        width = (hi - lo) if (lo is not None and hi - lo > 0) else (abs(hi) or 1)
        return round((v - hi) / width, 4)
    if L["status"] == "low" and lo is not None:
        width = (hi - lo) if (hi is not None and hi - lo > 0) else (abs(lo) or 1)
        return round((lo - v) / width, 4)
    return 0.0

def annotate(summaries):
    """Attach severity, lever, and priority to each summary (mutates in place).
    priority = out of range AND worsening; if NOTHING is worsening-and-flagged,
    fall back to all out-of-range markers so the 'worth raising' view is never
    empty while real findings exist."""
    worsening_flagged = [s for s in summaries
                         if s["concern"] and s["moved"] in ("worsened", "worsening")]
    use_fallback = (len(worsening_flagged) == 0)
    for s in summaries:
        s["severity"] = severity(s)
        s["lever"] = lever_for(s["biomarker"])
        if use_fallback:
            s["priority"] = bool(s["concern"])
        else:
            s["priority"] = bool(s["concern"] and s["moved"] in ("worsened", "worsening"))

def rngstr(L):
    if L["ref_low"] is not None and L["ref_high"] is not None:
        return f"range {fmt(L['ref_low'])}–{fmt(L['ref_high'])}"
    if L["ref_high"] is not None:
        return f"target < {fmt(L['ref_high'])}"
    if L["ref_low"] is not None:
        return f"target > {fmt(L['ref_low'])}"
    return ""

def mname(s):
    return s["display"]

def build_headline(name, date_range, summaries):
    """A deterministic ~100-150 word plain-language status paragraph, built only
    from the flags already computed. Describes; never diagnoses or prescribes."""
    latest_date = date_range[-1] if date_range else "the latest report"
    n = len(summaries)
    flagged = sorted([s for s in summaries if s["concern"]],
                     key=lambda s: s["severity"], reverse=True)
    improving = [s for s in summaries if s["moved"] in ("improved", "improving")]
    worsening = [s for s in summaries if s["moved"] in ("worsened", "worsening")]
    has_lever = any(s["lever"] for s in flagged)
    parts = []
    # 1. status line
    if flagged:
        top = flagged[:3]
        named = "; ".join(
            f"{mname(s)} {fmt(s['latest']['value'])} {s['unit']}"
            + (f" ({rngstr(s['latest'])})" if rngstr(s['latest']) else "")
            for s in top)
        more = f", plus {len(flagged) - 3} other{'s' if len(flagged) - 3 != 1 else ''}" if len(flagged) > 3 else ""
        parts.append(
            f"As of the most recent report ({latest_date}), {len(flagged)} of {n} tracked "
            f"markers are outside their usual range — most notably {named}{more}.")
    else:
        parts.append(
            f"As of the most recent report ({latest_date}), all {n} tracked markers sit "
            f"within their usual range.")
    # 2. improvements
    if improving:
        names = ", ".join(mname(s) for s in improving[:3])
        extra = f" and {len(improving) - 3} more" if len(improving) > 3 else ""
        parts.append(f"{len(improving)} marker{'s' if len(improving) != 1 else ''} "
                     f"improved over time ({names}{extra}).")
    # 3. worsening
    if worsening:
        names = ", ".join(mname(s) for s in worsening[:3])
        extra = f" and {len(worsening) - 3} more" if len(worsening) > 3 else ""
        parts.append(f"{len(worsening)} {'are' if len(worsening) != 1 else 'is'} trending "
                     f"the wrong way and worth watching ({names}{extra}).")
    # 4. general levers (only if at least one flagged marker has one)
    if has_lever:
        parts.append(
            "Several flagged markers are commonly influenced by everyday factors like diet, "
            "physical activity, sleep and weight; small, sustained changes often help — "
            "though what’s right for you is a conversation for your doctor.")
    # 5. descriptive close
    parts.append("This is a descriptive view of your own past reports, not a diagnosis.")
    return " ".join(parts)

def build_actions(summaries):
    """Action-driven 'what can help': group by common lifestyle actions and list,
    under each, the person's flagged markers it is commonly associated with.
    Returns (actions, context) where context is flagged markers that fit no action
    but carry a caveat (e.g. ESR/CRP)."""
    by_id = {s["biomarker"]: s for s in summaries}
    flagged_ids = [s["biomarker"] for s in summaries if s["concern"]]
    acts, ctx = actions_for(flagged_ids)
    actions = [dict(id=a["id"], label=a["label"], detail=a["detail"],
                    markers=[dict(biomarker=m, display=by_id[m]["display"]) for m in a["markers"]])
               for a in acts]
    context = [dict(biomarker=m, display=by_id[m]["display"], text=LEVERS.get(m, ""))
               for m in ctx]
    return actions, context

def build_narrative(bm_summaries):
    findings, improvements, focus, discuss = [], [], [], []
    for s in bm_summaries:
        L = s["latest"]
        rng = ""
        if L["ref_low"] is not None or L["ref_high"] is not None:
            if L["ref_low"] is not None and L["ref_high"] is not None:
                rng = f" (range {fmt(L['ref_low'])}–{fmt(L['ref_high'])})"
            elif L["ref_high"] is not None:
                rng = f" (target < {fmt(L['ref_high'])})"
            else:
                rng = f" (target > {fmt(L['ref_low'])})"
        label = f"{s['display']}: {fmt(L['value'])} {s['unit']}{rng}, {L['date']}"
        if s["concern"]:
            findings.append(dict(biomarker=s["biomarker"], text=label, status=L["status"]))
        # "Worth raising with a doctor" is now the priority subset: out of range AND
        # worsening (or, if nothing is worsening, all out-of-range markers).
        if s.get("priority"):
            tnote = ""
            if s["moved"] in ("worsened", "worsening") and s["trend"]:
                t = s["trend"]
                tnote = f" and trending the wrong way (from {fmt(t['from_value'])} in {t['from_date'][:4]})"
            discuss.append(dict(biomarker=s["biomarker"],
                                text=f"{s['display']} is outside the reference range on the latest test ({fmt(L['value'])} {s['unit']}{rng}){tnote}."))
        if s["moved"] in ("improved", "improving") and s["trend"]:
            t = s["trend"]
            improvements.append(dict(biomarker=s["biomarker"],
                text=f"{s['display']} moved from {fmt(t['from_value'])} ({t['from_date']}) to {fmt(t['to_value'])} {s['unit']} ({t['to_date']})."))
        if s["moved"] in ("worsened", "worsening") and s["trend"]:
            t = s["trend"]
            focus.append(dict(biomarker=s["biomarker"],
                text=f"{s['display']} moved from {fmt(t['from_value'])} ({t['from_date']}) to {fmt(t['to_value'])} {s['unit']} ({t['to_date']})."))
    # focus = union of concerns + worsening, de-duplicated by biomarker
    focus_ids = {f["biomarker"] for f in focus}
    for f in findings:
        if f["biomarker"] not in focus_ids:
            focus.append(dict(biomarker=f["biomarker"], text=f["text"]))
            focus_ids.add(f["biomarker"])
    return dict(findings=findings, improvements=improvements, focus_areas=focus, discuss=discuss)

def build_person(pid):
    p = json.load(open(os.path.join(SRC, f"{pid}.json"), encoding="utf-8"))
    by_bm = {}
    for o in p["observations"]:
        by_bm.setdefault(o["biomarker"], []).append(o)
    summaries = [summarize_biomarker(bid, pts) for bid, pts in by_bm.items()]
    summaries.sort(key=lambda s: (PANEL_ORDER.index(s["panel"]), s["display"]))
    annotate(summaries)
    narrative = build_narrative(summaries)
    dates = sorted(set(o["date"] for o in p["observations"]))
    labs = sorted(set(o["lab"] for o in p["observations"]))
    headline = build_headline(p["name"], [dates[0], dates[-1]] if dates else [], summaries)
    actions, action_context = build_actions(summaries)
    payload = dict(
        id=pid, name=p["name"], sex=p.get("sex"),
        generated=datetime.date.today().isoformat(),
        n_biomarkers=len(summaries), n_reports=len(dates),
        date_range=[dates[0], dates[-1]] if dates else [],
        dates=dates, labs=labs,
        panels=[dict(id=k, label=PANELS[k]) for k in PANEL_ORDER
                if any(s["panel"] == k for s in summaries)],
        biomarkers=summaries, narrative=narrative, headline=headline,
        actions=actions, action_context=action_context,
        disclaimer=DISCLAIMER,
    )
    with open(os.path.join(OUT, f"{pid}.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{pid:7} {payload['n_biomarkers']:3} biomarkers, {payload['n_reports']} reports {payload['date_range']} "
          f"| findings {len(narrative['findings'])}, improvements {len(narrative['improvements'])}, "
          f"focus {len(narrative['focus_areas'])}")
    return payload

if __name__ == "__main__":
    for pid in ("kamal", "seema", "mugdha"):
        build_person(pid)
