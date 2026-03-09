from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
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
    cursor = db.cursor(dictionary=True)

    for ing in raw_ingredients:
        ing = ing.strip()
        cursor.execute(
            "SELECT * FROM ingredients WHERE LOWER(ingredient_name) LIKE LOWER(%s)",
            (f"%{ing}%",)
        )
        result = cursor.fetchone()
        if result:
            matched_risks.append(result)
            if result['allergen_type']:
                allergens.append(result['allergen_type'])
            if result["caution_group"] and result["risk_level"] in ["Moderate", "High"]:
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
            if result["allergen_type"]:
                allergens.append(result["allergen_type"])
            if result["caution_group"]:
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
# Run App
# -------------------------------
if __name__ == '__main__':
    app.run(debug=True)

