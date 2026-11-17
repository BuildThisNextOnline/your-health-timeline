"""
General, non-prescriptive "levers" for markers that are commonly influenced by
everyday factors. These are EDUCATIONAL and GENERAL — not medical advice, not a
diagnosis, not a treatment or supplement recommendation. Every surface that shows
them pairs them with a "discuss with your doctor" caveat.

Design rule (matching the project's cautious stance):
- Only include a marker here when a genuinely uncontroversial, general lifestyle
  association exists. Markers that need clinical interpretation (electrolytes,
  liver enzymes, thyroid, differential %, bilirubin, PSA, creatinine, etc.) are
  deliberately omitted — no lever is honest-er than a forced one.
- Never name doses, supplements-as-prescription, drugs, or "you should".
"""

LEVERS = {
    # ---- Lipids ----
    "total_cholesterol": "commonly influenced by diet (saturated fat, refined carbs), physical activity and weight",
    "ldl":               "commonly influenced by diet (saturated fat), dietary fibre, physical activity and weight",
    "non_hdl":           "tracks overall lipids — commonly influenced by diet, physical activity and weight",
    "hdl":               "tends to respond to regular physical activity, not smoking, and healthy fats",
    "vldl":              "moves with triglycerides — commonly influenced by refined carbs, sugar, alcohol and activity",
    "triglycerides":     "commonly influenced by refined carbs, sugar, alcohol, physical activity and weight",
    "chol_hdl_ratio":    "improves as overall cholesterol balance improves — diet, activity and weight",
    "ldl_hdl_ratio":     "improves as overall cholesterol balance improves — diet, activity and weight",
    # ---- Blood sugar ----
    "glucose_fasting":   "commonly influenced by diet (refined carbs, sugar), physical activity and weight",
    "glucose_pp":        "commonly influenced by meal composition, portion size and activity after meals",
    "glucose_random":    "commonly influenced by diet, physical activity and weight",
    "hba1c":             "reflects longer-term blood sugar — commonly influenced by diet, activity and weight",
    "eag":               "reflects longer-term blood sugar — commonly influenced by diet, activity and weight",
    # ---- Uric acid ----
    "uric_acid":         "commonly influenced by diet (red meat, seafood, alcohol, sugary drinks) and hydration",
    # ---- Iron family ----
    "iron":              "commonly influenced by dietary iron, absorption (vitamin C helps; tea/coffee with meals hinders) and blood loss",
    "ferritin":          "iron stores — relate to dietary iron, absorption and blood loss",
    "tibc":              "a raised iron-binding capacity often accompanies low iron stores — relates to dietary iron and absorption",
    "hemoglobin":        "low haemoglobin often relates to iron or other nutritional factors",
    "hematocrit":        "a low packed cell volume often tracks with low haemoglobin and iron status",
    # ---- Vitamins ----
    "vitamin_d":         "relates to sunlight exposure and diet; supplementation is common but best confirmed with your doctor",
    "vitamin_b12":       "relates to diet (mainly in animal foods, so often lower on vegetarian/vegan diets) and absorption",
    "folate":            "relates to diet (leafy greens, legumes, fortified foods) and absorption",
    # ---- Inflammation (non-specific caveat, not a lifestyle lever) ----
    "esr":               "a non-specific inflammation marker that can rise with infection or many other conditions; interpret with clinical context",
    "crp":               "a non-specific inflammation marker that can rise with infection or many other conditions; interpret with clinical context",
    "hscrp":             "a non-specific inflammation marker; interpret with clinical context",
    # ---- Body composition ----
    "bmi":               "relates to overall diet and physical activity",
    "body_fat":          "relates to overall diet and physical activity",
    "visceral_fat":      "relates to overall diet and physical activity",
    "weight":            "relates to overall diet and physical activity",
}


def lever_for(bid):
    """Return the general lever phrase for a biomarker id, or None."""
    return LEVERS.get(bid)


# ---------------------------------------------------------------------------
# Action-driven view: instead of repeating "diet / activity / weight" under
# every lipid and glucose marker, group by the COMMON ACTION and list which
# markers it is commonly associated with. Still general & non-prescriptive.
# Each action: id, label, detail (short, optional), markers (biomarker ids it
# is commonly associated with). Order here = rough priority if counts tie.
# ---------------------------------------------------------------------------
ACTIONS = [
    dict(id="diet", label="A balanced diet",
         detail="lower in saturated fat, refined carbs and sugar; higher in fibre, vegetables and whole foods",
         markers=["total_cholesterol", "ldl", "non_hdl", "vldl", "triglycerides",
                  "chol_hdl_ratio", "ldl_hdl_ratio", "hba1c", "glucose_fasting",
                  "glucose_pp", "glucose_random", "eag"]),
    dict(id="activity", label="Regular physical activity",
         detail="most days of the week",
         markers=["hdl", "ldl", "non_hdl", "triglycerides", "chol_hdl_ratio",
                  "ldl_hdl_ratio", "hba1c", "glucose_fasting", "glucose_pp", "eag",
                  "bmi", "body_fat", "visceral_fat", "weight"]),
    dict(id="weight", label="Weight management",
         detail="where relevant",
         markers=["triglycerides", "vldl", "hdl", "ldl", "non_hdl", "hba1c",
                  "glucose_fasting", "uric_acid", "bmi", "body_fat", "visceral_fat", "weight"]),
    dict(id="alcohol", label="Limiting alcohol and sugary drinks",
         detail="",
         markers=["triglycerides", "vldl", "uric_acid", "hba1c", "glucose_fasting"]),
    dict(id="iron_intake", label="Dietary iron and absorption",
         detail="iron-rich foods with vitamin C; tea/coffee with meals hinders absorption",
         markers=["iron", "ferritin", "tibc", "hemoglobin", "hematocrit"]),
    dict(id="vitd", label="Sunlight and vitamin D",
         detail="sunlight exposure and diet; supplementation is common but best confirmed with your doctor",
         markers=["vitamin_d"]),
    dict(id="b12_folate", label="B12 and folate in the diet",
         detail="animal foods for B12; leafy greens and legumes for folate; absorption also matters",
         markers=["vitamin_b12", "folate"]),
    dict(id="hydration", label="Staying hydrated",
         detail="",
         markers=["uric_acid"]),
]

# Flagged markers that fit no lifestyle action but still carry a short caveat
# (non-specific inflammation markers) are surfaced separately as "context".
CONTEXT_ONLY = {"esr", "crp", "hscrp"}


def actions_for(flagged_ids):
    """Given the set of flagged biomarker ids, return (actions, context):
    - actions: list of {id,label,detail,markers:[id,...]} for actions that touch
      at least one flagged marker, each listing only the flagged markers it helps,
      ordered by how many flagged markers it covers (most first).
    - context: flagged ids that fit no action but have a caveat (e.g. ESR/CRP)."""
    flagged = set(flagged_ids)
    out, covered = [], set()
    for a in ACTIONS:
        helped = [m for m in a["markers"] if m in flagged]
        if helped:
            out.append(dict(id=a["id"], label=a["label"], detail=a["detail"], markers=helped))
            covered.update(helped)
    out.sort(key=lambda a: len(a["markers"]), reverse=True)
    context = [bid for bid in flagged if bid not in covered and (bid in CONTEXT_ONLY or bid in LEVERS)]
    return out, context
