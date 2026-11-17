"""
Safe, explicit unit normalisation.

Per the essays' caution: convert units ONLY where it is a well-defined arithmetic
conversion for that specific biomarker. Anything not listed here is left in its
original unit and NOT silently coerced. Each conversion records that it happened.
"""

def _norm_unit(u):
    if not u:
        return ""
    return (u.lower().replace(" ", "").replace("µ", "u").replace("μ", "u")
             .replace("%", "%").strip())

# (biomarker_id, from_unit_norm) -> (canonical_unit, factor)
# value_canonical = value_original * factor
CONVERSIONS = {
    # Vitamin D: nmol/L -> ng/mL  (divide by 2.496)
    ("vitamin_d", "nmol/l"): ("ng/mL", 1/2.496),
    ("vitamin_d", "ng/ml"):  ("ng/mL", 1.0),
    # Vitamin B12: pmol/L -> pg/mL (divide by 0.7378)
    ("vitamin_b12", "pmol/l"): ("pg/mL", 1/0.7378),
    ("vitamin_b12", "pg/ml"):  ("pg/mL", 1.0),
    # Glucose: mmol/L -> mg/dL (x18.0)
    ("glucose_fasting", "mmol/l"): ("mg/dL", 18.0),
    ("glucose_pp", "mmol/l"):      ("mg/dL", 18.0),
    ("glucose_random", "mmol/l"):  ("mg/dL", 18.0),
    # Cholesterol family: mmol/L -> mg/dL (x38.67)
    ("total_cholesterol", "mmol/l"): ("mg/dL", 38.67),
    ("ldl", "mmol/l"): ("mg/dL", 38.67),
    ("hdl", "mmol/l"): ("mg/dL", 38.67),
    ("vldl", "mmol/l"): ("mg/dL", 38.67),
    ("non_hdl", "mmol/l"): ("mg/dL", 38.67),
    # Triglycerides: mmol/L -> mg/dL (x88.57)
    ("triglycerides", "mmol/l"): ("mg/dL", 88.57),
    # Creatinine: umol/L -> mg/dL (/88.42)
    ("creatinine", "umol/l"): ("mg/dL", 1/88.42),
}

# ---- Canonical unit-label cleanup (spelling variants -> one display label) ----
_UNIT_LABELS = {
    "mg/dl":"mg/dL","mg/dl.":"mg/dL",
    "g/dl":"g/dL","gm/dl":"g/dL","gm%":"g/dL","g//dl":"g/dL","gm/dl.":"g/dL",
    "u/l":"U/L","iu/l":"U/L","u/i":"U/L",
    "ng/ml":"ng/mL","ng/dl":"ng/dL","pg/ml":"pg/mL",
    "ug/dl":"µg/dL","µg/dl":"µg/dL","μg/dl":"µg/dL",
    "uiu/ml":"µIU/mL","µiu/ml":"µIU/mL","μiu/ml":"µIU/mL","uiu/l":"µIU/mL",
    "pg":"pg","pq":"pg","fl":"fL","fi":"fL",
    "%":"%","ratio":"ratio","":"",
    "mmol/l":"mmol/L","umol/l":"µmol/L","µmol/l":"µmol/L",
    "mm/hr":"mm/hr","mm/hour":"mm/hr","mm/h":"mm/hr","mm":"mm/hr","mm/1st":"mm/hr",
    "iu/ml":"IU/mL","uiu/ml":"µIU/mL",
    "mg/l":"mg/L","mg/al":"mg/L",
    "kg":"kg","kg/m2":"kg/m²","kcal":"kcal",
}
# counts reported both as absolute and in thousands/millions -> one scale
def _canon_count(bid, value, unit):
    u = unit.lower().replace(" ","")
    if bid in ("platelets","wbc"):
        # target x10^3/µL
        if value is not None and value > 1500:   # absolute count
            value = round(value/1000.0, 2)
        return value, "×10³/µL"
    if bid == "rbc":
        return value, "×10⁶/µL"
    if bid == "egfr":
        return value, "mL/min/1.73m²"
    return None

# plausibility bounds (loose physiological sanity, NOT clinical ranges).
PLAUSIBLE = {
    "hba1c":(3,20),"glucose_fasting":(30,500),"glucose_pp":(40,600),"glucose_random":(40,600),
    "eag":(40,600),"total_cholesterol":(50,500),"ldl":(20,400),"hdl":(10,150),
    "triglycerides":(20,2000),"vldl":(2,120),"non_hdl":(20,450),"vitamin_d":(2,200),
    "vitamin_b12":(50,3000),"folate":(0.3,40),"tsh":(0.01,100),"t3_total":(0.3,400),
    "t4_total":(1,30),"ft3":(0.5,20),"ft4":(0.2,8),"creatinine":(0.1,15),"urea":(5,300),
    "bun":(2,150),"uric_acid":(1,20),"alt":(2,2000),"ast":(2,2000),"alp":(10,1500),
    "ggt":(2,2000),"hemoglobin":(3,22),"platelets":(10,900),"wbc":(1,100),"rbc":(2,8),
    "calcium":(4,16),"phosphorus":(1,10),"sodium":(110,170),"potassium":(2,8),
    "chloride":(80,130),"bilirubin_total":(0.05,30),"bilirubin_direct":(0,20),
    "bilirubin_indirect":(0,20),"albumin":(1,7),"protein_total":(3,12),"ferritin":(1,2000),
    "iron":(5,400),"tibc":(100,700),"uibc":(20,600),"esr":(0,150),"crp":(0,400),
    "hscrp":(0,100),"psa":(0,100),"ige":(0,10000),"apob":(10,250),"lpa":(0,400),
    "hematocrit":(15,65),"mcv":(50,130),"mch":(15,45),"mchc":(25,40),"rdw":(8,30),
    "neutrophils":(10,90),"lymphocytes":(5,70),"monocytes":(0,25),"eosinophils":(0,40),
    "basophils":(0,5),"ldl_hdl_ratio":(0,15),"chol_hdl_ratio":(0,20),"ag_ratio":(0,5),
    "bmi":(10,60),"body_fat":(2,60),"weight":(20,250),
}

def canon_unit(unit):
    if unit is None:
        return ""
    return _UNIT_LABELS.get(unit.lower().replace(" ",""), unit)

def is_unit_like(unit):
    """A plausible measurement unit: has a slash/%/digit, or maps to a known label,
    or is a short token. Rejects prose words like 'consumption' or 'mild'."""
    if unit is None:
        return False
    u = unit.strip()
    if u == "":
        return True
    if u.lower().replace(" ","") in _UNIT_LABELS:
        return True
    if any(c in u for c in "/%^³²") or any(ch.isdigit() for ch in u):
        return True
    # short alpha tokens like 'pg','fl','mm','U','g' are ok; long words are not
    return len(u) <= 4

def canonicalize(bid, value, unit):
    """Return (value, unit, note) with count scaling + unit-label cleanup."""
    note = ""
    cc = _canon_count(bid, value, unit)
    if cc is not None:
        value, unit = cc
        return value, unit, "count-scaled"
    return value, canon_unit(unit), note

def normalize(biomarker_id, value, unit):
    """Return (value_canonical, unit_canonical, converted:bool, note).
    Leaves value/unit unchanged when no safe conversion is defined."""
    if value is None:
        return value, unit, False, ""
    key = (biomarker_id, _norm_unit(unit))
    if key in CONVERSIONS:
        canon_unit, factor = CONVERSIONS[key]
        if factor == 1.0:
            return value, canon_unit, False, ""
        newv = round(value * factor, 3)
        return newv, canon_unit, True, f"converted from {unit} (x{factor:.4g})"
    return value, unit, False, ""
