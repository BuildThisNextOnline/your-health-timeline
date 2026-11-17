"""
Canonical biomarker catalog + name matching.

Design notes (following the Build This Next essays' cautions):
- We organise data around the PERSON and the BIOMARKER, not the report.
- We prefer the laboratory's OWN reference interval (extracted from the report).
  The `ref_adult` here is only a *fallback display hint* for common adult ranges,
  used when a report omits its range. It is clearly labelled as a general hint and
  is never presented as a personalised clinical range.
- Unit normalisation is applied ONLY where it is a safe arithmetic conversion
  (see units.py). Where comparability is uncertain we keep the original and flag it.
"""

# panel -> display label and ordering
PANELS = {
    "lipid":        "Lipid profile",
    "glucose":      "Blood sugar",
    "thyroid":      "Thyroid",
    "vitamins":     "Vitamins",
    "liver":        "Liver function",
    "kidney":       "Kidney function",
    "cbc":          "Complete blood count",
    "minerals":     "Minerals & electrolytes",
    "inflammation": "Inflammation",
    "iron":         "Iron studies",
    "coag":         "Coagulation",
    "cardiac":      "Cardiac / advanced",
    "cancer":       "Cancer markers",
    "allergy":      "Allergy",
    "urine":        "Urine",
    "body":         "Body composition",
    "other":        "Other",
}
PANEL_ORDER = ["lipid","glucose","thyroid","vitamins","liver","kidney","cbc",
               "minerals","inflammation","iron","coag","cardiac","cancer",
               "allergy","urine","body","other"]

# Each biomarker:
#   id, display, panel, unit (canonical/default), aliases (lowercased substrings),
#   ref_adult (fallback hint: (low, high) or None), higher_is (good/bad/neutral),
#   priority (higher = match first for ambiguous names)
def B(id, display, panel, unit, aliases, ref_adult=None, higher_is="neutral", priority=0):
    return dict(id=id, display=display, panel=panel, unit=unit, aliases=aliases,
                ref_adult=ref_adult, higher_is=higher_is, priority=priority)

CATALOG = [
    # ---- Lipid ----
    B("total_cholesterol","Total Cholesterol","lipid","mg/dL",
      ["total cholesterol","cholesterol total","cholesterol, total","serum cholesterol",
       "cholesterol - total","cholesterol"],
      (125,200),"bad",3),
    B("ldl","LDL Cholesterol","lipid","mg/dL",
      ["ldl cholesterol","ldl - cholesterol","cholesterol ldl","ldl direct","ldl-c","low density lipoprotein"],
      (0,100),"bad",20),
    B("hdl","HDL Cholesterol","lipid","mg/dL",
      ["hdl cholesterol","cholesterol hdl","hdl - cholesterol","hdl-c","high density lipoprotein"],
      (40,60),"good",20),
    B("vldl","VLDL Cholesterol","lipid","mg/dL",
      ["vldl cholesterol","vldl - cholesterol","vldl-c","very low density"],
      (5,40),"bad",20),
    B("triglycerides","Triglycerides","lipid","mg/dL",
      ["triglycerides","triglyceride","tg "],
      (0,150),"bad",10),
    B("non_hdl","Non-HDL Cholesterol","lipid","mg/dL",
      ["non hdl cholesterol","non-hdl cholesterol","non hdl-c","non - hdl","non-hdl"],
      (0,130),"bad",40),
    B("chol_hdl_ratio","Total Cholesterol / HDL Ratio","lipid","ratio",
      ["cholesterol / hdl","chol/hdl","cholesterol hdl ratio","tc/hdl","total cholesterol/hdl","chol / hdl ratio"],
      (0,4.5),"bad",30),
    B("ldl_hdl_ratio","LDL / HDL Ratio","lipid","ratio",
      ["ldl/hdl","ldl / hdl","ldl hdl ratio"],(0,3.5),"bad",30),
    B("apob","Apolipoprotein B (ApoB)","lipid","mg/dL",
      ["apolipoprotein b","apo b","apob","apo-b"],(0,90),"bad",30),
    B("lpa","Lipoprotein(a) / Lp(a)","lipid","mg/dL",
      ["lipoprotein (a)","lipoprotein(a)","lp(a)","lp (a)"],(0,30),"bad",30),

    # ---- Glucose ----
    B("glucose_fasting","Glucose (Fasting)","glucose","mg/dL",
      ["glucose fasting","fasting glucose","fasting blood sugar","glucose - fasting","fbs","blood sugar fasting","glucose, fasting"],
      (70,100),"bad",20),
    B("glucose_pp","Glucose (Post-Prandial)","glucose","mg/dL",
      ["glucose postprandial","post prandial","postprandial glucose","glucose pp","ppbs","glucose - postprandial","post-prandial","glucose, post prandial","2 hour"],
      (0,140),"bad",20),
    B("glucose_random","Glucose (Random)","glucose","mg/dL",
      ["random glucose","glucose random","random blood sugar","rbs"],(0,140),"bad",10),
    B("hba1c","HbA1c (Glycated Haemoglobin)","glucose","%",
      ["hba1c","glycated haemoglobin","glycated hemoglobin","glycosylated","a1c","hb a1c"],
      (0,5.7),"bad",30),
    B("eag","Estimated Average Glucose (eAG)","glucose","mg/dL",
      ["estimated average glucose","eag","average blood glucose"],(0,126),"bad",30),
    B("insulin_fasting","Insulin (Fasting)","glucose","uIU/mL",
      ["fasting insulin","insulin fasting","insulin, fasting"],(2,20),"bad",25),

    # ---- Thyroid ----
    B("tsh","TSH","thyroid","uIU/mL",
      ["tsh","thyroid stimulating hormone","thyroid-stimulating"],(0.4,4.0),"neutral",20),
    B("t3_total","T3 (Total)","thyroid","ng/dL",
      ["total t3","t3 total","triiodothyronine","t3,total","total triiodothyronine"],(80,200),"neutral",15),
    B("t4_total","T4 (Total)","thyroid","ug/dL",
      ["total t4","t4 total","thyroxine total","thyroxine - total","total thyroxine","t4,total"],(5,12),"neutral",15),
    B("ft3","Free T3 (FT3)","thyroid","pg/mL",
      ["free t3","ft3","free triiodothyronine"],(2.0,4.4),"neutral",25),
    B("ft4","Free T4 (FT4)","thyroid","ng/dL",
      ["free t4","ft4","free thyroxine"],(0.8,1.8),"neutral",25),

    # ---- Vitamins ----
    B("vitamin_d","Vitamin D (25-OH)","vitamins","ng/mL",
      ["vitamin d","25-hydroxy","25 hydroxy","25-oh","vit d","vitamin d25","vitamin d 25","cholecalciferol","25(oh)"],
      (30,100),"good",20),
    B("vitamin_b12","Vitamin B12","vitamins","pg/mL",
      ["vitamin b12","b12","cyanocobalamin","cobalamin","vit b12","vitamin b 12"],
      (211,911),"good",20),
    B("folate","Folate / Folic Acid","vitamins","ng/mL",
      ["folate","folic acid"],(3,17),"good",20),

    # ---- Liver ----
    B("alt","ALT (SGPT)","liver","U/L",
      ["alanine transaminase","alt","sgpt","alanine aminotransferase","alt/sgpt","alt (sgpt)","sgpt(alt)"],
      (0,50),"bad",20),
    B("ast","AST (SGOT)","liver","U/L",
      ["aspartate transaminase","ast","sgot","aspartate aminotransferase","ast/sgot","ast (sgot)","sgot(ast)"],
      (0,50),"bad",20),
    B("alp","ALP (Alkaline Phosphatase)","liver","U/L",
      ["alkaline phosphatase","alp"],(30,120),"bad",15),
    B("ggt","GGT (Gamma GT)","liver","U/L",
      ["gamma glutamyl","ggt","gamma gt","g.g.t"],(0,55),"bad",20),
    B("bilirubin_total","Bilirubin (Total)","liver","mg/dL",
      ["bilirubin total","total bilirubin","bilirubin - total","bilirubin,total"],(0,1.2),"bad",20),
    B("bilirubin_direct","Bilirubin (Direct)","liver","mg/dL",
      ["bilirubin direct","direct bilirubin","conjugated bilirubin"],(0,0.3),"bad",25),
    B("bilirubin_indirect","Bilirubin (Indirect)","liver","mg/dL",
      ["bilirubin indirect","indirect bilirubin","unconjugated"],(0,1.0),"bad",25),
    B("protein_total","Protein (Total)","liver","g/dL",
      ["total protein","protein total","protein - total","serum protein"],(6.0,8.3),"neutral",15),
    B("albumin","Albumin","liver","g/dL",
      ["albumin"],(3.5,5.2),"neutral",10),
    B("globulin","Globulin","liver","g/dL",
      ["globulin"],(2.0,3.5),"neutral",10),
    B("ag_ratio","A/G Ratio","liver","ratio",
      ["a/g ratio","albumin/globulin","a:g ratio","albumin globulin ratio"],(1.0,2.1),"neutral",25),

    # ---- Kidney ----
    B("creatinine","Creatinine","kidney","mg/dL",
      ["creatinine","creatinine serum","serum creatinine"],(0.6,1.3),"bad",15),
    B("urea","Urea","kidney","mg/dL",
      ["urea","blood urea","urea serum"],(15,45),"bad",10),
    B("bun","BUN (Urea Nitrogen)","kidney","mg/dL",
      ["blood urea nitrogen","bun","urea nitrogen"],(7,20),"bad",20),
    B("uric_acid","Uric Acid","kidney","mg/dL",
      ["uric acid"],(3.5,7.2),"bad",15),
    B("egfr","eGFR","kidney","mL/min/1.73m2",
      ["egfr","estimated gfr","gfr"],(90,200),"good",20),
    B("sodium","Sodium (Na)","minerals","mmol/L",
      ["sodium","na+","serum sodium"],(136,145),"neutral",10),
    B("potassium","Potassium (K)","minerals","mmol/L",
      ["potassium","k+","serum potassium"],(3.5,5.1),"neutral",10),
    B("chloride","Chloride (Cl)","minerals","mmol/L",
      ["chloride","cl-","serum chloride"],(98,107),"neutral",10),
    B("calcium","Calcium (Total)","minerals","mg/dL",
      ["calcium total","total calcium","calcium  total","calcium - total","serum calcium","calcium,total"],(8.6,10.3),"neutral",12),
    B("phosphorus","Phosphorus","minerals","mg/dL",
      ["phosphorus","phosphate","phosphorus serum"],(2.5,4.5),"neutral",12),
    B("magnesium","Magnesium","minerals","mg/dL",
      ["magnesium"],(1.7,2.4),"neutral",12),

    # ---- CBC ----
    B("hemoglobin","Haemoglobin","cbc","g/dL",
      ["haemoglobin","hemoglobin","hb ","hgb"],(13,17),"good",10),
    B("rbc","RBC Count","cbc","mill/cu.mm",
      ["rbc count","total rbc","red blood cell","r.b.c","erythrocyte count"],(4.5,5.5),"neutral",10),
    B("wbc","WBC / Total Leucocyte Count","cbc","×10³/µL",
      ["total leucocyte","wbc count","total wbc","leucocyte count","t.l.c","white blood cell","tlc"],(4,11),"neutral",10),
    B("platelets","Platelet Count","cbc","×10³/µL",
      ["platelet count","platelets","plt"],(150,410),"neutral",10),
    B("hematocrit","Haematocrit (PCV)","cbc","%",
      ["haematocrit","hematocrit","pcv","packed cell volume","hct"],(40,50),"neutral",12),
    B("mcv","MCV","cbc","fL",["mcv","mean corpuscular volume"],(80,100),"neutral",15),
    B("mch","MCH","cbc","pg",["mch ","mean corpuscular hemoglobin","mean corpuscular haemoglobin"],(27,32),"neutral",15),
    B("mchc","MCHC","cbc","g/dL",["mchc"],(32,36),"neutral",15),
    B("rdw","RDW","cbc","%",["rdw","red cell distribution"],(11.5,14.5),"neutral",15),
    B("neutrophils","Neutrophils","cbc","%",["neutrophils","neutrophil"],(40,80),"neutral",10),
    B("lymphocytes","Lymphocytes","cbc","%",["lymphocytes","lymphocyte"],(20,40),"neutral",10),
    B("monocytes","Monocytes","cbc","%",["monocytes","monocyte"],(2,10),"neutral",10),
    B("eosinophils","Eosinophils","cbc","%",["eosinophils","eosinophil"],(1,6),"neutral",10),
    B("basophils","Basophils","cbc","%",["basophils","basophil"],(0,2),"neutral",10),

    # ---- Inflammation / iron ----
    B("esr","ESR","inflammation","mm/hr",["esr","erythrocyte sedimentation"],(0,15),"bad",15),
    B("crp","CRP","inflammation","mg/L",["c-reactive protein","c reactive protein","crp"],(0,5),"bad",15),
    B("hscrp","hs-CRP","inflammation","mg/L",["hs-crp","hs crp","high sensitivity crp","hscrp","high-sensitivity c-reactive"],(0,1),"bad",30),
    B("ferritin","Ferritin","iron","ng/mL",["ferritin"],(30,300),"neutral",15),
    B("iron","Iron (Serum)","iron","ug/dL",["serum iron","iron "],(65,175),"neutral",12),
    B("tibc","TIBC","iron","ug/dL",["tibc","total iron binding"],(250,450),"neutral",18),
    B("uibc","UIBC","iron","ug/dL",["uibc","unsaturated iron binding"],(125,345),"neutral",18),

    # ---- Cardiac / cancer / allergy ----
    B("psa","PSA (Total)","cancer","ng/mL",["prostate specific antigen","prostatic specific antigen","psa"],(0,4),"bad",15),
    B("ige","IgE (Serum)","allergy","IU/mL",["immunoglobulin e","ige","ig e"],(0,100),"neutral",15),
    B("homocysteine","Homocysteine","cardiac","umol/L",["homocysteine"],(0,15),"bad",20),

    # ---- Body composition ----
    B("weight","Weight","body","kg",["weight"],None,"neutral",5),
    B("bmi","BMI","body","kg/m2",["bmi","body mass index"],(18.5,25),"neutral",15),
    B("body_fat","Body Fat","body","%",["body fat","fat percentage","body fat percentage","fat %"],(10,20),"bad",20),
    B("muscle_mass","Muscle Mass","body","kg",["muscle mass","skeletal muscle"],None,"good",20),
    B("visceral_fat","Visceral Fat","body","level",["visceral fat"],(1,9),"bad",20),
    B("bmr","BMR","body","kcal",["bmr","basal metabolic"],None,"neutral",15),
]

BY_ID = {b["id"]: b for b in CATALOG}

import re
def _norm(s):
    s = s.lower()
    s = s.replace("–","-").replace("—","-")
    s = re.sub(r"[^a-z0-9/%+.\- ]"," ", s)
    s = re.sub(r"\s+"," ", s).strip()
    return s

RATIO_IDS = {"chol_hdl_ratio","ldl_hdl_ratio","ag_ratio"}

# Pre-sort aliases by (priority desc, length desc) so specific names win.
# Each alias becomes a boundary-anchored regex so it won't match inside a larger
# word (e.g. 'phosphate' must not match inside 'glycerophosphate', 'a1c' must not
# match inside prose words).
_ALIAS_INDEX = []
for b in CATALOG:
    for a in b["aliases"]:
        na = _norm(a)
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(na).replace(r"\ ", r"\s+") + r"(?![a-z0-9])")
        _ALIAS_INDEX.append((b["priority"], len(na), pat, b["id"]))
_ALIAS_INDEX.sort(key=lambda t: (-t[0], -t[1]))

def match_biomarker(name):
    """Return canonical biomarker id for a raw test name, or None.
    Guards: a name containing 'ratio' only matches ratio biomarkers."""
    n = _norm(name)
    if not n:
        return None
    is_ratio = bool(re.search(r"\bratio\b", n))
    for prio, ln, pat, bid in _ALIAS_INDEX:
        if pat.search(n):
            if is_ratio and bid not in RATIO_IDS:
                continue
            if (not is_ratio) and bid in RATIO_IDS:
                continue
            return bid
    return None

if __name__ == "__main__":
    tests = ["LDL CHOLESTEROL","HDL - Cholesterol","Glycated Hemoglobin ( HbA1c ) HPLC",
             "TSH THYROID STIMULATING (TSH) HORMONE","VITAMIN D (25-OH)","Vitamin B12",
             "ALANINE TRANSAMINASE (ALTSGPT)","CALCIUM  TOTAL","Triglycerides","Cholesterol Total",
             "Total Leucocyte Count (TLC)","HbA1c","Serum Creatinine","Uric Acid","Body Fat %"]
    for t in tests:
        print(f"{t:45} -> {match_biomarker(t)}")
    print("Total biomarkers:", len(CATALOG))
