from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
# -------------------------------
# Database Connection
# -------------------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        port=330,
        user="root",
        password="r00t",
        database="food_safety"
    )


# -------------------------------
# Helper: Calculate Overall Risk
# -------------------------------
def calculate_overall_risk(risks):
    if not risks:
        return "Unknown"
    levels = []
    for r in risks:
        level = r.get('risk') or r.get('risk_level', '')
        levels.append(level)
    if 'High' in levels:
        return 'High'
    elif 'Moderate' in levels:
        return 'Moderate'
    else:
        return 'Low'


# -------------------------------
# Route 1: Get All Ingredients
# -------------------------------
@app.route('/ingredients', methods=['GET'])
def get_all_ingredients():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM ingredients")
    results = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(results)


# -------------------------------
# Route 2: Disease-Aware Filter
# -------------------------------
@app.route('/disease-aware', methods=['GET'])
def disease_aware():
    condition = request.args.get('condition', '')
    if not condition:
        return jsonify({'error': 'Health condition is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM ingredients WHERE LOWER(caution_group) LIKE LOWER(%s)",
        (f"%{condition}%",)
    )
    results = cursor.fetchall()
    cursor.close()
    db.close()

    return jsonify({
        'condition': condition,
        'ingredients_to_avoid': results
    })


# -------------------------------
# Route 3: Analyze Ingredient Text
# -------------------------------
@app.route('/analyze-ingredients', methods=['POST'])
def analyze_ingredients():
    data = request.get_json()
    ingredients_text = data.get('ingredients_text', '')

    if not ingredients_text:
        return jsonify({'error': 'Ingredients text is required'}), 400

    raw_ingredients = ingredients_text.split(',')
    matched_risks = []
    allergens = []
    health_warnings = []

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)  # FIXED: added buffered=True

    for ing in raw_ingredients:
        ing = ing.strip()
        cursor.execute(
            "SELECT * FROM ingredients WHERE LOWER(ingredient_name) LIKE LOWER(%s)",
            (f"%{ing}%",)
        )
        result = cursor.fetchone()
        if result:
            matched_risks.append(result)
            if result.get('allergen_type'):
                allergens.append(result['allergen_type'])
            if result.get("caution_group") and result.get("risk_level") in ["Moderate", "High"]:
                groups = result["caution_group"].split(";")
                for g in groups:
                    health_warnings.append(g.strip())

    cursor.close()
    db.close()

    overall_risk = calculate_overall_risk(matched_risks)

    if overall_risk == "High":
        risk_badge = "🔴 High Risk"
    elif overall_risk == "Moderate":
        risk_badge = "🟡 Moderate Risk"
    else:
        risk_badge = "🟢 Low Risk"

    return jsonify({
        'ingredient_risks': matched_risks,
        'overall_risk': overall_risk,
        'allergens': list(set(allergens)),
        'health_warnings': list(set(health_warnings)),
        'risk_badge': risk_badge
    })

# -------------------------------
# Route 4: Get Flagged Products
# -------------------------------
@app.route('/flagged', methods=['GET'])
def get_flagged_products():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM flagged_products")
    flagged = cursor.fetchall()
    cursor.close()
    db.close()
    return jsonify(flagged)


# -------------------------------
# Route 5: Submit Flag Report
# -------------------------------
@app.route('/flag', methods=['POST'])
def flag_product():
    data = request.get_json()
    product_name = data.get('product_name')
    brand = data.get('brand')
    reason = data.get('reason')
    description = data.get('description')

    if not product_name or not reason:
        return jsonify({'error': 'Product name and reason are required'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO flagged_products (product_name, brand, reason, description, status)
        VALUES (%s, %s, %s, %s, 'Under Review')
    """, (product_name, brand, reason, description))
    db.commit()
    cursor.close()
    db.close()

    return jsonify({'message': 'Thank you for reporting. Your submission is under review.'})


# -------------------------------
# Route 6: Search Product
# -------------------------------
@app.route('/search', methods=['GET'])
def search_product():
    product_name = request.args.get('name', '')
    if not product_name:
        return jsonify({'error': 'Product name is required'}), 400

    db = get_db()
    cursor = db.cursor(dictionary=True, buffered=True)

    cursor.execute(
        "SELECT * FROM products WHERE LOWER(product_name) LIKE LOWER(%s)",
        (f"%{product_name}%",)
    )
    product = cursor.fetchone()

    if not product:
        cursor.close()
        db.close()
        return jsonify({'error': 'Product not found in local database'}), 404

    ingredients_text = product['ingredients_text']
    raw_ingredients = ingredients_text.split(',')

    highlighted_ingredients = []
    allergens = []
    health_warnings = []

    for ing in raw_ingredients:
        ing = ing.strip()
        cursor.execute(
            "SELECT * FROM ingredients WHERE LOWER(ingredient_name) LIKE LOWER(%s)",
            (f"%{ing}%",)
        )
        result = cursor.fetchone()
        if result:
            highlighted_ingredients.append({
                "ingredient": result["ingredient_name"],
                "risk": result["risk_level"],
                "reason": result["explanation"],
                "caution_for": result["caution_group"]
            })
            if result.get('allergen_type'):
                allergens.append(result['allergen_type'])
            if result.get("caution_group"):
                groups = result["caution_group"].split(";")
                for g in groups:
                    health_warnings.append(g.strip())

    overall_risk = calculate_overall_risk(highlighted_ingredients)

    high_risk = [i for i in highlighted_ingredients if i["risk"] == "High"]
    moderate_risk = [i for i in highlighted_ingredients if i["risk"] == "Moderate"]

    cursor.close()
    db.close()

    return jsonify({
        "product": product,
        "overall_risk": overall_risk,
        "high_risk_ingredients": high_risk,
        "moderate_risk_ingredients": moderate_risk,
        "allergens": list(set(allergens)),
        "health_warnings": list(set(health_warnings))
    })

# -------------------------------
# Claim Verification Dictionary
# -------------------------------
CLAIM_RULES = {
    "no added sugar": {
        "banned_ingredients": ["sugar", "high fructose corn syrup", "invert sugar",
                               "glucose syrup", "dextrose", "fructose", "sucrose",
                               "maltodextrin", "corn syrup", "liquid glucose"],
        "message": "Claims 'No Added Sugar' but contains sugar-based ingredients."
    },
    "no preservatives": {
        "banned_ingredients": ["sodium benzoate", "potassium sorbate", "sodium nitrate",
                               "sulphur dioxide", "bha", "bht", "tbhq",
                               "calcium propionate", "sodium metabisulphite"],
        "message": "Claims 'No Preservatives' but contains preservative ingredients."
    },
    "low fat": {
        "banned_ingredients": ["palm oil", "hydrogenated vegetable oil", "vanaspati",
                               "coconut oil", "butter", "cream", "whole milk"],
        "message": "Claims 'Low Fat' but contains high-fat ingredients."
    },
    "no artificial colours": {
        "banned_ingredients": ["tartrazine", "sunset yellow", "brilliant blue",
                               "allura red", "carmoisine", "erythrosine"],
        "message": "Claims 'No Artificial Colours' but contains artificial colour additives."
    },
    "no msg": {
        "banned_ingredients": ["msg", "monosodium glutamate", "flavor enhancer (msg)", "e621"],
        "message": "Claims 'No MSG' but contains MSG or similar flavor enhancers."
    },
    "gluten free": {
        "banned_ingredients": ["wheat flour", "wheat", "barley", "rye", "malt extract"],
        "message": "Claims 'Gluten Free' but contains gluten-containing ingredients."
    },
    "sugar free": {
        "banned_ingredients": ["sugar", "high fructose corn syrup", "glucose syrup",
                               "dextrose", "sucrose", "fructose", "invert sugar"],
        "message": "Claims 'Sugar Free' but contains sugar or sugar-derived ingredients."
    },
    "natural": {
        "banned_ingredients": ["aspartame", "saccharin", "acesulfame potassium",
                               "sucralose", "tartrazine", "sodium benzoate", "bha", "bht"],
        "message": "Claims 'Natural' but contains artificial additives."
    }
}

# -------------------------------
# Route 7: Verify Marketing Claims
# -------------------------------
@app.route('/verify-claims', methods=['POST'])
def verify_claims():
    data = request.get_json()
    claims = data.get('claims', [])
    ingredients_text = data.get('ingredients_text', '')

    if not claims or not ingredients_text:
        return jsonify({'error': 'Both claims and ingredients_text are required'}), 400

    ingredients_lower = ingredients_text.lower()
    results = []

    for claim in claims:
        claim_clean = claim.strip().lower()
        matched_rule = None
        matched_key = None

        for key in CLAIM_RULES:
            if key in claim_clean or claim_clean in key:
                matched_rule = CLAIM_RULES[key]
                matched_key = key
                break

        if not matched_rule:
            results.append({
                "claim": claim,
                "status": "Unverified",
                "message": "We don't have a rule to verify this claim yet."
            })
            continue

        found_violations = []
        for banned in matched_rule["banned_ingredients"]:
            if banned.lower() in ingredients_lower:
                found_violations.append(banned)

        if found_violations:
            results.append({
                "claim": claim,
                "status": "Misleading",
                "message": matched_rule["message"],
                "violating_ingredients": found_violations
            })
        else:
            results.append({
                "claim": claim,
                "status": "Verified",
                "message": f"No ingredients found that contradict this claim."
            })

    statuses = [r["status"] for r in results]
    if "Misleading" in statuses:
        verdict = "⚠️ One or more claims appear misleading"
    elif "Unverified" in statuses:
        verdict = "Some claims could not be verified"
    else:
        verdict = "✅ All claims appear consistent with ingredients"

    return jsonify({
        "claims_checked": len(results),
        "verdict": verdict,
        "results": results
    })
# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)

