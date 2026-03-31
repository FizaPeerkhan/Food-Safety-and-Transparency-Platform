CLAIM_RULES = {
    "no added sugar": {
        "banned_ingredients": ["sugar", "high fructose corn syrup", "invert sugar",
                               "glucose syrup", "dextrose", "fructose", "sucrose",
                               "maltodextrin", "corn syrup", "liquid glucose", "jaggery", "honey"],
        "message": "⚠️ Claims 'No Added Sugar' but contains sugar-based ingredients."
    },
    "no preservatives": {
        "banned_ingredients": ["sodium benzoate", "potassium sorbate", "sodium nitrate",
                               "sulphur dioxide", "bha", "bht", "tbhq", "calcium propionate",
                               "sodium metabisulphite", "ins 211", "ins 202", "benzoate", "sorbate"],
        "message": "⚠️ Claims 'No Preservatives' but contains preservative ingredients."
    },
    "low fat": {
        "banned_ingredients": ["palm oil", "hydrogenated vegetable oil", "vanaspati",
                               "coconut oil", "butter", "cream", "whole milk", "ghee"],
        "message": "⚠️ Claims 'Low Fat' but contains high-fat ingredients."
    },
    "no artificial colours": {
        "banned_ingredients": ["tartrazine", "sunset yellow", "brilliant blue",
                               "allura red", "carmoisine", "erythrosine", "ins 102", "ins 110", "ins 129"],
        "message": "⚠️ Claims 'No Artificial Colours' but contains artificial colour additives."
    },
    "no msg": {
        "banned_ingredients": ["msg", "monosodium glutamate", "flavor enhancer", "e621", "ins 621"],
        "message": "⚠️ Claims 'No MSG' but contains MSG or similar flavor enhancers."
    },
    "gluten free": {
        "banned_ingredients": ["wheat flour", "wheat", "barley", "rye", "malt extract", "maida", "atta"],
        "message": "⚠️ Claims 'Gluten Free' but contains gluten-containing ingredients."
    },
    "sugar free": {
        "banned_ingredients": ["sugar", "high fructose corn syrup", "glucose syrup",
                               "dextrose", "sucrose", "fructose", "invert sugar", "jaggery"],
        "message": "⚠️ Claims 'Sugar Free' but contains sugar or sugar-derived ingredients."
    },
    "natural": {
        "banned_ingredients": ["aspartame", "saccharin", "acesulfame", "sucralose", 
                               "tartrazine", "sodium benzoate", "bha", "bht", "artificial flavor"],
        "message": "⚠️ Claims 'Natural' but contains artificial additives."
    },
    "dairy free": {
        "banned_ingredients": ["milk", "cream", "butter", "ghee", "whey", "casein", "lactose", "milk solids"],
        "message": "⚠️ Claims 'Dairy Free' but contains dairy ingredients."
    },
    "vegan": {
        "banned_ingredients": ["milk", "cream", "butter", "ghee", "whey", "casein", "egg", "honey", "gelatin"],
        "message": "⚠️ Claims 'Vegan' but contains animal-derived ingredients."
    }
}

def verify_claims(claims, ingredients_text):
    """Verify marketing claims against ingredients"""
    ingredients_lower = ingredients_text.lower()
    results = []

    for claim in claims:
        claim_clean = claim.strip().lower()
        matched_rule = None

        for key in CLAIM_RULES:
            if key in claim_clean or claim_clean in key:
                matched_rule = CLAIM_RULES[key]
                break

        if not matched_rule:
            results.append({
                "claim": claim, "status": "Unverified",
                "message": "ℹ️ We don't have a rule to verify this claim yet.",
                "violating_ingredients": []
            })
            continue

        found_violations = []
        for banned in matched_rule["banned_ingredients"]:
            if banned.lower() in ingredients_lower:
                found_violations.append(banned)

        if found_violations:
            results.append({
                "claim": claim, "status": "Misleading",
                "message": matched_rule["message"],
                "violating_ingredients": list(set(found_violations))
            })
        else:
            results.append({
                "claim": claim, "status": "Verified",
                "message": f"✅ '{claim}' - No contradicting ingredients found.",
                "violating_ingredients": []
            })

    statuses = [r["status"] for r in results]
    if "Misleading" in statuses:
        misleading_count = sum(1 for r in results if r["status"] == "Misleading")
        verdict = f"⚠️ {misleading_count} claim(s) appear misleading"
    elif "Unverified" in statuses:
        verdict = "ℹ️ Some claims could not be verified"
    else:
        verdict = "✅ All claims appear consistent with ingredients"

    return {"claims_checked": len(results), "verdict": verdict, "results": results}